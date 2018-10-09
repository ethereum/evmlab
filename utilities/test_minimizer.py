#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections, shutil
from evmlab import vm as VMUtils
from fuzzer import startDaemons, StateTest, start_processes, end_processes, processTraces
import copy

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def capcode(code):
    if len(code) > 20000:
        return code[:-5000]
    if len(code) > 10000:
        return code[:-2000]
    if len(code) > 1000:
        return code[:-200]
    if len(code) > 100:
        return code[:-10]
    if len(code) > 10:
        return code[:-4]

    return code[:-2]


def mutate(test_obj, counter ):
    counter = 0
    original = copy.deepcopy(test_obj)
    print(test_obj["randomStatetest"]["pre"].keys())
    accounts = test_obj["randomStatetest"]["pre"]
    prestate_account_list = list(accounts.keys())
    print("presetate accounts" , prestate_account_list)
    print("yielding original")
    yield(test_obj)
    for a in prestate_account_list:
        deleted = accounts.pop(a)
        print("deleted account ", a)
        rollback = yield copy.deepcopy(test_obj)
        if rollback:
            print("undeleted account ", a)
            accounts[a] = deleted

    # Done miminizing accounts, let's remove code
    prestate_account_list = list(accounts.keys())
    for add, data in accounts.items():
        code = data["code"]
        data["code"] = ""
        print("deleted code for ",add)
        rollback = yield copy.deepcopy(test_obj)
        if rollback:
            print("undeleted code for ", a)
            data["code"] = code

    # Done miminizing accounts, let's minimize input
    tx = test_obj["randomStatetest"]["transaction"]
    if len(tx["data"][0]) > 0:
        tx["data"][0] = ""
        rollback = yield copy.deepcopy(test_obj)
        if rollback:
            tx["data"][0] = data

    # Done miminizing accounts, let's cap code
    prestate_account_list = list(accounts.keys())
    for add, data in accounts.items():
        if "code" in data.keys():
            code = data["code"]
            while True:
                newcode = capcode(code)
                if newcode == "":
                    break
                data["code"] = newcode
                print("shortened code for ",add, len(data["code"]))
                rollback = yield copy.deepcopy(test_obj)
                if rollback:
                    print("unshortened code for ",add)
                    data["code"] = code
                    break
                else:
                    code = newcode
                    continue

    yield(test_obj)
        #done

def forkify(test_obj):
    original = copy.deepcopy(test_obj)
    postState = test_obj["randomStatetest"]["post"]
    current_fork = list(postState.keys())[0]
    triggered_forks = []

    for forkname in ["Frontier", "Homestead", "EIP150","EIP158", "Byzantium", "Constantinople"]:
        postState[forkname] = postState.pop(current_fork)
        current_fork = forkname
        consensus = yield copy.deepcopy(test_obj)
        if consensus:
            print("Test did not trigger on", forkname)
        else:
            print("Test triggered on", forkname)
            triggered_forks.append(forkname)



class Mimizer():
    def __init__(self):
        self.counter = 0

    def isConsensus(self, test_obj):
        """ Returns true if the clients are in consensus over the testcase """
        self.counter = self.counter +1 
        test = StateTest(copy.deepcopy(test_obj), self.counter, overwriteFork=False)
        test.writeToFile()
        start_processes(test)
        data = end_processes(test)
        failingTestcase = processTraces(test, forceSave = False)
        if failingTestcase is not None:
            return False
        return True


    def reportResult(self, testcase, typ, path):
        minified = "./%s.%s" % (typ, os.path.basename(path))
        with open(minified, "w+") as f:
            json.dump(testcase, f)
        print("Stored %s" % minified)

    def startMutation(self, test_original, path):
        counter = 1
        name =  list(test_original.keys())[0]
        print("pre", test_original.keys())
        testcase = {"randomStatetest" : test_original[name]}
        print("pos", testcase.keys())
        consensus = self.isConsensus(testcase)
        if consensus:
            print("No consensus error triggered!")
            return
        mutator = mutate(testcase, 0)
        next(mutator)
        # First minimize
        while True:
            # Roll back incase of consensus
            try:
                testcase = mutator.send(consensus)
                consensus = self.isConsensus(testcase)
                print("Consensus" , consensus, "count", counter) 
                counter = counter + 1
            except StopIteration as e:
                break

        self.reportResult(testcase, "minified", path)
        
        # Then maximise: try different forks
        forker = forkify(testcase)
        testcase = next(forker)
        while True:
            # Roll back incase of consensus
            try:
                testcase = forker.send(consensus)
                consensus = self.isConsensus(testcase)
                if not consensus:
                    # Find out forkname
                    current_fork = list(testcase["randomStatetest"]["post"].keys())[0]
                    self.reportResult(testcase, "%s.minified" % current_fork , path)
                counter = counter + 1
            except StopIteration as e:
                break

        


def main(args):
    if len(args) < 1:
        logger.warning("please provide a filename")
        return

    path = args[0] 
    testcase = None
    # Can we read the testfile? 
    with open(path, "r") as f:
        testcase = json.load(f)
    # Start all docker daemons that we'll use during the execution
    startDaemons()
    
    Mimizer().startMutation(testcase, path)

if __name__ == '__main__':
    main(sys.argv[1:])
