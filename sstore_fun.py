"""
This program generats a piece of bytecode which 

1. Assumes that slot 1 has non-zero value of '2'
2. Overwrites slot 1 with '0'
3. Calls itself
  3.1 Overwrites slot '1' with '3'
  3.2 stop
4. stop

The step in 3.1 should decrease the refund counter with 15k

This program reproduces the flaw that parity and aleth had concerning
negative-valued refund counters in different call contexts
"""
#!/usr/bin/env python

import json
import tempfile, os
from evmlab import compiler as c
from evmlab import vm
from evmlab import genesis

def generateCall():

    def sstore(k, v):
        p.push(v).push(k).op(c.SSTORE)

    label = 21
    p = c.Program()
    # Check if we're calling ourself:
    p.op(c.CALLER) #0
    p.op(c.ADDRESS)#1
    p.op(c.EQ)     #2
    # Yes, we are, go to 3
    p.push(label)  
    p.op(c.JUMPI) 
    # No, this is first call
    sstore(1,0) # Set slot 1 to 0

    # Do the call
    p.push(0)        # outsize 
    p.op(c.DUP1)     # out
    p.op(c.DUP1)     # insize
    p.op(c.DUP1)     # instart 
    p.op(c.DUP1)     # value 
    p.op(c.ADDRESS)  # address
    p.op(c.GAS)      # gas
    p.op(c.CALL)     #
    p.op(c.STOP)     # 

    #This is 3.1
    p.op(c.JUMPDEST) # posotion 21
    # Set slot 
    sstore(1,3)    
    p.op(c.STOP)
    return p.bytecode()


def main():
    print("0x%s" % generateCall())

if __name__ == '__main__':
    main()
