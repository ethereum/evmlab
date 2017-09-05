#!/usr/bin/env python3
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools
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

def parse_config():
    """Parses 'statetests.ini'-file, which 
    may contain user-specific configuration
    """

    import configparser
    config = configparser.ConfigParser()
    config.read('statetests.ini')
    import getpass
    uname = getpass.getuser()
    if uname not in config.sections():
        uname = "DEFAULT"

    cfg['DO_CLIENTS']  = config[uname]['clients'].split(",")
    cfg['FORK_CONFIG'] = config[uname]['fork_config']
    cfg['TESTS_PATH']  = config[uname]['tests_path']
    cfg['PYETH_DOCKER_NAME'] = config[uname]['pyeth_docker_name']
    cfg['CPP_DOCKER_NAME'] = config[uname]['cpp_docker_name']
    cfg['PARITY_DOCKER_NAME'] = config[uname]['parity_docker_name']
    cfg['GETH_DOCKER_NAME'] = config[uname]['geth_docker_name']
    cfg['PRESTATE_TMP_FILE']=config[uname]['prestate_tmp_file']
    cfg['SINGLE_TEST_TMP_FILE']=config[uname]['single_test_tmp_file']
    cfg['LOGS_PATH'] = config[uname]['logs_path']
    cfg['TESTETH_DOCKER_NAME'] = config[uname]['testeth_docker_name']
    logger.info("Config")
    logger.info("\tActive clients: %s",      cfg['DO_CLIENTS'])
    logger.info("\tFork config: %s",         cfg['FORK_CONFIG'])
    logger.info("\tTests path: %s",          cfg['TESTS_PATH'])
    logger.info("\tPyeth: %s",               cfg['PYETH_DOCKER_NAME'])
    logger.info("\tCpp: %s",                 cfg['CPP_DOCKER_NAME'])
    logger.info("\tParity: %s",              cfg['PARITY_DOCKER_NAME'])
    logger.info("\tGeth: %s",                cfg['GETH_DOCKER_NAME'])
    logger.info("\tPrestate tempfile: %s",   cfg['PRESTATE_TMP_FILE'])
    logger.info("\tSingle test tempfile: %s",cfg['SINGLE_TEST_TMP_FILE'])
    logger.info("\tLog path: %s",            cfg['LOGS_PATH'])



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
    with open(test_file) as json_data:
        general_test = json.load(json_data)
        for test_name in general_test:
            # should only be one test_name per file
            prestate = {}
            prestate['env'] = general_test[test_name]['env']
            prestate['pre'] = general_test[test_name]['pre']
            prestate['config'] = {} # for pyeth run_statetest.py
            prestate['config']['metropolisBlock'] = 2000 # same default as evmlab/genesis.py
            if fork_name == 'Byzantium':
                prestate['config']['metropolisBlock'] = 0
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



def outputs(stdouts):
    import json
    finished = False
    while not finished:
        items = []
        for outp in stdouts:
            if outp == "":
                items.append({})
                finished = True
            else:
                outp = outp.strip()
                try:
                    items.append(json.loads(outp))
                except ValueError:
                    logger.info("Invalid json: %s", outp)
                    items.append({})
        yield items

def canon(str):
    if str in [None, "0x", ""]:
        return ""
    if str[:2] == "0x":
        return str
    return "0x" + str

def toText(op):
    return VMUtils.toText(op)

def dumpJson(obj, prefix = None):
    import tempfile
    fd, temp_path = tempfile.mkstemp(prefix = 'randomtest_', suffix=".json")
    with open(temp_path, 'w') as f :
        json.dump(obj,f)
        logger.info("Saved file to %s" % temp_path)
    os.close(fd)
    return temp_path

def createRandomStateTest():
    cmd = ["docker", "run", "--rm", cfg['TESTETH_DOCKER_NAME'],"-t","StateTestsGeneral","--","--createRandomTest"]
    outp = "".join(VMUtils.finishProc(VMUtils.startProc(cmd)))
    #Validate that it's json

    path = dumpJson(json.loads(outp), "randomtest_")
    return path

def generateTests():
    while True: 
        yield createRandomStateTest()



