#!/usr/bin/env python3
import urwid, argparse, traceback, math
import json,sys, os, re
from evmlab.context import buildContexts
from evmlab.contract import Contract
from evmlab import reproduce, utils
from evmlab import vm as VMUtils
from evmlab.opcodes import opcodes

# Python3 support
try:
    xrange(0,1)
except NameError:
    xrange = range


def bold(text):
    return '\033[1m{}\033[0m'.format(text)


OUTPUT_DIR = "%s/output/" % os.path.dirname(os.path.realpath(__file__))

description = """
Tool to explore a json-trace in a debug-like interface
"""
examples = """

# Generate a trace and analyze with sources

python3 opviewer.py -s /path/to/contracts -j /path/to/combined.json --hash txHash

# Analyse a trace

python3 opviewer.py -f example.json

# Analyse a trace with sources

python3 opviewer.py -f example.json -s /path/to/contracts -j /path/to/combined.json --hash txHash
"""

parser = argparse.ArgumentParser(description=description,epilog = examples,formatter_class=argparse.RawDescriptionHelpFormatter)
evmchoice = parser.add_mutually_exclusive_group()
evmchoice.add_argument("-f","--file", type=str, help="Trace file to load")
evmchoice.add_argument('-g','--geth-evm', type=str,
                       help="Geth EVM binary or docker image name", default="holiman/gethvm")
evmchoice.add_argument('-p','--parity-evm',  type=str, default=None,
                       help="Parity EVM binary or docker image name")

parser.add_argument("--no-docker", action="store_true",
                    help="Set to true if using a local binary instead of a docker image")

sourcesettings = parser.add_argument_group('Sources', 'Settings used to display contract sources')
sourcesettings.add_argument("-s","--source", type=str, default="./", help="Contract source code directory")
sourcesettings.add_argument("-j","--json", type=str, help="Compiler combined-json output")
sourcesettings.add_argument('--hash', type=str, help="hash of the tx to view")

web3settings = parser.add_argument_group('Web3', 'Settings about where to fetch information from when displaying contract sources (default infura)')
web3settings.add_argument("--web3", type=str, default="https://mainnet.infura.io/",
                          help="Web3 API url to fetch info from (default 'https://mainnet.infura.io/'")

def getMemoryReference(opcode):

# opcodes with memory references:
# CALLDATACOPY, CODECOPY, EXTCODECOPY, RETURNDATACOPY, MLOAD, MSTORE*
# LOG*, CREATE, CALL, CALLCODE, RETURN, DELEGATECALL, STATICCALL, REVERT
# format of mem_opcodes dict is [[mem_offset, data_size], default]

    mem_opcodes = {
        0x37 : [0, 2],
        0x39 : [0, 2],
        0x3c : [1, 3],
        0x3e : [0, 2],
        0x51 : [0, -1, 32],
        0x52 : [0, -1, 32],
        0x53 : [0, -1, 1],
        0xa0 : [0, 1],
        0xa1 : [0, 1],
        0xa2 : [0, 1],
        0xa3 : [0, 1],
        0xa4 : [0, 1],
        0xf0 : [1, 2],
        0xf1 : [3, 4],
        0xf2 : [3, 4],
        0xf3 : [0, 1],
        0xf4 : [2, 3],
        0xfa : [2, 3],
        0xfd : [0, 1]
    }

    if opcode in mem_opcodes.keys():
        e = mem_opcodes[opcode]
        return e
    else:
        return -1

def memRefResolve(mem, refs, st, msg, opname):
        st = st[::-1]
        mrefs = [0, 0]
        mrefs[0] = int(st[refs[0]], 16)
        if (refs[1] == -1):
            mrefs[1] = refs[2]
        else:
            mrefs[1] = int(st[refs[1]], 16)
        return msg + " " + opname + " memory ref:\n" + "0x" + "".join(mem[(mrefs[0]*2)+2:(mrefs[0]+mrefs[1])*2+2]) + "\n"

def dumpArea(f, name, content):
        f.write(name + "\n\n")
        f.write(content + "\n\n")

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

def opDump(obj, addr):
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
    if addr:
        result.append([('bold',"{:10}: ".format("addr")), addr])

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
        if 'error' in op.keys() and op['error'] not in [None, '']:
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


class SourceException(Exception):
    pass

