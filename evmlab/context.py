from ethereum.utils import mk_contract_address, encode_hex
from .contract import Contract


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
    for addr in findContractChanges(ops, to):
        if addr in cache:
            c = cache[addr]
            if c and create and addr == to:
                # if it's cached, then the contract is already created so we need to create a new Contract instance w/ create = False
                newc = object.__new__(Contract)
                newc.__dict__ = c.__dict__.copy() 
                c = newc

        else:
            acc = api.getAccountInfo(addr, blnum)
            c = findContractForBytecode(contracts, acc['code'])
            cache[addr] = c
        if not c:
            print("Couldn't find contract for address {}".format(addr))
        if c and create and addr == to:
            c.create = True

        contract_stack.append(Context(addr, c))

    return contract_stack


def findContractChanges(ops, original_contract):
    """ This method searches through an EVM-output and locates any depth changes
     Returns a stack of address that are visited. Each depth change will push another addy on the stack
     """
    addr_stack = []

    cur_depth = None
    prev_depth = None
    prev_op = None
    cur_address = original_contract
    place_holders = [] # stores the index of where CREATE op addr should go in the addr_stack
    depth_to_addr = {} # mapping to track depth to an addr so we can easily push the current addr on the stack when we return from a call

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
            addr_stack.append(cur_address)
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
                place_holders.append(len(addr_stack))
            else:
                cur_address = prev_op['stack'][-2]
                depth_to_addr[cur_depth] = cur_address

            addr_stack.append(cur_address)

        if cur_depth < prev_depth:
            # RETURN op. we now know the prev_depth address, so add to context
            if cur_address is None and prev_op['op'] == 0xf3:
                prev_address = o['stack'][-1]
                i = place_holders.pop()
                addr_stack[i] = prev_address
            # Returned from a call
            cur_address = depth_to_addr[cur_depth]
            addr_stack.append(cur_address)

        prev_op = o
        prev_depth = cur_depth

    # handle debug_traceTransaction output
    def fixAddr(a):
        if len(a) > 40:
            if (a.startswith('0x') and len(a) == 42):
               return a 
            else:
                return "0x%s" % a[24:]
    
    addr_stack = [fixAddr(a) for a in addr_stack]

    return addr_stack


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

        return "Missing Contract", (0, 0)
