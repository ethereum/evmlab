#!/usr/bin/env python3

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

    content = []
    contractText = ""

    def __init__(self, sourcelist, contract=None):
        self.sourcelist = sourcelist

        self._loadSources()
        self._loadContract(contract)

    @property
    def create(self):
        return self._create

    @create.setter
    def create(self, val):
        self._create = val
        self._loadContractText()

    def isInitialized(self):
        return self.bin is not None or self.binRuntime is not None

    def getSourceCode(self, pc):
        [s, l, f, j] = self._getInstructionMapping(0)

        try:
            code_mapping = self._getInstructionMapping(pc)
        except KeyError:
            return "Missing code"
        s = int(s)
        l = int(l)

        # code_mapping offsets will be in relation to the entire contract file
        # this could be multiple contracts in a single .sol file, since we are
        # returning only the contract text, we need to update code_mapping offsets
        # to match the contractText
        transformed_mapping = [int(code_mapping[0]) - s, int(code_mapping[1]) - l]

        return self.contractText[s:s + l], transformed_mapping

    def getCode(self, pc):
        try:
            [s, l, f, j] = self._getInstructionMapping(pc)
        except KeyError:
            return "Missing code"

        s = int(s)
        l = int(l)
        return self.contractText[s:s + l]

    def getSource(self, pc):
        try:
            [s, l, f, j] = self._getInstructionMapping(pc)
        except KeyError:
            return ""

        s = int(s)
        l = int(l)
        f = int(f)
        text = self.content[f]

        return (text[:s], text[s:s + l], text[s + l:])

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

    def _loadSources(self):
        for file in self.sourcelist:
            with open(file) as s:
                print(s.name)
                self.content.append(s.read())

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

        if self.isInitialized():
            self._loadContractText()

    def _loadContractText(self):
        [s, l, f, j] = self._getInstructionMapping(0)

        f = int(f)

        self.contractText = self.content[f]
