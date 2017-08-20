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
from evmlab import gethvm
from evmlab import compiler as c
from evmlab import opcodes



OPCODES = {}
op_keys = opcodes.opcodes.keys()
for op_key in op_keys:
	name = opcodes.opcodes[op_key][0]
	OPCODES[name] = op_key



FORK_CONFIG = 'EIP158'
#FORK_CONFIG = 'Byzantium'


TESTS_PATH = '/ethereum/tests/GeneralStateTests'
CPP_TESTS_PATH = '/ethereum/tests'

TESTETH_COMMAND = 'testeth'


PRESTATE_TMP_FILE = 'prestate.json'


def getAllFiles():
	all_files = []
	for subdir, dirs, files in os.walk(TESTS_PATH):
		for file in files:
			test_file = os.path.join(subdir, file)
			if test_file.endswith('.json'):
				all_files.append(test_file)
	return all_files

def convertGeneralTest(test_file):
	with open(test_file) as json_data:
		test_folder = test_file.split(os.sep)[-2]
		
		general_test = json.load(json_data)
		#print("general_test:", general_test)
		for test_name in general_test:
			# should only be one test_name per file
			prestate = {}
			prestate['env'] = general_test[test_name]['env']
			prestate['pre'] = general_test[test_name]['pre']
			#print("prestate:", prestate)
			general_tx = general_test[test_name]['transaction']
			transactions = []
			for test_i in general_test[test_name]['post'][FORK_CONFIG]:
				test_tx = general_tx.copy()
				#print("general_tx:", general_tx)
				#print("test_i:", test_i)
				d_i = test_i['indexes']['data']
				g_i = test_i['indexes']['gas']
				v_i = test_i['indexes']['value']
				test_tx['data'] = general_tx['data'][d_i]
				test_tx['gasLimit'] = general_tx['gasLimit'][g_i]
				test_tx['value'] = general_tx['value'][v_i]
				#print("test_tx:", test_tx)
				test_dgv = (d_i, g_i, v_i)
				transactions.append((test_tx, test_dgv))
	return prestate, transactions



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
					print("Invalid json: %s" % outp)
					items.append({})
		yield items

def canon(str):
	if str in [None, "0x", ""]:
		return ""
	if str[:2] == "0x":
		return str
	return "0x" + str

def toText(op):
	if len(op.keys()) == 0:
		return "END"
	if 'pc' in op.keys():
		#return "pc {pc} op {op} gas {gas} cost {gasCost} depth {depth} stack {stack}".format(**op)
		return "pc {pc} op {op} gas {gas} depth {depth} stack {stack}".format(**op)
	elif 'output' in op.keys():
		op['output'] = canon(op['output'])
		return "output {output} gasUsed {gasUsed}".format(**op)
	return "N/A"


def bstrToInt(b_str):
	b_str = b_str.replace("b", "")
	b_str = b_str.replace("'", "")
	return int(b_str)

def bstrToHex(b_str):
	return '0x{0:01x}'.format(bstrToInt(b_str))

def toHexQuantities(vals):
	quantities = []
	for val in vals:
		val_int = parse_int_or_hex(val)
		quantities.append('0x{0:01x}'.format(val_int))
	return quantities