def startParity(test_file):
    logger.info("running state test in parity.")
    testfile_path = os.path.abspath(test_file)
    mount_testfile = testfile_path + ":" + "/mounted_testfile"

    parity_docker_cmd = ["docker", "run", "--rm", "-t", "-v", mount_testfile, cfg['PARITY_DOCKER_NAME'], "--json", "--statetest", "/mounted_testfile"]
    logger.info(" ".join(parity_docker_cmd))
    
    return VMUtils.startProc(parity_docker_cmd)


def startCpp(test_subfolder, test_name, test_dgv):
    logger.info("running state test in cpp-ethereum.")
    [d,g,v] = test_dgv

    cpp_mount_tests = cfg['TESTS_PATH'] + ":" + "/mounted_tests"
    cmd = ["docker", "run", "--rm", "-t", "-v", cpp_mount_tests, cfg['CPP_DOCKER_NAME']]
    cmd.extend(['-t',"StateTestsGeneral/%s" %  test_subfolder,'--'])
    cmd.extend(['--singletest', test_name])
    cmd.extend(['--jsontrace',"'{ \"disableStorage\":true }'" ])
    cmd.extend(['--singlenet',cfg['FORK_CONFIG']])
    cmd.extend(['-d',str(d),'-g',str(g), '-v', str(v) ])
    cmd.extend(['--testpath', '"/mounted_tests"'])

    logger.info("cpp_cmd: %s " % " ".join(cmd))

    return VMUtils.startProc(cmd)

def startGeth(test_case, test_tx):
    logger.info("running state test in geth.")
    genesis = gen.Genesis()
    for account_key in test_case['pre']:
        account = test_case['pre'][account_key]
        account['address'] = account_key
        genesis.addPrestateAccount(account)
    genesis.setCoinbase(test_case['env']['currentCoinbase'])
    genesis.setTimestamp(test_case['env']['currentTimestamp'])
    genesis.setGasLimit(test_case['env']['currentGasLimit'])
    genesis.setDifficulty(test_case['env']['currentDifficulty'])
    genesis.setBlockNumber(test_case['env']['currentNumber'])

    if cfg['FORK_CONFIG'] == 'Metropolis' or cfg['FORK_CONFIG'] == 'Byzantium':
        genesis.setMetropolisActivation(0)
    
    geth_genesis = genesis.geth()
    g_path = genesis.export_geth()
    if sys.platform == "darwin":
        # OS X workaround for https://github.com/docker/for-mac/issues/1298 "The path /var/folders/wb/d8qys65575g8m2691vvglpmm0000gn/T/tmpctxz3buh.json is not shared from OS X and is not known to Docker." 
        g_path = "/private" + g_path
    
    input_data = test_tx['data']
    if input_data[0:2] == "0x":
        input_data = input_data[2:]
    
    tx_to = test_tx['to']
    tx_value = parse_int_or_hex(test_tx['value'])
    gas_limit = parse_int_or_hex(test_tx['gasLimit'])
    gas_price = parse_int_or_hex(test_tx['gasPrice'])
    block_gaslimit = parse_int_or_hex(test_case['env']['currentGasLimit'])
    
    if gas_limit > block_gaslimit:
        logger.info("Tx gas limit exceeds block gas limit. not calling geth")
        return []
    
    sender = '0x' + getTxSender(test_tx)
    sender_balance = parse_int_or_hex(test_case['pre'][sender]['balance'])
    balance_required = (gas_price * gas_limit) + tx_value
    
    if balance_required > sender_balance:
        logger.info("Insufficient balance. not calling geth")
        return []
    
    intrinsic_gas = getIntrinsicGas(test_tx)
    if tx_to == "":
        # create contract cost not included in getIntrinsicGas
        intrinsic_gas += 32000
    
    if gas_limit < intrinsic_gas:
        logger.info("Insufficient startgas. not calling geth")
        return []
    
    if tx_to == "" and input_data == "":
        logger.warn("No init code")
        #return []
    
    if tx_to in test_case['pre']:
        if 'code' in test_case['pre'][tx_to]:
            if test_case['pre'][tx_to]['code'] == '':
                logger.warn("To account in prestate has no code")
                #return []
    
    vm = VMUtils.GethVM(executable = cfg['GETH_DOCKER_NAME'], docker = True)


    return vm.start(genesis = g_path, gas = gas_limit, price = gas_price, json = True, sender = sender, receiver = tx_to, input = input_data, value = tx_value)



