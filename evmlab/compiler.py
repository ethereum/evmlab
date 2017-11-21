STOP          = 0x00 # Pops: 0, Pushes: 0, Gas: 0],
ADD           = 0x01 # Pops: 2, Pushes: 1, Gas: 3],
MUL           = 0x02 # Pops: 2, Pushes: 1, Gas: 5],
SUB           = 0x03 # Pops: 2, Pushes: 1, Gas: 3],
DIV           = 0x04 # Pops: 2, Pushes: 1, Gas: 5],
SDIV          = 0x05 # Pops: 2, Pushes: 1, Gas: 5],
MOD           = 0x06 # Pops: 2, Pushes: 1, Gas: 5],
SMOD          = 0x07 # Pops: 2, Pushes: 1, Gas: 5],
ADDMOD        = 0x08 # Pops: 3, Pushes: 1, Gas: 8],
MULMOD        = 0x09 # Pops: 3, Pushes: 1, Gas: 8],
EXP           = 0x0a # Pops: 2, Pushes: 1, Gas: 10],
SIGNEXTEND    = 0x0b # Pops: 2, Pushes: 1, Gas: 5],
LT            = 0x10 # Pops: 2, Pushes: 1, Gas: 3],
GT            = 0x11 # Pops: 2, Pushes: 1, Gas: 3],
SLT           = 0x12 # Pops: 2, Pushes: 1, Gas: 3],
SGT           = 0x13 # Pops: 2, Pushes: 1, Gas: 3],
EQ            = 0x14 # Pops: 2, Pushes: 1, Gas: 3],
ISZERO        = 0x15 # Pops: 1, Pushes: 1, Gas: 3],
AND           = 0x16 # Pops: 2, Pushes: 1, Gas: 3],
OR            = 0x17 # Pops: 2, Pushes: 1, Gas: 3],
XOR           = 0x18 # Pops: 2, Pushes: 1, Gas: 3],
NOT           = 0x19 # Pops: 1, Pushes: 1, Gas: 3],
BYTE          = 0x1a # Pops: 2, Pushes: 1, Gas: 3],
SHA3          = 0x20 # Pops: 2, Pushes: 1, Gas: 30],
ADDRESS       = 0x30 # Pops: 0, Pushes: 1, Gas: 2],
BALANCE       = 0x31 # Pops: 1, Pushes: 1, Gas: 20],
ORIGIN        = 0x32 # Pops: 0, Pushes: 1, Gas: 2],
CALLER        = 0x33 # Pops: 0, Pushes: 1, Gas: 2],
CALLVALUE     = 0x34 # Pops: 0, Pushes: 1, Gas: 2],
CALLDATALOAD  = 0x35 # Pops: 1, Pushes: 1, Gas: 3],
CALLDATASIZE  = 0x36 # Pops: 0, Pushes: 1, Gas: 2],
CALLDATACOPY  = 0x37 # Pops: 3, Pushes: 0, Gas: 3],
CODESIZE      = 0x38 # Pops: 0, Pushes: 1, Gas: 2],
CODECOPY      = 0x39 # Pops: 3, Pushes: 0, Gas: 3],
GASPRICE      = 0x3a # Pops: 0, Pushes: 1, Gas: 2],
EXTCODESIZE   = 0x3b # Pops: 1, Pushes: 1, Gas: 20],
EXTCODECOPY   = 0x3c # Pops: 4, Pushes: 0, Gas: 20],
RETURNDATASIZE= 0x3D
RETURNDATACOPY= 0x3E
BLOCKHASH     = 0x40 # Pops: 1, Pushes: 1, Gas: 20],