NEWLINE_PATTERN = re.compile('\n')
def opSource(c, opcode, srcptr, track=True, length=12):
    """
    @brief formats an execution step to the corresponding source code
    """
    if 'pc' in opcode.keys():
        contract, code_pos = c.getSourceCode(opcode['pc'])

        if code_pos == [-1, -1]:
            raise SourceException()

        start = code_pos[0]
        end = start + code_pos[1]
        code = contract[start:end]

        # determine which line the code is on
        start_code_line = len(re.findall(NEWLINE_PATTERN, contract[:start]))
        # num of lines of code
        code_lines = len(re.findall(NEWLINE_PATTERN, code)) + 1

        split = contract.splitlines()

        if track:
            if start_code_line == 0 or code_lines >= length:
                srcptr = start_code_line
                view = split[start_code_line : start_code_line + length]
            else:
                offset = math.floor((length - code_lines)/2)
                line_end = min(start_code_line + code_lines + offset, len(split))
                line_start = max(line_end - length, 0)

                srcptr = line_start
                view = split[line_start : line_end]
        else:
            if srcptr + length > len(split):
                srcptr = max(len(split) - length, 0)
            view = split[srcptr: srcptr + length]

        viewtxt = "\n".join(view)

        # highlight the current code in the view

        # determine the code start offset for the view
        code_start_offset = start - len("\n".join(split[:srcptr])) - 1
        code_end_offset = code_start_offset + code_pos[1]
        if (code_start_offset <= 0):
            # current code starts before the view
            if (code_end_offset < 0):
                # current code is before the view
                pass
            elif (code_end_offset > len(viewtxt)):
                # entire view is current code
                viewtxt = [('source', viewtxt)]
            else:
                # first part of view is current code
                viewtxt = [('source', viewtxt[:code_end_offset]), viewtxt[code_end_offset:]]
        else:
            # current code starts within or after the view
            if (code_start_offset > len(viewtxt)):
                # current code is after the view
                pass
            elif (code_end_offset > len(viewtxt)):
                # second part of view is current code
                viewtxt = [viewtxt[:code_start_offset], ('source', viewtxt[code_start_offset:])]
            else:
                # current code is within the current view
                viewtxt = [viewtxt[:code_start_offset], ('source', viewtxt[code_start_offset:code_end_offset]), viewtxt[code_end_offset:]]

        return srcptr, viewtxt
    else:
        return srcptr, ""


wrap = lambda x, y : urwid.LineBox( x,y)

