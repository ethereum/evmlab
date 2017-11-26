from ethereum.utils import mk_contract_address, encode_hex


def buildContexts(ops, api, contracts, txhash):
    contexts = {}

    tx = api.getTransaction(txhash)
    to = tx['to']
    blnum = int(tx['blockNumber'])

    if to == '0x0':
        to = None

    create = to is None

    # contract deployment
    # need to generate the contract address in order to fetch the bytecode
    if to is None:
        baddr = mk_contract_address(tx['from'], tx['nonce'])
        to = '0x%s' % encode_hex(baddr).decode()

    for depth, addr in findContextChanges(ops, to).items():
        acc = api.getAccountInfo(addr, blnum)
        c = findContractForBytecode(contracts, acc['code'])
        if not c:
            print("Couldn't find contract for address {}".format(addr))
            # print(acc['code'])
        if c and create and addr == to:
            c.create = True

        contexts[depth] = Context(addr, c)

    return contexts


def findContextChanges(ops, original_context):
    """ This method searches through an EVM-output and locates any depth changes
     Returns a dict of <depth>: <address>
     """
    contexts = {}

    cur_depth = None
    prev_depth = None
    prev_op = None
    cur_address = original_context

    for o in ops:
        if not 'depth' in o.keys():
            # We're done here
            break

        # Address tracking - what's the context we're executing in
        cur_depth = o['depth']

        # depth may not always start at 1. testrpc starts at 0
        # this will set the prev_depth from the first op
        if not prev_op:
            prev_depth = cur_depth
            # TODO this might not work for deploys
            contexts[cur_depth] = cur_address

        if cur_depth > prev_depth:
            # Made it into a call-variant
            # All call-lookalikes are 'gas,address,value' on stack,
            # so address is second item of prev line
            #
            # There's one exception, though; CREATE
            # With a CREATE, we don't know the address until after the RETURN
            if prev_op['op'] == 0xf0:
                cur_address = None
            elif prev_op['op'] != 0xf4:
                cur_address = prev_op['stack'][-2]
                contexts[cur_depth] = cur_address

        if cur_depth < prev_depth:
            if cur_address is None:
                print(prev_op)
                print(o)
                # TODO set context for cur_depth here. Should be RETURN opcode & get address from that
            # Returned from a call
            cur_address = contexts[cur_depth]

        prev_op = o
        prev_depth = cur_depth

    return contexts


def findContractForBytecode(contracts, bytecode):
    if bytecode.startswith('0x'):
        bytecode = bytecode[2:]

    for c in contracts:
        if c.bin == bytecode or c.binRuntime == bytecode:
            return c

    return None


class Context(object):
    def __init__(self, address, contract):
        self.address = address
        self.contract = contract

    def getSourceCode(self, pc):
        if self.contract:
            return self.contract.getSourceCode(pc)

        return "Missing Contract"
