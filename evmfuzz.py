#!/bin/env python3
import random
import string
import subprocess
import json




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
        return "pc {pc:>5} op {op:>3} {opName} gas {gas:>8} cost {gasCost:>8} depth {depth:>2} stack {stack}".format(**op)
    elif 'time' in op.keys():# Final one
        
        if 'output' not in op.keys():
           op['output'] = ""

        op['output'] = canon(op['output'])
        fmt = "output {output} gasUsed {gasUsed}"
        if 'error' in op.keys():
            e = op['error']
            if e.lower().find("out of gas") > -1:
                e = "OOG"
            fmt = fmt + " err: OOG"
        return fmt.format(**op)
    return "N/A"


def execute(code, gas = 0xFFFF, verbose = False):

    from evmlab import gethvm, parityvm
    from evmlab.genesis import Genesis


    gvm =  gethvm.VM("holiman/gethvm", docker = True)
    pvm =  parityvm.VM("holiman/parityvm", docker = True)

    g_out = gvm.execute(code = code, gas = gas,json=True, genesis = Genesis().export_geth())
    p_out = pvm.execute(code = code, gas = gas,json=True, genesis = Genesis().export_parity())

    def json_gen(o):
        for line in o:
            if len(line) > 0 and line[0] == "{":
                yield json.loads(line)

    g_out_json = json_gen(g_out)
    p_out_json = json_gen(p_out)
    num_fin = 0

    prev_parity_pc = 0
    while True:
        g = next(g_out_json, {})
        p = next(p_out_json, {})
        
        if g == p and g == {}:
            break

        a = toText(g)
        b = toText(p)

        if a == b:
            print("[👍] %s" % a)
        else:
            # Parity repeats the last instruction, which makes sense, since 
            # otherwise it wouldn't be possible to see what effect the last op
            # had on the stack. Geth, however, ends on a 'STOP', which is semantically
            # nicer, as if the code is surrounded by a space of zeroes.  
            # One way to detect this is to look at the 'PC'. 
            #  * Parity will report the same PC as the last op, 
            #  * Geth will increment the PC by one, going outside the actual code length
            
            if 'pc' in p.keys():
                parity_pc = p['pc']
                if prev_parity_pc == parity_pc and g['op'] == 0:
                    # Now we can safely ignore it
                    print("[👍] END")
            else:
                print ("Diff: ")
                print("[G] %s " % (a))
                print("[P] %s " % (b))
        
        if 'pc' in p.keys():
            prev_parity_pc = p['pc']


    return

def getRandomCode():
    cmd = ["docker", "run","holiman/testeth","--randomcode","100"]
    import subprocess
    print(" ".join(cmd))
    return subprocess.check_output(cmd).strip().decode("utf-8")[2:]

def fuzz(gas):

    for i in range(1,10):
        print("----Fuzzing--- ")
        code = ''.join(random.choice(string.hexdigits) for _ in range(100))
        execute(code, gas )
        print("-------- ")


def main():
    # parse args
    code = "732a50613a76a4c2c58d052d5ebf3b03ed3227eae9316001600155"
    gas = 0xffffff
    execute(code, gas)
    code = "7034b58fe4b8140fac218b4a113b14ae3a6471a42fd9979a285bfbd6df9dd70d656097f0ac6d30a3fa37ed70cd8d2e997844f26077948b055b3481fce44a4f2a8418787649af282a45b1363ccf7afa980b9a0fb4847a111d9b010c16212ed4e17c8506a6800e231ffb792f3ac96c308e2872d95bf3b4053135ed71b62d91987cb7b4137585626d220c628a72ea6299af836245523373a94f5374fce5edbc8e2a8697c15331677e6ebf0b633df3fac5f46aecf6fc9e6ae0b1ee3cb3b169113d80146f2ccb1caa9f61805a67a11d560ad9e4895174d079dd73245d52190fbe88c84d77b146247286dda069e1ec854b8e6a96cabb03946957a64a7a4bcefa9db42c7a32f1d685071a40cf6841a5494d671740976003f25f3d197de4807174d8419cb5a605f6e0542ef0d8e36daef9ff5b653bf37521f166073125f57bdad71b7e46111995b12dca9cf3186a7cdc6e28118afb02c1332d7ccd2dfc95741ffa716b7bf6ff250836e2993b1a0a0ecb5c102d3950a9017026451f1de5eb9289a3c44ad5fb82e0f75b7d5c301a63bb6c678343bba249ce288de1b598e8d2e974e293a4582d65a49e76d8b0d07921b1c10ff0d9ffa5b8750d3997a5578cd1f41765da338529d41775941e86cfdd9b4e35300cc5c531d8b5b4f47a562d94528a6f55c281d795c1ca48d031785d1f5749c161b6a46dab2dc51f238922dca691be3832be7d85c82f2ca03b490ad825b32bd4b3f2bb7f92279764932f01bd149ef8a31e69f574842c530545b887f96225ac4b6d06b0fa2d5168e35419000217c4ee76e51bee904e2d9fa905349063b5bd81d6548b121b8e0a6965741a6680a032771b6864c9cf9cdb9ba4f3125cd7183bd45bcc40938ec3851e886474afb693126933f081abdec592998350516192956271674c523271f78e04ffde759af8037ddfb11280f04594cb4174617b5c748f42777c44b2fa278f4406b0ba05edc10b15"

#    code = getRandomCode()
    execute(code, gas)


    #fuzz(gas )

if __name__ == '__main__':
    main()

