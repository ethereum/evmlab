#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections, shutil
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

        # A list of clients-tuples: name , isDocker, path
        self.active_clients = []
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

        # Artefacts are where stuff is stored
        self.artefacts = resolve(config[uname]['artefacts'])
        # temp paths is where we put stuff we don't necessarily save
        self.temp_path  = resolve(config[uname]['tests_path'])

        #here = os.path.dirname(os.path.realpath(__file__))
        self.host_id = "%s-%s-%d" % (uname, time.strftime("%a_%H_%M_%S"), os.getpid())

        logger.info("\n".join(self.info()))

        os.makedirs(self.artefacts, exist_ok = True)
        os.makedirs(self.testfilesPath(), exist_ok = True)
        os.makedirs(self.logfilesPath(), exist_ok = True)


    def testfilesPath(self):
        return "%s/testfiles/" % self.temp_path

    def logfilesPath(self):
        return "%s/logs/" % self.temp_path

    def clientNames(self):
        return [name for (name,y,z) in self.active_clients]

    def info(self):
        out = []
        out.append("Active clients:")
        for (name, isDocker, path) in self.active_clients:
            out.append("  * {} : {} docker:{}".format(name, path, isDocker) )

        out.append("Test generator: native (py)")
        out.append("Fork config:   %s" % self.fork_config)
        out.append("Artefacts:     %s" % self.artefacts)
        out.append("Tempfiles:     %s" % self.temp_path)
        out.append("Log path:      %s" % self.logfilesPath())
        out.append("Test files:    %s" % self.testfilesPath())
        return out

cfg =Config('statetests.ini')

class RawStateTest():

    def __init__(self, statetest, identifier, filename):
        self.identifier = identifier
        self._filename = filename
        self.statetest = statetest
        self.canon_traces = []
        self.procs = []
        self.traceFiles = []
        self.additionalArtefacts = []

    def filename(self):
        return self._filename

    def id(self):
        return self.identifier


    def fullfilename(self):
        return os.path.abspath("%s/%s" % (cfg.testfilesPath(),self.filename()))

    def writeToFile(self):
        # write to unique tmpfile
        logger.debug("Writing file %s" % self.fullfilename())
        with open(self.fullfilename(), 'w') as outfile:
            json.dump(self.statetest, outfile)

    def removeFiles(self):
        if True:
            return
        f = self.fullfilename()
        logger.debug("Removing test file %s" % f)
        os.remove(f)

        #delete non-failed traces
        for f in self.traceFiles:
            logger.debug("Removing trace file %s" % f)
            os.remove(f)

    def tempTraceFilename(self, client):
        return "%s-%s.trace.log" % (self.identifier, client)

    def tempTraceLocation(self, client):
        return os.path.abspath("%s/%s" % (cfg.logfilesPath(),self.tempTraceFilename(client)))

    def storeTrace(self, client, output, command):
        filename = self.tempTraceLocation(client)
        logging.debug("Writing %s full trace to %s" % (self.id(), filename ))
        with open(filename, "w+") as f: 
            f.write("# command\n")
            f.write("# %s\n\n" % command)
            f.write(output)

        self.traceFiles.append(filename)

    def saveArtefacts(self):
        # Save the actual test json
        saveloc = "%s/%s" % (cfg.artefacts, self.filename())
        logger.info("Saving testcase as %s", saveloc)
        shutil.move(self.fullfilename() , saveloc)

        newTracefiles = []

        for f in self.traceFiles:
            fname = os.path.basename(f)
            newloc = "%s/%s" % (cfg.artefacts,fname)
            logger.info("Saving trace as %s", newloc)
            shutil.move(f, newloc)
            newTracefiles.append(newloc)
    
        self.traceFiles = newTracefiles
 
    def addArtefact(self, fname, data):
        fullpath = "%s/%s-%s" % (cfg.artefacts, self.id(), fname)
        logger.info("Saving artefact %s", fullpath)
        with open(fullpath, "w+") as f:
            f.write(data)    
        self.additionalArtefacts.append(fullpath)

    def listArtefacts(self):
        return {
            "id"   : self.id(),
            "file" : self.filename(), 
            "traces": [os.path.basename(f) for f in self.traceFiles],
            "other" : [os.path.basename(f) for f in self.additionalArtefacts], 
        }

