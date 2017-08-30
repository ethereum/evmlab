#!/usr/bin/env python3
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

import json
import tempfile, os
from web3 import Web3, RPCProvider
from sys import argv, exit

from . import etherchain
from . import compiler as c
from . import genesis as gen
from . import opcodes
from . import evmtrace
from . import multiapi


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
        if len(l) == 0 or l[0] != "{":
            print("Odd line: %s" % l)
            continue
        o = json.loads(l.strip())
        if 'opName' in o and o['opName'] in externals.keys():
            accounts.add(externals[o['opName']](o))
    
    return accounts

def findStorageLookups(list_of_output, original_context):
    """ This method searches through an EVM-output and locates SLOAD queries
    Returns a list of (<address>, <key>)
    """

    # call context
    context = [] 
    # duplicate avoidance
    refs = set()

    # In order to do this, we need to track the context (address) we're executing in
    callstack = []

    cur_depth = 1
    prev_depth = 1
    prev_op = None
    cur_address = original_context

    for l in list_of_output:
        if len(l) == 0 or l[0] != "{":
            continue

        o = json.loads(l.strip())
        if not 'depth' in o.keys():
            #We're done here
            break
        # Address tracking - what's the context we're executing in
        cur_depth = o['depth']
        if cur_depth > prev_depth:
            #Made it into a call
            callstack.append(cur_address)
            # All call-lookalikes are 'gas,address,value' on stack, 
            # so address is second item of prev line
            cur_address = prev_op['stack'][-2]
        if cur_depth < prev_depth:
            # Returned from a call
            cur_address = callstack.pop()

        # Sload tracking
        if o['opName'] in ['SLOAD']:
            key  = o['stack'][-1]
            entry = (cur_address, key)
            refs.add(entry)

        prev_op = o
        prev_depth = cur_depth

    return refs


def debugdump(obj):
    import pprint
    pprint.PrettyPrinter().pprint(obj)


def reproduceTx(txhash, vm, api):

    genesis = gen.Genesis()
    
    tx = api.getTransaction(txhash)

    s = tx['from']
    r = tx['to']
    tx['input'] = tx['input'][2:]

    #debugdump(tx)
    blnum = int(tx['blockNumber'])


    externals_fetched = set()
    externals_tofetch = set([s,r])

    storage_slots_fetched = set()
    slots_to_fetch = set()
    receivercode = ""
    done = False
    while not done:
        done = True
        # Add accounts that we know of 
        for addr in list(externals_tofetch):
            acc = api.getAccountInfo( addr , blnum)
            genesis.add(acc)
            #debugdump(acc)
            done = False
        
        externals_fetched.update(externals_tofetch)

        for (addr,key) in list(slots_to_fetch):
            val = api.getStorageSlot( addr, key, blnum)
            genesis.addStorage(addr, key, val)
            done = False
        storage_slots_fetched.update(slots_to_fetch)
        
        if not done:
            (g_path, p_path) = genesis.export(txhash[:8])
            genesis_path = g_path
            if vm.genesis_format == 'parity':
                genesis_path = p_path

            print("Executing tx...")
            # We could use the following to set the code for parity:
            #receivercode = genesis.codeAt(r)
            vm_args = {
                "receiver"  : r,
                "sender"    : s,
                "genesis"   : genesis_path, 
                "json"      : True, 
                "input"     : tx['input'], 
                "memory"    : False,
            }
            output =  vm.execute(**vm_args)

            fd, temp_path = tempfile.mkstemp( prefix=txhash[:8]+'_', suffix=".txt")
            with open(temp_path, 'w') as f :
                f.write("\n".join(output))
                print("Saved trace to %s" % temp_path)
            os.close(fd)

            # External accounts to lookup
            externals_found = findExternalCalls(output)
            externals_tofetch = externals_found.difference(externals_fetched)
            if len(externals_tofetch) > 0:
                print("External accounts to fetch: %s " % externals_tofetch )
  
            # Storage slots to lookup
            slots_found = findStorageLookups(output, r)
            slots_to_fetch = slots_found.difference(storage_slots_fetched)
            if len(slots_to_fetch) > 0:
                print("SLOTS to fetch: %s " % slots_to_fetch)


    artefacts = {
        'geth genesis'   : g_path, 
        'parity genesis' : p_path, 
        'json-trace': temp_path}

    try:
        annotated_trace = evmtrace.traceEvmOutput(temp_path)
        fd, a_trace = tempfile.mkstemp( prefix=txhash[:8]+'_', suffix=".evmtrace.txt")
        with open(a_trace, 'w') as f :
            f.write(str(annotated_trace))
        os.close(fd)
        
        artefacts['annotated trace'] = a_trace

    except Exception as e:
        print("Evmtracing failed")
        print(e)

    return artefacts, vm_args
        

def testStoreLookup():
    tr = "/data/workspace/evmlab/0xd6d519043d40691a36c9e718e47110309590e6f47084ac0ec00b53718e449fd3_der80goh.txt"
    with open(tr, "r") as f:
        l = findStorageLookups(f,"recipient")
        debugdump(l)


def fetch(args):
    if len(args) < 1:
        print("Usage: ./reproduce.py <tx hash>")
        exit(1)
    evmbin = "evm"
    tx = args[0]
    web3 = Web3(RPCProvider(host = 'mainnet.infura.io', port= 443, ssl=True))
    chain = etherchain.EtherChainAPI()
    api = multiapi.MultiApi(web3 = web3, etherchain = chain)
    reproduceTx(tx, evmbin, api)


if __name__ == '__main__':
    #fetch(argv[1:])
    test()
    #testStoreLookup()