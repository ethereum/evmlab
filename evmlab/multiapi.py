class MultiApi(object):

    """ Helper class for using several API:s. 
    Currently supports web3 and etherchain

    web3 is a bit better, since it allows for querying about balance
    and things at specified block height.
    """

    def __init__(self, web3 = None, etherchain = None):
        self.web3 = web3
        self.etherchain = etherchain


    def getAccountInfo(self, address, blnum = None):
        acc = {}
        if self.web3 is not None: 
            acc['balance'] = self.web3.eth.getBalance(address, blnum)
            acc['code']    = self.web3.eth.getCode(address, blnum)
            acc['nonce']   = self.web3.eth.getTransactionCount(address, blnum)
            acc['address'] = address
        elif self.etherchain is not None: 
            acc = self.etherchain.getAccount(address)
        return acc

    def getTransaction(self,h):

        translations = [("sender", "from"),
                        ("recipient", "to"),
                        ("block_id", "blockNumber" )]

        if self.web3 : 
            obj = self.web3.eth.getTransaction(h)
            for (a,b) in translations:
                obj[a] = obj[b]

        else:
            obj = self.etherchain.getTransaction(h)
            for (a,b) in translations:
                obj[b] = obj[a]

        return obj
