#!/usr/bin/env python3
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections
from contextlib import redirect_stderr, redirect_stdout
import ethereum.transactions as transactions
from ethereum.utils import decode_hex, parse_int_or_hex, sha3, to_string, \
    remove_0x_head, encode_hex, big_endian_to_int

from evmlab import genesis as gen
from evmlab import vm as VMUtils
from evmlab import opcodes

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

cfg ={}
local_cfg = {}

def parse_config():
    """Parses 'statetests.ini'-file, which 
    may contain user-specific configuration
    """

    import configparser, getpass
    config = configparser.ConfigParser()
    config.read('statetests.ini')
    uname = getpass.getuser()
    if uname not in config.sections():
        uname = "DEFAULT"

    cfg['RANDOM_TESTS'] = config[uname]['random_tests']
    cfg['DO_CLIENTS']  = config[uname]['clients'].split(",")
    cfg['FORK_CONFIG'] = config[uname]['fork_config']
    cfg['TESTS_PATH']  = config[uname]['tests_path']

    global local_cfg

    local_cfg = collections.defaultdict(lambda: None, config[uname])
    print(local_cfg["geth.binary"])
    print(local_cfg["test"])
    # Make it possible to run in paralell sessions    
    cfg['PRESTATE_TMP_FILE']    ="%s-%d" % (config[uname]['prestate_tmp_file'] , os.getpid())
    cfg['SINGLE_TEST_TMP_FILE'] ="%s-%d" % (config[uname]['single_test_tmp_file'], os.getpid())

    cfg['LOGS_PATH'] = config[uname]['logs_path']

    logger.info("Config")
    logger.info("\tActive clients:")
    for c in cfg['DO_CLIENTS']:
        logger.info("\t* {} : {} docker:{}".format(c, getBaseCmd(c)[0],getBaseCmd(c)[1]) )

    logger.info("\tTest generator:")
    logger.info("\t* {} : {} docker:{}".format('testeth', getBaseCmd('testeth')[0],getBaseCmd('testeth')[1]) )
 
    logger.info("\tFork config:          %s",         cfg['FORK_CONFIG'])
    logger.info("\tPrestate tempfile:    %s",   cfg['PRESTATE_TMP_FILE'])
    logger.info("\tSingle test tempfile: %s",cfg['SINGLE_TEST_TMP_FILE'])
    logger.info("\tLog path:             %s",            cfg['LOGS_PATH'])



def getBaseCmd(bin_or_docker):
    """ Gets the configured 'base_command' for an image or binary. 
    Returns a path or image name and a boolean if it's a docker 
    image or not (needed to know if any mounts are needed)
    returns a tuple: ( name  , isDocker)
    """

    binary = local_cfg["{}.binary".format(bin_or_docker) ]
    if binary:
        return (binary, False)

    image = local_cfg["{}.docker_name".format(bin_or_docker)]
    if image: 
        return (image, True)

        
parse_config()


# used to check for unknown opcode names in traces
OPCODES = {}
op_keys = opcodes.opcodes.keys()
for op_key in op_keys:
    if op_key in opcodes.opcodesMetropolis and cfg['FORK_CONFIG'] != 'Byzantium':
        continue
    name = opcodes.opcodes[op_key][0]
    # allow opcode lookups by either name or number assignment
    OPCODES[name] = op_key
    OPCODES[op_key] = name



def iterate_tests(path = '/GeneralStateTests/', ignore = []):
    logging.info (cfg['TESTS_PATH'] + path)
    for subdir, dirs, files in sorted(os.walk(cfg['TESTS_PATH'] + path)):
        for f in files:
            if f.endswith('json'):
                for ignore_name in ignore:
                    if f.find(ignore_name) != -1:
                        continue
                    yield os.path.join(subdir, f)


