"""
"""
#!/usr/bin/env python

import json
import tempfile, os
from evmlab import compiler as c
from evmlab import vm
from evmlab import genesis

def generateCall():
    """
    Makes a call to identity
    """

    p = c.Program()
    p.mstore(0,0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
    p.call(5000,0x01,0, instart= 0x0, insize= 0xff, out = 0x00 ,outsize = 0xfb)#0x2e83dbe)
    p.op(c.RETURNDATASIZE)
    p.op(c.STOP)
    return p.bytecode()


def main():
    g = genesis.Genesis()
    
    g.setConfigMetropolis()
    
    (geth_g, parity_g) = g.export()
    print(parity_g)

    geth = vm.GethVM("/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm")
    par = vm.ParityVM(executable="holiman/std-parityvm", docker=True)

    g_out = geth.execute(code = generateCall(), genesis = geth_g, json=True, gas=10000000, memory=False)
    p_out = par.execute(code = generateCall(), genesis = parity_g, json=True, gas=10000000, memory=True)
    l = len(g_out)
    if len(p_out) < l:
        l = len(p_out)

    for i in range(0,l):
        print("g:" + vm.toText(json.loads(g_out[i])))
        print("p:" + vm.toText(json.loads(p_out[i])))


if __name__ == '__main__':
    main()