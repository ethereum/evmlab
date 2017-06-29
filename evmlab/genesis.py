import json
class Genesis(object):
    """ Utility to create genesis files"""
    
    def __init__(self):
        self.alloc  = {}

    def geth(self):
        g = {
            "nonce":      "0x0000000000000000",
            "difficulty": "0x1",
            "mixhash":    "0x0000000000000000000000000000000000000000000000000000000000000000",
            "coinbase":   "0x0000000000000000000000000000000000000000",
            "timestamp":  "0x00",
            "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "extraData":  "0x0000000000000000000000000000000000000000000000000000000000000000",
            "gasLimit":   "0x3D0900",
            "alloc": self.alloc,
            "config": {
                "eip150Block": 0, 
                "eip158Block": 0, 
                "eip155Block": 0, 
                "homesteadBlock": 0, 
                "daoForkBlock": 0,
                "metropolisBlock": 2000,
            }
        }
        return g

    def parity(self):

        builtins = {
                "0000000000000000000000000000000000000001": { "builtin": { "name": "ecrecover", "pricing": { "linear": { "base": 3000, "word": 0 } } } },
                "0000000000000000000000000000000000000002": { "builtin": { "name": "sha256", "pricing": { "linear": { "base": 60, "word": 12 } } } },
                "0000000000000000000000000000000000000003": { "builtin": { "name": "ripemd160", "pricing": { "linear": { "base": 600, "word": 120 } } } },
                "0000000000000000000000000000000000000004": { "builtin": { "name": "identity", "pricing": { "linear": { "base": 15, "word": 3 } } } }
            }
        builtins.update(self.alloc)
        g = {
            "name": "lab",
            "engine": {
               "Ethash": {
                  "params": {
                    "gasLimitBoundDivisor": "0x0400",
                    "minimumDifficulty": "0x020000",
                    "difficultyBoundDivisor": "0x0800",
                    "durationLimit": "0x0d",
                    "blockReward": "0x4563918244F40000",
                    "registrar": "",
                    "frontierCompatibilityModeLimit": "0x0",
                    "eip155Transition" : "0x0",
                    "eip160Transition" : "0x0",
                    "eip161abcTransition" : "0x0",
                    "eip161dTransition" : "0x0",

                    }
                }
            },
            "genesis": {
                "seal": {
                  "ethereum": {
                    "nonce": "0x0000000000000042",
                    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000"
                  }
                },
                "difficulty": "0x400",
                "author": "0x3333333333333333333333333333333333333333",
                "timestamp": "0x0",
                "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
                "extraData": "0x0",
                "gasLimit": "0x8000000",
            },
            "params": {
                "accountStartNonce": "0x0",
                "maximumExtraDataSize": "0x20",
                "minGasLimit": "0x1388",
                "networkID" : "0x0",
                "eip98Transition": "0x0",
                "eip86Transition": "0x0"
            },
            "accounts": self.alloc,
        }
        return g

    def has(self, account):
        return account.lower() in self.alloc.keys()

    def add(self, account): 
            
        """
        Data format from EtherChain:
                {
                "address": "0x6090a6e47849629b7245dfa1ca21d94cd15878ef",
                "balance": 0,
                "nonce": null,
                "code": "0x60...",
                "name": null,
                "storage": null,
                "firstSeen": "2017-04-26T19:12:56.000Z"
            }
            """
        n = account['nonce'] 
        if n is None:
            n = 0
        b = hex(account['balance'])

        self.alloc[account['address'].lower()] = {
            "balance" : b, 
            "code" : account['code'], 
            "nonce" : hex(n), 
        }

    def export_geth(self):
        import tempfile, os
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        with open(temp_path, 'w') as f :
            json.dump(self.geth(),f)
        os.close(fd)
        print("Temp file %s " % temp_path)
        return temp_path

    def prettyprint(self):
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(self.geth())
