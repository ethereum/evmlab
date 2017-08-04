
import os
import requests
import json

here = os.path.dirname(os.path.abspath(__file__))

def log(x):
    print("[+] %s" % x)


def savejson(fname, obj):
    fqfn = '%s/datastore/%s' % (here, fname)
    with open(fqfn, 'w+') as outfile:
        outfile.write(json.dumps(obj))

    log("Wrote file %s" % fqfn)

def loadjson(fname):
#   return None
    try:
        with open('%s/datastore/%s' % (here, fname), 'r') as infile:
            return json.loads(infile.read())
    except Exception as e:
        print(e)
        return None


class EtherChainAPI():

    def __init__(self, offline = False):
        self.offline = offline
        self.cachedBlocks = None
        self.flushcounter = 0

    def getBlockInfo(self, blockNumberOrHash):
        """
        Fields :
            {"number":101010
            ,"hash":"0x3e5c2f13bc01a0a32c7eda3560ec3ede19c9d2f6c0fda8436999eee2914e862d"
            ,"parentHash":"0x8290679004240a002dcf274bf56310c2654b5137c643e5c20ff647ebda61033b"
            ,"uncleHash":"0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347"
            ,"coinbase":"0xc603ab5ef41fc61aa8b76beddb09e3cfcbb174bd"
            ,"root":"0x3df3a270c940336f7585d9b62a37fa04b2e2794f3267915f65b202e37a93c4e5"
            ,"txHash":"0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421"
            ,"difficulty":3871451743585
            ,"gasLimit":3141592
            ,"gasUsed":0
            ,"time":"2015-08-17T12:53:09.000Z"
            ,"extra":"0x476574682f76312e302e312f77696e646f77732f676f312e342e32"
            ,"mixDigest":null
            ,"nonce":"0xeaedaa0e2baa6334"
            ,"tx_count":0
            ,"uncle_count":0
            ,"size":544
            ,"blockTime":1
            ,"reward":5000000000000000000}      
        """
        # Load cached data
        if self.cachedBlocks == None:
            self.cachedBlocks = loadjson(".blocks.json") or {}

        if(self.cachedBlocks.has_key(blockNumberOrHash)):
            return self.cachedBlocks[blockNumberOrHash]


        url = "https://etherchain.org/api/block/%s"  % str(blockNumberOrHash)
        log(url)
        data = requests.get(url).json()['data'][0]

        #save
        self.cachedBlocks[data['hash']] = data
        self.cachedBlocks[data['number']] = data

        self.flushcounter = self.flushcounter+1
        if self.flushcounter > 50:#Always on now
            savejson('.blocks.json', self.cachedBlocks)
            self.flushcounter =0 

        return data
    def getBlockTime(self, blockNumberOrHash):
        return self.getBlockInfo(blockNumberOrHash)['time']


    def getTransaction(self, txhash):
        return requests.get("https://etherchain.org/api/tx/%s" % txhash).json()['data'][0]

    def getAllTransactions(self, address):
        """ Returns an iterator of all transactions to/from the specified address
            Internally, this shelves transactions to disk, and only queries for new 
            transactions
        """
        # Load cached data
        cachedTransactions = loadjson(".%s-transactions.json" % address) or {'byhash':{}}

        tx_byhash = cachedTransactions['byhash']

        stats = {"added" : 0}
        
        def insert(tx):
            if not tx_byhash.has_key(tx['hash']):
                tx_byhash[tx['hash']] = tx
                stats['added'] = stats['added']+1
                return True
            return False

        #Fetch new data
        abort = self.offline
        while not abort:
            offset = len(tx_byhash)

            url = "https://etherchain.org/api/account/%s/tx_asc/%d" % (address, offset)
            log(url)
            resp = requests.get(url)
            if resp.status_code == 200 :
                jsondata = resp.json()['data']
                for tx in jsondata:
                    if not insert(tx): 
                        log("Error, we got a tx we already have. Probably missing earlier transactions for %s" % address)
                        abort = True

                if len(jsondata) < 50:
                    abort = True

            else:
                raise Exception("Failed to get %s history" % instr)


        #Save cache
        if stats['added'] > 0:
            savejson(".%s-transactions.json" % address, cachedTransactions)
            print("Added %d transactions for %s" % (stats['added'], address))

        # Return txs starting at lowest nonce
        for h,tx in tx_byhash.items():
            yield tx


    def outgoingTransactions(self, address):
        for tx in self.getAllTransactions(address):
            if tx['sender'].lower() == address.lower():
                yield tx

    def contractCreateTransactions(self, address):
        for tx in self.outgoingTransactions(address):
            if tx['newContract'] != 0:
                yield tx

    def contractCreationTransaction(self, address):
        for tx in self.incomingTransactions(address):
            if tx['newContract'] != 0:
                yield tx
        return


    def incomingTransactions(self, address):
        for tx in self.getAllTransactions(address):
            if tx['recipient'].lower() == address.lower():
                yield tx

    def sendersTo(self, address):
        address = address.lower()
        allTxs = []
        totalCost =0
        senders = set()
        
        log("Loading senders to %s" % address)
        
        for tx in self.incomingTransactions(address):
            gasUsed = float(tx['gasUsed'])
            price = float(tx['price'])
            cost = (gasUsed * price)
            senders.add(tx['sender'])
            allTxs.append(tx['time'])
            #print(tx)
            totalCost = totalCost + cost

        allTxs.sort()
        return (senders, totalCost, allTxs)

    def getAccount(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]


    def getBalance(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]['balance']

    def getCode(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]['code']


    def getBalances(self,addresses):
        return [(address,self.getBalance(address)) for address in addresses]


    def findNewContracts(self, address):
        """ Finds all contracts created by a given address
        Returns all previously unseen contract"""

        foundContracts = {}

        # Find them all
        for tx in self.contractCreateTransactions(address):
            newC = tx['recipient'].lower()
            foundContracts[newC] = tx

        #Check which we already know about
        knownContracts = loadjson(".%s-contracts.json" % address) or {}

        diff = []
        for k,v in foundContracts.iteritems():
            if not k in knownContracts.keys():
                diff.append(v)
                knownContracts[k] = v
        # Save
        if len(diff) > 0:
            savejson(".%s-contracts.json" % address, knownContracts)
        return diff

    def getAllContracts(self, address):
        """ Finds all contracts created by a given address"""
        self.findNewContracts(address)
        knownContracts = loadjson(".%s-contracts.json" % address) or {}
        return knownContracts.values()


if __name__ == '__main__':
    api = EtherChainAPI(offline=True)
    