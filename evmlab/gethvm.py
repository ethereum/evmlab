import os
import signal
from subprocess import Popen, PIPE, TimeoutExpired

FNULL = open(os.devnull, 'w')

class VM(object):
    """Utility to execute geth `evm` """

    def __init__(self,executable="evm", docker=False):
        self.executable = executable
        self.docker = docker
        self.genesis_format = "geth"
        self.lastCommand = ""

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
            cmd.append("--code")
            cmd.append(code)

        if codeFile is not None:
            cmd.append("--codefile")
            cmd.append(codeFile)

        if genesis is not None:
            cmd.append("--prestate")
            cmd.append(genesis)

        if gas is not None:
            cmd.append("--gas")
            cmd.append("%d" % gas)

        if price is not None:
            cmd.append("--price")
            cmd.append("%d" % price)
        
        if sender is not None:
            cmd.append("--sender")
            cmd.append(sender)

        if receiver is not None:
            cmd.append("--receiver")
            cmd.append(receiver)

        if input is not None and input != "":
            cmd.append("--input")
            cmd.append(input)

        if value is not None:
            cmd.append("--value")
            cmd.append("%d" % value)

        if not memory:
            cmd.append("--nomemory")
        if json:
            cmd.append("--json")

        cmd.append("run")


        if dontExecuteButReturnCommand:
            return cmd
        
        self.lastCommand = " ".join(cmd)

        with Popen(cmd, stdout=PIPE, preexec_fn=os.setsid) as process:
            try:
                output = process.communicate(timeout=15)[0]
            except TimeoutExpired:
                os.killpg(process.pid, signal.SIGINT) # send signal to the process group
                output = process.communicate()[0]
        return output.decode().strip().split("\n")