def doCpp(test_subfolder, test_name, test_dgv):
	# pass command as string to Popen
	cpp_cmd = TESTETH_COMMAND
	cpp_cmd += " -t StateTestsGeneral/" + test_subfolder + " --"
	cpp_cmd += " --singletest " + test_name
	#cpp_cmd += " --jsontrace '{ \"disableStorage\":true, \"disableMemory\":true }'"
	cpp_cmd += " --jsontrace '{ \"disableStorage\":true }'"
	cpp_cmd += " --singlenet " + FORK_CONFIG
	cpp_cmd += " -d " + str(test_dgv[0]) + " -g " + str(test_dgv[1]) + " -v " + str(test_dgv[2])
	cpp_cmd += " --testpath \"" + CPP_TESTS_PATH + "\""
	print("cpp_cmd:")
	print(cpp_cmd)
	cpp_p = subprocess.Popen(cpp_cmd, shell=True, stdout=subprocess.PIPE, close_fds=True)
	print("cpp_result:", cpp_p)

	"""
	# pass command as list to Popen
	cpp_cmd = []
	cpp_cmd.append(TESTETH_COMMAND)
	cpp_cmd.append("-t")
	cpp_cmd.append("StateTestsGeneral/"+test_subfolder)
	cpp_cmd.append("--")
	cpp_cmd.append("--singletest")
	cpp_cmd.append(test_name)
	cpp_cmd.append("--jsontrace")
	# cannot get the json options to pass in correctly with cpp_cmd as an array and shell=False
	cpp_cmd.append("'{\"disableStorage\":true,\"disableMemory\":true}'")
	cpp_cmd.append("--singlenet")
	cpp_cmd.append(FORK_CONFIG)
	cpp_cmd.append("-d")
	cpp_cmd.append(str(test_dgv[0]))
	cpp_cmd.append("-g")
	cpp_cmd.append(str(test_dgv[1]))
	cpp_cmd.append("-v")
	cpp_cmd.append(str(test_dgv[2]))
	cpp_cmd.append("--testpath")
	cpp_cmd.append(CPP_TESTS_PATH)
	print("cpp_cmd:")
	print(" ".join(cpp_cmd))
	cpp_p = subprocess.Popen(cpp_cmd, shell=False, stdout=subprocess.PIPE, close_fds=True)
	print("cpp_result:", cpp_p)
	"""

	cpp_out = []
	for cpp_line in cpp_p.stdout:
		cpp_out.append(cpp_line.decode())
		print(cpp_line.decode())

	cpp_steps = [] # if no output
	for c_line in cpp_out:
		if c_line[0:2] == '[{': # detect line with json trace
			cpp_steps = json.loads(c_line)
	
	canon_steps = []
	prev_step = {}
	for c_step in cpp_steps:
		trace_step = {}
		trace_step['pc'] = c_step['pc']
		c_step['opName'] = c_step['op']
		if c_step['op'] == 'INVALID':
			continue
		if c_step['op'] not in OPCODES:
			print("got cpp step for an unknown opcode:")
			print(c_step)
			continue
		trace_step['op'] = OPCODES[c_step['op']]
		c_step['gas'] = int(c_step['gas'])
		if c_step['op'] == 'STOP':
			continue
		trace_step['gas'] = '0x{0:01x}'.format(c_step['gas'])
		trace_step['depth'] = c_step['depth']
		trace_step['stack'] = toHexQuantities(c_step['stack'])
		prev_step = c_step
		canon_steps.append(toText(trace_step))

	return canon_steps




def doGeth(test_case, test_tx):
	genesis = gen.Genesis()
	for account_key in test_case['pre']:
		account = test_case['pre'][account_key]
		account['address'] = account_key
		genesis.addPrestateAccount(account)
	genesis.setCoinbase(test_case['env']['currentCoinbase'])
	genesis.setTimestamp(test_case['env']['currentTimestamp'])
	genesis.setGasLimit(test_case['env']['currentGasLimit'])
	genesis.setDifficulty(test_case['env']['currentDifficulty'])
	if FORK_CONFIG == 'Metropolis' or FORK_CONFIG == 'Byzantium':
		genesis.setMetropolisActivation(0)
	
	geth_genesis = genesis.geth()
	#print("geth_genesis:", geth_genesis)
	g_path = genesis.export_geth()
	
	input_data = test_tx['data']
	if input_data[0:2] == "0x":
		input_data = input_data[2:]
	
	tx_to = test_tx['to']
	tx_value = parse_int_or_hex(test_tx['value'])
	gas_limit = parse_int_or_hex(test_tx['gasLimit'])
	gas_price = parse_int_or_hex(test_tx['gasPrice'])
	block_gaslimit = parse_int_or_hex(test_case['env']['currentGasLimit'])
	
	if gas_limit > block_gaslimit:
		print("Tx gas limit exceeds block gas limit. not calling geth")
		return []
	
	sender = '0x' + getTxSender(test_tx)
	sender_balance = parse_int_or_hex(test_case['pre'][sender]['balance'])
	balance_required = (gas_price * gas_limit) + tx_value
	
	if balance_required > sender_balance:
		print("Insufficient balance. not calling geth")
		return []
	
	intrinsic_gas = getIntrinsicGas(test_tx)
	if tx_to == "":
		# create contract cost not included in getIntrinsicGas
		intrinsic_gas += 32000
	
	if gas_limit < intrinsic_gas:
		print("Insufficient startgas. not calling geth")
		return []
	
	if tx_to == "" and input_data == "":
		print("no init code. not calling geth")
		return []
	
	if tx_to in test_case['pre']:
		if 'code' in test_case['pre'][tx_to]:
			if test_case['pre'][tx_to]['code'] == '':
				print("To account in prestate has no code. not calling geth")
				return []
	
	vm = gethvm.VM("evm")
	print("executing geth vm.")
	g_output = vm.execute(genesis = g_path, gas = gas_limit, price = gas_price, json = True, sender = sender, receiver = tx_to, input = input_data, value = tx_value)
	print("geth vm executed. printing output:")
	for g_step in g_output:
		print(g_step)
	print("done with geth output.")
	
	g_output = g_output[:-1] # last one is {"output":"","gasUsed":"0x34a48","time":4787059}
	
	g_steps = []
	for step_txt in g_output:
		try:
			step = json.loads(step_txt)
			step['depth'] -= 1 # geth trace starts depth at 1, python at 0 (subtract to match)
			if step['op'] == 0:
				print("skipping STOP step")
				# skip STOP since they don't appear in python trace
				continue
			if step['opName'].startswith("Missing opcode"):
				print("skipping Missing opcode step.")
				continue
			del step['memory']
			del step['memSize']
			del step['error']
			g_steps.append(step)
		except Exception as e:
			print("exception e:", e)
	
	print("printing fixed geth trace:")
	g_canon_trace = []
	for g_step in g_steps:
		print(g_step)
		g_canon = toText(g_step)
		g_canon_trace.append(g_canon)
	return g_canon_trace



