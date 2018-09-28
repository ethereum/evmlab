"""
"""
#!/usr/bin/env python

import json
import tempfile, os
from evmlab import compiler as c
from evmlab import vm
from evmlab import genesis

def generateCall():

    # the caller
    p = c.Program()
    #   create2(self,value = 0,instart = 0, insize = 0, salt = 0):
    p.op(c.ADDRESS)
    p.create2(0,0,0,0)

    # the callee, doing the create
    return p.bytecode()


def main():
    g = genesis.Genesis()
    
    g.setConfigConstantinople()
    bytecode = generateCall()
    #print("code:", bytecode)
#    g.addPrestateAccount({'address':'0x0000000000000000000000000000000000000000', 'code': '0x'+bytecode, 'balance':"0x00",'nonce':"0x01"})

    (geth_g, parity_g) = g.export()
    print(parity_g)
    print(geth_g)

    geth = vm.GethVM("/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm")

    g_out = geth.execute(code = bytecode, receiver="0x0000000000000000000000000000000000000000", genesis = geth_g, json=True, gas=100000, memory=False)
    #print(geth.lastCommand)
    print("")
    l = len(g_out)
    for i in range(0,l):
        print(vm.toText(json.loads(g_out[i])))


if __name__ == '__main__':
    main()