def startPython(test_file, test_tx):
    logger.info("running state test in pyeth.")
    tx_encoded = json.dumps(test_tx)
    tx_double_encoded = json.dumps(tx_encoded) # double encode to escape chars for command line
    
    # command if not using a docker container
    # pyeth_process = subprocess.Popen(["python", "run_statetest.py", test_file, tx_double_encoded], shell=False, stdout=subprocess.PIPE, close_fds=True)
    
    # command to run docker container
    # docker run --volume=/absolute/path/prestate.json:/mounted_prestate cdetrio/pyethereum run_statetest.py mounted_prestate "{\"data\": \"\", \"gasLimit\": \"0x0a00000000\", \"gasPrice\": \"0x01\", \"nonce\": \"0x00\", \"secretKey\": \"0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8\", \"to\": \"0x0f572e5295c57f15886f9b263e2f6d2d6c7b5ec6\", \"value\": \"0x00\"}"
    
    prestate_path = os.path.abspath(test_file)
    mount_flag = prestate_path + ":" + "/mounted_prestate"
    pyeth_docker_cmd = ["docker", "run", "--rm", "-t", "-v", mount_flag, cfg['PYETH_DOCKER_NAME'], "run_statetest.py", "/mounted_prestate", tx_double_encoded]
    
    logger.info(" ".join(pyeth_docker_cmd))

    return VMUtils.startProc(pyeth_docker_cmd)

def finishProc(name, process, canonicalizer):

    outp = VMUtils.finishProc(process)
    logging.info("End of %s trace, processing..." % name)
    canon_steps = canonicalizer(outp)
    canon_text = [toText(step) for step in canon_steps]
    logging.info("Done processing %s trace (%d steps), returning in canon format" % (name, len(canon_text)))
    return canon_text

def finishParity(process):
    return finishProc("parity", process, VMUtils.ParityVM.canonicalized)

def finishCpp(process):
    return finishProc("cpp", process, VMUtils.CppVM.canonicalized)

def finishGeth(process):
    return finishProc("geth", process, VMUtils.GethVM.canonicalized)

def finishPython(process):
    return finishProc("python", process, VMUtils.PyVM.canonicalized)


def startClient(client, single_test_tmp_file, prestate_tmp_file, tx, test_subfolder, test_name, tx_dgv, test_case):
    """ Starts the client process, returns a tuple
    ( process , end_function)
    Invoke the end_function with the process as arg to stop the process and read output
    """
    if client == 'GETH':
        return (startGeth(test_case, tx), finishGeth)
    if client == 'CPP':
        return (startCpp(test_subfolder, test_name, tx_dgv), finishCpp)
    if client == 'PY':
        return (startPython(prestate_tmp_file, tx), finishPython)
    if client == 'PAR':
        return (startParity(single_test_tmp_file), finishParity)
    
    logger.error("ERROR! client not supported:", client)
    return []


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
    'static_Call50000',
    'static_Call50000bytesContract50_1',
    'static_Call50000bytesContract50_2',
    'static_Call50000bytesContract50_3',
    'static_CallToNameRegistratorAddressTooBigLeft',
    'static_log3_MaxTopic',
    'static_log4_Caller',
    'static_RawCallGas',
    'static_RawCallGasValueTransfer',
    'static_RawCallGasValueTransferAsk',
    'static_RawCallGasValueTransferMemory',
    'static_RawCallGasValueTransferMemoryAsk',
    'static_refund_CallA_notEnoughGasInCall',
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
    'TransactionDataCosts652'
]

regex_skip = [skip.replace('*', '') for skip in SKIP_LIST if '*' in skip]



# to resume running after interruptions
START_I = 0



def main():
    fail_count = 0
    pass_count = 0
    failing_files = []
    test_number = 0
