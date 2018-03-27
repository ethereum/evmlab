import os
import json
from .opcodes import opcodes
from . import compiler

OPCODE_FORMATS = {
    "ADD":          "{0} + {1}",
    "SUB":          "{0} - {1}",
    "EXP":          "{0} ** {1}",
    "MUL":          "{0} * {1}",
    "DIV":          "{0} / {1}",
    "EQ":           "{0} == {1}",
    "LT":           "{0} < {1}",
    "GT":           "{0} > {1}",
    "AND":          "{0} & {1}",
    "OR":           "{0} | {1}",
    "XOR":          "{0} ^ {1}",
    "NOT":          "!{0}",
    "ISZERO":       "{0} == 0",
    "JUMP":         "JUMP(pc={0})",
    "JUMPI":        "JUMPI(pc={0}, cond={1})",
    "MLOAD":        "MLOAD(off={0})",
    "MSTORE":       "MSTORE(off={0}, data={1})",
    "SHA3":         "SHA3(off={0}, len={1})",
    "SLOAD":        "SLOAD(addr={0})",
    "SSTORE":       "SSTORE(addr={0}, data={1})",
    "CALL":         "CALL(gas={0}, addr={1}, value={2}, in={3}, insize={4}, out={5}, outsize={6})",
    "DELEGATECALL": "DELEGATECALL(gas={0}, addr={1}, in={2}, insize={3}, out={4}, outsize={5})",
    "STATICCALL":   "STATICCALL(gas={0}, addr={1}, in={2}, insize={3}, out={4}, outsize={5})",
    "CALL":         "CALL(gas={0}, addr={1}, value={2}, in={3}, insize={4}, out={5}, outsize={6})",
    "EXTCODECOPY":  "EXTCODECOPY(addr={0}, to={1}, from={2}, size={3}))",
    "CODECOPY":     "CODECOPY(to={1}, from={2}, size={3}))",
    "CREATE":       "CREATE(val={0}, offset={1}, size={2})"
}

def opinfo(opcode):
    if opcode in opcodes.keys():
        return opcodes[opcode]
    return "INVALID",0,0,0

class Annotable(object):
    def __init__(self):
        self.annotations = {}
        super(Annotable, self).__init__()

    def setAnnotation(self, obj):
        self.annotations[type(obj)] = obj


class OpcodeNode(Annotable):
    def __init__(self, pc, depth, opcode, args, result):
        super(OpcodeNode, self).__init__()
        self.pc = pc
        self.opcode = opcode
        self.depth = depth
        self.opname, self.ins, self.outs, self.gas = opinfo(opcode)
        self.args = args
        self.result = result

    def __str__(self):
        if self.opname in OPCODE_FORMATS:
            fmt = OPCODE_FORMATS[self.opname].format(*self.args)
        else:
            fmt = "{0}({1})".format(self.opname, ', '.join(self.args))
        if self.result:
            return "{0:40} -> {1}".format(fmt, ', '.join(self.result))
        else:
            return fmt

    def toHtml(self):
        if self.opname in OPCODE_FORMATS:
            fmt = OPCODE_FORMATS[self.opname].format(*self.args)
        else:
            fmt = "{0}({1})".format(self.opname, ', '.join(self.args))
        if self.result:
            return "{0:40} -> {1}".format(fmt, ', '.join(self.result))
        else:
            return fmt

class CallNode(OpcodeNode):
    def __init__(self, pc, depth, opcode, args, result, ops):
        super(CallNode, self).__init__(pc, depth, opcode, args, result)
        self.ops = ops


class PushNode(OpcodeNode):
    def __init__(self, pc, depth, opcode, args, result):
        super(PushNode, self).__init__(pc, depth, opcode, args, result)

    def __str__(self):
        return self.result[0]

    def toHtml(self):
        return str(self)


def buildAST(trace):
    ops = []
    stack = []
    pc = 0

    for step in trace:
        pc = step.get('pc', pc)
        if step['op'] in opcodes.keys():
            opname, ins, outs, gas = opcodes[step['op']]
        else:
            opname, ins, outs,gas = "INVALID",0,0,0

        if ins > 0:
            args = stack[-ins:][::-1]
            stack = stack[:-ins]
        else:
            args = []
        if 'ops' in step:
            ops.append(CallNode(pc, step['depth'], step['op'], args, step['result'], buildAST(step['ops'])))
        elif opname.startswith('PUSH'):
            ops.append(PushNode(pc, step['depth'], step['op'], args, step['result']))
        else:
            ops.append(OpcodeNode(pc, step['depth'], step['op'], args, step['result']))
        pc += step.get('len', 1)
        stack.extend(step['result'][::-1])
    return ops