def convertGeneralTest(test_file, fork_name):
    # same default as evmlab/genesis.py
    metroBlock = 2000
    if fork_name == 'Byzantium':
        metroBlock = 0


    with open(test_file) as json_data:
        general_test = json.load(json_data)
        for test_name in general_test:
            # should only be one test_name per file
            prestate = {
                'env' : general_test[test_name]['env'],
                'pre' : general_test[test_name]['pre'],
                'config' : { # for pyeth run_statetest.py
                    'metropolisBlock' : 2000, # same default as evmlab/genesis.py
                    'eip158Block' : 2000,
                    'eip150Block' : 2000,
                    'eip155Block' : 2000,
                    'homesteadBlock' : 2000,
                }
            }
            if cfg['FORK_CONFIG'] == 'Byzantium':
                prestate['config'] = {
                    'metropolisBlock' : 0,
                    'eip158Block' : 0,
                    'eip150Block' : 0,
                    'eip155Block' : 0,
                    'homesteadBlock' : 0,
                }
            if cfg['FORK_CONFIG'] == 'Homestead':
                prestate['config']['homesteadBlock'] = 0
            #print("prestate:", prestate)
            general_tx = general_test[test_name]['transaction']
            transactions = []
            for test_i in general_test[test_name]['post'][fork_name]:
                test_tx = general_tx.copy()
                d_i = test_i['indexes']['data']
                g_i = test_i['indexes']['gas']
                v_i = test_i['indexes']['value']
                test_tx['data'] = general_tx['data'][d_i]
                test_tx['gasLimit'] = general_tx['gasLimit'][g_i]
                test_tx['value'] = general_tx['value'][v_i]
                test_dgv = (d_i, g_i, v_i)
                transactions.append((test_tx, test_dgv))

        return prestate, transactions


def selectSingleFromGeneral(single_i, general_testfile, fork_name):
    # a fork/network in a general state test has an array of test cases
    # each element of the array specifies (d,g,v) indexes in the transaction
    with open(general_testfile) as json_data:
        general_test = json.load(json_data)
        #logger.info("general_test: %s", general_test)
        for test_name in general_test:
            # should only be one test_name per file
            single_test = general_test
            single_tx = single_test[test_name]['transaction']
            general_tx = single_test[test_name]['transaction']
            selected_case = general_test[test_name]['post'][fork_name][single_i]
            single_tx['data'] = [ general_tx['data'][selected_case['indexes']['data']] ]
            single_tx['gasLimit'] = [ general_tx['gasLimit'][selected_case['indexes']['gas']] ]
            single_tx['value'] = [ general_tx['value'][selected_case['indexes']['value']] ]
            selected_case['indexes']['data'] = 0
            selected_case['indexes']['gas'] = 0
            selected_case['indexes']['value'] = 0
            single_test[test_name]['post'] = {}
            single_test[test_name]['post'][fork_name] = []
            single_test[test_name]['post'][fork_name].append(selected_case)
            return single_test



def getIntrinsicGas(test_tx):
    tx = transactions.Transaction(
        nonce=parse_int_or_hex(test_tx['nonce'] or b"0"),
        gasprice=parse_int_or_hex(test_tx['gasPrice'] or b"0"),
        startgas=parse_int_or_hex(test_tx['gasLimit'] or b"0"),
        to=decode_hex(remove_0x_head(test_tx['to'])),
        value=parse_int_or_hex(test_tx['value'] or b"0"),
        data=decode_hex(remove_0x_head(test_tx['data'])))

    return tx.intrinsic_gas_used

def getTxSender(test_tx):
    tx = transactions.Transaction(
        nonce=parse_int_or_hex(test_tx['nonce'] or b"0"),
        gasprice=parse_int_or_hex(test_tx['gasPrice'] or b"0"),
        startgas=parse_int_or_hex(test_tx['gasLimit'] or b"0"),
        to=decode_hex(remove_0x_head(test_tx['to'])),
        value=parse_int_or_hex(test_tx['value'] or b"0"),
        data=decode_hex(remove_0x_head(test_tx['data'])))
    if 'secretKey' in test_tx:
        tx.sign(decode_hex(remove_0x_head(test_tx['secretKey'])))
    return encode_hex(tx.sender)

def canon(str):
    if str in [None, "0x", ""]:
        return ""
    if str[:2] == "0x":
        return str
    return "0x" + str

def toText(op):
    return VMUtils.toText(op)

def dumpJson(obj, dir = None, prefix = None):
    import tempfile
    fd, temp_path = tempfile.mkstemp(prefix = 'randomtest_', suffix=".json", dir = dir)
    with open(temp_path, 'w') as f :
        json.dump(obj,f)
        logger.info("Saved file to %s" % temp_path)
    os.close(fd)
    return temp_path

