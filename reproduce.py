"""
This is a tool to replicate live on-chain events. It starts with a transaction id

1 Fetch the transaction data from an API. 
2 Fetch the data at destination
3 Fetch balance and nonce at source
4 Execute transaction
5 If transaction has any externally reaching ops (BALANCE, EXTCODECOPY, CALL etc), 
  * Fetch info about those accounts
6. Go back to 4 until all account info is fetched. Code, balance, nonce etc. 
7. Generate a genesis, and code to invoke the on-chain event.

"""
#!/usr/bin/env python

import json
import tempfile, os
from evmlab import etherchain
from evmlab import compiler as c
from evmlab import genesis as gen

def generateCall(addr, gas = None, value = 0):
    """ Generates a piece of code which calls the supplies address"""
    p = c.Program()
    p.call(gas,addr, value)
    p.op(c.POP)
    return p.bytecode()

def findExternalCalls(list_of_output):
    externals = {
                "CALL"         : lambda o : o['stack'][-2], 
                "CALLCODE"     : lambda o : o['stack'][-2], 
                "DELEGATECALL" : lambda o : o['stack'][-2], 
                "EXTCODECOPY"  : lambda o : o['stack'][-1],
                "EXTCODESIZE"  : lambda o : o['stack'][-1],
                "BALANCE"      : lambda o : o['stack'][-1],
                }
    accounts = set()
    for l in list_of_output:
        o = json.loads(l.strip())
        if 'opName' in o and o['opName'] in externals.keys():
            accounts.add(externals[o['opName']](o))
    
    return list(accounts)

def reproduceTx(txhash, evmbin):
    
    from evmlab import gethvm
    vm = gethvm.VM(evmbin)
    genesis = gen.Genesis()
    api = etherchain.EtherChainAPI()

    """
            {
            "hash": "0xb8fdb51a1731a3a53d255b757432d0e2cdf65d12e90f76d66f80e907cf113b9e",
            "sender": "0x0b61c0c5ea330248b17069a7bdff35bf2c4062f0",
            "recipient": "0x6090a6e47849629b7245dfa1ca21d94cd15878ef",
            "accountNonce": "68",
            "price": 4000804100,
            "gasLimit": 300000,
            "amount": 0,
            "block_id": 3830525,
            "time": "2017-06-06T17:31:31.000Z",
            "newContract": 0,
            "isContractTx": null,
            "blockHash": "0xbf7daca54e2d00f5692f48af120e27aa3650ec72a424847b40ae3a6adad4f89a",
            "parentHash": "0xb8fdb51a1731a3a53d255b757432d0e2cdf65d12e90f76d66f80e907cf113b9e",
            "txIndex": null,
            "gasUsed": 81180,
            "type": "tx"
        }
    """

    tx = api.getTransaction(txhash)
    s = tx['sender']
    r = tx['recipient']
    bootstrap = generateCall(r)
    toAdd  = [s,r]
    done = False
    while not done:    
        done = True
        # Add accounts that we know of 
        for x in toAdd:
            if not genesis.has(x): 
                print("Adding %s to alloc... " % x)
                genesis.add(api.getAccount(x))
                done = False
        if not done:
            #genesis.prettyprint()
            g_path = genesis.export_geth()
            print("Executing tx...")
            output =  vm.execute(code = bootstrap, genesis = g_path, json = True)
            externalAccounts = findExternalCalls(output)
            print("Externals: %s " % externalAccounts )
            toAdd = externalAccounts

    #Now save a trace
    output =  vm.execute(code = bootstrap, genesis = g_path, json = True)

    fd, temp_path = tempfile.mkstemp(suffix=".txt")
    with open(temp_path, 'w') as f :
        f.write("\n".join(output))

    os.close(fd)


    print("Saved trace to %s" % temp_path)
    print("Genesis complete: %s" % g_path)


def test():
    evmbin = "/home/martin/go/src/github.com/ethereum/go-ethereum/build/bin/evm"
    tx = "0x66abc672b9e427447a8a8964c7f4671953fab20571ae42ae6a4879687888c495"
    reproduceTx(tx, evmbin)


if __name__ == '__main__':
    test()