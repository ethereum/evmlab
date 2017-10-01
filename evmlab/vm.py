import os, signal, json, itertools
from subprocess import Popen, PIPE, TimeoutExpired
from ethereum.utils import parse_int_or_hex,decode_hex,remove_0x_head
import logging
from . import opcodes
logger = logging.getLogger()

FNULL = open(os.devnull, 'w')

valid_opcodes = opcodes.reverse_opcodes.keys()


def add_0x(str):
    if str in [None, "0x", ""]:
        return ""
    if str[:2] == "0x":
        return str
    return "0x" + str

def strip_0x(txt):
    if len(txt) >= 2 and txt[:2] == '0x':
        return txt[2:]
    return txt

def toHexQuantities(vals):
    quantities = []
    for val in vals:
        val_int = parse_int_or_hex(val)
        quantities.append('0x{0:01x}'.format(val_int))
    return quantities

bstrToInt = lambda b_str: int(b_str.replace("b", "").replace("'", ""))
bstrToHex = lambda b_str: '0x{0:01x}'.format(bstrToInt(b_str))


def toText(op):
    if len(op.keys()) == 0:
        return "END"
    if 'pc' in op.keys():
        op_key = op['op']
        if op_key in opcodes.opcodes.keys():
            opname = opcodes.opcodes[op_key][0]
        else:
            opname = "UNKNOWN"
        op['opname'] = opname
        return "pc {pc:>5} op {opname:>10}({op:>3}) gas {gas:>8} depth {depth:>2} stack {stack}".format(**op)
    elif 'stateRoot' in op.keys():
        return "stateRoot {}".format(op['stateRoot'])
    elif 'time' in op.keys():# Final one

        if 'output' not in op.keys():
           op['output'] = ""

        op['output'] = canon(op['output'])
        fmt = "output {output} gasUsed {gasUsed}"
        if 'error' in op.keys():
            e = op['error']
            if e.lower().find("out of gas") > -1:   
                e = "OOG"
            fmt = fmt + " err: OOG"
        return fmt.format(**op)
    return "N/A"

def getIntrinsicGas(data):
    import ethereum.transactions as transactions
    tx = transactions.Transaction(
        nonce=0,
        gasprice=0,
        startgas=0,
        to=b"",
        value=0,
        data=decode_hex(remove_0x_head(data)))
    
    return tx.intrinsic_gas_used

def compare_traces(clients_canon_traces, names):

    """ Compare 'canonical' traces from the clients"""

    canon_traces = list(itertools.zip_longest(*clients_canon_traces))
    logger.info("Comparing traces")
    num_clients = len(names)
    equivalent = True
    for step in canon_traces:
        wrong_clients = []
        step_equiv = True
        for i in range(1, num_clients):
            if step[i] != step[0]:
                step_equiv = False
                wrong_clients.append(i)

        if step_equiv == True:
            logger.debug('[*]       {}'.format(step[0]))
        else:
            equivalent = False
            logger.info("")
            for i in range(0, num_clients):
                if i in wrong_clients or len(wrong_clients) == num_clients-1:
                    logger.info('[!!] {:>4} {}'.format(names[i], step[i]))
                else:
                    logger.info('[*] {:>5} {}'.format(names[i], step[i]))

    return equivalent


def startProc(cmd):
    # passing a list to Popen doesn't work. Can't read stdout from docker container when shell=False
    #pyeth_process = subprocess.Popen(pyeth_docker_cmd, shell=False, stdout=subprocess.PIPE, close_fds=True)

    # need to pass a string to Popen and shell=True to get stdout from docker container
    print(" ".join(cmd))
    return Popen(" ".join(cmd), stdout=PIPE,shell=True, preexec_fn=os.setsid)


def finishProc(process, extraTime=False):
    timeout = 15
    if extraTime:
        timeout = 30
    try:
        (stdoutdata, stderrdata) = process.communicate(timeout=timeout)
    except TimeoutExpired:
        logger.info("TIMEOUT ERROR!")
        os.killpg(process.pid, signal.SIGINT) # send signal to the process group
        (stdoutdata, stderrdata) = process.communicate()


    return stdoutdata.decode().strip().split("\n")

class VM(object):

    def __init__(self,executable="evmbin", docker = False):
        self.executable = executable
        self.docker = docker
        self.genesis_format = "parity"
        self.lastCommand = ""

    def _run(self,cmd):
        self.lastCommand = " ".join(cmd)
        return finishProc(startProc(cmd))

    def _start(self, cmd):
        self.lastCommand = " ".join(cmd)
        return startProc(cmd)

