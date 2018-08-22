#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections
from contextlib import redirect_stderr, redirect_stdout

from evmlab import vm as VMUtils

import docker
dockerclient = docker.from_env()

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Config():

    def __init__(self, file = "statetests.ini"):
        """Parses 'statetests.ini'-file, which 
        may contain user-specific configuration
        """

        import configparser, getpass
        config = configparser.ConfigParser()
        config.read(file)
        uname = getpass.getuser()
        if uname not in config.sections():
            uname = "DEFAULT"

        self.random_tests = config[uname]['random_tests']

        # A list of clients-tuples: name , isDocker, path
        self.active_clients = []
        logger.info("lcietn %s" % config[uname]['clients'])
        for c in config[uname]['clients'].split(","):
            key = "{}.binary".format(c)
            if key in config[uname]:
                self.active_clients.append((c , False, config[uname][key]))
            key = "{}.docker_name".format(c)
            if key in config[uname]:
                self.active_clients.append((c , True, config[uname][key]))
        
        self.fork_config = config[uname]['fork_config']

        def resolve(path):
            path = path.strip()
            path = os.path.expanduser(path)
            path = os.path.abspath(path)
            return path

        self.logs_path = resolve(config[uname]['logs_path'])
        # Artefacts are where stuff is stored
        self.artefacts = resolve(config[uname]['artefacts'])
        # temp paths is where we put stuff we don't necessarily save
        self.temp_path  = resolve(config[uname]['tests_path'])

        #here = os.path.dirname(os.path.realpath(__file__))
        self.host_id = "%s-%s-%d" % (uname, time.strftime("%a_%H_%M_%S"), os.getpid())

        self.info()

        os.makedirs(self.testfilesPath(), exist_ok = True)
        os.makedirs(self.logs_path, exist_ok = True)
        os.makedirs(self.artefacts, exist_ok = True)


    def testfilesPath(self):
        return "%s/testfiles/" % self.temp_path

    def clientNames(self):
        return [name for (name,y,z) in self.active_clients]

    def info(self):
        logger.info("Config")
        logger.info("  Active clients:")
        for (name, isDocker, path) in self.active_clients:
            logger.info("\t* {} : {} docker:{}".format(name, path, isDocker) )

        logger.info("  Test generator: native (py)")
     
        logger.info("  Fork config:   %s",self.fork_config)
        logger.info("  Log path:      %s",self.logs_path)
        logger.info("  Artefacts:     %s",self.artefacts)
        logger.info("  Tempfiles:     %s",self.temp_path)
        logger.info("  Test files:    %s",self.testfilesPath())

cfg =Config('statetests.ini')

class StateTest():
    """ This class represents a single statetest, with a single post-tx result: one transaction
    executed on one single fork
    """
    def __init__(self, statetest, counter):
        self.number = None
        self.identifier = "%s-%d" %(cfg.host_id, counter)
        # Replace the top level name 'randomStatetest' with something meaningful (same as filename)        
        statetest['randomStatetest%s' % self.identifier] =statetest.pop('randomStatetest', None) 
        self.statetest = statetest
        self.canon_traces = []
        self.procs = []
        self.traceFiles = []

    def id(self):
        return self.identifier

    def fullfilename(self):
        return os.path.abspath("%s/%s" % (cfg.testfilesPath(),self.filename()))

    def filename(self):
        return "%s-test.json" % self.identifier


    def writeToFile(self):
        # write to unique tmpfile
        logger.info("Writing file %s" % self.fullfilename())
        with open(self.fullfilename(), 'w') as outfile:
            json.dump(self.statetest, outfile)

    def removeFiles(self):
        f = self.fullfilename()
        logger.info("Removing test file %s" % f)
        os.remove(f)

        #delete non-failed traces
        for f in self.traceFiles:
            logger.info("Removing trace file %s" % f)
            os.remove(f)

    def tempTraceLocation(self, client):
        return os.path.abspath("%s/%s-%s.trace.log" % (cfg.logs_path,self.identifier, client))

    def saveTrace(self, client, output, command):
        filename = self.tempTraceLocation(client)
        logging.info("Writing %s full trace to %s" % (self.id(), filename ))
        with open(filename, "w+") as f: 
            f.write("# command\n")
            f.write("# %s\n\n" % command)
            f.write(output)

        self.traceFiles.append(filename)

    def saveArtefacts(self):
        # Save the actual test json
        saveloc = "%s/%s" % (cfg.artefacts, self.filename())
        logger.info("Saving testcase as %s", saveloc)
        os.rename(self.fullfilename() , saveloc)

        for f in self.traceFiles:
            fname = os.path.basename(f)
            newloc = "%s/%s" % (cfg.artefacts,fname)
            logger.info("Saving trace as %s", newloc)
            os.rename(f, newloc)

 
    def addArtefact(self, fname, data):
        fullpath = "%s/%s-%s" % (cfg.artefacts, self.id(), fname)
        logger.info("Saving artefact %s", fullpath)
        with open(fullpath, "w+") as f:
            f.write(data)