COINBASE      = 0x41 # Pops: 0, Pushes: 1, Gas: 2],
TIMESTAMP     = 0x42 # Pops: 0, Pushes: 1, Gas: 2],
NUMBER        = 0x43 # Pops: 0, Pushes: 1, Gas: 2],
DIFFICULTY    = 0x44 # Pops: 0, Pushes: 1, Gas: 2],
GASLIMIT      = 0x45 # Pops: 0, Pushes: 1, Gas: 2],
POP           = 0x50 # Pops: 1, Pushes: 0, Gas: 2],
MLOAD         = 0x51 # Pops: 1, Pushes: 1, Gas: 3],
MSTORE        = 0x52 # Pops: 2, Pushes: 0, Gas: 3],
MSTORE8       = 0x53 # Pops: 2, Pushes: 0, Gas: 3],
SLOAD         = 0x54 # Pops: 1, Pushes: 1, Gas: 50],
SSTORE        = 0x55 # Pops: 2, Pushes: 0, Gas: 0],
JUMP          = 0x56 # Pops: 1, Pushes: 0, Gas: 8],
JUMPI         = 0x57 # Pops: 2, Pushes: 0, Gas: 10],
PC            = 0x58 # Pops: 0, Pushes: 1, Gas: 2],
MSIZE         = 0x59 # Pops: 0, Pushes: 1, Gas: 2],
GAS           = 0x5a # Pops: 0, Pushes: 1, Gas: 2],
JUMPDEST      = 0x5b # Pops: 0, Pushes: 0, Gas: 1],
LOG0          = 0xa0 # Pops: 2, Pushes: 0, Gas: 375],
LOG1          = 0xa1 # Pops: 3, Pushes: 0, Gas: 750],
LOG2          = 0xa2 # Pops: 4, Pushes: 0, Gas: 1125],
LOG3          = 0xa3 # Pops: 5, Pushes: 0, Gas: 1500],
LOG4          = 0xa4 # Pops: 6, Pushes: 0, Gas: 1875],
CREATE        = 0xf0 # Pops: 3, Pushes: 1, Gas: 32000],
CREATE2       = 0xfb # 
CALL          = 0xf1 # Pops: 7, Pushes: 1, Gas: 40],
CALLCODE      = 0xf2 # Pops: 7, Pushes: 1, Gas: 40],
RETURN        = 0xf3 # Pops: 2, Pushes: 0, Gas: 0],
DELEGATECALL  = 0xf4 # Pops: 6, Pushes: 0, Gas: 40],
STATICCALL    = 0xfa
REVERT        = 0xfd
SUICIDE       = 0xff # Pops: 1, Pushes: 0, Gas: 0],
SELFDESTRUCT  = 0xff # Pops: 1, Pushes: 0, Gas: 0],

PUSH1         =0x60
PUSH32        =0x7f

DUP1  = 0x80
DUP2  = 0x81
DUP3  = 0x82
DUP4  = 0x83
DUP5  = 0x84
DUP6  = 0x85
DUP7  = 0x86
DUP8  = 0x87
DUP9  = 0x88
DUP10 = 0x89
DUP11 = 0x8a
DUP12 = 0x8b
DUP13 = 0x8c
DUP14 = 0x8d
DUP15 = 0x8e
DUP16 = 0x8f

SWAP1  = 0x90
SWAP2  = 0x91
SWAP3  = 0x92
SWAP4  = 0x93
SWAP5  = 0x94
SWAP6  = 0x95
SWAP7  = 0x96
SWAP8  = 0x97
SWAP9  = 0x98
SWAP10 = 0x99
SWAP11 = 0x9a
SWAP12 = 0x9b
SWAP13 = 0x9c
SWAP14 = 0x9d
SWAP15 = 0x9e
SWAP16 = 0x9f

import sys

def bytecode(value):

	typ = type(value)
	if typ == str and value[:2] == "0x":
		value = value[2:]

	if typ in [float, int]:
		value = '{0:02x}'.format(int(value))

	if sys.version_info < (3, 0):
		if typ == unicode and value[:2] == "0x":
			value = value[2:]
		if typ == long:
			value = '{0:02x}'.format(int(value))

	value = ('0' * (len(value) % 2)) + value
	return value