"""
docker run --volume=/absolute/path/prestate.json:/mounted_prestate cdetrio/pyethereum run_statetest.py mounted_prestate "{\"data\": \"\", \"gasLimit\": \"0x0a00000000\", \"gasPrice\": \"0x01\", \"nonce\": \"0x00\", \"secretKey\": \"0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8\", \"to\": \"0x0f572e5295c57f15886f9b263e2f6d2d6c7b5ec6\", \"value\": \"0x00\"}"
"""

def doPython(test_file, test_tx):
	print("executing pyeth vm.")
	tx_encoded = json.dumps(test_tx)
	tx_double_encoded = json.dumps(tx_encoded) # double encode to escape chars for command line
	print("tx_double_encoded:", tx_double_encoded)
	# command if not using a docker container
	#pyeth_p = subprocess.Popen(["python", "run_statetest.py", test_file, tx_double_encoded], shell=False, stdout=subprocess.PIPE, close_fds=True)
	prestate_path = os.path.abspath(test_file)
	mount_flag = prestate_path + ":" + "/mounted_prestate"
	pyeth_docker_cmd = ["docker", "run", "-i", "-t", "-v", mount_flag, "cdetrio/pyethereum", "run_statetest.py", "/mounted_prestate", tx_double_encoded]
	print(" ".join(pyeth_docker_cmd))
	# command as list doesn't work, cant read stdout from docker container when shell=False
	#pyeth_p = subprocess.Popen(pyeth_docker_cmd, shell=False, stdout=subprocess.PIPE, close_fds=True)
	# need to use string command and shell=True to get stdout from docker container
	pyeth_p = subprocess.Popen(" ".join(pyeth_docker_cmd), shell=True, stdout=subprocess.PIPE, close_fds=True)
	print("pyeth vm executed. printing python output")
	pyout = []
	for line in pyeth_p.stdout:
		line = line.decode()
		print(line, end='')
		if line.startswith("test_tx:"):
			continue
		if line.startswith("tx_decoded:"):
			continue
		json_pos = line.find('{')
		if json_pos >= 0:
			op_json = json.loads(line[json_pos:])
			pyout.append(op_json)
	print("done with py output.")
	print("pyout:", pyout)
	py_trace = []
	for py_step in pyout:
		trace_step = {}
		if py_step['event'] == 'eth.vm.op.vm':
			trace_step['pc'] = bstrToInt(py_step['pc'])
			trace_step['opName'] = py_step['op']
			trace_step['op'] = py_step['inst']
			trace_step['gas'] = bstrToHex(py_step['gas'])
			trace_step['depth'] = py_step['depth']
			if trace_step['opName'] == 'STOP':
				# geth logs code-out-of-range as a STOP, and we can't distinguish them from actual STOPs (that pyeth logs)
				continue
			hex_stack = []
			for el in py_step['stack']:
				el = el.replace("b", "")
				el = el.replace("'", "")
				el = int(el)
				hex_stack.append('0x{0:01x}'.format(el))
			trace_step['stack'] = hex_stack
			py_trace.append(trace_step)
		#else: # non-opcode python trace events (exits etc.)
		#	print(py_step)
	
	py_canon_trace = []
	for step in py_trace:
		py_canon_step = toText(step)
		py_canon_trace.append(py_canon_step)
	return py_canon_trace



