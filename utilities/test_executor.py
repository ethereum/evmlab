#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections, shutil
from evmlab import vm as VMUtils
from fuzzer import startDaemons, RawStateTest, start_processes, end_processes, processTraces
import copy

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def runTest(test_obj, filename):
    id = "".join(filename.split("-")[:-1])
    print("id",id )
    test = RawStateTest(copy.deepcopy(test_obj),id, filename)
    test.writeToFile()
    start_processes(test)
    end_processes(test)
    failingTestcase = processTraces(test, forceSave = False)
    if failingTestcase is None:
            return

    

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
    
    runTest(testcase, os.path.basename(path))


if __name__ == '__main__':
    main(sys.argv[1:])
