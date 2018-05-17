import os, signal, json, itertools, traceback, sys
from subprocess import Popen, PIPE, TimeoutExpired
import platform
import logging
import re
from . import opcodes
from . import parse_int_or_hex,decode_hex,remove_0x_head

logger = logging.getLogger()

FNULL = open(os.devnull, 'w')

valid_opcodes = opcodes.reverse_opcodes.keys()

# The 'stateRoot' output is missing from some clients (parity). 
# Enable this once they implement it
INCLUDE_STATEROOT=True

strip_0x = remove_0x_head
bstrToInt = lambda b_str: int(b_str.replace("b", "").replace("'", ""))
bstrToHex = lambda b_str: '0x{0:01x}'.format(bstrToInt(b_str))

def add_0x(str):
    if str in [None, "0x", ""]:
        return ""
    if str[:2] == "0x":
        return str
    return "0x" + str

def toHexQuantities(vals):
    """ Formats a list of values into a list of hex-encoded values """
    return ['0x{0:01x}'.format(parse_int_or_hex(val)) for val in vals]


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

        op['output'] = strip_0x(op['output'])
        fmt = "output {output} gasUsed {gasUsed}"
        if 'error' in op.keys():
            e = op['error']
            if e.lower().find("out of gas") > -1:   
                e = "OOG"
            fmt = fmt + " err: OOG"
        return fmt.format(**op)
    return "N/A"
""" Not used (??)
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
"""
def compare_traces(clients_canon_traces, names):

    """ Compare 'canonical' traces from the clients"""

    full_output = []
    log = lambda x: full_output.append(x)


    canon_traces = list(itertools.zip_longest(*clients_canon_traces))

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
            log('[*] {:>8} {}'.format("", step[0]))
        else:
            equivalent = False
            for i in range(0, num_clients):
                if i in wrong_clients or len(wrong_clients) == num_clients-1:
                    log('[!!] {:>7} {}'.format(names[i], step[i]))
                else:
                    log('[*] {:>8} {}'.format(names[i], step[i]))

    return (equivalent, full_output)


def startProc(cmd):
    # passing a list to Popen doesn't work. Can't read stdout from docker container when shell=False
    #pyeth_process = subprocess.Popen(pyeth_docker_cmd, shell=False, stdout=subprocess.PIPE, close_fds=True)

    # need to pass a string to Popen and shell=True to get stdout from docker container
    print(" ".join(cmd))
    return Popen(" ".join(cmd), stdout=PIPE,shell=True, stderr=PIPE, preexec_fn=os.setsid)


def finishProc(process, extraTime=False, output="stdout", timeout = 30):

    if extraTime:
        timeout = 45
    try:
        (stdoutdata, stderrdata) = process.communicate(timeout=timeout)
    except TimeoutExpired:
        logger.info("TIMEOUT ERROR!")
        os.killpg(process.pid, signal.SIGINT) # send signal to the process group
        (stdoutdata, stderrdata) = process.communicate()

    if output == 'stdout':
        return stdoutdata.decode().strip().split("\n")
    return stderrdata.decode().strip().split("\n")

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

class JsVM(VM):
    @staticmethod
    def canonicalized(output):
        steps = []
        for index, line in enumerate(output):
            if line and line.startswith('# {'):
                result = json.loads(line.strip('# '))
                steps.append(result)
        return steps


class HeraVM(VM):
    @staticmethod
    def canonicalized(output):
        from . import opcodes
        valid_opcodes = opcodes.reverse_opcodes.keys()

        steps = []
        for x in output:
            try:
                if len(x) > 0  and x[0] == "{":
                    step = json.loads(x)
                    if 'stateRoot' in step.keys() and INCLUDE_STATEROOT:
                      steps.append(step)
                    else:
                      step['gas'] = hex(step['gas'])
                      step['stack'] = step['stack'][::-1]
                      for i in range(0, len(step['stack'])):
                          step['stack'][i] = re.sub(r'0x0+([0-9a-f]+)$', '0x\g<1>', step['stack'][i])

                      steps.append(step)

            except Exception as e:
                logger.info('Exception parsing Hera json:')
                logger.info(e)
                logger.info('problematic line:')
                logger.info(x[:500])

        return steps