def createRandomStateTest():
    (name, isDocker) = getBaseCmd("testeth")
    if isDocker:
        cmd = ['docker', "run", "--rm",name]
    else:
        cmd = [name]

    cmd.extend(["-t","GeneralStateTests","--","--createRandomTest"])
    outp = "".join(VMUtils.finishProc(VMUtils.startProc(cmd)))
    #Validate that it's json
    try:
        test = json.loads(outp)
        test['randomStatetest']['_info'] = {'sourceHash': "0000000000000000000000000000000000000000000000000000000000001337", "comment":"x"}

        return test
    except:
        print("Exception generating test")
        print('-'*60)
        traceback.print_exc(file=sys.stdout)
        print('-'*60)
    return None


def generateTests():
    import getpass, time
    uname = getpass.getuser()
    host_id = "%s-%s-%d" % (uname, time.strftime("%a_%H_%M_%S"), os.getpid())
    here = os.path.dirname(os.path.realpath(__file__))

    cfg['TESTS_PATH'] = "%s/generatedTests/" % here
    # cpp needs the tests to be placed according to certain rules... 
    testfile_dir = "%s/generatedTests/GeneralStateTests/stRandom" % here
    filler_dir = "%s/generatedTests/src/GeneralStateTestsFiller/stRandom" % here 

    os.makedirs( testfile_dir , exist_ok = True)
    os.makedirs( filler_dir, exist_ok = True)
    import pathlib

    counter = 0
    while True: 
        test_json =  createRandomStateTest()
        if test_json == None: 
            time.sleep(2)
            continue

        identifier = "%s-%d" %(host_id, counter)
        test_fullpath = "%s/randomStatetest%s.json" % (testfile_dir, identifier)
        filler_fullpath = "%s/randomStatetest%sFiller.json" % (filler_dir, identifier)
        test_json['randomStatetest%s' % identifier] =test_json.pop('randomStatetest', None) 

        
        with open(test_fullpath, "w+") as f:
            json.dump(test_json, f)
            pathlib.Path(filler_fullpath).touch()

        yield test_fullpath
        counter = counter +1

def startParity(test_file):

    testfile_path = os.path.abspath(test_file)
    mount_testfile = testfile_path + ":" + "/mounted_testfile"

    (name, isDocker) = getBaseCmd("parity")
    if isDocker:
        cmd = ["docker", "run", "--rm", "-t", "-v", mount_testfile, name, "state-test", "/mounted_testfile", "--json"]
    else:
        cmd = [name,"state-test", testfile_path, "--json"]


    return {'proc':VMUtils.startProc(cmd ), 'cmd': " ".join(cmd), 'output' : 'stdout'}


def startCpp(test_subfolder, test_name, test_dgv):

    [d,g,v] = test_dgv


    (name, isDocker) = getBaseCmd("cpp")
    if isDocker:
        cpp_mount_tests = cfg['TESTS_PATH'] + ":" + "/mounted_tests"
        cmd = ["docker", "run", "--rm", "-t", "-v", cpp_mount_tests, name
                ,'-t',"GeneralStateTests/%s" %  test_subfolder
                ,'--'
                ,'--singletest', test_name
                ,'--jsontrace',"'{ \"disableStorage\":true, \"disableMemory\":true }'"
                ,'--singlenet',cfg['FORK_CONFIG']
                ,'-d',str(d),'-g',str(g), '-v', str(v)
                ,'--testpath', '"/mounted_tests"']
    else:
        cmd = [name
                ,'-t',"GeneralStateTests/%s" %  test_subfolder
                ,'--'
                ,'--singletest', test_name
                ,'--jsontrace',"'{ \"disableStorage\":true, \"disableMemory\":true }'"
                ,'--singlenet',cfg['FORK_CONFIG']
                ,'-d',str(d),'-g',str(g), '-v', str(v)
                ,'--testpath',  cfg['TESTS_PATH']]


    if cfg['FORK_CONFIG'] == 'Homestead' or cfg['FORK_CONFIG'] == 'Frontier':
        cmd.extend(['--all']) # cpp requires this for some reason

    return {'proc':VMUtils.startProc(cmd ), 'cmd': " ".join(cmd), 'output' : 'stdout'}

