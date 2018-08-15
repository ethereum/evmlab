#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
import argparse
import json
from . import templates
from . import randomtest
from . import rndval

def main():
    description = """
    Tool to generate random statetests.
        """
    examples = """
    Examples

    # Reproduce a tx with a local evm binary
    python3 statetests.py --random=random_compressed_state
        """
    parser = argparse.ArgumentParser(description=description, epilog=examples,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)


    parser.add_argument('-r', '--random', help="Generate randomly filled test. optionally provide a compressed randomstate.", default=None)
    parser.add_argument('-t', '--template', help="Select statetest template", default='RandomStateTest')
    parser.add_argument('-S', '--include-random-state', action="store_true", default=False,
                        help="include random state in output. Can be used as a seed to reproduce the filled template")
    parser.add_argument('-c', '--count', default=1, type=int, help="number of random statetests to be generated [%default]")

    args = parser.parse_args()
    selected_template = getattr(templates.object_based, "TEMPLATE_"+args.template)

    if not selected_template:
        raise Exception("Template does not exist! - templates.object_based.TEMPLATE_%s"%args.template)

    t = templates.new(selected_template)

    if args.random:
        rndval.RandomSeed.set_state(args.random)  # set the state if provided, otherwise stay silent.
    elif args.include_random_state:
        rndval.RandomSeed.set_state()  # add random seed

    for _ in range(args.count):
        print(json.dumps(t, cls=randomtest.RandomTestsJsonEncoder), end="\n")
