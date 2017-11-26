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
    bin = None
    ins = None
    binRuntime = None
    insRuntime = None
    create = False
    content = []

    def __init__(self, sourcelist, contract=None):
        self.sourcelist = sourcelist

        def load(key):
            try:
                return contract[key]
            except KeyError:
                print("Contract JSON missing key: %s" % key)
                return None

        if contract:
            self._addBinRuntime(load('bin-runtime'))
            self.mappingRuntime = parseSourceMap(load('srcmap-runtime'))
            self._addBin(load('bin'))
            self.mapping = parseSourceMap(load('srcmap'))

        self._loadSources()

    def isInitialized(self):
        return self.bin is not None or self.binRuntime is not None

    def getSourceCode(self, pc):
        i = self._getMappingIndex(pc)

        if i == -1:
            return "Missing code"

        mapping = self.mapping if self.create else self.mappingRuntime

        [s, l, f, j] = mapping[i]
        # Where
        # s is the byte-offset to the start of the range in the source file,
        # l is the length of the source range in bytes and
        # f is the source index mentioned above.
        # j can be either i, o or -
        #   i   signifying whether a jump instruction goes into a function,
        #   o   returns from a function or
        #   -   is a regular jump as part of e.g. a loop.

        s = int(s)
        l = int(l)
        f = int(f)
        text = self.content[f]
        return text[s:s + l]

    def getSource(self, pc):
        i = self._getMappingIndex(pc)

        # if pc > len(self.mapping):
        if i == -1:
            return ""

        [s, l, f, j] = self.mapping[i]
        s = int(s)
        l = int(l)
        f = int(f)
        text = self.content[f]

        return (text[:s], text[s:s + l], text[s + l:])

    def _getMappingIndex(self, pc):
        ins = self.ins if self.create else self.insRuntime
        pcs = list(ins.keys())

        if pc in pcs:
            return pcs.index(pc)

        return -1

    def _loadSources(self):
        for file in self.sourcelist:
            with open(file) as s:
                print(s.name)
                self.content.append(s.read())

    def _addBinRuntime(self, bytecode):
        self.binRuntime = bytecode
        self.insRuntime = parseCode(bytecode)

    def _addBin(self, bytecode):
        self.bin = bytecode
        self.ins = parseCode(bytecode)