class StateTest(RawStateTest):
    """ This class represents a single statetest, with a single post-tx result: one transaction
    executed on one single fork
    """

    def __init__(self, statetest, counter, overwriteFork=True):
        self.number = None
        identifier = "%s-%d" %(cfg.host_id, counter)
        filename =  "%s-test.json" % identifier
        super().__init__(statetest, identifier, filename)


        if overwriteFork and "Byzantium" in statetest['randomStatetest']['post'].keys():
            # Replace the fork with what we are currently configured for
            postState = statetest['randomStatetest']['post'].pop('Byzantium')
            statetest['randomStatetest']['post'][cfg.fork_config] = postState 


        # Replace the top level name 'randomStatetest' with something meaningful (same as filename)        
        statetest['randomStatetest%s' % self.identifier] =statetest.pop('randomStatetest', None) 

        self.statetest = statetest
        self.canon_traces = []
        self.procs = []
        self.traceFiles = []
        self.additionalArtefacts = []


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
        volumes={
            cfg.testfilesPath():{ 'bind':'/testfiles/', 'mode':"rw"},
            cfg.logfilesPath():{ 'bind':'/logs/', 'mode':"rw"},
            })

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
    
    # For now, we need to disable stream, since otherwise the stderr and stdout 
    # gets mixed, which causes false positives. 
    # This really is a bottleneck, since it means all execution will be serial instead
    # of paralell, and makes it really slow. The fix is either to fix the python docker
    # api, or make sure that parity also prints the stateroot on stderr, which currently
    # can only be read from stdout. 

    # Update, now using stream again, with 1>&2 (piping stdout into stderr)
    stream = True
    #logger.info("executing in %s: %s" %  (name," ".join(cmd)))
    container = dockerclient.containers.get(name)
    (exitcode, output) = container.exec_run(cmd, stream=stream,stdout=stdout, stderr = stderr)     
    

    # If stream is False, then docker soups up the output, and we just decode it once
    # when the caller wants it
    if not stream:
        return {
                'output': lambda: output.decode(), 
                'cmd':" ".join(cmd)
                }
    
    # If the stream is True, then we need to iterate over output, and decode each
    # chunk
    return {
         'output': lambda: "".join([chunk.decode() for chunk in output]), 
         'cmd':" ".join(cmd)
         }

def shWrap(cmd, output):
    """ Wraps a command in /bin/sh, with output to the given file"""
    return ["/bin/sh","-c"," ".join(cmd) + " &> /logs/%s" % output]


def startGeth(test):
    """
    With daemonized docker images, we execute basically the following

    docker exec -it ggeth2 evm --json --code "6060" run
    or
    docker exec -it <name> <command>

    """
    cmd = ["evm","--json","--nomemory","statetest","/testfiles/%s" % os.path.basename(test.filename())]
    cmd = shWrap(cmd, test.tempTraceFilename('geth'))
    return execInDocker("geth", cmd, stdout = False)


def startParity(test):
    cmd = ["/parity-evm","state-test", "--std-json","/testfiles/%s" % os.path.basename(test.filename())]
    #cmd = ["/bin/sh","-c","/parity-evm state-test --std-json /testfiles/%s 1>&2" % os.path.basename(test.filename())]
    cmd = shWrap(cmd,test.tempTraceFilename('parity'))
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

    logger.info("Starting processes for %s on test %s" % ( cfg.clientNames(), test.id()))
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



def end_processes(test):
    """ End processes for the given test, slurp up the output and compare the traces
    returns the length of the canon-trace emitted (or -1)
    """
    # Handle the old processes
    if test is None: 
        return None
    tracelen = 0
    canon_steps = None
    canon_trace = []
    for (proc_info, client_name) in test.procs:
        t0 = time.time()
        full_trace = proc_info["output"]()
        t1 = time.time()
        #logger.info("Wait for %s took in %.02f milliseconds" % (client_name, 1000 * (t1 - t0)))
        #test.storeTrace(client_name, full_trace,proc_info['cmd'])
        canonicalizer = canonicalizers[client_name]
        canon_steps = []
        with open(test.tempTraceLocation(client_name)) as output:
            canon_step_generator = canonicalizer(output)
            canon_trace = [VMUtils.toText(step) for step in canon_step_generator]
        test.canon_traces.append(canon_trace)
        tracelen = len(canon_trace)
        t2 = time.time()
        logger.info("Processed %s steps for %s on test %s, wtime: %.02f ms, pTime:%.02f ms" 
            % (tracelen, client_name, test.identifier, 1000 * (t1 - t0), 1000 * (t2 - t1)))


    stats = VMUtils.traceStats(canon_steps)
    #print(stats)
    #print(canon_steps)
    #print("\n".join(canon_trace))
    return (tracelen, stats)

