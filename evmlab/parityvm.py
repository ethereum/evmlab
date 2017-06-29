import subprocess,os
FNULL = open(os.devnull, 'w')

class VM(object):
	"""Utility to execute geth `evm` """

	def __init__(self,executable="evmbin"):
		self.executable = executable

	def execute(self, code = None, codeFile = None, genesis = None, gas = 4700000, json = False, statdump=True, sender= None, memory=False,  input = None):

		cmd = [self.executable]

		if codeFile is not None :
			with open(codeFile,"r") as f: 
				code = f.read()

		if code is not None : 
			cmd.append("--code")
			cmd.append(code)


		if genesis is not None : 
			cmd.append("--chain")
			cmd.append(genesis)

		if gas is not None: 
			cmd.append("--gas")
			cmd.append("%s" % hex(gas)[2:])
		
		if sender is not None: 
			cmd.append("--from")
			cmd.append(sender)

		if input is not None:
			cmd.append("--input")
			cmd.append(input)
#
#		if not memory:
#			cmd.append("--nomemory")
		if json: 
			cmd.append("--json")

#		cmd.append("run")
		print " ".join(cmd)
		return subprocess.check_output(cmd).strip().split("\n")