from functools import reduce
import json


def int_or_none(v):
    if v in ('i', 'o', '-'):
        return v
    if v == '':
        return None
    return int(v)

def add_missing_values(arr):
    missing = 4 - len(arr)
    return arr + [None] * missing

def is_push(inst):
    return inst >= 0x60 and inst < 0x7f

def pushdata_length(inst):
    return inst - 0x5f

def instruction_length(inst):
    if is_push(inst):
        return 1 + pushdata_length(inst)
    return 1


class SourceMap(object):

    def __init__(self, source, data, contract):
        self.source = source
        self.data = data
        self.contract = contract
        self.source_line_offsets = self._compute_source_line_offsets(source)
        self.byte_to_instr = self._compute_byte_to_instr()

    @classmethod
    def from_standard_json(self, source, data, contract):
        return SourceMap(source, data, contract)

    @property
    def bin(self):
        from binascii import unhexlify
        bytes = self.data['contracts'][self.contract]['bin-runtime']
        # bytes = bytes.replace('__test.sol:SafeMath_____________________', '0000000000000000000000000000000000000000')
        return unhexlify(bytes)

    @property
    def srcmap(self):
        _srcmap = self.data['contracts'][self.contract]['srcmap-runtime']
        return self._fill_srcmap(_srcmap)

    def _fill_srcmap(self, srcmap):
        elems = srcmap.split(';')
        elems = [[int_or_none(v) for v in e.split(':')] for e in elems]
        elems = [add_missing_values(e) for e in elems]

        # fill missing values
        prev_elem = elems[0]
        for elem in elems[1:]:
            for i in range(len(elem) - 1):  # don't do anything to last elem ('i', 'o', '-')
                if elem[i] is None:
                    elem[i] = prev_elem[i]
            prev_elem = elem
        return elems

    def _compute_byte_to_instr(self):
        result = []
        byte_idx = 0
        instr_idx = 0

        while byte_idx < len(self.bin):
            length = instruction_length(self.bin[byte_idx])
            for i in range(length):
                result.append(instr_idx)
            byte_idx += length
            instr_idx += 1

        return result

    def _compute_source_line_offsets(self, source):
        offsets = [0]
        for i in range(len(source)):
            if source[i] == '\n':
                offsets.append(i+1)
        return offsets

    def line_number_for_instr(self, instr):
        offset = self.srcmap[instr][0]

        prev_n = self.source_line_offsets[0]
        ln = 1
        for n in self.source_line_offsets[1:]:
            if offset >= prev_n and offset < n:
                return ln
            prev_n = n
            ln += 1
        return ln

    def instr_for_pc(self, pc):
        return self.byte_to_instr[pc]

    def line_for_instr(self, instr):
        offset = self.srcmap[instr][0]

        start = self.source.rfind('\n', 0, offset)
        end = self.source.find('\n', offset)
        return self.source[start+1:end]
