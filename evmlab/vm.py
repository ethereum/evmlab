import os, signal, json
from subprocess import Popen, PIPE, TimeoutExpired
from ethereum.utils import parse_int_or_hex
import logging
logger = logging.getLogger()

FNULL = open(os.devnull, 'w')


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


class VM(object):

    def __init__(self,executable="evmbin", docker = False):
        self.executable = executable
        self.docker = docker
        self.genesis_format = "parity"
        self.lastCommand = ""

    def _run(self,cmd):
        self.lastCommand = " ".join(cmd)
        with Popen(cmd, stdout=PIPE, preexec_fn=os.setsid) as process:
            try:
                output = process.communicate(timeout=15)[0]
            except TimeoutExpired:
                os.killpg(process.pid, signal.SIGINT) # send signal to the process group
                output = process.communicate()[0]

        return output.decode().strip().split("\n")


class CppVM(VM):

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        valid_opcodes = opcodes.reverse_opcodes.keys()

        for x in output:
            if x[0:2] == "[{":
                steps = json.loads(x)
            logger.info(output)

        canon_steps = []

        for step in steps:
            logger.info(step)
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

        return canon_steps

class PyVM(VM):

    @staticmethod
    def canonicalized(output):
        from . import opcodes

        def formatStackItem(el):
            return '0x{0:01x}'.format(int(el.replace("b", "").replace("'", "")))

        def json_steps():
            for line in output:
                logger.info(line.rstrip() + "\r")
                if line.startswith("test_tx:"):
                    continue
                if line.startswith("tx_decoded:"):
                    continue
                json_index = line.find("{")
                if json_index >= 0:
                    yield(json.loads(line[json_index:]))

        canon_steps = []
        for step in json_steps():
 
            # geth logs code-out-of-range as a STOP, and we 
            # can't distinguish them from actual STOPs (that pyeth logs)
            if step['event'] == 'eth.vm.op.vm':
                if step['inst'] == 'STOP':
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

    def execute(self, code = None, codeFile = None, genesis = None, 
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

        if dontExecuteButReturnCommand:
            return cmd
        
        return self._run(cmd)

    @staticmethod
    def canonicalized(output):
        from . import opcodes
        # last one is {"output":"","gasUsed":"0x34a48","time":4787059}
        output = output[:-1] 

        steps = [json.loads(x) for x in output if x[0] == "{"]

        canon_steps = []
        for step in steps:
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
        steps = [json.loads(x) for x in output if x[0] == "{"]

        canon_steps = []
        for p_step in steps:
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
        
        return canon_steps