class Program():

	def __init__(self):
		self.compiled = []
		self.ops = []
		self.mstore= lambda index,value: self.push(value).push(index).op(MSTORE)
		self.mstore8= lambda index,value: self.push(value).push(index).op(MSTORE8)
		self.add =   lambda x,y: self.push(y).push(x).op(ADD)
		self.sub =   lambda x,y: self.push(y).push(x).op(SUB)
		self.mul =   lambda x,y: self.push(y).push(x).op(MUL)
		self.div =   lambda x,y: self.push(y).push(x).op(DIV)
		self.sdiv =  lambda x,y: self.push(y).push(x).op(SDIV)
		self.mod =   lambda x,y: self.push(y).push(x).op(MOD)
		self.smod =  lambda x,y: self.push(y).push(x).op(SMOD)
		self.exp =   lambda x,y: self.push(y).push(x).op(EXP)

		self.create       = lambda v,p,s:self.push(s).push(p).push(v).op(CREATE)
		self.codecopy     = lambda t,f,s:self.push(s).push(f).push(t).op(CODECOPY)
		self.extcodecopy  = lambda a,t,f,s:self.push(s).push(f).push(t).push(a).op(CODECOPY)
		self.extcoodesize = lambda a:self.push(a).op(EXTCODESIZE)
		self.selfdestruct = lambda a: self.push(a).op(SUICIDE)

		#log without topics and data mem[p..(p+s))
		self.log0        = lambda p, s: self.push(s).push(p).op(LOG0)                  
		#log with topic t1 and data mem[p..(p+s))
		self.log1        = lambda p, s, t1: self.push(t1).push(s).push(p).op(LOG1)
		#log with topics t1, t2 and data mem[p..(p+s))
		self.log2        = lambda p, s, t1, t2: self.push(t2).push(t1).push(s).push(p).op(LOG3)
		#log with topics t1, t2, t3 and data mem[p..(p+s))
		self.log3        = lambda p, s, t1, t2, t3:  self.push(t3).push(t2).push(t1).push(s).push(p).op(LOG3)
		#log with topics t1, t2, t3, t4 and data mem[p..(p+s))
		self.log4        = lambda p, s, t1, t2, t3, t4: self.push(t4).push(t3).push(t2).push(t1).push(s).push(p).op(LOG3)
		self.jump        = lambda label : self.push(label).op(JUMP)
		self.jumpi        = lambda label,cond : self.push(cond).push(label).op(JUMPI)
		self.revert      = lambda  memStart, memSize: self.push(memSize).push(memStart).op(REVERT)

		
	def _add(self, x):
		if x == None:
			return self

		if type(x) == str:
			self.compiled.append(x)
		else:
			self.compiled.append(bytecode(x))

		return self

	def extend(self,program):
		self.compiled.extend(program.compiled)

	def _addOp(self,op,v = None):
		self._add(op)
		self._add(v)
		return self

	def op(self,x):
		self._add(x)
		return self

	def push(self,value):
		value = bytecode(value)
		length = len(value) / 2

		assert length <=32

		self._addOp(PUSH1+(length-1), bytecode(value));
		return self



	def call(self,gas ,address,value = 0,instart = 0, insize = 0, out = 0, outsize = 0):
		self.push(outsize)
		self.push(out)
		self.push(insize)
		self.push(instart)
		self.push(value)
		self.push(address)
		if gas is not None:
			self.push(gas)
		else:
			self.op(GAS)
		self._addOp(CALL)
		return self

	def callcode(self,gas ,address,value = 0,instart = 0, insize = 0, out = 0, outsize = 0):
		self.push(outsize)
		self.push(out)
		self.push(insize)
		self.push(instart)
		self.push(value)
		self.push(address)
		self.push(gas)
		self._addOp(CALLCODE)
		return self

	def delegatecall(self,gas ,address,instart = 0, insize = 0, out = 0, outsize = 0):
		self.push(outsize)
		self.push(out)
		self.push(insize)
		self.push(instart)
		self.push(address)
		if gas is not None:
			self.push(gas)
		else:
			self.op(GAS)
		self._addOp(DELEGATECALL)
		return self

	def staticcall(self,gas ,address,instart = 0, insize = 0, out = 0, outsize = 0):
		self.push(outsize)
		self.push(out)
		self.push(insize)
		self.push(instart)
		self.push(address)
		if gas is not None:
			self.push(gas)
		else:
			self.op(GAS)
		self._addOp(STATICCALL)
		return self

	def rreturn(self, memStart=0, memSize=0):
		self.push(memSize)
		self.push(memStart)
		self._addOp(RETURN)
		return self


	def bytecode(self):
		return "".join(self.compiled)

	def label(self):
		return len(self.bytecode()) / 2

	def jumpdest(self):
		here = self.label()
		self.op(JUMPDEST)
		return here
	

	def __str__(self):
		return ",".join(self.compiled)