def processTraces(test, forceSave=False):
    if test is None:
        return None

    # Process previous traces

    (equivalent, trace_output) = VMUtils.compare_traces(test.canon_traces, cfg.clientNames()) 

    if equivalent and not forceSave:
        test.removeFiles()
        return None
    
    if not equivalent:
        logger.warning("CONSENSUS BUG!!!")

    trace_summary = get_summary(trace_output)
    # save the state-test
    test.saveArtefacts()
    # save combined trace and abbreviated trace
    test.addArtefact("combined_trace.log","\n".join(trace_output))
    test.addArtefact("shortened_trace.log","\n".join(trace_summary))

    return test

class TestExecutor():

    def __init__(self):
        self.pass_count = 0
        self.fail_count = 0
        self.failures = []
        self.traceLengths = collections.deque([],100)
        self.traceDepths = collections.deque([], 100)
        self.traceConstantinopleOps = collections.deque([], 100)
        self.start_time = time.time()

    def postprocess_test(self, test, reporting=False):
        # End previous procs
        print("posprocessing")
        if test is None:
            return
        data = end_processes(test)
        if data is not None:
            (traceLength, stats) = data
            self.traceLengths.append(traceLength)
            self.traceDepths.append(stats['maxDepth'])
            self.traceConstantinopleOps.append(stats['constatinopleOps'])

        # Process previous traces
        failingTestcase = processTraces(test, forceSave = False)
        if failingTestcase is None:
            self.pass_count = self.pass_count +1
        else:
            self.fail_count = self.fail_count +1
            self.failures.append(failingTestcase.listArtefacts())

        if reporting:
        # Do some reporting
            time_elapsed = time.time() - self.start_time
            logger.info("Fails: {}, Pass: {}, #test {} speed: {:f} tests/s".format(
                    self.fail_count, 
                    self.pass_count, 
                    (self.fail_count + self.pass_count),
                    (self.fail_count + self.pass_count) / time_elapsed
                ))



    def startFuzzing(self):   
        previous_test = None
        self.start_time = time.time()
        n = 0
        running_tests = []
        MAX_PARALELL = 5
        for test in generateTests():
            n = n+1
            #Prepare the current test
            #logger.info("Test id: %s" % test.id())
            test.writeToFile()
            # Start new procs
            start_processes(test)
            # Put the new test to the first position
            running_tests.insert(0, test)
            
            if len(running_tests) >= MAX_PARALELL:
                self.postprocess_test(running_tests.pop(), n % 10)
    
            #input("Press Enter to continue...")

        while len(running_tests) > 0:
            self.postprocess_test(running_tests.pop(), len(running_tests) == 0)
        
        return (n, len(self.fail_count), pass_count, self.failures)

    def status(self):
        import collections, statistics
        from datetime import datetime
        return {
            "starttime" : datetime.utcfromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S'),
            "pass" : self.pass_count, 
            "fail" : self.fail_count,
            "failures" : self.failures,
            "speed" : (self.fail_count + self.pass_count) / (time.time() - self.start_time),
            "mean" : statistics.mean(self.traceLengths) if self.traceLengths else "NA",
            "stdev" : statistics.stdev(self.traceLengths) if len(self.traceLengths) >2 else "NA",
            "numZero" : self.traceLengths.count(0) if self.traceLengths else "NA" ,
            "max" : max(self.traceLengths) if self.traceLengths else "NA",
            "maxDepth" : max(self.traceDepths) if self.traceDepths else "NA",
            "numConst" : statistics.mean(self.traceConstantinopleOps) if self.traceConstantinopleOps else "NA",
        }

def testSummary():
    """Enable this, and test by passing a trace-output via console"""
    with open(sys.argv[1]) as f:
        print("".join(get_summary(f.readlines())))

def main():
    # Start all docker daemons that we'll use during the execution
    startDaemons()

    TestExecutor().startFuzzing()


def testSpeedGenerateTests():
    """This method produces json-files, each containing one statetest, with _one_ poststate. 
    It stores each test with a filename that is unique per user and per process, so that two
    paralell executions should not interfere with eachother. 
    
    returns (filename, object) 
    """

    from evmlab.tools.statetests import templates
    from evmlab.tools.statetests import randomtest
    import time
    t = templates.new(templates.object_based.TEMPLATE_RandomStateTest)
    test = {}
    test.update(t)
    counter = 0
    start = time.time()
    while True: 
        x0 = time.time()
        #test.update(t)
        test_obj = json.loads(json.dumps(t, cls=randomtest.RandomTestsJsonEncoder))
        x = str(test_obj)
        print(test_obj["randomStatetest"]["transaction"]["to"])
        x1 = time.time()
        print("%d %f (tot %f/s)" % (counter, x1 - x0, counter / (x1 - start) ))
        counter = counter +1


if __name__ == '__main__':
    main()