def dumpJson(obj, dir = None, prefix = None):
    import tempfile
    fd, temp_path = tempfile.mkstemp(prefix = 'randomtest_', suffix=".json", dir = dir)
    with open(temp_path, 'w') as f :
        json.dump(obj,f)
        logger.info("Saved file to %s" % temp_path)
    os.close(fd)
    return temp_path

    

def generateTests():
    """This method produces json-files, each containing one statetest, with _one_ poststate. 
    It stores each test with a filename that is unique per user and per process, so that two
    paralell executions should not interfere with eachother. 
    
    returns (filename, object) 
    """

    from evmlab.tools.statetests import templates
    from evmlab.tools.statetests import randomtest

    t = templates.new(templates.object_based.TEMPLATE_RandomStateTest)
    test = {}
    counter = 0
    while True: 
        test.update(t)
        test_obj = json.loads(json.dumps(t, cls=randomtest.RandomTestsJsonEncoder))
        s = StateTest(test_obj, counter)
        counter = counter +1
        yield s
        #break

def main():
    # Start all docker daemons that we'll use during the execution
    startDaemons()
    perform_tests(generateTests)


def get_summary(combined_trace, n=20):
    """Returns (up to) n (default 20) preceding steps before the first diff, and the diff-section
    """
    from collections import deque
    buf = deque([],n)
    index = 0
    for index, line in enumerate(combined_trace):
        if line.startswith("[!!]"):
            buf.append("\n---- [ %d steps in total before diff ]-------\n\n" % (index))
            break
        buf.append(line)

    for i in range(index, min(len(combined_trace), index+5 )):
        buf.append(combined_trace[i])

    return list(buf)

def startDaemon(clientname, imagename):


    dockerclient.containers.run(image = imagename, 
        entrypoint="sleep",
        command = ["356d"],
        name=clientname,
        detach=True, 
        remove=True,
        volumes={cfg.testfilesPath():{ 'bind':'/testfiles/', 'mode':"rw"}})

        ##    cmd = ["docker", "run", "--rm", "-t",
        ##          "--name", clientname, 
        ##         "-v", "/tmp/testfiles/:/testfiles/", 
        ##       "--entrypoint","sleep", imagename, "356d"]
        ##  return {'proc':VMUtils.startProc(cmd ), 'cmd': " ".join(cmd), 'output' : 'stdout'}
    logger.info("Started docker daemon %s %s" % (imagename, clientname))

def killDaemon(clientname):
    try:
        c = dockerclient.containers.get(clientname)
        c.kill()
        c.stop()
    except Exception as e:
        pass

 #   VMUtils.finishProc(VMUtils.startProc(["docker", "kill",clientname]))

def startDaemons():
    """ startDaemons starts docker processes for all clients. The actual execution of 
    testcases is then performed via docker exec. Means that executing a specific testcase
    does not require starting a whole new docker context, instead we just reuse the existing
    docker process. 
    The startDaemon basically does this: 

    ```
    docker run ethereum/client-go:alltools-latest sleep 356d    
    ```

    """

    daemons = []
    #Start the processes
    for (client_name, isDocker, cmd) in cfg.active_clients:
        if isDocker:
            logger.info("Starting daemon for %s : %s", client_name, cmd)
            # First, kill off any existing daemons
            killDaemon(client_name)
            procinfo = startDaemon(client_name, cmd)
            daemons.append( (procinfo, client_name ))        
        else:
            logger.warning("Not a docker client %s",client_name)



def execInDocker(name, cmd, stdout = True, stderr=True):
    start_time = time.time()
    stream = False
    #logger.info("executing in %s: %s" %  (name," ".join(cmd)))
    container = dockerclient.containers.get(name)
    (exitcode, output) = container.exec_run(cmd, stream=stream,stdout=stdout, stderr = stderr)     
    logger.info("Executing %s : done in %f seconds" % (name, time.time() - start_time))


    return {'output': [output], 'cmd':" ".join(cmd)}


def startGeth(test):
    """
    With daemonized docker images, we execute basically the following

    docker exec -it ggeth2 evm --json --code "6060" run
    or
    docker exec -it <name> <command>

    """
    cmd = ["evm","--json","--nomemory","statetest","/testfiles/%s" % os.path.basename(test.filename())]
    return execInDocker("geth", cmd, stdout = False)
    

def startParity(test):
    cmd = ["/parity-evm","state-test", "--std-json","/testfiles/%s" % os.path.basename(test.tmpfile)]
    return execInDocker("parity", cmd)

def startHera(test):
    cmd = [ "/build/test/testeth", 
            "-t","GeneralStateTests","--",
            "--vm", "hera",
            "--evmc", "evm2wasm.js=true", "--evmc", "fallback=false",
            "--singletest", "/testfiles/%s" % os.path.basename(test.tmpfile), test.name,
            ]
    return execInDocker("hera", cmd, stderr=False)

