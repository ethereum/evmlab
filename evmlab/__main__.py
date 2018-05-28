#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
EVMLab command line utility: #> python3 -m evmlab <subcommand> <args>
"""
import sys


def usage(msg=""):
    description="""
EVMLab command line utility

Usage:
    #> python3 -m evmlab <subcommand> <args>

    available subommands
    * opviewer      ...     reproduce and debug transactions
    * reproducer    ...     reproduce transactions


    %s
""" % msg
    print(description)
    return 1  # exitcode / hint error condition


# configure available subcommands here
SUBCOMMAND = {'opviewer': lambda:sys.exit(usage("--not yet implemented--")),
              'reproducer': lambda:sys.exit(usage("--not yet implemented--"))}


def main():
    if not len(sys.argv)>1:
        sys.exit(usage("- subcommand is mandatory"))

    cmd_util = sys.argv.pop(1)  # pop <util> from cmdline args

    ret = SUBCOMMAND.get(cmd_util.strip().lower(), usage)()
    sys.exit(ret)


if __name__ == "__main__":
    main()