def startGeth(test_file):

    testfile_path = os.path.abspath(test_file)
    mount_testfile = testfile_path + ":" + "/mounted_testfile"

    (name, isDocker) = getBaseCmd("geth")
    if isDocker:
        cmd = ["docker", "run", "--rm", "-t", "-v", mount_testfile, name, "--json", "--nomemory", "statetest", "/mounted_testfile"]
        return {'proc':VMUtils.startProc(cmd ), 'cmd': " ".join(cmd), 'output' : 'stdout'}
    else:
        cmd = [name,"--json", "--nomemory", "statetest", testfile_path]
        return {'proc':VMUtils.startProc(cmd ), 'cmd': " ".join(cmd), 'output' : 'stderr'}




def startPython(test_file, test_tx):

    tx_encoded = json.dumps(test_tx)
    tx_double_encoded = json.dumps(tx_encoded) # double encode to escape chars for command line

    # command if not using a docker container
    # pyeth_process = subprocess.Popen(["python", "run_statetest.py", test_file, tx_double_encoded], shell=False, stdout=subprocess.PIPE, close_fds=True)

    # command to run docker container
    # docker run --volume=/absolute/path/prestate.json:/mounted_prestate cdetrio/pyethereum run_statetest.py mounted_prestate "{\"data\": \"\", \"gasLimit\": \"0x0a00000000\", \"gasPrice\": \"0x01\", \"nonce\": \"0x00\", \"secretKey\": \"0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8\", \"to\": \"0x0f572e5295c57f15886f9b263e2f6d2d6c7b5ec6\", \"value\": \"0x00\"}"

    prestate_path = os.path.abspath(test_file)
    mount_flag = prestate_path + ":" + "/mounted_prestate"
    cmd = ["docker", "run", "--rm", "-t", "-v", mount_flag, cfg['PYETH_DOCKER_NAME'], "run_statetest.py", "/mounted_prestate", tx_double_encoded]

    return {'proc':VMUtils.startProc(cmd), 'cmd': " ".join(cmd), 'output' : 'stdout'}



TEST_WHITELIST = []


SKIP_LIST = [
    #'modexp_*', # regex example
    'POP_Bounds',
    'POP_BoundsOOG',
    'MLOAD_Bounds',
    'Call1024PreCalls', # Call1024PreCalls does produce a trace difference, worth fixing that trace
    'createInitFailStackSizeLargerThan1024',
    'createJS_ExampleContract',
    'CALL_Bounds',
    'mload32bitBound_Msize ',
    'mload32bitBound_return2',
    'Call1MB1024Calldepth ',
    'shallowStackOK',
    'stackOverflowM1PUSH', # slow
    'static_Call1MB1024Calldepth', # slow
    'static_Call1024BalanceTooLow',
    'static_Call1024BalanceTooLow2',
    'static_Call1024OOG',
    'static_Call1024PreCalls',
    'static_Call1024PreCalls2', # slow
    'static_Call1024PreCalls3', #slow
    'static_Call50000',
    'static_Call50000bytesContract50_1',
    'static_Call50000bytesContract50_2',
    'static_Call50000bytesContract50_3',
    'static_CallToNameRegistratorAddressTooBigLeft',
    'static_Call50000_identity2',
    'static_Call50000_identity',
    'static_Call50000_ecrec',
    'static_Call50000_rip160',
    'static_Call50000_sha256',
    'static_Return50000_2',
    'static_callChangeRevert',
    'static_log3_MaxTopic',
    'static_log4_Caller',
    'static_RawCallGas',
    'static_RawCallGasValueTransfer',
    'static_RawCallGasValueTransferAsk',
    'static_RawCallGasValueTransferMemory',
    'static_RawCallGasValueTransferMemoryAsk',
    'static_refund_CallA_notEnoughGasInCall',
    'static_LoopCallsThenRevert',
    'HighGasLimit', # geth doesn't run
    'zeroSigTransacrionCreate', # geth fails this one
    'zeroSigTransacrionCreatePrice0', # geth fails
    'zeroSigTransaction', # geth fails
    'zeroSigTransaction0Price', # geth fails
    'zeroSigTransactionInvChainID',
    'zeroSigTransactionInvNonce',
    'zeroSigTransactionInvNonce2',
    'zeroSigTransactionOOG',
    'zeroSigTransactionOrigin',
    'zeroSigTransactionToZero',
    'zeroSigTransactionToZero2',
    'OverflowGasRequire2',
    'TransactionDataCosts652',
    'stackLimitPush31_1023',
    'stackLimitPush31_1023',
    'stackLimitPush31_1024',
    'stackLimitPush31_1025', # test runner crashes
    'stackLimitPush32_1023',
    'stackLimitPush32_1024',
    'stackLimitPush32_1025', # big trace, onsensus failure
    'stackLimitGas_1023',
    'stackLimitGas_1024', # consensus bug
    'stackLimitGas_1025'
]

