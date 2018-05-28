#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import json
from evmlab import compiler as c
from evmlab import vm
from evmlab import genesis

def generateInitcode(addr):
    """
    Initcode which copies something else
    """

    p = c.Program()
    p.push(0x00)
    p.op(c.DUP1)
    p.push(addr)
    p.op(c.DUP1)
    p.op(c.EXTCODESIZE)
    p.op(c.DUP1)
    p.op(c.SWAP4)
    p.op(c.DUP1)
    p.op(c.SWAP2)
    p.op(c.SWAP3)
    p.op(c.EXTCODECOPY)
    p.push(0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef)
    p.op(c.DUP3)
    p.op(c.MSTORE)

    p.op(c.SWAP1)
    p.push(32)
    p.op(c.ADD)
    p.op(c.SWAP1)

    p.op(c.RETURN)
    return p.bytecode()

def main():

    cloneaddr = 0x123456789A123456789A123456789A123456789A

    g = genesis.Genesis()    
    g.setConfigMetropolis()
    g.add({'address': hex(cloneaddr), 
        'nonce': 0, 
        'code' : "0x1337", 
        'balance' : 0
        })
    (geth_g, parity_g) = g.export()

    initcode = generateInitcode(cloneaddr)

    #geth = vm.GethVM("/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm")
    geth = vm.GethVM("holiman/gethvm", docker=True)
    print("Bytecode: ", initcode)

    g_out = geth.execute(code = initcode, genesis = geth_g, json=True, gas=0xFFFF, memory=True)

    for i in g_out:
        obj = json.loads(i)
        if 'stack' in obj.keys():
            print("{}  {}".format(obj['opName'], obj['stack']))
        else:
            print(i)

if __name__ == '__main__':
    main()