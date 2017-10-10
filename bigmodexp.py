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
    Makes a call to modexp
    """

    p = c.Program()
    p.mstore(0x3,0xff2a1e53 )
    p.delegatecall(0x11ecd01b,0x5,0x0,0x60)
    p.op(c.STOP)
    return p.bytecode()

def main():
    g = genesis.Genesis()
    
    g.setConfigMetropolis()
    
    (geth_g, parity_g) = g.export()
    print(parity_g)

    geth = vm.GethVM("/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm")
    par = vm.ParityVM(executable="holiman/std-parityvm", docker=True)
    print("Bytecode: ")
    print(generateCall())

    g_out = geth.execute(code = generateCall(), genesis = geth_g, json=True, gas=0xFFFF, memory=True)
    p_out = par.execute(code = generateCall(), genesis = parity_g, json=True, gas=0xFFFF, memory=True)
    l = len(g_out)
    if len(p_out) < l:
        l = len(p_out)

    for i in range(0,l):
        print(g_out[i])
        print("g:" + vm.toText(json.loads(g_out[i])))
        print("p:" + vm.toText(json.loads(p_out[i])))


if __name__ == '__main__':
    main()