regex_skip = [skip.replace('*', '') for skip in SKIP_LIST if '*' in skip]



# to resume running after interruptions
START_I = 0


def testIterator():
    if cfg['RANDOM_TESTS'] == 'Yes':
        logger.info("generating random tests...")
        return generateTests()
    else:
        logger.info("iterating over state tests...")
        return iterate_tests(ignore=['stMemoryTest','stMemoryTest','stMemoryTest'])


def main():
    fail_count = 0
    pass_count = 0
    failing_files = []
    test_number = 0
    start_time = time.time()
    for f in testIterator():
        with open(f) as json_data:
            general_test = json.load(json_data)
            test_name = list(general_test.keys())[0]
            if TEST_WHITELIST and test_name not in TEST_WHITELIST:
                continue
            if test_name in SKIP_LIST and test_name not in TEST_WHITELIST:
                logger.info("skipping test: %s" % test_name)
                continue
            if regex_skip and re.search('|'.join(regex_skip), test_name) and test_name not in TEST_WHITELIST:
                logger.info("skipping test (regex match): %s" % test_name)
                continue


        (test_number, num_fails, num_passes,failures) = perform_test(f, test_name, test_number)

        failing_files.extend(failures)

        #Total sums
        fail_count = fail_count + num_fails
        pass_count = pass_count + num_passes

        time_elapsed = time.time() - start_time

        logger.info("f/p/t: {},{},{}".format( num_fails, num_passes, (num_fails + num_passes)))
        logger.info("Total fails {}, pass {}, #tests {} (speed {:f} tests/s)".format(
            fail_count,
            pass_count, 
            fail_count+pass_count,  
            (fail_count+pass_count) / time_elapsed))
        logger.info("Failing files: %s" % str(failing_files))

        #if fail_count > 0:
        #    break
    # done with all tests. print totals
    logger.info("fail_count: %d" % fail_count)
    logger.info("pass_count: %d" % pass_count)
    logger.info("total:      %d" % (fail_count + pass_count))


def finishProc(name, processInfo, canonicalizer, fulltrace_filename = None):
    """ Ends the process, returns the canonical trace and also writes the 
    full process output to a file, along with the command used to start the process"""

    process = processInfo['proc']

    extraTime = False
    if name == "py":
        extraTime = True

    outp = VMUtils.finishProc(processInfo['proc'], extraTime, processInfo['output'])

    if fulltrace_filename is not None:
        #logging.info("Writing %s full trace to %s" % (name, fulltrace_filename))
        with open(fulltrace_filename, "w+") as f: 
            f.write("# command\n")
            f.write("# %s\n\n" % processInfo['cmd'])
            f.write("\n".join(outp))

    canon_text = [toText(step) for step in canonicalizer(outp)]
    logging.info("Processed %s steps for %s" % (len(canon_text), name))
    return canon_text

def get_summary(combined_trace, n=20):
    """Returns (up to) n (default 20) preceding steps before the first diff, and the diff-section
    """
    from collections import deque
    buf = deque([],n)
    index = 0
    for index, line in enumerate(combined_trace):
        buf.append(line)
        if line.startswith("[!!]"):
            break

    for i in range(index, min(len(combined_trace), index+5 )):
        buf.append(combined_trace[i])

    return list(buf)


def perform_test(testfile, test_name, test_number = 0):

    logger.info("file: %s, test name %s " % (testfile,test_name))

    pass_count = 0
    failures = []
    fork_name        = cfg['FORK_CONFIG']
    clients          = cfg['DO_CLIENTS']
    test_tmpfile     = cfg['SINGLE_TEST_TMP_FILE']
    prestate_tmpfile = cfg['PRESTATE_TMP_FILE']

    try:
        prestate, txs_dgv = convertGeneralTest(testfile, fork_name)
    except Exception as e:
        logger.warn("problem with test file, skipping.")
        return (test_number, fail_count, pass_count, failures)