class CppVM(VM):

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        valid_opcodes = opcodes.reverse_opcodes.keys()

        steps = []
        for x in output:
            try:
                if x[0:2] == "[{":
                        steps = json.loads(x)

                if x[0:2] == "{\"":
                    # A bug in testeth
                    if x[-1] == '.':
                        x = x[:-1]

                    step = json.loads(x)
                    if 'stateRoot' in step.keys() and INCLUDE_STATEROOT:
                        steps.append(step)

            except Exception as e:
                logger.info('Exception parsing cpp json:')
                logger.info(e)
                logger.info('problematic line:')
                logger.info(x[:500])

        canon_steps = []

        try:
            for step in steps:
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

                # Sometimes, the last one is duplicated. let's just remove that, if so

                if len(canon_steps) > 1:
                    last = canon_steps[-1]
                    slast = canon_steps[-2]
                    if slast['depth'] == last['depth'] and slast['pc'] == last['pc']:
                        canon_steps = canon_steps[:-1]

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
            if 'stateRoot' in step.keys():
                # dont log stateRoot when tx doesnt execute, to match cpp and parity
                if len(canon_steps) and INCLUDE_STATEROOT:
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

    def makeCommand(self, **kwargs):
        cmd = []

        def get(v, default = None):
            if v in kwargs.keys() and kwargs[v]:
                return kwargs[v]
            return default

        def extend(v, flagname=None, default=None):
            if flagname == None:
                flagname = v

            if get(v, default=default):
                cmd.extend(["--%s" % flagname, str(get(v,default=default))])

        if self.docker: 
            cmd.extend(['docker', 'run', '--rm'])
            # If any files are referenced, they need to be mounted
            if get('genesis') is not None:
                genesis_mount = os.path.dirname(get('genesis'))
                cmd.append('-v')
                if platform.system() == 'Darwin':
                    cmd.append('%s:%s' % (os.path.join('/private', genesis_mount.strip('/')), genesis_mount))
                else:
                    cmd.append('%s:%s' % (genesis_mount, genesis_mount))

        cmd.append( self.executable ) 

        if get('receiver') == "":
            kwargs.pop("receiver", None)
            kwargs['code'] = kwargs.pop('input', "")
            cmd.append("--create")

        extend('code')
        extend('codeFile', 'codefile')
        extend('genesis', 'prestate')
        extend('gas', default=4700000)
        extend('sender')
        extend('receiver')
        extend('input')
        extend('value')

        if not get('memory'):
            cmd.append("--nomemory")
        if get('json'):
            cmd.append("--json")
        if get('statdump'):
            cmd.append("--statdump")
        if get('create'):
            cmd.append("--create")

        cmd.append("run")

        return cmd

    def start(self, **kwargs):
        return self._start(self.makeCommand(**kwargs))

    def execute(self, **kwargs):
        return finishProc(self.start(**kwargs))

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        parsed_steps = []
        for line in output:
            if len(line) > 0 and line[0] == "{":
                try:
                    parsed_steps.append(json.loads(line))
                except Exception as e:
                    logger.warn('Exception [1] parsing geth output:')
                    traceback.print_exc(file=sys.stdout)
                    logger.warn(e)

        canon_steps = []
        if len(parsed_steps) == 0:
            return canon_steps
            
        try:
            if 'output' in parsed_steps[-1]:
                # last one is {"output":"","gasUsed":"0x34a48","time":4787059}
                # Remove    
                parsed_steps = parsed_steps[:-1]

            for step in parsed_steps:
                if 'stateRoot' in step.keys() :
                    # don't log stateRoot when tx doesnt execute, to match cpp and parity
                    # should be last step
                    if len(canon_steps) and INCLUDE_STATEROOT:
                        canon_steps.append(step)
                    
                    continue


                # Ignored for now
                if 'error' in step.keys() and 'output' in step.keys():
                    continue
                if 'time' in step.keys():
                    continue

                if not 'op' in step.keys():
                    logger.warn("Missing 'op': %s" % str(step))
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
            logger.warn('Exception [2] parsing geth output:')
            traceback.print_exc(file=sys.stdout)
            logger.warn(e)

        return canon_steps



class ParityVM(VM):

    def __init__(self,executable="evmbin", docker = False):
        super().__init__(executable, docker)
    
    def makeCommand(self, **kwargs):
        
        def get(v, default = None):
            if v in kwargs.keys() and kwargs[v]:
                return kwargs[v]
            return default


        code = get('code')
        codeFile = get('codeFile')
        genesis = get('genesis')
        gas = get('gas')
        price = get('price')
        sender = get('sender')
        receiver = get('receiver')
        input = get('input')
        _json = get('json')
        
        if self.docker: 
            cmd = ['docker', 'run','--rm']
            # If any files are referenced, they need to be mounted
            if get('genesis') is not None:
                genesis_mount = os.path.dirname(get('genesis'))
                cmd.append('-v')
                if platform.system() == 'Darwin':
                    cmd.append('%s:%s' % (os.path.join('/private', genesis_mount.strip('/')), genesis_mount))
                else:
                    cmd.append('%s:%s' % (genesis_mount, genesis_mount))

            cmd.append( self.executable )
            cmd.append("/parity-evm")
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
        if _json: 
            cmd.append("--json")

        return cmd

    def start(self, **kwargs):
        return self._start(self.makeCommand(**kwargs))


    def execute(self, **kwargs):
        return finishProc(self.start(**kwargs))

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        parsed_steps = []
        for line in output:
            if len(line) > 0 and line[0] == "{":
                try:
                    parsed_steps.append(json.loads(line))
                except Exception as e:
                    logger.warn('Exception [1] parsing parity output:')
                    logger.warn(e)

        canon_steps = []
        try:
            for p_step in parsed_steps:
                if 'test' in p_step.keys():
                    # first step of trace has test name
                    continue

                if 'stateRoot' in p_step.keys():
                    # dont log the stateRoot for basic tx's (that have no EVM steps)
                    # should be last step
                    if len(canon_steps) and INCLUDE_STATEROOT:
                        canon_steps.append(step)
                    continue

                # Ignored for now
                if 'error' in p_step.keys() or 'output' in p_step.keys():
                    continue

                if not 'op' in p_step.keys():
                    logger.warn("Missing 'op': %s" % str(p_step))
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
            logger.warn('Exception [2] parsing parity output:')
            logger.warn(e)

        return canon_steps



