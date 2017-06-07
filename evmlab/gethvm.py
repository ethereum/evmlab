import subprocess,os
FNULL = open(os.devnull, 'w')

class VM(object):
	"""Utility to execute geth `evm` """

	def __init__(self,executable="evm"):
		self.executable = executable

	def execute(self, code = None, codeFile = None, genesis = None, gas = 4700000, json = False, statdump=True):

		cmd = [self.executable]

		if statdump: 
			cmd.append("--statdump")

		if code is not None : 
			cmd.append("--code")
			cmd.append(code)

		if codeFile is not None : 
			cmd.append("--codefile")
			cmd.append(codeFile)

		if genesis is not None : 
			cmd.append("--prestate")
			cmd.append(genesis)

		if gas is not None: 
			cmd.append("--gas")
			cmd.append("%d" % gas)
		
		if json: 
			cmd.append("--json")

		cmd.append("run")
		print " ".join(cmd)
		return subprocess.check_output(cmd).strip().split("\n")
