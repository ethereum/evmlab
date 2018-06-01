#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import json
from evmlab import compiler as c
from evmlab import vm
from evmlab import genesis

def generateCall():
    """
    Makes a call to ecadd
    """

    p = c.Program()
    p.call(0x7bc9,0x06,0)
    p.op(c.GAS)
    return p.bytecode()


def main():
    g = genesis.Genesis()
    g.setConfigMetropolis()
    (geth_g, parity_g) = g.export()

    geth = vm.GethVM("/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm")
    outp = geth.execute(code = generateCall(), genesis = geth_g, json=True)
    prev = 0
    for l in outp:
        obj = json.loads(l)
        if 'gas' in obj.keys():
            g = int(obj['gas'],16)
            print(l)
            print("Gas: %d (delta: %d)" % (g, (g-prev)))
            prev = g


if __name__ == '__main__':
    main()