class CppVM(VM):

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        valid_opcodes = opcodes.reverse_opcodes.keys()
        logger.debug(output)

        steps = []
        for x in output:
            try:
                if x[0:2] == "[{":
                        steps = json.loads(x)

                if x[0:2] == "{\"":
                    step = json.loads(x)
                    if 'stateRoot' in step.keys():
                        steps.append(step)

            except Exception as e:
                logger.info('Exception parsing cpp json:')
                logger.info(e)
                logger.info('problematic line:')
                logger.info(x)

        canon_steps = []

        try:
            for step in steps:
                logger.debug(step)
                if 'stateRoot' in step.keys():
                    if len(canon_steps): # dont log state root if no previous EVM steps
                        canon_steps.append(step) # should happen last
                    continue
                if step['op'] in ['INVALID', 'STOP'] :
                    # skip STOPs
                    continue
                if step['op'] not in valid_opcodes:
                    logger.info("got cpp step for an unknown opcode:")
                    logger.info(step)
                    continue

                trace_step = {
                    'pc'  : step['pc'],
                    'gas': '0x{0:01x}'.format(int(step['gas'])) ,
                    'op': opcodes.reverse_opcodes[step['op']],
                    'depth' : step['depth'],
                    'stack' : toHexQuantities(step['stack']),
                }
                canon_steps.append(trace_step)
        except Exception as e:
            logger.info('Exception parsing cpp step:')
            logger.info(e)

        return canon_steps

class PyVM(VM):

    @staticmethod
    def canonicalized(output):
        from . import opcodes

        def formatStackItem(el):
            return '0x{0:01x}'.format(int(el.replace("b", "").replace("'", "")))

        def json_steps():
            for line in output:
                logger.debug(line.rstrip())
                if line.startswith("tx:"):
                    continue
                if line.startswith("tx_decoded:"):
                    continue
                json_index = line.find("{")
                if json_index >= 0:
                    try:
                        yield(json.loads(line[json_index:]))
                    except Exception as e:
                        logger.info("Exception parsing python output:")
                        logger.info(e)
                        logger.info("problematic line:")
                        logger.info(line)
                        yield({})

        canon_steps = []
        for step in json_steps():
            #print (step)
            if 'stateRoot' in step.keys() and len(canon_steps):
                # dont log stateRoot when tx doesnt execute, to match cpp and parity
                canon_steps.append(step)
                continue
            if 'event' not in step.keys():               
                continue
            if step['event'] == 'eth.vm.op.vm':
                if step['op'] not in valid_opcodes:
                    # invalid opcode
                    continue
                if step['op'] == 'STOP':
                    # geth logs code-out-of-range as a STOP, and we 
                    # can't distinguish them from actual STOPs (that pyeth logs)
                    continue

                trace_step = {
                    'opName' : step['op'],
                    'op'     : step['inst'],
                    'depth'  : step['depth'],
                    'pc'     : bstrToInt(step['pc']),
                    'gas'    : bstrToHex(step['gas']),
                }

                trace_step['stack'] = [formatStackItem(el) for el in step['stack']]
                canon_steps.append(trace_step)

        return canon_steps


