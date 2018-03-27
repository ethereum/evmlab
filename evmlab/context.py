from .contract import Contract
from . import mk_contract_address, encode_hex

def buildContexts(ops, api, contracts, txhash):
    contract_stack = []

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

    cache = {}
    for addr in getAddresses(ops, to):
        if addr in cache:
            c = cache[addr]

            if create and addr == to:
                if addr + '_created' in c:
                    c = cache[addr + '_created']
                else:
                    # if it's cached, then the contract is already created so we need
                    # to return the Contract instance w/ create = False
                    newc = object.__new__(Contract)
                    newc.__dict__ = c.__dict__.copy()
                    newc.create = False
                    c = newc
                    cache[addr + '_created'] = c

        else:
            acc = api.getAccountInfo(addr, blnum)
            c = findContractForBytecode(contracts, acc['code'])
            cache[addr] = c
            if not c:
                print("Couldn't find contract for address {}".format(addr))
            if c and create and addr == to:
                c.create = True

        contract_stack.append(Context(addr, c))

    # contractTexts are not loaded by default, the following will
    # load the contractTexts and populate the sourceCache for the contract
    # corresponding to each op in this tx, greatly improving the response
    # time when quickly moving through the opviewer ui
    i = 0
    while i < len(ops):
        pc = ops[i]['pc']
        contract_stack[i].getSourceCode(pc)
        i += 1

    return contract_stack


def getAddresses(ops, original_contract):
    """ determine the address of the sourceCode for each operation
     Returns an array of addresses, 1 for each op in ops
     """
    addresses = []

    cur_depth = None
    prev_depth = None
    prev_op = None
    cur_address = original_contract
    place_holders = []  # stores the index of where CREATE op addr should go in the addr_stack
    depth_to_addr = {}  # mapping to track depth to an addr so we can easily push the current addr on the stack when we return from a call

    step = 0
    for o in ops:
        if not 'depth' in o.keys():
            # We're done here
            break

        # Address tracking
        cur_depth = o['depth']

        # depth may not always start at 1. ganache-cli starts at 0
        # this will set the prev_depth from the first op
        if not prev_op:
            prev_depth = cur_depth
            depth_to_addr[cur_depth] = cur_address

        if cur_depth > prev_depth:
            # Made it into a call-variant
            # All call-lookalikes are 'gas,address,value' on stack,
            # so address is second item of prev line
            #
            # There's one exception, though; CREATE
            # With a CREATE, we don't know the address until after the RETURN
            # so we push a placeholder and update on the Return
            if prev_op['op'] == 0xf0:
                cur_address = None
                place_holders.append([len(addresses)])
            else:
                cur_address = prev_op['stack'][-2]

            depth_to_addr[cur_depth] = cur_address

        if cur_depth < prev_depth:
            # RETURN op. we now know the prev_depth address, so add to context
            if cur_address is None and prev_op['op'] == 0xf3:
                prev_address = o['stack'][-1]
                for i in place_holders.pop():
                    addresses[i] = prev_address
            # Returned from a call
            cur_address = depth_to_addr[cur_depth]

        if not cur_address:
            place_holders[-1].append(len(addresses))

        addresses.append(cur_address)
        prev_op = o
        prev_depth = cur_depth

    # handle debug_traceTransaction output
    def fixAddr(a):
        if a and len(a) > 40:
            if (a.startswith('0x') and len(a) == 42):
                return a
            else:
                return "0x%s" % a[24:]

    addresses = [fixAddr(a) for a in addresses]

    return addresses


def findContractForBytecode(contracts, bytecode):
    if bytecode.startswith('0x'):
        bytecode = bytecode[2:]

    for c in contracts:
        # ignore last 34 bytes which is just metadata
        if c.bin and c.bin[:68] == bytecode[:68] or c.binRuntime and c.binRuntime[:68] == bytecode[:68]:
            return c

    return None


class Context(object):
    def __init__(self, address, contract):
        self.address = address
        self.contract = contract

    def getSourceCode(self, pc):
        if self.contract:
            return self.contract.getSourceCode(pc)

        return "Missing Contract", (0, 0)

    @property
    def name(self):
        return self.contract.name if self.contract else "?"