DO_CLIENTS = ['PY', 'CPP']
#DO_CLIENTS = ['PY', 'CPP', 'GETH']


DO_TEST = None
DO_LIST = None

DO_TEST = 'callcall_00'
#DO_TEST = 'CALL_BoundsOOG'
#DO_TEST = 'shallowStack'
#DO_TEST = 'RevertOpcodeInCreateReturns'


SKIP_LIST = [
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
#'static_Call50000_ecrec',
#'static_Call50000_identity',
#'static_Call50000_identity2',
#'static_Call50000_rip160',
#'static_Call50000_sha256',
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


START_I = 0


def main():
	all_files = getAllFiles()
	fail_count = 0
	pass_count = 0
	failing_files = []
	file_i = 0
	for f in all_files:
		file_i += 1
		if file_i < START_I:
			continue
		if f.find("stMemoryTest") != -1:
			continue
		if f.find("stMemoryStressTest") != -1:
			continue
		if f.find("stQuadraticComplexityTest") != -1:
			continue
		with open(f) as json_data:
			general_test = json.load(json_data)
			test_name = list(general_test.keys())[0]
			if DO_TEST is not None and test_name != DO_TEST:
				continue
			if DO_LIST is not None and test_name not in DO_LIST:
				continue
			if test_name in SKIP_LIST:
				print("skipping test:", test_name)
				continue
			print("f:", f)
			print("test_name:", test_name + ".")
		try:
			prestate, txs_dgv = convertGeneralTest(f)
		except Exception as e:
			print("problem with test file, skipping.")
			continue
		print("prestate:", prestate)
		print("txs:", txs_dgv)
		with open(PRESTATE_TMP_FILE, 'w') as outfile:
			json.dump(prestate, outfile)
			
		with open(PRESTATE_TMP_FILE) as json_data:
			test_case = json.load(json_data)

		test_subfolder = f.split(os.sep)[-2]
		for tx_and_dgv in txs_dgv:
			tx = tx_and_dgv[0]
			tx_dgv = tx_and_dgv[1]
			print("f:", f)
			print("test_name:", test_name + ".")
			
			equivalent = True
			py_canon_trace = doPython(PRESTATE_TMP_FILE, tx)
			cpp_canon_trace = doCpp(test_subfolder, test_name, tx_dgv)
			if 'GETH' in DO_CLIENTS:
				geth_canon_trace = doGeth(test_case, tx)
			else:
				geth_canon_trace = []
			#print("got cpp_canon_trace:", cpp_canon_trace)
			canon_traces = list(itertools.zip_longest(py_canon_trace, geth_canon_trace, cpp_canon_trace)) # py3
			print("comparing traces:")
			for steps in canon_traces:
				[py, geth, cpp] = steps
				if 'GETH' in DO_CLIENTS:
					if py == cpp and py == geth:
						print("[*]          %s" % py)
					elif py == cpp and py != geth:
						print("[*]    PY:>> %s \n" % (py))
						print("[*]   CPP:>> %s \n" % (cpp))
						print("[!!] GETH:>> %s \n" % (geth))
					else:
						equivalent = False
						print("[!!] GETH:>> %s \n" % (geth))
						print("[!!]   PY:>> %s \n" % (py))
						print("[!!]  CPP:>> %s \n" % (cpp))
				else:
					if py == cpp:
						print("[*]          %s" % py)
					else:
						equivalent = False
						print("[!!]   PY:>> %s \n" % (py))
						print("[!!]  CPP:>> %s \n" % (cpp))

			if equivalent is False:
				fail_count += 1
				print("CONSENSUS BUG!!!\a")
				failing_files.append(test_name)
			else:
				pass_count += 1
				print("equivalent.")
			print("f/p/t:", fail_count, pass_count, (fail_count + pass_count))
			print("failures:", failing_files)

	print("fail_count:", fail_count)
	print("pass_count:", pass_count)
	print("total:", fail_count + pass_count)




"""
## could not get redirect_stdout to work
## need to get this working for python-afl fuzzer
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
	print("main.")
	#import afl
	#afl.start()
	main()

sys.argv