#    for f in iterate_tests(ignore=['stMemoryTest','stMemoryTest','stMemoryTest']):
    for f in generateTests():
        with open(f) as json_data:
            general_test = json.load(json_data)
            test_name = list(general_test.keys())[0]
            if TEST_WHITELIST and test_name not in TEST_WHITELIST:
                continue
            if test_name in SKIP_LIST and test_name not in TEST_WHITELIST:
                logger.info("skipping test:", test_name)
                continue
            if regex_skip and re.search('|'.join(regex_skip), test_name) and test_name not in TEST_WHITELIST:
                logger.info("skipping test (regex match):", test_name)
                continue


        (test_number, num_fails, num_passes,failures) = perform_test(f, test_name, test_number)

        logger.info("f/p/t: %d,%d,%d" % ( num_fails, num_passes, (num_fails + num_passes)))
        logger.info("failures: %s" % str(failing_files))

        fail_count = fail_count + num_fails
        pass_count = pass_count + num_passes
        failing_files.extend(failures)
        #break
    # done with all tests. print totals
    logger.info("fail_count: %d" % fail_count)
    logger.info("pass_count: %d" % pass_count)
    logger.info("total:      %d" % (fail_count + pass_count))

def setupLogToFile(filename):
    
    # remove all old handlers
    for hdlr in logger.handlers[:]:  
        if type(hdlr) == logging.FileHandler:
            hdlr.close()
            logger.removeHandler(hdlr)

    file_logger = logging.FileHandler(filename)
    logger.addHandler(file_logger)
    return file_logger

def perform_test(f, test_name, test_number = 0):

    logger.info("file: %s, test name %s " % (f,test_name))

    pass_count = 0
    failures = []
    fork_name = cfg['FORK_CONFIG']

    try:
        prestate, txs_dgv = convertGeneralTest(f, fork_name)
    except Exception as e:
        logger.warn("problem with test file, skipping.")
        return (test_number, fail_count, pass_count, failures)

    clients = cfg['DO_CLIENTS']
    test_tmpfile = cfg['SINGLE_TEST_TMP_FILE']
    prestate_tmpfile = cfg['PRESTATE_TMP_FILE']

    
    logger.info("prestate: %s", prestate)
    logger.debug("txs: %s", txs_dgv)

    with open(prestate_tmpfile, 'w') as outfile:
        json.dump(prestate, outfile)
        
    test_case = prestate
    test_subfolder = f.split(os.sep)[-2]

    for tx_i, tx_and_dgv in enumerate(txs_dgv):
        test_number += 1
        if test_number < START_I and not TEST_WHITELIST:
            continue

        # set up logging to file
        log_filename =  os.path.abspath(cfg['LOGS_PATH'] + '/' + test_name + '.log')
        file_log = setupLogToFile(log_filename)

        tx = tx_and_dgv[0]
        tx_dgv = tx_and_dgv[1]
        logger.info("file: %s", f)
        logger.info("test_name: %s. tx_i: %s", test_name, tx_i)
                
        clients_canon_traces = []
        procs = []

        #Start the processes
        for client_name in clients:

            if client_name == 'GETH':
                procs.append( (startGeth(test_case, tx), finishGeth) ) 
            if client_name == 'CPP':
                procs.append( (startCpp(test_subfolder, test_name, tx_dgv), finishCpp) )
            if client_name == 'PY':
                procs.append( (startPython(prestate_tmpfile, tx), finishPython) )
            if client_name == 'PAR':
                single_statetest = selectSingleFromGeneral(tx_i, f, fork_name)
                with open(test_tmpfile, 'w') as outfile:
                    json.dump(single_statetest, outfile)

                procs.append( (startParity(test_tmpfile), finishParity) )

#            procs.append(startClient(client_name ,test_tmpfile, prestate_tmpfile, tx, test_subfolder, test_name, tx_dgv, test_case))

        # Read the outputs
        for (proc, end_fn) in procs:
            canon_trace = end_fn(proc)
            clients_canon_traces.append(canon_trace)
            
        if VMUtils.compare_traces(clients_canon_traces, clients):
            logger.info("equivalent.")
            pass_count += 1
            passfail = 'PASS'
        else:
            logger.info("CONSENSUS BUG!!!\a")
            passfail = 'FAIL'
            failures.append(test_name)

        file_log.close()
        logger.removeHandler(file_log)
        # Rename file if it passed or not
        trace_file = os.path.abspath(log_filename)
        passfail_log_filename = cfg['LOGS_PATH'] + '/' + str(test_number).zfill(4) + '-' + passfail + '-' + test_subfolder + '-' +  test_name + '-' + str(tx_i) + '.log.txt'
        renamed_trace = os.path.abspath(passfail_log_filename)
        os.rename(trace_file, renamed_trace)

    

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


if __name__ == '__main__':
    main()
