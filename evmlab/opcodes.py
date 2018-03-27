from copy import copy
import collections
import binascii

from . import parse_int_or_hex,decode_hex,remove_0x_head,bytearray_to_bytestr,encode_hex

# Taken from https://github.com/ethereum/pyethereum/blob/develop/ethereum/opcodes.py
# Done this way to reduce dependencies a bit
# schema: [opcode, ins, outs, gas]

opcodes = {
    0x00: ['STOP', 0, 0, 0],
    0x01: ['ADD', 2, 1, 3],
    0x02: ['MUL', 2, 1, 5],
    0x03: ['SUB', 2, 1, 3],
    0x04: ['DIV', 2, 1, 5],
    0x05: ['SDIV', 2, 1, 5],
    0x06: ['MOD', 2, 1, 5],
    0x07: ['SMOD', 2, 1, 5],
    0x08: ['ADDMOD', 3, 1, 8],
    0x09: ['MULMOD', 3, 1, 8],
    0x0a: ['EXP', 2, 1, 10],
    0x0b: ['SIGNEXTEND', 2, 1, 5],
    0x10: ['LT', 2, 1, 3],
    0x11: ['GT', 2, 1, 3],
    0x12: ['SLT', 2, 1, 3],
    0x13: ['SGT', 2, 1, 3],
    0x14: ['EQ', 2, 1, 3],
    0x15: ['ISZERO', 1, 1, 3],
    0x16: ['AND', 2, 1, 3],
    0x17: ['OR', 2, 1, 3],
    0x18: ['XOR', 2, 1, 3],
    0x19: ['NOT', 1, 1, 3],
    0x1a: ['BYTE', 2, 1, 3],
    0x20: ['SHA3', 2, 1, 30],
    0x30: ['ADDRESS', 0, 1, 2],
    0x31: ['BALANCE', 1, 1, 20],
    0x32: ['ORIGIN', 0, 1, 2],
    0x33: ['CALLER', 0, 1, 2],
    0x34: ['CALLVALUE', 0, 1, 2],
    0x35: ['CALLDATALOAD', 1, 1, 3],
    0x36: ['CALLDATASIZE', 0, 1, 2],
    0x37: ['CALLDATACOPY', 3, 0, 3],
    0x38: ['CODESIZE', 0, 1, 2],
    0x39: ['CODECOPY', 3, 0, 3],
    0x3a: ['GASPRICE', 0, 1, 2],
    0x3b: ['EXTCODESIZE', 1, 1, 20],
    0x3c: ['EXTCODECOPY', 4, 0, 20],
    0x3d: ['RETURNDATASIZE', 0, 1, 2],
    0x3e: ['RETURNDATACOPY', 3, 0, 3],
    0x40: ['BLOCKHASH', 1, 1, 20],
    0x41: ['COINBASE', 0, 1, 2],
    0x42: ['TIMESTAMP', 0, 1, 2],
    0x43: ['NUMBER', 0, 1, 2],
    0x44: ['DIFFICULTY', 0, 1, 2],
    0x45: ['GASLIMIT', 0, 1, 2],
    0x50: ['POP', 1, 0, 2],
    0x51: ['MLOAD', 1, 1, 3],
    0x52: ['MSTORE', 2, 0, 3],
    0x53: ['MSTORE8', 2, 0, 3],
    0x54: ['SLOAD', 1, 1, 50],
    0x55: ['SSTORE', 2, 0, 0],
    0x56: ['JUMP', 1, 0, 8],
    0x57: ['JUMPI', 2, 0, 10],
    0x58: ['PC', 0, 1, 2],
    0x59: ['MSIZE', 0, 1, 2],
    0x5a: ['GAS', 0, 1, 2],
    0x5b: ['JUMPDEST', 0, 0, 1],
    0xa0: ['LOG0', 2, 0, 375],
    0xa1: ['LOG1', 3, 0, 750],
    0xa2: ['LOG2', 4, 0, 1125],
    0xa3: ['LOG3', 5, 0, 1500],
    0xa4: ['LOG4', 6, 0, 1875],
    0xf0: ['CREATE', 3, 1, 32000],
    0xf1: ['CALL', 7, 1, 40],
    0xf2: ['CALLCODE', 7, 1, 40],
    0xf3: ['RETURN', 2, 0, 0],
    0xf4: ['DELEGATECALL', 6, 0, 40],
    0xfa: ['STATICCALL', 6, 1, 40],
    0xfd: ['REVERT', 2, 0, 0],
    0xff: ['SUICIDE', 1, 0, 0],
}