class TransactionTrace(Annotable):
    def __init__(self, ops):
        super(TransactionTrace, self).__init__()
        self.ops = ops

    @classmethod
    def build(cls, trace):
        return TransactionTrace(buildAST(trace))

    def __str__(self):
        lines = []
        stack = [(self, 0)]
        while stack:
            call, startidx = stack.pop()
            for i in range(startidx, len(call.ops)):
                op = call.ops[i]
                lines.append("{0:>4} 0x{1:0>4x} {2}{3}".format(op.depth,op.pc, '  '*len(stack), str(op)))
                if hasattr(op, 'ops'):
                    stack.append((call, i + 1))
                    stack.append((op, 0))
                    break
                elif hasattr(op, 'expression') and hasattr(op.expression, 'ops'):
                    stack.append((call, i + 1))
                    stack.append((op.expression, 0))
                    break
        return '\n'.join(lines)

    def iterator(self):
        #lines = []
        stack = [(self, 0)]
        while stack:
            call, startidx = stack.pop()
            for i in range(startidx, len(call.ops)):
                op = call.ops[i]
                yield (len(stack), op)
                #lines.append("0x{0:0>4x} {1}{2}".format(op.pc, '  '*len(stack), str(op)))
                if hasattr(op, 'ops'):
                    stack.append((call, i + 1))
                    stack.append((op, 0))
                    break
                elif hasattr(op, 'expression') and hasattr(op.expression, 'ops'):
                    stack.append((call, i + 1))
                    stack.append((op.expression, 0))
                    break
        #return '\n'.join(lines)


class ReachingDefinitions(list):
    """Encapsulates a list of the sources of each argument to an operation."""


class ReachesDefinitions(list):
    """Encapsulates a list of the consumers of an operation's output."""


class VariableName(str):
    """Annotation for variable name assignments."""


class AssignmentStatement(object):
    def __init__(self, depth, pc, varname, expression):
        self.pc = pc
        self.depth = depth
        self.varname = varname
        self.expression = expression

    def __str__(self):
        return "{0} = {1}".format(self.varname, self.expression)


class ExpressionStatement(object):
    def __init__(self, depth, pc, expression):
        self.pc = pc
        self.depth = depth
        self.expression = expression

    def __str__(self):
        return str(self.expression)


class VariableExpression(object):
    def __init__(self, depth, varname):
        self.varname = varname
        self.depth = depth

    def __str__(self):
        return self.varname


class OperationExpression(object):
    def __init__(self, depth, op, args):
        self.op = op
        self.depth = depth
        self.args = args

    @property
    def opname(self):
        return self.op.opname

    @property
    def pc(self):
        return self.op.pc

    def __str__(self):
        if self.op.opname in OPCODE_FORMATS:
            return OPCODE_FORMATS[self.op.opname].format(*self.args)
        else:
            return "{0}({1})".format(self.opname, ', '.join(map(str, self.args)))


class CallExpression(OperationExpression):
    def __init__(self, depth,op, args, ops):
        super(CallExpression, self).__init__(depth, op, args)
        self.ops = ops


class LiteralExpression(OperationExpression):
    def __init__(self, depth, value):
        self.value = value
        self.depth = depth

    def __str__(self):
        return self.value


def findReachings(ast):
    stack = []
    for op in ast.ops:
        if op.ins > 0:
            args = stack[-op.ins:]
            stack = stack[:-op.ins]
        else:
            args = []
        if op.opname.startswith('DUP'):
            stack.extend(args)
            stack.append(args[0])
        elif op.opname.startswith('SWAP'):
            stack.append(args[-1])
            stack.extend(args[1:-1])
            stack.append(args[0])
        else:
            for arg in args:
                arg.annotations[ReachesDefinitions].append(op)
            op.setAnnotation(ReachingDefinitions(args[::-1]))
            op.setAnnotation(ReachesDefinitions())
            stack.extend([op] * op.outs)
        if hasattr(op, 'ops'):
            findReachings(op)


def nameIterator():
    prefixIterator = nameIterator()
    prefix = ""
    while True:
        for i in "abcdefghijklmnopqrstuvwxyz":
            yield prefix + i
        prefix = next(prefixIterator)


def buildExpression(op):
    subexps = []
    for arg in op.annotations[ReachingDefinitions]:
        if VariableName in arg.annotations:
            subexps.append(VariableExpression(op.depth, arg.annotations[VariableName]))
        else:
            subexps.append(buildExpression(arg))
    if isinstance(op, CallNode):
        return CallExpression(op.depth, op, subexps, composeOperations(op.ops))
    elif isinstance(op, PushNode):
        return LiteralExpression(op.depth, op.result[0])
    else:
        return OperationExpression(op.depth, op, subexps)


def composeOperations(ops):
    varnames = nameIterator()
    statements = []
    for op in ops:
        # Ignore SWAP and DUP, which don't have annotations
        if ReachingDefinitions not in op.annotations:
            continue
        reaches = op.annotations[ReachesDefinitions]
        if not op.opname.startswith('PUSH'):
            if len(reaches) == 0:
                statements.append(ExpressionStatement(op.depth, op.pc, buildExpression(op)))
            elif len(reaches) > 1 or isinstance(op, CallNode):
                varname = next(varnames)
                op.setAnnotation(VariableName(varname))
                statements.append(AssignmentStatement(op.depth, op.pc, varname, buildExpression(op)))
    return statements