#    logger.info("prestate: %s", prestate)
    logger.debug("txs: %s", txs_dgv)

    with open(prestate_tmpfile, 'w') as outfile:
        json.dump(prestate, outfile)

    test_subfolder = testfile.split(os.sep)[-2]

    for tx_i, tx_and_dgv in enumerate(txs_dgv):
        test_number += 1
        if test_number < START_I and not TEST_WHITELIST:
            continue

        test_id = "{:0>4}-{}-{}-{}".format(test_number,test_subfolder,test_name,tx_i)
        logger.info("test id: %s" % test_id)

        single_statetest = selectSingleFromGeneral(tx_i, testfile, fork_name)
        with open(test_tmpfile, 'w') as outfile:
            json.dump(single_statetest, outfile)

        tx = tx_and_dgv[0]
        tx_dgv = tx_and_dgv[1]


        clients_canon_traces = []
        procs = []

        canonicalizers = {
            "geth" : VMUtils.GethVM.canonicalized, 
            "cpp"  : VMUtils.CppVM.canonicalized, 
            "py"   : VMUtils.PyVM.canonicalized, 
            "parity"  :  VMUtils.ParityVM.canonicalized ,
        }
        logger.info("Starting processes for %s" % clients)

        #Start the processes
        for client_name in clients:

            if client_name == 'geth':
                procinfo = startGeth(test_tmpfile)
            elif client_name == 'cpp':
                procinfo = startCpp(test_subfolder, test_name, tx_dgv)
            elif client_name == 'py':
                procinfo = startPython(prestate_tmpfile, tx)
            elif client_name == 'parity':
                procinfo = startParity(test_tmpfile)
            else:
                logger.warning("Undefined client %s", client_name)
                continue
            procs.append( (procinfo, client_name ))

        traceFiles = []
        # Read the outputs
        for (procinfo, client_name) in procs:
            if procinfo['proc'] is None:
                continue

            canonicalizer = canonicalizers[client_name]
            full_trace_filename = os.path.abspath("%s/%s-%s.trace.log" % (cfg['LOGS_PATH'],test_id, client_name))
            traceFiles.append(full_trace_filename)
            canon_trace = finishProc(client_name, procinfo, canonicalizer, full_trace_filename)
            clients_canon_traces.append(canon_trace)

        (equivalent, trace_output) = VMUtils.compare_traces(clients_canon_traces, clients) 

        if equivalent:
            #delete non-failed traces
            for f in traceFiles:
                os.remove(f)

            pass_count += 1
            passfail = 'PASS'
        else:
            logger.warning("CONSENSUS BUG!!!")
            failures.append(test_name)

            # save the state-test
            statetest_filename = "%s/%s-test.json" %(cfg['LOGS_PATH'], test_id)
            os.rename(test_tmpfile,statetest_filename)

            # save combined trace
            passfail = 'FAIL'
            passfail_log_filename = "%s/%s-%s.log.txt" % ( cfg['LOGS_PATH'], passfail,test_id)
            with open(passfail_log_filename, "w+") as f:
                logger.info("Combined trace: %s" , passfail_log_filename)
                f.write("\n".join(trace_output))

            # save a summary of the trace, with up to 20 steps preceding the first diff
            trace_summary = get_summary(trace_output)
            summary_log_filename = "%s/%s-%s.summary.txt" % ( cfg['LOGS_PATH'], passfail,test_id)
            with open(summary_log_filename, "w+") as f:
                logger.info("Summary trace: %s" , summary_log_filename)
                f.write("\n".join(trace_summary))


    return (test_number, len(failures), pass_count, failures)

"""
## need to get redirect_stdout working for the python-afl fuzzer

# currently doPython() spawns a new process, and gets the pyethereum VM trace from the subprocess.Popen shell output.
# python-afl cannot instrument a separate process, so this prevents it from measuring the code/path coverage of pyeth

# TODO: invoke pyeth state test runner as a module (so python-afl can measure path coverage), and use redirect_stdout to get the trace


def runStateTest(test_case):
    _state = init_state(test_case['env'], test_case['pre'])
    f = io.StringIO()
    with redirect_stdout(f):
        computed = compute_state_test_unit(_state, test_case["transaction"], config_spurious)
    f.seek(0)
    py_out = f.read()
    print("py_out:", py_out)
"""
def testSummary():
    """Enable this, and test by passing a trace-output via console"""
    with open(sys.argv[1]) as f:
        print("".join(get_summary(f.readlines())))

if __name__ == '__main__':
#    testSummary()
    main()
