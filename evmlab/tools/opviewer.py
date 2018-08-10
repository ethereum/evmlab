#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Opviewer - Ethereum Transaction Debugger
"""
import os
import json
import argparse, math
import logging

from evmlab.context import buildContexts
from evmlab.contract import Contract
from evmlab import reproduce, utils
from evmlab import vm as VMUtils
from evmlab.opcodes import reverse_opcodes

logger = logging.getLogger(__name__)

try:
    import ethereum_input_decoder
except ImportError:
    ethereum_input_decoder = None
    logger.warning(
        "Transaction input decoder package not installed. run `#> pip install evmlab[abidecoder]` to install.")
try:
    import urwid
except ImportError:
    logger.fatal("Console UI (urwid) package not installed. run `#> pip install evmlab[consolegui]` to install.")

# Python3 support
# Todo: six instead of custom checks? do we support py2?
try:
    xrange
except NameError:
    xrange = range


class SourceException(Exception):
    # TODO: create exception hierarchy in evmlab package
    pass


class Console:

    @staticmethod
    def bold(text):
        # Todo: not used? get rid of this or use it
        return '\033[1m{}\033[0m'.format(text)


# Todo: get rid of this
# OUTPUT_DIR = "%s/output/" % os.path.dirname(os.path.realpath(__file__))  # should not use realpath of file as we are inside the package.


# NEWLINE_PATTERN = re.compile('\n')


class DebugViewer(object):
    # todo: review staticmethods and check if they really belong to debugviewer (visualization vs. generic helper)

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

    @staticmethod
    def wrap(x, y):
        return urwid.LineBox(x, y)

    @staticmethod
    def getMemoryReference(opcode):

        # opcodes with memory references:
        # CALLDATACOPY, CODECOPY, EXTCODECOPY, RETURNDATACOPY, MLOAD, MSTORE*
        # LOG*, CREATE, CALL, CALLCODE, RETURN, DELEGATECALL, STATICCALL, REVERT
        # format of mem_opcodes dict is [[mem_offset, data_size], default]

        # TODO: use mnemonics instead of opcodes
        # TODO: move to class
        mem_opcodes = {
            0x37: [0, 2],
            0x39: [0, 2],
            0x3c: [1, 3],
            0x3e: [0, 2],
            0x51: [0, -1, 32],
            0x52: [0, -1, 32],
            0x53: [0, -1, 1],
            0xa0: [0, 1],
            0xa1: [0, 1],
            0xa2: [0, 1],
            0xa3: [0, 1],
            0xa4: [0, 1],
            0xf0: [1, 2],
            0xf1: [3, 4],
            0xf2: [3, 4],
            0xf3: [0, 1],
            0xf4: [2, 3],
            0xfa: [2, 3],
            0xfd: [0, 1]
        }

        if opcode in mem_opcodes.keys():
            e = mem_opcodes[opcode]
            return e
        else:
            return -1

    @staticmethod
    def memRefResolve(mem, refs, st, msg, opname, oplimit):
        append = ""
        st = st[::-1]
        mem = mem[2:]
        mrefs = [0, 0]
        mrefs[0] = int(st[refs[0]], 16)
        if (refs[1] == -1):
            mrefs[1] = refs[2]
        else:
            mrefs[1] = int(st[refs[1]], 16)
        if oplimit > 0 and mrefs[1] > oplimit:
            mrefs[1] = oplimit
            append = "..."
        if mrefs[1] < 0 or mrefs[0] < 0 or mrefs[0] > len(mem) / 2:
            mrefs = [0, 0]
            append = " - memory access beyond expansion"
        if (mrefs[0] + mrefs[1]) > len(mem) / 2:
            mrefs[1] = len(mem / 2) - mrefs[0]
            append = " - attempted read beyond memory bound of %d bytes" % (mrefs[0] + mrefs[1] - len(mem / 2))
        return msg + " " + opname + " memory ref:\n" + "0x" + "".join(
            mem[(mrefs[0] * 2):(mrefs[0] + mrefs[1]) * 2]) + append + "\n"

    @staticmethod
    def dumpArea(f, name, content):
        # TODO: get rid of this?
        f.write(name + "\n\n")
        f.write(content + "\n\n")

    @staticmethod
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
            start_code_line = contract[:start].count('\n')
            # start_code_line = len(re.findall(NEWLINE_PATTERN, contract[:start]))
            # num of lines of code
            code_lines = code.count('\n') + 1
            # code_lines = len(re.findall(NEWLINE_PATTERN, code)) + 1

            split = contract.splitlines()

            if track:
                if start_code_line == 0 or code_lines >= length:
                    srcptr = start_code_line
                    view = split[start_code_line: start_code_line + length]
                else:
                    offset = math.floor((length - code_lines) / 2)
                    line_end = min(start_code_line + code_lines + offset, len(split))
                    line_start = max(line_end - length, 0)

                    srcptr = line_start
                    view = split[line_start: line_end]
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
                    viewtxt = [viewtxt[:code_start_offset], ('source', viewtxt[code_start_offset:code_end_offset]),
                               viewtxt[code_end_offset:]]

            return srcptr, viewtxt
        else:
            return srcptr, ""

    @staticmethod
    def getStackAnnotations(opcode):
        """
        Returns a list of annotations for stack elements, given the opcode 'op'.
        Example, ifcode = CALL:
        ['gas', 'address','value', 'instart', 'insize', 'outstart', 'outsize']
        """
        # TODO: impmort opcodes and reuse them
        opcodes = {
            0x00: ['STOP', 0, 0, 0, []],
            0x01: ['ADD', 2, 1, 3, ['operand', 'operand']],
            0x02: ['MUL', 2, 1, 5, ['operand', 'operand']],
            0x03: ['SUB', 2, 1, 3, ['operand', 'operand']],
            0x04: ['DIV', 2, 1, 5, ['numerator', 'denominator']],
            0x05: ['SDIV', 2, 1, 5, ['numerator', 'denominator']],
            0x06: ['MOD', 2, 1, 5, ['x', 'modulator']],
            0x07: ['SMOD', 2, 1, 5, ['x', 'modulator']],
            0x08: ['ADDMOD', 3, 1, 8, ['operand', 'operand', 'modulator']],
            0x09: ['MULMOD', 3, 1, 8, ['operand', 'operand', 'modulator']],
            0x0a: ['EXP', 2, 1, 10, ['base', 'exponent']],
            0x0b: ['SIGNEXTEND', 2, 1, 5, ['byte', 'bit']],
            0x10: ['LT', 2, 1, 3, ['x', 'y']],
            0x11: ['GT', 2, 1, 3, ['x', 'y']],
            0x12: ['SLT', 2, 1, 3, ['x', 'y']],
            0x13: ['SGT', 2, 1, 3, ['x', 'y']],
            0x14: ['EQ', 2, 1, 3, ['x', 'y']],
            0x15: ['ISZERO', 1, 1, 3, ['x']],
            0x16: ['AND', 2, 1, 3, ['x', 'y']],
            0x17: ['OR', 2, 1, 3, ['x', 'y']],
            0x18: ['XOR', 2, 1, 3, ['x', 'y']],
            0x19: ['NOT', 1, 1, 3, ['x']],
            0x1a: ['BYTE', 2, 1, 3, ['index', 'word']],
            0x20: ['SHA3', 2, 1, 30, ['offset', 'size']],
            0x30: ['ADDRESS', 0, 1, 2, []],
            0x31: ['BALANCE', 1, 1, 20, ['address']],
            0x32: ['ORIGIN', 0, 1, 2, []],
            0x33: ['CALLER', 0, 1, 2, []],
            0x34: ['CALLVALUE', 0, 1, 2, []],
            0x35: ['CALLDATALOAD', 1, 1, 3, ['position']],
            0x36: ['CALLDATASIZE', 0, 1, 2, []],
            0x37: ['CALLDATACOPY', 3, 0, 3, ['memOffset', 'dataOffset', 'length']],
            0x38: ['CODESIZE', 0, 1, 2, []],
            0x39: ['CODECOPY', 3, 0, 3, ['memOffset', 'codeOffset', 'length']],
            0x3a: ['GASPRICE', 0, 1, 2, []],
            0x3b: ['EXTCODESIZE', 1, 1, 20, ['address']],
            0x3c: ['EXTCODECOPY', 4, 0, 20, ['address', 'memOffset', 'codeOffset', 'length']],
            0x3d: ['RETURNDATASIZE', 0, 1, 2, []],
            0x3e: ['RETURNDATACOPY', 3, 0, 3, ['memOffset', 'dataOffset', 'length']],
            0x40: ['BLOCKHASH', 1, 1, 20, ['blocknum']],
            0x41: ['COINBASE', 0, 1, 2, []],
            0x42: ['TIMESTAMP', 0, 1, 2, []],
            0x43: ['NUMBER', 0, 1, 2, []],
            0x44: ['DIFFICULTY', 0, 1, 2, []],
            0x45: ['GASLIMIT', 0, 1, 2, []],
            0x50: ['POP', 1, 0, 2, ['popvalue']],
            0x51: ['MLOAD', 1, 1, 3, ['offset']],
            0x52: ['MSTORE', 2, 0, 3, ['mempos', 'data']],
            0x53: ['MSTORE8', 2, 0, 3, ['mempos', 'data']],
            0x54: ['SLOAD', 1, 1, 50, ['location']],
            0x55: ['SSTORE', 2, 0, 0, ['location', 'data']],
            0x56: ['JUMP', 1, 0, 8, ['destination']],
            0x57: ['JUMPI', 2, 0, 10, ['destination', 'cond']],
            0x58: ['PC', 0, 1, 2, []],
            0x59: ['MSIZE', 0, 1, 2, []],
            0x5a: ['GAS', 0, 1, 2, []],
            0x5b: ['JUMPDEST', 0, 0, 1, []],
            0xa0: ['LOG0', 2, 0, 375, ['memstart', 'memsize']],
            0xa1: ['LOG1', 3, 0, 750, ['memstart', 'memsize', 'topic1']],
            0xa2: ['LOG2', 4, 0, 1125, ['memstart', 'memsize', 'topic1', 'topic2']],
            0xa3: ['LOG3', 5, 0, 1500, ['memstart', 'memsize', 'topic1', 'topic2', 'topic3']],
            0xa4: ['LOG4', 6, 0, 1875, ['memstart', 'memsize', 'topic1', 'topic2', 'topic3', 'topic4']],
            0xf0: ['CREATE', 3, 1, 32000, ['value', 'mstart', 'msize']],
            0xf1: ['CALL', 7, 1, 40, ['gas', 'address', 'value', 'instart', 'insize', 'outstart', 'outsize']],
            0xf2: ['CALLCODE', 7, 1, 40, ['gas', 'address', 'value', 'instart', 'insize', 'outstart', 'outsize']],
            0xf3: ['RETURN', 2, 0, 0, ['memstart', 'length']],
            0xf4: ['DELEGATECALL', 6, 0, 40, ['gas', 'address', 'instart', 'insize', 'outstart', 'outsize']],
            0xfa: ['STATICCALL', 6, 1, 40, ['gas', 'address', 'instart', 'insize', 'outstart', 'outsize']],
            0xfd: ['REVERT', 2, 0, 0, ['memstart', 'length']],
            0xff: ['SUICIDE', 1, 0, 0, ['beneficiary']],
        }

        dup_annotation = ['duptarget']
        swap_annotation = ['operand', 'operand']
        for i in range(1, 17):
            opcodes[0x7f + i] = ['DUP' + str(i), i, i + 1, 3, dup_annotation]
            opcodes[0x8f + i] = ['SWAP' + str(i), i + 1, i + 1, 3, swap_annotation]
            dup_annotation = [''] + dup_annotation
            swap_annotation = ['swaptarget'] + [''] * i + ['swaptarget']

        if opcode in opcodes.keys():
            return opcodes[opcode][4]

        return []

    @staticmethod
    def hexdump(src, length=16, sep='.', minrows=8, start=0, prevsrc=""):
        """
        @brief Return {src} in hex dump.
        """
        txt = lambda c: chr(c) if 0x20 <= c < 0x7F else "."

        result = []
        result.append('           00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  |  [ --ascii--]')
        result.append('')
        rows = []

        for i in xrange(0, 16):
            subSrc = src[2 * (start * 16 + i * 16):2 * (start * 16 + i * 16) + length * 2]
            hexa = ''
            text = ''
            if len(subSrc) > 0:
                for h in xrange(0, len(subSrc), 2):
                    if h == length:
                        hexa += ' '
                    byte = int(subSrc[h:h + 2], 16)

                    # Check if it changed from op before
                    changed = False
                    if prevsrc is not None:
                        index = 2 * (start + i) * 16 + h
                        if index + 2 > len(prevsrc):
                            changed = True
                        elif int(prevsrc[index:index + 2], 16) != byte:
                            changed = True

                    if changed:
                        hexa += "{:02x}•".format(byte)
                    else:
                        hexa += "{:02x} ".format(byte)
                    text += txt(byte)

            rows.append('{:08x}:  {:<49} | {:<16} '.format(16 * (start + i), hexa, text))
            if len(rows) == minrows:
                break
        result.extend(rows)
        return '\n'.join(result)

    @staticmethod
    def stackdump(st, length=16, minrows=8, start=0, opcode=None):
        """
        @brief Return the 'st' stackdump nicely formatted
        Also adds stack annotations if 'opcode' is provided
        """

        result = []
        annotations = []
        if opcode is not None:
            annotations = DebugViewer.getStackAnnotations(opcode)

        top_item = start + min(minrows, len(st) - 1)  # 0
        bottom_item = start  # 0

        # Note:
        # Stack 'st' is [bottom , ... , top]
        # Annotation 'annotations' is [top , .. , bottom]

        for i in xrange(start, min(minrows, len(st))):
            stackvalue = ""
            annotation = ""

            if i < len(st):
                val = int(st[-1 - i], 16)
                stackvalue = "  {:02} : {:.>64x}".format(i, val)
            else:
                stackvalue = "  {:02} : {:64}".format(i, "")

            if len(annotations) > i:
                annotation = annotations[i]

            result.append("{} {}".format(stackvalue, annotation))

        return '\n'.join(result)

    @staticmethod
    def opDump(obj, addr):
        """
        @brief returns information about current exeution step
        """

        def attr(x, tryCastToInt=True):
            prelim = ('bold', "{:10}: ".format(x))
            if x in obj.keys():
                v = obj[x]
                if type(v) != type(0) and tryCastToInt:
                    try:
                        v = int(v, 16)
                    except Exception as e:
                        # It's text
                        return [prelim, "{:6}\n".format(v.strip())]
                # An int
                if type(v) == type(0):
                    return [prelim, "{:6d} (0x{:02x})\n".format(v, v)]
                return [prelim, "{:6} \n".format(v)]
            else:
                # Not available
                return [prelim, "<N/A>\n"]

        result = []

        result.append(attr('pc'))
        result.append(attr('op'))
        result.append(attr('opName', False))
        result.append(attr('gasCost'))
        result.append(attr('gas'))
        result.append(attr('memSize'))
        result.append(attr('depth'))
        if addr:
            result.append([('bold', "{:10}: ".format("addr")), addr])

        return result

    @staticmethod
    def toText(op):
        """
        @brief Formats an execution-step to one line of text
        """

        def attr(x, fmt, tryCastToInt=True):
            if x in op.keys():
                v = op[x]
                if type(v) != type(0) and tryCastToInt:
                    try:
                        v = int(v, 16)
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

        result.append(attr('opName', '{:>12}', False))
        result.append(attr('op', '{:>5x}'))
        result.append(attr('gas', '{:>8x}'))
        result.append(attr('gasCost', '{:>8d}'))
        result.append(attr('depth', '{:>2d}'))
        return " ".join(result)

    @staticmethod
    def opTrace(ops=[], sel=0, offset=0):
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
        result = [header, ""]

        for i, op in enumerate(ops):
            if i + offset == sel:
                result.append("{:<4} >> {}".format(i + offset, DebugViewer.toText(op)))
            else:
                result.append("{:<4}    {}".format(i + offset, DebugViewer.toText(op)))

        return "\n".join(result)

    def setTrace(self, trace, op_contracts=[], txhash=None, txinput=None):
        self.operations = trace
        self.op_contracts = op_contracts

        ops_view = urwid.Text(self.getOp())
        mem_view = urwid.Text(self.getMem())
        memref_view = urwid.Text(self.getMemref())
        stack_view = urwid.Text(self.getStack())
        trace_view = urwid.Text(self.getTrace())
        source_view = urwid.Text(self.getSource())
        help_view = urwid.Text(self.getHelp())
        # palettes are currently not used
        palette = [
            ('banner', 'black', 'light gray'),
            ('streak', 'black', 'dark red'),
            ('bg', 'black', 'dark blue'), ]
        palette = [
            ('headings', 'white,underline', 'black', 'bold,underline'),  # bold text in monochrome mode
            ('body_text', 'dark cyan', 'light gray'),
            ('buttons', 'yellow', 'dark green', 'standout'),
            ('section_text', 'body_text'),  # alias to body_text
            ('source', 'white', 'black', 'bold'),  # bold text in monochrome mode
        ]

        self.ops_view = ops_view
        self.mem_view = mem_view
        self.memref_view = memref_view
        self.stack_view = stack_view
        self.trace_view = trace_view
        self.source_view = source_view
        self.help_view = help_view

        # indicate the online lookup with a * at the end of decoded
        try:
            txinput_decoded = ethereum_input_decoder.AbiMethod.from_input_lookup(ethereum_input_decoder.Utils.str_to_bytes(txinput)) if ethereum_input_decoder else "<input decoder not installed>"
        except Exception as e:  # not going to import from eth_abi to not make the code depending on it
            txinput_decoded = "!! DecodingError: %s" %e


        inp_view = urwid.Text("""
  > tx:       %s
  > input:    %s
  > decoded*: %s""" % (txhash,
                      txinput,
                      txinput_decoded))

        top = DebugViewer.wrap(urwid.Pile([
            DebugViewer.wrap(inp_view, ""),
            urwid.Columns([
                urwid.Pile([
                    DebugViewer.wrap(ops_view, "Op"),
                    DebugViewer.wrap(trace_view, "Trace")]
                ),
                urwid.Pile([
                    DebugViewer.wrap(mem_view, "Memory"),
                    DebugViewer.wrap(memref_view, "Memory Reference by Opcode"),
                    DebugViewer.wrap(stack_view, "Stack"),
                    DebugViewer.wrap(source_view, "Source"),
                ])
            ])
        ]), "Retromix")

        horiz = urwid.Pile([top, DebugViewer.wrap(help_view, "Help")])
        fill = urwid.Filler(horiz, 'top')

        # self.dbg("Loaded %d operations" % len(self.operations) )

        loop = urwid.MainLoop(fill, palette, unhandled_input=lambda input: self.show_or_exit(input))
        loop.run()

    def _op(self, key=None, default=None):

        if self.opptr > len(self.operations) - 1:
            return default

        op = self.operations[self.opptr]
        if key == None:
            return op
        if key not in op.keys():
            return default
        if op[key]:
            return op[key]
        return default

    def _prevop(self, key=None, default=None):

        if self.opptr > len(self.operations) - 2:
            return default

        op = self.operations[self.opptr - 1]
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

        return DebugViewer.opDump(self._op(default={'pc': 1}), addr)

    def getMem(self):
        m = self._op('memory', "0x")
        if type(m) is list:
            m = "0x%s" % "".join(m)
        prev_m = self._prevop('memory', "0x")
        if type(prev_m) is list:
            prev_m = "0x%s" % "".join(prev_m)
        return DebugViewer.hexdump(m[2:], start=self.memptr, prevsrc=prev_m[2:])

    def _getMemref(self, bound):
        m = self._op('memory', [])
        mc = ""
        mc_prev = ""
        ms = DebugViewer.getMemoryReference(self._op('op', "0"))
        ms_prev = DebugViewer.getMemoryReference(self._prevop('op', "0"))
        if type(ms) is list:
            mc = DebugViewer.memRefResolve(m, ms, self._op('stack', []), "Pre-exec", self._op('opName', 'op'), bound)
        if type(ms_prev) is list:
            mc_prev = DebugViewer.memRefResolve(m, ms_prev, self._prevop('stack', []), "Post-exec",
                                                self._prevop('opName', 'op'), bound)
        return mc + mc_prev

    def getMemref(self):
        return self._getMemref(256)

    def getStack(self):
        st = self._op('stack', [])
        opcode = self._op('op', None)
        return DebugViewer.stackdump(st, start=self.stackptr, opcode=opcode)

    def getTrace(self):
        # Trace 2 * pad + 1 lines

        pad = 12
        sel = self.opptr
        start = max(sel - pad, 0)

        end = min(start + 2 * pad + 1, len(self.operations) - 1)

        ops = self.operations[start: end]
        return DebugViewer.opTrace(ops=ops, sel=sel, offset=start)

    def getSource(self, track=None):

        if len(self.op_contracts) == 0:
            return "No Source Provided"

        op = self.operations[self.opptr]

        if 'depth' not in op:
            return ""

        if not self.op_contracts[self.opptr]:
            return "Missing context"

        if track is None:
            track = self.srctrack

        try:
            self.srcptr, txt = DebugViewer.opSource(self.op_contracts[self.opptr], op, self.srcptr, track=track)
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
        self.source_view.set_text(self.getSource())  # needs to occur before getOp to print correct addr
        self.ops_view.set_text(self.getOp())
        self.trace_view.set_text(self.getTrace())
        self.mem_view.set_text(self.getMem())
        self.memref_view.set_text(self.getMemref())
        self.stack_view.set_text(self.getStack())
        self.help_view.set_text(self.getHelp())

    def dbg(self, text):
        if self.help_view is not None:
            self.help_view.set_text(text)

    def show_or_exit(self, key):
        """
        @brief handles key-events
        """
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

        step = 1
        if key in ('A', 'Z'):
            step = 10 if len(self.operations) <= 1000 else 100
        elif key in ('S', 'X', 'D', 'C', 'F', 'V'):
            step = 10

        # UP trace
        if key in ('a', 'A'):
            self.opptr = max(0, self.opptr - step)
            self._refresh()

        # DOWN trace
        if key in ('z', 'Z'):
            self.opptr = min(self.opptr + step, len(self.operations) - 1)
            self._refresh()

        # UP mem
        if key in ('s', 'S'):
            self.memptr = max(0, self.memptr - step)
            self.mem_view.set_text(self.getMem())

        # DOWN mem
        if key in ('x', 'X'):
            self.memptr = self.memptr + step
            self.mem_view.set_text(self.getMem())

        # UP stack
        if key in ('d', 'D'):
            self.stackptr = max(0, self.stackptr - step)
            self.stack_view.set_text(self.getStack())

        # DOWN stack
        if key in ('c', 'C'):
            self.stackptr = self.stackptr + step
            self.stack_view.set_text(self.getStack())

        # UP source
        if key in ('f', 'F'):
            self.srcptr = max(0, self.srcptr - step)
            self.source_view.set_text(self.getSource(track=False))

        # DOWN source
        if key in ('v', 'V'):
            self.srcptr = self.srcptr + step
            self.source_view.set_text(self.getSource(track=False))

        if key in ('t', 'T'):
            self.srctrack = not self.srctrack
            if self.srctrack:
                self.srcptr = 0
            self.source_view.set_text(self.getSource())

        if key in ('g', 'G'):
            self.dbg("TODO: Implement GOTO")

        if key in ('m', 'M'):
            snap_name = os.path.join(os.getcwd(), "evmlab.state.snapshot%s.txt" % self.snapn)
            ops = "".join(str(e[0][1] + e[1]) for e in self.getOp())
            try:
                sf = open(snap_name, "w")
                DebugViewer.dumpArea(sf, "OP STATE", str(ops))
                DebugViewer.dumpArea(sf, "TRACE", self.getTrace())
                DebugViewer.dumpArea(sf, "MEMORY REFERENCE", self._getMemref(0))
                DebugViewer.dumpArea(sf, "MEMORY DUMP", self.getMem())
                DebugViewer.dumpArea(sf, "STACK", self.getStack())
                sf.close()
                self.dbg("Saved snapshot to %s" % snap_name)
            except Exception as e:
                self.dbg(str(e))
            self.snapn += 1


class EvmTrace(object):
    """
    Main Wrapper class to handle Evm Traces
    """

    def __init__(self, api="https://mainnet.infura.io/remix"):

        self.api = utils.getApi(api)
        self.source_path = None

        self.txhash = None
        self.txinput = None

        # internal state
        self.ops = []
        self.contracts = []
        self.op_contracts = []

    @staticmethod
    def get_evm_handler(vmtype, path, docker=True):
        """
        utility function to get Geth/Parity VMObjects

        :param vmtype: string type of evm geth|parity
        :param path: path to evm binary
        :param docker: is this a docker container
        :return: either GethVM or ParityVM object
        """
        if vmtype == "geth":
            vmclass = VMUtils.GethVM
        elif vmtype == "parity":
            vmclass = VMUtils.ParityVM
        else:
            raise Exception("vmtype not supported.")

        return vmclass(executable=path, docker=docker)

    def show(self):
        """
        show() urwid ui

        @info: ideally this is not part of this class. we should probably move this to another class e.g. UrwidUI(EvmTrace)
        :return:
        """
        if not self.ops:
            raise Exception("need to reproduce/load trace first")

        DebugViewer().setTrace(self.ops, self.op_contracts, self.txhash, self.txinput)

    def reproduce(self, tx, vm):
        """

        :param tx:  # tx hash
        :param vm:  # see OpViewer.get_evm_handler(...)
        :return: self
        """
        artefacts, vm_args = reproduce.reproduceTx(tx, vm, self.api)
        logger.debug("done reproducing transaction trace...")
        ## TODO: fix artefacts
        ## TODO: get rid of saveFiles
        ## TODO: generally get rid of tempfile logic.
        # saved_files = utils.saveFiles(OUTPUT_DIR, artefacts)
        # fname = os.path.join(saved_files['json-trace']['path'], saved_files['json-trace']['name'])

        return self.load_trace(path=artefacts['json-trace'])

    def load_trace(self, tx=None, _json=None, path=None):
        if _json:
            return self.load_trace_json(data=_json)
        elif tx:
            self.txhash = tx
            self.txinput = self.api.getTransaction(tx)["input"]
            return self.load_trace(_json=self.api.traceTransaction(tx=tx))
        elif path:
            return self.load_trace_file(path=path)
        raise Exception("either tx, _json debugtrace or path to a json_debugtrace required")

    def load_trace_json(self, data):
        """Parse the output from debug_traceTransaction"""
        ops = []

        if 'jsonrpc' in data:
            # get rid of jsonrpc envelope if it is available
            data = data['result']
        xops = data['structLogs']
        for op in xops:
            newOp = dict(op)  # get rid of attributeDict if data comes from api
            newOp['opName'] = op['op']
            newOp['op'] = reverse_opcodes[op['op']]

            if 'memory' in op.keys():
                if op['memory'] is None:
                    newOp['memory'] = "0x"
                else:
                    newOp['memory'] = "0x" + "".join(op['memory'])
                    logger.debug("Memory set to %s" % newOp['memory'])
            ops.append(newOp)
        logger.debug("Loaded %d items from structlogs" % len(ops))

        self.ops = ops
        logger.debug("trace loaded (structLogs).")
        return self

    def load_trace_file(self, path):
        if not os.path.isfile(path):
            raise Exception("%s - is not a file" % path)

        logger.debug("loading trace file: %s" % path)
        with open(path) as f:
            #
            # 1) try json tracefile
            #
            try:
                return self.load_trace_json(json.load(f))
            except json.decoder.JSONDecodeError:
                logger.debug('Failed to parse file in debug_traceTransaction format')
            #
            # 2) try line-by-line json
            #
            logger.debug("Trying to load %s in geth format")
            f.seek(0)  # rewind
            data = f.read()
            try:
                return self._loadJsonObjects(data)
            except Exception as e:
                logger.debug(e)
            #
            # 3) try load weird json format
            #
            try:
                return self._loadWeirdJson(data)
            except Exception as e:
                logger.debug(e)

        raise Exception("could not load json trace file")

    def _loadJsonObjects(self, data):
        """Load the json from geth `evm`"""

        ops = []
        for l in data.split("\n"):
            l = l.strip()
            if l.startswith("#"):
                continue
            if len(l) == 0:
                continue
            op = json.loads(l)
            if 'action' in op.keys():
                continue
            ops.append(op)

        if not ops:
            raise Exception("could not load json line-by-line code")

        self.ops = ops
        logger.debug("trace loaded (json objects)")
        return self

    def _loadWeirdJson(self, data):
        ops = []

        text = ""
        for l in data.split("\n"):
            # However, sometimes they're spread out
            if l.strip() == '{':
                text = ""
            text = text + l.strip()
            if l.strip() == '}':
                jsondata = json.loads(text)
                ops.append(jsondata)

        if not ops:
            raise Exception("could not load weird json")

        self.ops = ops
        logger.debug("trace loaded (weird json).")
        return self

    def load_source(self, text, bytecode):
        # TODO: load single contract source
        pass

    def load_contract_sources_from_combined_json(self, tx, combined_json, source_prefix=''):
        # TODO: untested, need reference file
        contracts = []
        sources = []

        # get sources (text) for all contracts
        for file in [os.path.join(source_prefix, s) for s in combined_json['sourceList']]:
            with open(file) as s:
                logger.debug(s.name)
                sources.append(s.read())

        # get contract
        for contract, val in combined_json['contracts'].iteritems():
            contracts.append(Contract(sources, val, contract))

        self.contracts = contracts
        self.op_contracts = buildContexts(self.ops, self.api, contracts, tx)
        return self

    def save(self, path):
        # TODO: save artefacts, trace files, ...
        pass


def main():
    """
    ##python3 opviewer.py -f test.json

    :return:
    """

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

    parser = argparse.ArgumentParser(description=description, epilog=examples,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-v', "--verbose", action="store_true", default=False, help="Set loglevel to DEBUG")

    evmchoice = parser.add_mutually_exclusive_group()
    evmchoice.add_argument("-f", "--file", type=str, help="Trace file to load")
    evmchoice.add_argument('-g', '--geth-evm', type=str,
                           help="Geth EVM binary or docker image name", default=None)
    evmchoice.add_argument('-p', '--parity-evm', type=str, default=None,
                           help="Parity EVM binary or docker image name")

    parser.add_argument("--no-docker", action="store_true",
                        help="Set to true if using a local binary instead of a docker image")

    sourcesettings = parser.add_argument_group('Sources', 'Settings used to display contract sources')
    sourcesettings.add_argument("-s", "--source", type=str, default="./", help="Contract source code directory")
    sourcesettings.add_argument("-j", "--json", type=str, help="Compiler combined-json output")
    sourcesettings.add_argument('--hash', type=str, help="hash of the tx to view")

    web3settings = parser.add_argument_group('Web3',
                                             'Settings about where to fetch information from when displaying contract sources (default infura)')
    web3settings.add_argument("--web3", type=str, default="https://mainnet.infura.io/remix",
                              help="Web3 API url to fetch info from (default 'https://mainnet.infura.io/remix'")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.hash and not args.hash.startswith("0x"):
        args.hash = "0x%s" % args.hash

    if args.parity_evm and args.geth_evm:
        parser.error("please either specify --geth-evm or --parity-evm and not both.")

    # -- End of arg normalization

    logger.debug("--start--")
    # TODO: talk to infura to get a debug_traceTransaction enabled endpoint (be fair, not reuse remix ;))
    trace = EvmTrace(api=args.web3)

    logger.debug("init done.")

    if not args.file:
        # reproduce or get trace from remote api
        if not args.hash:
            parser.error('hash is required ')

        # reproduce
        if args.parity_evm or args.geth_evm:
            logger.debug("reproducing trace ...")
            vmtype, vmpath = ("parity", args.parity_evm) if args.parity_evm else ("geth", args.geth_evm)
            logger.debug("using VM: %s @ %s (docker=%s)" % (vmtype, vmpath, not args.no_docker))
            vm = EvmTrace.get_evm_handler(vmtype=vmtype, path=vmpath, docker=not args.no_docker)
            trace.reproduce(tx=args.hash, vm=vm)
        else:
            # load from api
            logger.debug("fetching traces from remote api ...")
            trace.load_trace(tx=args.hash)
    else:
        # load from file
        trace.load_trace(path=args.file)

        # eventually load combined.json
        if args.json:
            if not args.hash:
                parser.error('hash is required ')

            with open(args.json, 'r') as f:
                combined = json.load(f)
            trace.load_contract_sources_from_combined_json(tx=args.hash,
                                                           combined_json=combined, source_prefix=args.source)
    trace.show()
    logger.debug("--end--")


if __name__ == '__main__':
    logging.basicConfig(format='[%(filename)s - %(funcName)20s() ][%(levelname)8s] %(message)s',
                        level=logging.INFO)
    main()