opcodesMetropolis = { 0x3d, 0x3e, 0xfa, 0xfd }

for i in range(1, 33):
    opcodes[0x5f + i] = ['PUSH' + str(i), 0, 1, 3]

for i in range(1, 17):
    opcodes[0x7f + i] = ['DUP' + str(i), i, i + 1, 3]
    opcodes[0x8f + i] = ['SWAP' + str(i), i + 1, i + 1, 3]

reverse_opcodes = {}
for o in opcodes:
    vars()[opcodes[o][0]] = opcodes[o]
    reverse_opcodes[opcodes[o][0]] = o

# Non-opcode gas prices
GDEFAULT = 1
GMEMORY = 3
GQUADRATICMEMDENOM = 512  # 1 gas per 512 quadwords
GSTORAGEREFUND = 15000
GSTORAGEKILL = 5000
GSTORAGEMOD = 5000
GSTORAGEADD = 20000
GEXPONENTBYTE = 10    # cost of EXP exponent per byte
GCOPY = 3             # cost to copy one 32 byte word
GCONTRACTBYTE = 200   # one byte of code in contract creation
GCALLVALUETRANSFER = 9000   # non-zero-valued call
GLOGBYTE = 8          # cost of a byte of logdata

GTXCOST = 21000       # TX BASE GAS COST
GTXDATAZERO = 4       # TX DATA ZERO BYTE GAS COST
GTXDATANONZERO = 68   # TX DATA NON ZERO BYTE GAS COST
GSHA3WORD = 6         # Cost of SHA3 per word
GSHA256BASE = 60      # Base c of SHA256
GSHA256WORD = 12      # Cost of SHA256 per word
GRIPEMD160BASE = 600  # Base cost of RIPEMD160
GRIPEMD160WORD = 120  # Cost of RIPEMD160 per word
GIDENTITYBASE = 15    # Base cost of indentity
GIDENTITYWORD = 3     # Cost of identity per word
GECRECOVER = 3000     # Cost of ecrecover op

GSTIPEND = 2300

GCALLNEWACCOUNT = 25000
GSUICIDEREFUND = 24000

# Anti-DoS HF changes
SLOAD_SUPPLEMENTAL_GAS = 150
CALL_SUPPLEMENTAL_GAS = 660
EXTCODELOAD_SUPPLEMENTAL_GAS = 680
BALANCE_SUPPLEMENTAL_GAS = 380
CALL_CHILD_LIMIT_NUM = 63
CALL_CHILD_LIMIT_DENOM = 64
SUICIDE_SUPPLEMENTAL_GAS = 5000


def parseCode(code):
    code = code[2:] if code[:2] == '0x' else code

    try:
        codes = [c for c in decode_hex(code)]
    except ValueError as e:
        print(code)
        raise Exception("Did you forget to link any libraries?") from e

    instructions = collections.OrderedDict()
    pc = 0
    length = None
    while pc < len(codes):
        try:
            opcode = opcodes[codes[pc]]
        except KeyError:
            opcode = ['INVALID', 0, 0, 0]
        if opcode[0][:4] == 'PUSH':
            opcode = copy(opcode)
            length = codes[pc] - 0x5f
            pushData = codes[pc + 1 : pc + length + 1]
            pushData = "0x" + encode_hex(bytearray_to_bytestr(pushData))
            if type(pushData) is not str:
                pushData = pushData.decode()
            opcode.append(pushData)

        instructions[pc] = opcode

        if length is not None:
            pc += length
            length = None
        pc += 1

    return instructions