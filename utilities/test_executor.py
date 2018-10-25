#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Executes state tests on multiple clients, checking for EVM trace equivalence

"""
import json, sys, re, os, subprocess, io, itertools, traceback, time, collections, shutil
from evmlab import vm as VMUtils
from fuzzer import Fuzzer,  RawStateTest, Config
import copy
import time
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
 

def runTest(test_obj, filename, f):
    id = "".join(filename.split("-")[:-1])
    print("id",id )
    if len(id) == 0:
        #Just use everything up to .json
        id = "".join(filename.split(".")[:-1])
    test = RawStateTest(copy.deepcopy(test_obj),id, filename, f._config)
    test.writeToFile()
    f.start_processes(test)
    time.sleep(1)
    f.end_processes(test)
    failingTestcase = f.processTraces(test, forceSave = True)
    if failingTestcase is None:
            return

    
class dummy():
    def __init__(self):
        self.configfile = "statetests.ini"
        self.force_save = True
        self.enable_reporting = False
        self.docker_force_update_image = []

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
    
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


    f = Fuzzer(config=Config(dummy()))

    f.start_daemons()
    
    runTest(testcase, os.path.basename(path),f)


if __name__ == '__main__':
    main(sys.argv[1:])