def startCpp(test):
    
    #docker exec -it cpp /usr/bin/testeth -t GeneralStateTests -- --singletest /testfiles/0001--randomStatetestmartin-Fri_09_42_57-7812-0-1-test.json randomStatetestmartin-Fri_09_42_57-7812-0   --jsontrace '{ "disableStorage" : false, "disableMemory" : false, "disableStack" : false, "fullStorage" : true }' 
    #docker exec -it cpp /usr/bin/testeth -t GeneralStateTests -- --singletest /testfiles/0015--randomStatetestmartin-Fri_10_15_53-13070-3-3-test.json randomStatetestmartin-Fri_10_15_53-13070-3 --jsontrace '{"disableStack": false, "fullStorage": false, "disableStorage": false, "disableMemory": false}'

    cmd = ["/usr/bin/testeth",
            "-t","GeneralStateTests","--",
            "--singletest", "/testfiles/%s" % os.path.basename(test.tmpfile), test.name,
            "--jsontrace", "'%s'" % json.dumps({"disableStorage": True, "disableMemory": True, "disableStack": False, "fullStorage": False}) 
            ]
    return execInDocker("cpp", cmd, stderr=False)


def start_processes(test):

    starters = {'geth': startGeth, 'cpp': startCpp, 'parity': startParity, 'hera': startHera}

    logger.info("Starting processes for %s on test %s" % ( cfg.clientNames(), test.identifier))
    #Start the processes
    for (client_name, x, y) in cfg.active_clients:
        if client_name in starters.keys():
            procinfo = starters[client_name](test)
            test.procs.append( (procinfo, client_name ))        
        else:
            logger.warning("Undefined client %s", client_name)


canonicalizers = {
    "geth" : VMUtils.GethVM.canonicalized, 
    "cpp"  : VMUtils.CppVM.canonicalized, 
    "py"   : VMUtils.PyVM.canonicalized, 
    "parity"  :  VMUtils.ParityVM.canonicalized ,
    "hera" : VMUtils.HeraVM.canonicalized,
}

def readOutput(processInfo):
    """ Ends the process, returns the canonical trace and also writes the 
    full process output to a file, along with the command used to start the process"""

    outp = ""
    for chunk in processInfo['output']:
        outp = outp + chunk.decode()
    return outp



def end_processes(test):
    # Handle the old processes
    if test is not None:
        for (proc_info, client_name) in test.procs:
            canonicalizer = canonicalizers[client_name]
            full_trace = readOutput(proc_info)
            test.saveTrace(client_name, full_trace,proc_info['cmd'])
            canon_trace = [VMUtils.toText(step) for step in canonicalizer(full_trace.split("\n"))]
            test.canon_traces.append(canon_trace)
            logger.info("Processed %s steps for %s on test %s" % (len(canon_trace), client_name, test.identifier))


def processTraces(test):
    if test is None:
        return True

    # Process previous traces

    (equivalent, trace_output) = VMUtils.compare_traces(test.canon_traces, cfg.clientNames()) 

    if equivalent and False:
        test.removeFiles()
    else:
        logger.warning("CONSENSUS BUG!!!")
        trace_summary = get_summary(trace_output)
        # save the state-test
        test.saveArtefacts()
        # save combined trace and abbreviated trace
        test.addArtefact("combined_trace.log","\n".join(trace_output))
        test.addArtefact("shortened_trace.log","\n".join(trace_summary))

    return equivalent

def perform_tests(test_iterator):
    
    pass_count = 0
    fail_count = 0
    failures = []

    previous_test = None

    start_time = time.time()

    n = 0

    def __end_previous_test():
        nonlocal n, fail_count, pass_count
        global traceFiles

        # End previous procs
        traceFiles = end_processes(previous_test)

        # Process previous traces
        if processTraces(previous_test):
            pass_count = pass_count +1
        else:
            fail_count = fail_count +1

        # Do some reporting

        if n % 10 == 0:
            time_elapsed = time.time() - start_time
            logger.info("Fails: {}, Pass: {}, #test {} speed: {:f} tests/s".format(
                    fail_count, 
                    pass_count, 
                    (fail_count + pass_count),
                    (fail_count + pass_count) / time_elapsed
                ))

    for test in test_iterator():
        n = n+1
        #Prepare the current test
        logger.info("Test id: %s" % test.id())
        test.writeToFile()

        # Start new procs
        start_processes(test)

        __end_previous_test()

        previous_test = test

    __end_previous_test()

    return (n, len(failures), pass_count, failures)

def testSummary():
    """Enable this, and test by passing a trace-output via console"""
    with open(sys.argv[1]) as f:
        print("".join(get_summary(f.readlines())))

if __name__ == '__main__':
#    testSummary()
    main()