def trace(web3, txid, compose = True):
    result = web3._requestManager.request_blocking('debug_traceTransaction', (txid, {'tracer': tracer}))
    ast = TransactionTrace.build(result)
    findReachings(ast)
    if compose: 
        ast = TransactionTrace(composeOperations(ast.ops))
 
    return ast

def traceEvmOutput(tracefile, compose = True):
    result = evmResult(tracefile)
    ast = TransactionTrace.build(result)
    findReachings(ast)
    if compose: 
        ast = TransactionTrace(composeOperations(ast.ops))
 
    return ast

def evmResult(tracefile):

    def isPush(op):
        return op >= compiler.PUSH1 and op <= compiler.PUSH32 

    res = {
        'stack' : [{"ops" : []}]
    }
    npushes = {0: 0, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 16: 1, 17: 1, 18: 1, 19: 1, 20: 1, 21: 1, 22: 1, 23: 1, 24: 1, 25: 1, 26: 1, 32: 1, 48: 1, 49: 1, 50: 1, 51: 1, 52: 1, 53: 1, 54: 1, 55: 0, 56: 1, 57: 0, 58: 1, 59: 1, 60: 0, 61: 1, 62: 0, 64: 1, 65: 1, 66: 1, 67: 1, 68: 1, 69: 1, 80: 0, 81: 1, 82: 0, 83: 0, 84: 1, 85: 0, 86: 0, 87: 0, 88: 1, 89: 1, 90: 1, 91: 0, 96: 1, 97: 1, 98: 1, 99: 1, 100: 1, 101: 1, 102: 1, 103: 1, 104: 1, 105: 1, 106: 1, 107: 1, 108: 1, 109: 1, 110: 1, 111: 1, 112: 1, 113: 1, 114: 1, 115: 1, 116: 1, 117: 1, 118: 1, 119: 1, 120: 1, 121: 1, 122: 1, 123: 1, 124: 1, 125: 1, 126: 1, 127: 1, 128: 2, 129: 3, 130: 4, 131: 5, 132: 6, 133: 7, 134: 8, 135: 9, 136: 10, 137: 11, 138: 12, 139: 13, 140: 14, 141: 15, 142: 16, 143: 17, 144: 2, 145: 3, 146: 4, 147: 5, 148: 6, 149: 7, 150: 8, 151: 9, 152: 10, 153: 11, 154: 12, 155: 13, 156: 14, 157: 15, 158: 16, 159: 17, 160: 0, 161: 0, 162: 0, 163: 0, 164: 0, 240: 1, 241: 1, 242: 1, 243: 0, 244: 0, 255: 0}

    with open(tracefile) as f:
        for line in f:
        
            log = json.loads(line)
            if 'output' in log.keys():
                return res['stack'][0]['ops']

            def peek(n):
                return int(log['stack'][-1-n],16)

            def isOp(op):
                return log['op'] == op

            d = ' '.ljust(log['depth']*4)

            if log['depth'] != len(res['stack']):
                res['stack'] = res['stack'][0:-1]
            #print("line", line)
            try:
                frame = res['stack'][-1]
            except Exception as e:
                print(res)
                print(line)
                raise e

            if log['depth'] == len(res['stack']):
                opinfo = {
                "op" : log['op'], 
                "depth" : log['depth'],
                'result' : [],
                }
                if len(frame['ops']) > 0:
                    prevop = frame['ops'][-1]
                    for i in range(0,npushes[prevop['op']]):
                        prevop['result'].append(hex(peek(i)))

                if isOp(compiler.CALL) or isOp(compiler.CALLCODE) or isOp(compiler.DELEGATECALL) or isOp(compiler.STATICCALL):
                    opinfo["error"] = None;
                    opinfo["return"] = None;
                    opinfo["ops"] = [];
                    opinfo["gas"]   = peek(0)
                    opinfo["to"]    = peek(1)

                    if isOp(compiler.DELEGATECALL) or isOp(compiler.STATICCALL):
                        instart = peek(-2)
                        insize  = peek(-3)
                    else:
                        opinfo["value"] = peek(2)
                        instart = peek(3)
                        insize  = peek(4)

                    opinfo["input"] = log['memory'][instart: instart + insize];
                    res['stack'].append(opinfo)

                elif isOp(compiler.RETURN):
                    out = peek(0)
                    outsize = peek(1)
                    print("Out" , out)
                    print("Outsize", outsize)
                    frame['return'] = log['memory'][out:out+outsize]
                elif isOp(compiler.STOP) or isOp(compiler.SELFDESTRUCT):
                    frame['return'] = None
                elif isOp(compiler.JUMPDEST):
                    opinfo['pc'] = log['pc']

                if isPush(log['op']):
                    opinfo['len'] = log['op'] - 0x5e

                frame['ops'].append(opinfo)

        
def testFile(fname):
    testfile = os.path.join(os.path.dirname(__file__), fname)
    ast = traceEvmOutput(testfile)
    print(str(ast))
    print("OK")

if __name__ == '__main__':
#    testFile("example_trace.txt")
    testFile("example_trace2.txt")
