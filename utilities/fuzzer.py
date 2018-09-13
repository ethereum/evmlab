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

class StateTest():
    """ This class represents a single statetest, with a single post-tx result: one transaction
    executed on one single fork
    """
    def __init__(self, statetest, counter):
        self.number = None
        self.identifier = "%s-%d" %(cfg.host_id, counter)

        # Replace the fork with what we are currently configured for
        postState = statetest['randomStatetest']['post']['Byzantium']
        del(statetest['randomStatetest']['post']['Byzantium'])
        statetest['randomStatetest']['post'][cfg.fork_config] = postState 


        # Replace the top level name 'randomStatetest' with something meaningful (same as filename)        
        statetest['randomStatetest%s' % self.identifier] =statetest.pop('randomStatetest', None) 
        self.statetest = statetest
        self.canon_traces = []
        self.procs = []
        self.traceFiles = []
        self.additionalArtefacts = []

    def id(self):
        return self.identifier

    def fullfilename(self):
        return os.path.abspath("%s/%s" % (cfg.testfilesPath(),self.filename()))

    def filename(self):
        return "%s-test.json" % self.identifier


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

    def tempTraceLocation(self, client):
        return os.path.abspath("%s/%s-%s.trace.log" % (cfg.logfilesPath(),self.identifier, client))

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
    stream = True
    #logger.info("executing in %s: %s" %  (name," ".join(cmd)))
    container = dockerclient.containers.get(name)
    (exitcode, output) = container.exec_run(cmd, stream=stream,stdout=stdout, stderr = stderr)     
    logger.info("Executing %s took in %f seconds" % (name, time.time() - start_time))
    

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
    cmd = ["/parity-evm","state-test", "--std-json","/testfiles/%s" % os.path.basename(test.filename())]
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
    for (proc_info, client_name) in test.procs:
        logger.info("Proc '%s'" % client_name)
        full_trace = proc_info["output"]()
        test.storeTrace(client_name, full_trace,proc_info['cmd'])
        canonicalizer = canonicalizers[client_name]
        canon_trace = [VMUtils.toText(step) for step in canonicalizer(full_trace.split("\n"))]
        test.canon_traces.append(canon_trace)
        tracelen = len(canon_trace)
        logger.info("Processed %s steps for %s on test %s" % (tracelen, client_name, test.identifier))
        
    return tracelen

def processTraces(test):
    if test is None:
        return None

    # Process previous traces

    (equivalent, trace_output) = VMUtils.compare_traces(test.canon_traces, cfg.clientNames()) 

    if equivalent:
        test.removeFiles()
        return None
    else:
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
        self.start_time = time.time()


    def startFuzzing(self):   
        previous_test = None
        self.start_time = time.time()
        n = 0

        def __end_previous_test():
            nonlocal n

            # End previous procs
            traceLength = end_processes(previous_test)
            if traceLength is not None:
                self.traceLengths.append(traceLength)

            # Process previous traces
            failingTestcase = processTraces(previous_test)
            if failingTestcase is None:
                self.pass_count = self.pass_count +1
            else:
                self.fail_count = self.fail_count +1
                self.failures.append(failingTestcase.listArtefacts())
 
            # Do some reporting
            if n % 10 == 0:
                time_elapsed = time.time() - self.start_time
                logger.info("Fails: {}, Pass: {}, #test {} speed: {:f} tests/s".format(
                        self.fail_count, 
                        self.pass_count, 
                        (self.fail_count + self.pass_count),
                        (self.fail_count + self.pass_count) / time_elapsed
                    ))

        for test in generateTests():
            n = n+1
            #Prepare the current test
            logger.info("Test id: %s" % test.id())
            test.writeToFile()

            # Start new procs
            start_processes(test)

            __end_previous_test()

            previous_test = test

        __end_previous_test()

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
        }

def testSummary():
    """Enable this, and test by passing a trace-output via console"""
    with open(sys.argv[1]) as f:
        print("".join(get_summary(f.readlines())))

def main():
    # Start all docker daemons that we'll use during the execution
    startDaemons()

    TestExecutor().startFuzzing()


if __name__ == '__main__':
    main()


def testParityInterleavedOutput():
    """ Tests interleaved stdout/stderr, which happens when using Stream=True docker execution
    Expected output:

    {'pc': 0, 'gas': '0x477896', 'op': 91, 'depth': 0, 'stack': []}
    {'pc': 1, 'gas': '0x477895', 'op': 96, 'depth': 0, 'stack': []}
    {'pc': 3, 'gas': '0x477892', 'op': 97, 'depth': 0, 'stack': ['0xd1']}
    {'pc': 6, 'gas': '0x47788f', 'op': 97, 'depth': 0, 'stack': ['0xd1', '0xc09a']}
    {'pc': 9, 'gas': '0x47788c', 'op': 111, 'depth': 0, 'stack': ['0xd1', '0xc09a', '0xa7f6']}
    {'pc': 26, 'gas': '0x477889', 'op': 20, 'depth': 0, 'stack': ['0xd1', '0xc09a', '0xa7f6', '0x948ec1a91609740f44b8d0c74c4785d8']}
    {'pc': 27, 'gas': '0x477886', 'op': 99, 'depth': 0, 'stack': ['0xd1', '0xc09a', '0x0']}
    {'pc': 32, 'gas': '0x477883', 'op': 81, 'depth': 0, 'stack': ['0xd1', '0xc09a', '0x0', '0x4ebfdb04']}
    {'stateRoot': '3b63251e410b65ae32806a89e101b93e81b51096e4c00f6c3b547fe43350f504'}
 
    """   
    data = """# command
# /parity-evm state-test --std-json /testfiles/martin-Tue_08_30_12-19208-13127-test.json

{"test":"randomStatetestmartin-Tue_08_30_12-19208-13127:byzantium:0","action":"starting"}
{"pc":0,"op":91,"opName":"JUMPDEST","gas":"0x477896","stack":[],"storage":{},"depth":1}
{"pc":1,"op":96,"opName":"PUSH1","gas":"0x477895","stack":[],"storage":{},"depth":1}
{"pc":3,"op":97,"opName":"PUSH2","gas":"0x477892","stack":["0xd1"],"storage":{},"depth":1}
{"pc":6,"op":97,"opName":"PUSH2","gas":"0x47788f","stack":["0xd1","0xc09a"],"storage":{},"depth":1}
{"pc":9,"op":111,"opName":"PUSH16","gas":"0x47788c","stack":["0xd1","0xc09a","0xa7f6"],"storage":{},"depth":1}
{"pc":26,"op":20,"opName":"EQ","gas":"0x477889","stack":["0xd1","0xc09a","0xa7f6","0x948ec1a91609740f44b8d0c74c4785d8"],"storage":{},"depth":1}
{"pc":27,"op":99,"opName":"PUSH4","gas":"0x477886","stack":["0xd1","0xc09a","0x0"],"storage":{},"depth":1}
{"pc":32,"op":81,"opName":"MLOAD","gas":"0x{"error":"State root mismatch (got: 0x3b63251e410b65ae32806a89e101b93e81b51096e4c00f6c3b547fe43350f504, expected: 0x00000000000000000000000000000000000000000000000000000000deadc0de)","gasUsed":"0x266573df9038e0","time":273}
477883","stack":["0xd1","0xc09a","0x0","0x4ebfdb04"],"storage":{},"depth":1}"""
    output = VMUtils.ParityVM.canonicalized(data.split("\n"))
    print("\n".join([str(x) for x in output]))


