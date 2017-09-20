import json
import sys
import re
import os
import io
from contextlib import redirect_stderr, redirect_stdout

from ethereum.utils import decode_hex, parse_int_or_hex, sha3, to_string, \
    remove_0x_head, encode_hex, big_endian_to_int

import ethereum.transactions as transactions
from ethereum.exceptions import InvalidTransaction
from ethereum.messages import apply_transaction
from ethereum.config import default_config, config_homestead, config_tangerine, config_spurious, config_metropolis, Env
import ethereum.tools.new_statetest_utils as new_statetest_utils
from ethereum.slogging import configure_logging

configure_logging(':trace', log_json=True)

init_state = new_statetest_utils.init_state


def compute_state_test_unit(state, txdata, konfig):
    state.env.config = konfig
    s = state.snapshot()
    try:
        # Create the transaction
        tx = transactions.Transaction(
            nonce=parse_int_or_hex(txdata['nonce'] or b"0"),
            gasprice=parse_int_or_hex(txdata['gasPrice'] or b"0"),
            startgas=parse_int_or_hex(txdata['gasLimit'] or b"0"),
            to=decode_hex(remove_0x_head(txdata['to'])),
            value=parse_int_or_hex(txdata['value'] or b"0"),
            data=decode_hex(remove_0x_head(txdata['data'])))
        if 'secretKey' in txdata:
            tx.sign(decode_hex(remove_0x_head(txdata['secretKey'])))
        else:
            tx.v = parse_int_or_hex(txdata['v'])
        # Run it
        prev = state.to_dict()
        print("calling apply_transaction")
        success, output = apply_transaction(state, tx)
        print("Applied tx")
    except InvalidTransaction as e:
        print("Exception: %r" % e)
        success, output = False, b''
    state.commit()
    post = state.to_dict()
    output_decl = {
        "hash": '0x' + encode_hex(state.trie.root_hash),
        #"indexes": indices,
        #"diff": mk_state_diff(prev, post)
    }
    state.revert(s)
    return output_decl




def runStateTest(test_case, test_transaction):
    print("running stateTest")
    pre_state = init_state(test_case['env'], test_case['pre'])
    #print("inited state:", _state.to_dict())
    print("pyeth default spurious config")
    test_config = config_spurious
    if test_case['config']['metropolisBlock'] == 0:
        print("pyeth setting metro config")
        test_config = config_metropolis
    elif test_case['config']['eip158Block'] != 0 and test_case['config']['eip150Block'] == 0:
        print("pyeth setting tangerine config")
        test_config = config_tangerine
    elif test_case['config']['eip150Block'] != 0 and test_case['config']['homesteadBlock'] == 0:
        print("pyeth setting homestead config")
        test_config = config_homestead
    computed = compute_state_test_unit(pre_state, test_transaction, test_config)
    #print("computed:", computed)


if __name__ == '__main__':
    print("statetest.py main.")
    pycmd, test_file, test_tx = sys.argv
    print("test_tx:", test_tx)
    print("tx_decoded:", json.loads(test_tx))
    #tx = json.loads(json.loads(test_tx))
    tx = json.loads(test_tx)
    #print("tx_decoded:", json.loads(tx_decoded))
    with open(test_file) as json_data:
        test_case = json.load(json_data)

    runStateTest(test_case, tx)