class DebugViewer():

    def __init__(self):

        self.memptr = 0
        self.stackptr = 0
        self.opptr = 0
        self.srcptr = 0
        self.srctrack = True
        self.snapn = 0

        self.ops_view = None
        self.mem_view = None
        self.memref_view = None
        self.stack_view = None
        self.trace_view = None
        self.source_view = None
        self.help_view = None


    def setTrace(self, trace, op_contracts=[]):
        self.operations = trace
        self.op_contracts = op_contracts

        ops_view   = urwid.Text(self.getOp())
        mem_view   = urwid.Text(self.getMem())
        memref_view  = urwid.Text(self.getMemref())
        stack_view = urwid.Text(self.getStack())
        trace_view = urwid.Text(self.getTrace())
        source_view = urwid.Text(self.getSource())
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
            ('source', 'white', 'black', 'bold'), # bold text in monochrome mode
            ]

        self.ops_view = ops_view
        self.mem_view = mem_view
        self.memref_view = memref_view
        self.stack_view = stack_view
        self.trace_view = trace_view
        self.source_view = source_view
        self.help_view = help_view


        top = wrap(urwid.Columns([
                            urwid.Pile([
                                wrap(ops_view,"Op"),
                                wrap(trace_view, "Trace")]
                                ),
                            urwid.Pile([
                                wrap(mem_view,"Memory"),
                                wrap(memref_view, "Memory Reference by Opcode"),
                                wrap(stack_view, "Stack"),
                                wrap(source_view, "Source"),
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
        if op[key] is not None:
            return op[key]
        return default


    def getOp(self):
        addr = None
        if (len(self.op_contracts) > 0):
            c = self.op_contracts[self.opptr]
            addr = "{} ({})".format(c.address, c.name.split(':')[-1])
        
        return opDump(self._op(default={'pc':1}), addr)

    def getMem(self):
        m = self._op('memory',"0x")
        if type(m) is list:
            m = "0x%s" % "".join(m)
        prev_m = self._prevop('memory',"0x")
        if type(prev_m) is list:
            prev_m = "0x%s" % "".join(prev_m)
        return hexdump(m[2:], start = self.memptr, prevsrc = prev_m[2:])

    def getMemref(self):
        m = self._op('memory',[])
        mc = ""
        mc_prev = ""
        ms = getMemoryReference(self._op('op', "0"))
        ms_prev = getMemoryReference(self._prevop('op', "0"))
        if type (ms) is list:
            mc = memRefResolve(m, ms, self._op('stack', []), "Pre-exec", self._op('opName', 'op'))
        if type (ms_prev) is list:
            mc_prev = memRefResolve(m, ms_prev, self._prevop('stack', []), "Post-exec", self._prevop('opName', 'op'))
        return mc+mc_prev
        

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

    def getSource(self, track=None):
        op = self.operations[self.opptr]

        if len(self.op_contracts) == 0:
            return "No Source Provided"

        if 'depth' not in op:
            return ""

        if not self.op_contracts[self.opptr]:
            return "Missing context"

        if track is None:
            track = self.srctrack

        try:
            self.srcptr, txt = opSource(self.op_contracts[self.opptr], op, self.srcptr, track=track)
            return txt
        except SourceException:
            return self.source_view.text

    def getHelp(self):
        return """Key navigation
        a: Trace up        s: Mem up     d: Stack up    f: Source up    t: track source on/off    m: write data to snapshot file
        z: Trace down      x: Mem down   c: Stack down  v: Source down  Use uppercase for large steps
    press `q` to quit
        """

    def _refresh(self):
        self.source_view.set_text(self.getSource()) # needs to occur before getOp to print correct addr
        self.ops_view.set_text(self.getOp())
        self.trace_view.set_text(self.getTrace())
        self.mem_view.set_text(self.getMem())
        self.memref_view.set_text(self.getMemref())
        self.stack_view.set_text(self.getStack())
        self.help_view.set_text(self.getHelp())

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
        if key in ('A','Z'):
            step = 10 if len(self.operations) <= 1000 else 100
        elif key in ('S','X','D','C','F','V'):
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

        # UP source
        if key in ('f','F'):
            self.srcptr = max(0, self.srcptr-step)
            self.source_view.set_text(self.getSource(track=False))

        # DOWN source
        if key in ('v','V'):
            self.srcptr = self.srcptr+step
            self.source_view.set_text(self.getSource(track=False))

        if key in ('t', 'T'):
            self.srctrack = not self.srctrack
            if self.srctrack:
                self.srcptr = 0
            self.source_view.set_text(self.getSource())

        if key in ('g','G'):
            self.dbg("TODO: Implement GOTO")

        if key in ('m','M'):
            snap_name = OUTPUT_DIR + "state.snapshot" + str(self.snapn) + ".txt"
            ops = "".join(str(e[0][1] + e[1]) for e in self.getOp())
            try:
                sf = open(snap_name, "w")
                dumpArea(sf, "OP STATE", str(ops))
                dumpArea(sf, "TRACE", self.getTrace())
                dumpArea(sf, "MEMORY REFERENCE", self.getMemref())
                dumpArea(sf, "MEMORY DUMP", self.getMem())
                dumpArea(sf, "STACK", self.getStack())
                sf.close()
                self.dbg("Saved snapshot to %s" % snap_name)
            except Exception as e:
                self.dbg(str(e))
            self.snapn += 1


def loadJsonDebugStackTrace(fname):
    """Parse the output from debug_traceTransaction"""
    from evmlab.opcodes import reverse_opcodes

    try:
        with open(fname) as f:
            one_json_blob = json.load(f)
    except json.decoder.JSONDecodeError:
        print('Failed to parse file in debug_traceTransaction format')
        return None

    ops = []
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

    vm = None
    fname = args.file
    api = utils.getApi(args.web3)

    if not fname:
        if not args.hash:
            parser.error('hash is required to reproduce the tx if a trace file is not provided')

        #reproduce the tx
        if args.parity_evm:
            vm = VMUtils.ParityVM(args.parity_evm, not args.no_docker)
        else:
            vm = VMUtils.GethVM(args.geth_evm, not args.no_docker)

        artefacts, vm_args = reproduce.reproduceTx(args.hash, vm, api)
        saved_files = utils.saveFiles(OUTPUT_DIR, artefacts)

        fname = os.path.join(saved_files['json-trace']['path'], saved_files['json-trace']['name'])


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


    op_contracts = []
    if args.json:
        if not args.hash:
            parser.error('hash is required if contract json is provided')

        contracts = []
        with open(args.json) as f:
            combined = json.load(f)

            sources = []
            for file in [os.path.join(args.source, s) for s in combined['sourceList']]:
                with open(file) as s:
                    print(s.name)
                    sources.append(s.read())

            for contract in combined['contracts'].keys():
                val = combined['contracts'][contract]
                c = Contract(sources, val, contract)
                contracts.append(c)

        op_contracts = buildContexts(ops, api, contracts, args.hash)

    if vm:
        print("\nTo view the generated trace:\n")
        cmd = "python3 opviewer.py -f %s" % fname
        if args.json:
            cmd += " --web3 %s -s %s -j %s --hash %s" % (args.web3, args.source, args.json, args.hash)
        print(cmd)

    DebugViewer().setTrace(ops, op_contracts)

if __name__ == '__main__':
    options = parser.parse_args()
    main(options)
