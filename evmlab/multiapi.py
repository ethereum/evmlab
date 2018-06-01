
import shelve, traceback
from . import utils

class MultiApi(object):

    """ Helper class for using several API:s. 
    Currently supports web3 and etherchain

    web3 is a bit better, since it allows for querying about balance
    and things at specified block height.
    """

    def __init__(self, web3 = None, etherchain = None):
        self.web3 = web3
        self.etherchain = etherchain

    def _getCached(self,key):
        db = shelve.open(".api_cache")
        obj = None
        if key in db:
            obj = db[key]
        db.close()
        return obj

    def _putCached(self,key, obj):
        db = shelve.open(".api_cache")
        db[key] = obj
        db.close()

    def getAccountInfo(self, address, blnum = None):
        acc = {}

        
        print("GetAccountInfo(%s, %s)"% (address, str(blnum)))

        if blnum is not None: 
            cachekey = "%s-%d" % (address, blnum)
            cached = self._getCached(cachekey)
            if cached is not None:
                return cached

        if self.web3 is not None:
            # web3 only accepts checksummed addresses
            chk_address = utils.checksumAddress(address) 
            acc['balance'] = self.web3.eth.getBalance(chk_address, blnum)
            acc['code']    = self.web3.eth.getCode(chk_address, blnum)
            acc['nonce']   = self.web3.eth.getTransactionCount(chk_address, blnum)
            acc['address'] = address
    
            # testrpc will return 0x0 if no code, geth expects 0x
            if acc['code'] == '0x0':
                acc['code'] = '0x'

            # cache it, but only if it's at a specific block number
            if blnum is not None:
                self._putCached(cachekey, acc)

        elif self.etherchain is not None: 
            acc = self.etherchain.getAccount(address)

        return acc

    def getTransaction(self,h):

        cachekey = "tx-%s" % h

        o = self._getCached(cachekey)
        if o is not None:
            return o

        translations = [("sender", "from"),
                        ("recipient", "to"),
                        ("block_id", "blockNumber" )]

        if self.web3 : 
            obj = self.web3.eth.getTransaction(h)
            obj_dict = {}
            for a in obj:
              obj_dict[a] = obj[a]
            for (a,b) in translations:
                obj_dict[a] = obj_dict[b]

        else:
            obj = self.etherchain.getTransaction(h)
            obj_dict = {key: value for (key, value) in obj}
            for (a,b) in translations:
                obj_dict[b] = obj_dict[a]

        self._putCached( cachekey, obj_dict)
        return obj_dict

    def getStorageSlot(self, addr, key, blnum = None):

        print("GetStorageSlot(%s, %s, %s)"% (addr, key, str(blnum)))

        if blnum is not None: 
            cachekey = "%s-%d-%s" % (addr,blnum,key)
            cached = self._getCached(cachekey)
            if cached is not None:
                return cached

        if self.web3:
            try:
                value = self.web3.eth.getStorageAt(addr, key, blnum)
                self._putCached(cachekey, value)
                return value
            except Exception as e:
                print("ERROR OCCURRED: trace may not be correct")    
                traceback.print_exc()
                return ""
            
        else:
            print("getStorageSlot not implemented for etherchain api")
            return ""

    def traceTransaction(self, tx, disableStorage=False, disableMemory=False, disableStack=False, tracer=None,
                               timeout=None):
        if self.web3 is None:
            raise Exception("debug_traceTransaction requires web3 to be configured")

        # TODO: caching
        return self.web3.manager.request_blocking("debug_traceTransaction",
                                                  [tx, {"disableStorage": disableStorage,
                                                        "disableMemory": disableMemory,
                                                        "disableStack": disableStack,
                                                        "tracer": tracer,
                                                        "timeout": timeout}])