class GethVM(VM):

    def __init__(self,executable="evmbin", docker = False):
        super().__init__( executable, docker)
        self.genesis_format="geth"

    def start(self, code = None, codeFile = None, genesis = None, 
        gas = 4700000, price = None, json = False, statdump = False, 
        sender = None, receiver = None, memory = False, input = None, 
        value = None, dontExecuteButReturnCommand = False):

        if self.docker: 
            cmd = ['docker', 'run', '--rm']
            # If any files are referenced, they need to be mounted
            if genesis is not None:
                cmd.append('-v')
                cmd.append('%s:%s' % (genesis,"/mounted_genesis"))
                genesis = "mounted_genesis"

            cmd.append( self.executable ) 
        else:
            cmd = [self.executable]
    
        if receiver == "":
            receiver = None
            code = input
            input = None
            cmd.append("--create")

        if statdump:
            cmd.append("--statdump")
        if code is not None:
            cmd.extend(["--code", code])
        if codeFile is not None:
            cmd.extend(["--codefile", codeFile])
        if genesis is not None:
            cmd.extend(["--prestate", genesis])
        if gas is not None:
            cmd.extend(["--gas","%d" % gas])
        if price is not None:
            cmd.extend(["--price","%d" % price] )
        if sender is not None:
            cmd.extend(["--sender", sender])
        if receiver is not None:
            cmd.extend(["--receiver", receiver])
        if input is not None and input != "":
            cmd.extend(['--input', input])
        if value is not None:
            cmd.extend(["--value", "%d" % value])
        if not memory:
            cmd.append("--nomemory")
        if json:
            cmd.append("--json")

        cmd.append("run")

        return self._start(cmd)

    def execute(self, code = None, codeFile = None, genesis = None, 
        gas = 4700000, price = None, json = False, statdump = False, 
        sender = None, receiver = None, memory = False, input = None, 
        value = None):

        proc = self.start(code,codeFile,genesis,gas,price,json,statdump,sender,receiver,memory,input,value)
        return finishProc(proc)

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        parsed_steps = []
        for line in output:
            logger.debug(line)
            if len(line) > 0 and line[0] == "{":
                try:
                    parsed_steps.append(json.loads(line))
                except Exception as e:
                    logger.warn('Exception parsing geth output:')
                    logger.warn(e)
        
        canon_steps = []
        try:
            if 'output' in parsed_steps[-1]:
                # last one is {"output":"","gasUsed":"0x34a48","time":4787059}
                # Remove    
                parsed_steps = parsed_steps[:-1]

            for step in parsed_steps:
                if 'stateRoot' in step.keys() and len(canon_steps):
                    # don't log stateRoot when tx doesnt execute, to match cpp and parity
                    # should be last step
                    canon_steps.append(step)
                    continue
                if step['op'] == 0:
                    # skip STOPs
                    continue
                if step['opName'] == "" or step['op'] not in opcodes.opcodes:
                    # invalid opcode
                    continue
                trace_step = {
                    'pc'  : step['pc'],
                    'gas': step['gas'],
                    'op': step['op'],
                    # we want a 0-based depth
                    'depth' : step['depth'] -1,
                    'stack' : step['stack'],
                }
                canon_steps.append(trace_step)
        except Exception as e:
            logger.warn('Exception parsing geth output:')
            logger.warn(e)

        return canon_steps



class ParityVM(VM):

    def __init__(self,executable="evmbin", docker = False):
        super().__init__(executable, docker)
    
    def execute(self, code = None, codeFile = None, genesis = None, 
        gas = 4700000, price = None, json = False, statdump=True, 
        sender= None, receiver = None, memory=False,  input = None,
        dontExecuteButReturnCommand = False):

        if self.docker: 
            cmd = ['docker', 'run','--rm']
            # If any files are referenced, they need to be mounted
            if genesis is not None:
                cmd.append('-v')
                cmd.append('%s:%s' % (genesis,"/mounted_genesis"))
                genesis = "mounted_genesis"

            cmd.append( self.executable ) 
        else:
            cmd = [self.executable]

        if codeFile is not None :
            with open(codeFile,"r") as f: 
                code = f.read()

        if code is not None:
            cmd.extend(["--code", strip_0x(code)])
        if genesis is not None : 
            cmd.extend(["--chain", genesis])
        if gas is not None: 
            cmd.extend(["--gas","%s" % hex(gas)[2:]])
        if price is not None:
            cmd.extend(["--gas-price","%d" % price] )
        if sender is not None: 
            cmd.extend(["--from", strip_0x(sender)])
        if receiver is not None:
            cmd.extend(["--to",strip_0x(receiver)])
        if input is not None:
            cmd.extend(["--input", input])
        if json: 
            cmd.append("--json")
        if dontExecuteButReturnCommand:
            return cmd

        return self._run(cmd)

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        parsed_steps = []
        for line in output:
            logger.debug(line)
            if len(line) > 0 and line[0] == "{":
                try:
                    parsed_steps.append(json.loads(line))
                except Exception as e:
                    logger.warn('Exception parsing parity output:')
                    logger.warn(e)

        canon_steps = []
        try:
            for p_step in parsed_steps:
                if 'stateRoot' in p_step.keys() and len(canon_steps):
                    # dont log the stateRoot for basic tx's (that have no EVM steps)
                    # should be last step
                    canon_steps.append(p_step)
                    continue

                # Ignored for now
                if 'error' in p_step.keys() or 'output' in p_step.keys():
                    continue

                if p_step['op'] == 0:
                    # skip STOPs
                    continue
                if p_step['opName'] == "" or p_step['op'] not in opcodes.opcodes:
                    # invalid opcode
                    continue
                trace_step = {
                    'pc'  : p_step['pc'],
                    'gas': p_step['gas'],
                    'op': p_step['op'],
                    # parity depth starts at 1, but we want a 0-based depth
                    'depth' : p_step['depth'] -1,
                    'stack' : p_step['stack'],
                }
                canon_steps.append(trace_step)
        except Exception as e:
            logger.warn('Exception parsing parity output:')
            logger.warn(e)

        return canon_steps



