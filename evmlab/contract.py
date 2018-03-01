#!/usr/bin/env python3
import re

from evmlab.opcodes import parseCode

"""
Solidity source code mappings, as 
documented [here](http://solidity.readthedocs.io/en/develop/miscellaneous.html#source-mappings)

"""


def update(original, changes):
    retval = []
    for i in range(0, len(original)):
        val = original[i]
        if i < len(changes) and len(changes[i]) > 0:
            val = changes[i]
        retval.append(val)
    return retval


def parseSourceMap(maptext):
    mapping = []

    if maptext is None:
        return mapping

    entries = maptext.split(";")
    m = ["", "", "", ""]
    for e in entries:
        vals = e.split(":")
        m = update(m, vals)
        mapping.append(m)
    return mapping


class Contract():
    _create = False

    bin = None
    ins = None
    binRuntime = None
    insRuntime = None
    lastSource = None
    name = ""

    def __init__(self, sources, contract=None, name=""):
        self.sources = sources or []
        self._contractTexts = {}
        self._sourceCache = {}
        self.name = name 

        self._loadContract(contract)

    @property
    def create(self):
        return self._create

    @create.setter
    def create(self, val):
        self._create = val
        self._loadContractTexts()

    @property
    def contractTexts(self):
        if len(self._contractTexts.keys()) == 0:
            self._loadContractTexts()

        return self._contractTexts

    def isInitialized(self):
        return self.bin is not None or self.binRuntime is not None

    def getSourceCode(self, pc):
        try:
            [s, l, f, j] = self._getInstructionMapping(pc)
            f = int(f)
            c = self.contractTexts[f]
        except KeyError:
            if self.lastSource:
                return self._sourceCache[self.lastSource][0], self._sourceCache[self.lastSource][1]
            
            return "Missing code", (0, 0)
        s = int(s)
        l = int(l)

        h = hash((s, l, f, j))
        if h in self._sourceCache:
            self.lastSource = h
            return self._sourceCache[h][0], self._sourceCache[h][1]

        # contract is missing, return the last valid ins mapping
        if f < 0:
            while True:
                pc -= 1
                try:
                    [s, l, f, j] = self._getInstructionMapping(pc)
                except KeyError:
                    f = -1
                f = int(f)
                if f > 0:
                    c = self.contractTexts[f]
                    s = int(s)
                    l = int(l)
                    break

        # see if text contains multiple contracts
        contract_start_indices = [m.start(0)
                                  for m in re.finditer('^ *contract ', c)]

        # for multi contract files, get the start of the contract for the current instruction
        if len(contract_start_indices) > 1:
            contract_start = 0
            contract_end = -1

            for i in contract_start_indices:
                if i == s:
                    contract_start = s
                    break
                elif i > s:
                    # get the previous index
                    ci = contract_start_indices.index(i) - 1
                    if ci >= 0:
                        contract_start = contract_start_indices[ci]
                    break
                elif s > i and i == contract_start_indices[-1]:
                    contract_start = contract_start_indices[-1]

            pos = contract_start + c[contract_start:].find('{')
            openBr = 0
            while pos < len(c):
                if c[pos] == '{':
                    openBr += 1
                elif c[pos] == '}':
                    openBr -= 1

                if openBr == 0:
                    contract_end = pos + 1
                    break

                pos += 1

            # return only the contract we're interested in
            # we need to update the bytes start & end pos to reflect the truncated text we are returning
            res = (c[contract_start:contract_end], [s - contract_start, l])
            self._sourceCache[h] = res

            self.lastSource = h
            return res[0], res[1]
        else:
            self._sourceCache[h] = (c, [s, l])
            self.lastSource = h
            return c, [s, l]

    def _getInstructionMapping(self, pc):
        """
        :param pc: programCounter to fetch mapping for
        :return: [s, l, f, j] where:
             s is the byte-offset to the start of the range in the source file,
             l is the length of the source range in bytes and
             f is the source index mentioned above.
             j can be either i, o or -
               i   signifying whether a jump instruction goes into a function,
               o   returns from a function or
               -   is a regular jump as part of e.g. a loop.
        """
        i = self._getMappingIndex(pc)
        mapping = self.mapping if self.create else self.mappingRuntime

        return mapping[i]

    def _getMappingIndex(self, pc):
        ins = self.ins if self.create else self.insRuntime
        pcs = list(ins.keys())

        if pc in pcs:
            return pcs.index(pc)

        raise KeyError

    def _loadContract(self, contract):
        if not contract:
            return

        def load(key):
            try:
                return contract[key]
            except KeyError:
                print("Contract JSON missing key: %s" % key)
                return None

        bytecode = load('bin-runtime')
        if bytecode:
            self.binRuntime = bytecode
            self.insRuntime = parseCode(bytecode)

        bytecode = load('bin')
        if bytecode:
            self.bin = bytecode
            self.ins = parseCode(bytecode)

        self.mappingRuntime = parseSourceMap(load('srcmap-runtime'))
        self.mapping = parseSourceMap(load('srcmap'))

    def _loadContractTexts(self):
        self._sourceCache = {}
        mapping = self.mapping if self.create else self.mappingRuntime

        contract_indexes = set()
        for [s, l, f, j] in mapping:
            f = int(f)
            if (f > 0):
                contract_indexes.add(f)

        for i in contract_indexes:
            self._contractTexts[i] = self.sources[i]