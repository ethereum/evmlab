#!/usr/bin/env python3
import urwid, argparse, traceback
import json,sys
# Python3 support
try:
    xrange(0,1);
except NameError:
    xrange = range;


def bold(text):
    return '\033[1m{}\033[0m'.format(text)


description = """
Tool to explore a json-trace in a debug-like interface
"""
examples = """

# Analyse a trace

python3 traceviewer.py -f example.json
"""

parser = argparse.ArgumentParser(description=description,epilog = examples,formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-f","--file", type=str, help="File to load")

def getStackAnnotations(opcode):
    """ 
    Returns a list of annotations for stack elements, given the opcode 'op'. 
    Example, ifcode = CALL:
    ['gas', 'address','value', 'instart', 'insize', 'outstart', 'outsize']
    """

    opcodes = {
        0x00: ['STOP', 0, 0, 0, []],
        0x01: ['ADD', 2, 1, 3, ['operand', 'operand']],
        0x02: ['MUL', 2, 1, 5, ['operand', 'operand']],
        0x03: ['SUB', 2, 1, 3, ['operand', 'operand']],
        0x04: ['DIV', 2, 1, 5, ['numerator', 'denominator']],
        0x05: ['SDIV', 2, 1, 5, ['numerator', 'denominator']],
        0x06: ['MOD', 2, 1, 5, ['x', 'modulator']],
        0x07: ['SMOD', 2, 1, 5,['x', 'modulator']],
        0x08: ['ADDMOD', 3, 1, 8,['operand', 'operand', 'modulator']],
        0x09: ['MULMOD', 3, 1, 8, ['operand', 'operand', 'modulator']],
        0x0a: ['EXP', 2, 1, 10, ['base','exponent']],
        0x0b: ['SIGNEXTEND', 2, 1, 5, ['byte','bit']],
        0x10: ['LT', 2, 1, 3, ['x','y'] ],
        0x11: ['GT', 2, 1, 3, ['x','y'] ],
        0x12: ['SLT', 2, 1, 3, ['x','y'] ],
        0x13: ['SGT', 2, 1, 3, ['x','y'] ],
        0x14: ['EQ', 2, 1, 3, ['x','y'] ],
        0x15: ['ISZERO', 1, 1, 3, ['x'] ],
        0x16: ['AND', 2, 1, 3, ['x','y'] ],
        0x17: ['OR', 2, 1, 3, ['x','y'] ],
        0x18: ['XOR', 2, 1, 3, ['x','y'] ],
        0x19: ['NOT', 1, 1, 3, ['x'] ],
        0x1a: ['BYTE', 2, 1, 3, ['index','word'] ],
        0x20: ['SHA3', 2, 1, 30, ['offset','size'] ],
        0x30: ['ADDRESS', 0, 1, 2, [] ],
        0x31: ['BALANCE', 1, 1, 20, ['address'] ],
        0x32: ['ORIGIN', 0, 1, 2, [] ],
        0x33: ['CALLER', 0, 1, 2, [] ],
        0x34: ['CALLVALUE', 0, 1, 2, [] ],
        0x35: ['CALLDATALOAD', 1, 1, 3, ['position'] ],
        0x36: ['CALLDATASIZE', 0, 1, 2, [] ],
        0x37: ['CALLDATACOPY', 3, 0, 3, ['memOffset', 'dataOffset', 'length'] ],
        0x38: ['CODESIZE', 0, 1, 2, [] ],
        0x39: ['CODECOPY', 3, 0, 3, ['memOffset', 'codeOffset', 'length']],
        0x3a: ['GASPRICE', 0, 1, 2, [] ],
        0x3b: ['EXTCODESIZE', 1, 1, 20, ['address'] ],
        0x3c: ['EXTCODECOPY', 4, 0, 20, ['address','memOffset', 'codeOffset', 'length']  ],
        0x3d: ['RETURNDATASIZE', 0, 1, 2, [] ],
        0x3e: ['RETURNDATACOPY', 3, 0, 3, ['memOffset', 'dataOffset', 'length']  ],
        0x40: ['BLOCKHASH', 1, 1, 20, ['blocknum'] ],
        0x41: ['COINBASE', 0, 1, 2, [] ],
        0x42: ['TIMESTAMP', 0, 1, 2, [] ],
        0x43: ['NUMBER', 0, 1, 2, [] ],
        0x44: ['DIFFICULTY', 0, 1, 2, [] ],
        0x45: ['GASLIMIT', 0, 1, 2, [] ],
        0x50: ['POP', 1, 0, 2, ['popvalue'] ],
        0x51: ['MLOAD', 1, 1, 3, ['offset'] ],
        0x52: ['MSTORE', 2, 0, 3, ['mempos','data'] ],
        0x53: ['MSTORE8', 2, 0, 3, ['mempos','data'] ],
        0x54: ['SLOAD', 1, 1, 50, ['location'] ],
        0x55: ['SSTORE', 2, 0, 0, ['location','data'] ],
        0x56: ['JUMP', 1, 0, 8, ['destination'] ],
        0x57: ['JUMPI', 2, 0, 10, ['destination','cond'] ],
        0x58: ['PC', 0, 1, 2, [] ],
        0x59: ['MSIZE', 0, 1, 2, [] ],
        0x5a: ['GAS', 0, 1, 2, [] ],
        0x5b: ['JUMPDEST', 0, 0, 1, [] ],
        0xa0: ['LOG0', 2, 0, 375, ['memstart','memsize'] ],
        0xa1: ['LOG1', 3, 0, 750, ['memstart','memsize','topic1'] ],
        0xa2: ['LOG2', 4, 0, 1125, ['memstart','memsize','topic1','topic2'] ],
        0xa3: ['LOG3', 5, 0, 1500, ['memstart','memsize','topic1','topic2','topic3'] ],
        0xa4: ['LOG4', 6, 0, 1875, ['memstart','memsize','topic1','topic2','topic3','topic4'] ],
        0xf0: ['CREATE', 3, 1, 32000, ['value','mstart','msize'] ],
        0xf1: ['CALL', 7, 1, 40, ['gas','address','value','instart','insize','outstart','outsize'] ],
        0xf2: ['CALLCODE', 7, 1, 40, ['gas','address','value','instart','insize','outstart','outsize'] ],
        0xf3: ['RETURN', 2, 0, 0, ['memstart','length'] ],
        0xf4: ['DELEGATECALL', 6, 0, 40, ['gas','address','instart','insize','outstart','outsize'] ],
        0xfa: ['STATICCALL', 6, 1, 40, ['gas','address','instart','insize','outstart','outsize'] ],
        0xfd: ['REVERT', 2, 0, 0, ['memstart','length'] ],
        0xff: ['SUICIDE', 1, 0, 0, ['beneficiary'] ],
    }

    dup_annotation = ['duptarget']
    swap_annotation = ['operand', 'operand']
    for i in range(1, 17):

        opcodes[0x7f + i] = ['DUP' + str(i), i, i + 1, 3,dup_annotation]
        opcodes[0x8f + i] = ['SWAP' + str(i), i + 1, i + 1, 3, swap_annotation]
        dup_annotation = ['']+dup_annotation
        swap_annotation = ['swaptarget'] + ['']*i + [ 'swaptarget']

    if opcode in opcodes.keys():
        return opcodes[opcode][4]

    return []

def hexdump( src, length=16, sep='.', minrows = 8 , start =0, prevsrc = ""):
    """
    @brief Return {src} in hex dump.
    """
    txt = lambda c: chr(c) if 0x20 <= c < 0x7F else "."

    result = [];

    
    result.append('           00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  |  [ --ascii--]')
    result.append('')
    rows = []

    for i in xrange(0,16):
        subSrc = src[ 2 * (start * 16 + i * 16) :2 * ( start * 16 + i * 16) +length*2]
        hexa = ''
        text = '';
        if len(subSrc) > 0:
            for h in xrange(0,len(subSrc),2):
                if h == length:
                    hexa += ' '
                byte = int(subSrc[h:h+2],16)

                # Check if it changed from op before
                changed = False
                if prevsrc is not None:
                    index = 2* (start+i)*16 + h
                    if index +2 > len(prevsrc) :
                        changed = True
                    elif int(prevsrc[index:index+2],16) != byte:
                        changed = True

                if changed:
                    hexa += "{:02x}•".format(byte)
                else:
                    hexa += "{:02x} ".format(byte)
                text += txt(byte)

        rows.append('{:08x}:  {:<49} | {:<16} '.format(16*(start+i), hexa, text))
        if len(rows) == minrows:
            break
    result.extend(rows)
    return '\n'.join(result);


def stackdump(st, length = 16, minrows=8, start =0, opcode = None):
    """ 
    @brief Return the 'st' stackdump nicely formatted
    Also adds stack annotations if 'opcode' is provided
    """

    result = []
    annotations = []
    if opcode is not None:
        annotations = getStackAnnotations(opcode)

    top_item = start+min(minrows, len(st)-1) # 0
    bottom_item = start                      # 0

    # Note: 
    # Stack 'st' is [bottom , ... , top]
    # Annotation 'annotations' is [top , .. , bottom]

    for i in xrange(start , min(minrows, len(st))):
        stackvalue = ""
        annotation = ""

        if i < len(st):
            val = int(st[-1-i],16)
            stackvalue = "  {:02} : {:.>64x}".format(i, val)
        else:
            stackvalue = "  {:02} : {:64}".format(i, "")

        if len(annotations) > i:
            annotation = annotations[i]

        result.append("{} {}".format(stackvalue, annotation))

    return '\n'.join(result)

def opDump(obj):
    """
    @brief returns information about current exeution step
    """

    def attr(x, tryCastToInt= True):
        prelim = ('bold',"{:10}: ".format(x))
        if x in obj.keys():
            v = obj[x]
            if type(v) != type(0) and tryCastToInt:
                try:
                    v = int(v,16)
                except Exception as e:
                    # It's text
                    return [prelim, "{:6}\n".format(v.strip())]
            # An int
            if type(v) == type(0):
                return [prelim, "{:6d} (0x{:02x})\n".format(v,v)]
            return [prelim, "{:6} \n".format(v)]
        else:
            # Not available
            return [prelim, "<N/A>\n"]


    result = []

    result.append(attr('pc'))
    result.append(attr('op'))
    result.append(attr('opName',False))
    result.append(attr('gasCost'))
    result.append(attr('gas'))
    result.append(attr('memSize'))
    result.append(attr('depth'))
    
    return result

def toText(op):
    """
    @brief Formats an execution-step to one line of text
    """
    def attr(x,fmt,tryCastToInt= True):
        if x in op.keys():
            v = op[x]
            if type(v) != type(0) and tryCastToInt:
                try:
                    v = int(v,16)
                except Exception as e:
                    pass
            return fmt.format(v)

        return "N/A"

    result = []

    def precheck(op):
        if not op.keys():
            return "END" 
        if 'stateRoot' in op.keys():
            return "stateRoot {}".format(op['stateRoot'])
        if 'error' in op.keys() and op['error'] is not None:
            if str(op['error']).find('gas') > -1:
                return "OOG" 
            return "Err: {}".format(op['error']) 
        return None

    abort = precheck(op)

    if abort:
        result.append(abort)
        return " ".join(result)

    result.append(attr('pc', '{:>5d}'))
    result.append(attr('opName','{:>12}', False))
    result.append(attr('op', '{:>5x}'))
    result.append(attr('gas', '{:>8x}'))
    result.append(attr('gasCost', '{:>8d}'))
    result.append(attr('depth','{:>2d}'))
    return " ".join(result)


def opTrace(ops = [], sel = 0, offset = 0):
    """
    @brief formats a list of instructions to a table 
    """
    header = "|".join(["step    ",
            " pc   ",
            "  opname  ",
            " opcode ",
            " gas  ",
            "gascost",
            "depth"
            ])
    result = [header,""]

    for i, op in enumerate(ops):
        if i+offset == sel:
            result.append("{:<4} >> {}".format(i+offset,toText(op)))
        else:
            result.append("{:<4}    {}".format(i+offset,toText(op)))

    return "\n".join(result)



wrap = lambda x, y : urwid.LineBox( x,y)

class DebugViewer():

    def __init__(self):

        self.memptr = 0 
        self.stackptr = 0
        self.opptr = 0

        self.ops_view = None
        self.mem_view = None
        self.stack_view = None
        self.trace_view = None
        self.help_view = None


    def setTrace(self,trace):
        self.operations = trace

        ops_view   = urwid.Text(self.getOp())
        mem_view   = urwid.Text(self.getMem())
        stack_view = urwid.Text(self.getStack())
        trace_view = urwid.Text(self.getTrace())
        help_view  = urwid.Text(self.getHelp())
        # palettes are currently not used
        palette = [
            ('banner', 'black', 'light gray'),
            ('streak', 'black', 'dark red'),
            ('bg', 'black', 'dark blue'),]
        palette=[
            ('headings', 'white,underline', 'black', 'bold,underline'), # bold text in monochrome mode
            ('body_text', 'dark cyan', 'light gray'),
            ('buttons', 'yellow', 'dark green', 'standout'),
            ('section_text', 'body_text'), # alias to body_text
            ]

        self.ops_view = ops_view
        self.mem_view = mem_view
        self.stack_view = stack_view
        self.trace_view = trace_view
        self.help_view = help_view


        top = wrap(urwid.Columns([
                            urwid.Pile([
                                wrap(ops_view,"Op"),
                                wrap(trace_view, "Trace")]
                                ),
                            urwid.Pile([
                                wrap(mem_view,"Memory"), 
                                wrap(stack_view, "Stack")
                                ])
                    ]),"Retromix")

        horiz = urwid.Pile([top, wrap(help_view,"Help")])
        fill = urwid.Filler(horiz, 'top')
        
        #self.dbg("Loaded %d operations" % len(self.operations) )

        loop = urwid.MainLoop(fill, palette, unhandled_input=lambda input: self.show_or_exit(input))
        loop.run()

    def _op(self, key = None, default = None):

        if self.opptr > len(self.operations)-1:
            return default

        op = self.operations[self.opptr]
        if key == None:
            return op
        if key not in op.keys():
            return default
        if op[key]:
            return op[key]
        return default

    def _prevop(self, key = None, default = None):

        if self.opptr > len(self.operations)-2:
            return default

        op = self.operations[self.opptr-1]
        if key == None:
            return op
        if key not in op.keys():
            return default
        if op[key]:
            return op[key]
        return default


    def getOp(self):
        return opDump(self._op(default={'pc':1}))

    def getMem(self):
        m = self._op('memory',"0x")
        prev_m = self._prevop('memory',"0x")
        return hexdump(m[2:], start = self.memptr, prevsrc = prev_m[2:])

    def getStack(self):
        st = self._op('stack',[])
        opcode = self._op('op',None)
        return stackdump(st, start=self.stackptr, opcode = opcode)

    def getTrace(self):
        # Trace 2 * pad + 1 lines

        pad = 12
        sel = self.opptr
        start = max(sel-pad, 0)
     
        end = min(start+2*pad+1, len(self.operations)-1)


        ops = self.operations[start : end]
        return opTrace(ops = ops, sel = sel, offset = start)

    def getHelp(self):
        return """Key navigation
        a: Trace up        s: Mem up     d: Stack up
        z: Trace down      x: Mem down   c: Stack down        Use uppercase for large steps
    press `q` to quit
        """
    def _refresh(self):
        self.ops_view.set_text(self.getOp())
        self.trace_view.set_text(self.getTrace())
        self.mem_view.set_text(self.getMem())
        self.stack_view.set_text(self.getStack())

    def dbg(self,text):
        if self.help_view is not None:
            self.help_view.set_text(text)

    def show_or_exit(self,key):
        """ 
        @brief handles key-events
        """
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        
        step = 1
        if key in ('A','Z','S','X','D','C'):
            step = 10
        
        # UP trace
        if key in ('a','A'):
            self.opptr = max(0, self.opptr-step)
            self._refresh()

        # DOWN trace
        if key in ('z','Z'):
            self.opptr = min(self.opptr+step, len(self.operations)-1)
            self._refresh()

        # UP mem
        if key in ('s','S'):
            self.memptr = max(0, self.memptr-step)
            self.mem_view.set_text(self.getMem())

        # DOWN mem
        if key in ('x','X'):
            self.memptr = self.memptr+step
            self.mem_view.set_text(self.getMem())

        # UP stack
        if key in ('d','D'):
            self.stackptr = max(0, self.stackptr-step)
            self.stack_view.set_text(self.getStack())

        # DOWN stack
        if key in ('c','C'):
            self.stackptr = self.stackptr+step
            self.stack_view.set_text(self.getStack())

        if key in ('g','G'):
            self.dbg("TODO: Implement GOTO")


def loadJsonDebugStackTrace(fname):
    """Parse the output from debug_getTrace"""
    from evmlab.opcodes import reverse_opcodes
    
    ops = []
    try:
        with open(fname) as f:
            one_json_blob = json.load(f)
            xops = one_json_blob['result']['structLogs']
            for op in xops:
                op['opName'] = op['op']
                op['op'] = reverse_opcodes[op['op']]
                if 'memory' in op.keys():
                    if op['memory'] == None:
                        op['memory'] = "0x"
                    else:
                        op['memory'] = "0x"+"".join(op['memory'])
                        print("Memory set to ", op['memory'])
                ops.append(op)
            print("Loaded %d items from structlogs" % len(ops))
            return ops
    except Exception as e:
        traceback.print_exc()
    return None

def loadJsonObjects(fname):
    """Load the json from geth `evm`"""
    print("Trying to load geth format")
    ops = []
    
    with open(fname) as f:
        for l in f:
            l = l.strip()
            if l.startswith("#"):
                continue
            if len(l) == 0:
                continue
            op = json.loads(l)
            if 'action' in op.keys():
                continue
            ops.append(op)
    return ops

def loadWeirdJson(fname):
    ops = []
    with open(fname) as f:
        text = ""
        for l in f:
            #However, sometimes they're spread out
            if l.strip() == '{':
                text = ""
            text = text + l.strip()
            if l.strip() == '}':
                data = json.loads(text)
                ops.append(data)
    return ops

##python3 opviewer.py -f test.json
def main(args):
    ops = []

    fname = args.file

    ops = loadJsonDebugStackTrace(fname)
    if ops == None:
        # Usually, each line is a json-object
        try:
            ops = loadJsonObjects(fname)
        except Exception as e:
            print("Error loading json:")
            traceback.print_exc()
            print("Trying alternate loader")
            ops = loadWeirdJson(fname)

    DebugViewer().setTrace(ops)

if __name__ == '__main__':
    options = parser.parse_args()
    main(options)
