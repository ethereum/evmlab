#!/bin/env python3
import random
import string
import subprocess
import json

def cmdGeth(genesis = None, code = "", gas = 0):
    """evm --debug --gas 1048575 --code ""  --json run  
    """
    cmd = [G_VM, "--code", code ,"--json"]
    if gas > 0: 
        cmd.append("--gas")
        cmd.append("%d" % gas)
    cmd.append("run")

    return cmd


def cmdParity(genesis = None, code = "", gas = 0):
    """parity-evm --code 732a50613a76a4c2c58d052d5ebf3b03ed3227eae9316001600155  --json --gas fffff
    """
    cmd = [P_VM, "--code", code , "--json"]
    if gas > 0: 
        cmd.append("--gas")
        cmd.append("%s" % hex(gas)[2:])

    return cmd

def json_ops(output):

    for line in output:
        if len(line) > 0 and line[0] == "{":
            yield json.loads(line)

def outputs(json_generators):
    for g in json_generators:   
        outp = stdout.readline()
        if outp == "":
            items.append({})
            finished = True
        else:
            outp = outp.strip()
            try:
                items.append(json.loads(outp))
            except ValueError:
                print("Invalid json: %s" % outp)
                items.append({})
    yield items

def canon(str):
    if str in [None, "0x", ""]:
        return ""
    if str[:2] == "0x":
        return str
    return "0x" + str

def toText(op):
    if len(op.keys()) == 0:
        return "END"
    if 'pc' in op.keys():
        return "pc {pc} op {op} gas {gas} cost {gasCost} depth {depth} stack {stack}".format(**op)
    elif 'output' in op.keys():
        op['output'] = canon(op['output'])
        return "output {output} gasUsed {gasUsed}".format(**op)
    return "N/A"

def execute(code, gas = 0xFFFF, verbose = False):

    from evmlab import gethvm, parityvm
    from evmlab.genesis import Genesis


    gvm =  gethvm.VM("holiman/gethvm", docker = True)
    pvm =  parityvm.VM("holiman/parityvm", docker = True)

    geth_genesis = Genesis().export_geth()
    parity_genesis = Genesis().export_parity()


    outp1 = gvm.execute(code = code, gas = gas, price=1, json=True, genesis = geth_genesis)
    outp2 = pvm.execute(code = code, gas = gas, price=1, json=True, genesis = parity_genesis)

    outp1_json = [x for x in json_ops(outp1)]
    outp2_json = [x for x in json_ops(outp2)]

    for o in range(0,max(len(outp1_json),len(outp2_json))):
        
        if o < len(outp1_json):
            g = outp1_json[o]
        else: 
            g = {}

        if o < len(outp2_json):
            p = outp2_json[o]
        else: 
            p = {}

        p = outp2_json[o]
    
        a = toText(g)
        b = toText(p)

        if a == b:
            print("[*] %s" % a)
        else:
            print("[!!] G:>> %s " % (a))
            print("[!!] P:>> %s " % (b))


    return

def getRandomCode():
    cmd = ["docker", "run","holiman/testeth","--randomcode","100"]
    import subprocess
    print(" ".join(cmd))
    return subprocess.check_output(cmd).strip()

def fuzz(gas):

    for i in range(1,10):
        print("----Fuzzing--- ")
        code = ''.join(random.choice(string.hexdigits) for _ in range(100))
        execute(code, gas )
        print("-------- ")


def main():
    print( getRandomCode())
    # parse args
    code = "732a50613a76a4c2c58d052d5ebf3b03ed3227eae9316001600155"
    gas = 0xffff

    execute(code, gas)
    
    #fuzz(gas )

if __name__ == '__main__':
    main()

