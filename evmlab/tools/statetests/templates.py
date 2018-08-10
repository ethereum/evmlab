#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
import copy


def new(template):
    return copy.deepcopy(template)


TEMPLATE_TransactionTest = {
    "randomTransactionTest": {
        "transaction":
            {
                "data": "[CODE]",
                "gasLimit": "[HEX]",
                "gasPrice": "[HEX]",
                "nonce": "[HEX]",
                "to": "[HASH20]",
                "value": "[HEX]",
                "v": "[V]",
                "r": "[0xHASH32]",
                "s": "[0xHASH32]"
            }
    }
}

TEMPLATE_STATETest = {
    "randomStatetest": {
        "env": {
            "currentCoinbase": "[0xADDRESS]",
            "currentDifficulty": "0x20000",
            "currentGasLimit": "[BLOCKGASLIMIT]",
            "currentNumber": "1",
            "currentTimestamp": "1000",
            "previousHash": "[HASH32]"
        },
        "expect": [
            {
                "indexes": {
                    "data": -1,
                    "gas": -1,
                    "value": -1
                },
                "network": [">=Frontier"],
                "result": {
                    "a94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                        "nonce": "1"
                    }
                }
            }
        ],
        "pre": {
            "ffffffffffffffffffffffffffffffffffffffff": {
                "balance": "[HEX]",
                "code": "[CODE]",
                "nonce": "[V]",
                "storage": {
                }
            },
            "1000000000000000000000000000000000000000": {
                "balance": "[HEX]",
                "code": "[CODE]",
                "nonce": "[V]",
                "storage": {
                }
            },
            "b94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": "[HEX]",
                "code": "[CODE]",
                "nonce": "[V]",
                "storage": {
                }
            },
            "c94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": "[HEX]",
                "code": "[CODE]",
                "nonce": "[V]",
                "storage": {
                }
            },
            "d94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": "[HEX]",
                "code": "[CODE]",
                "nonce": "[V]",
                "storage": {
                }
            },
            "a94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": "[HEX]",
                "code": "0x",
                "nonce": "0",
                "storage": {
                }
            }
        },
        "transaction": {
            "data": [
                "[CODE]"
            ],
            "gasLimit": [
                "[TRANSACTIONGASLIMIT]",
                "3000000"
            ],
            "gasPrice": "[GASPRICE]",
            "nonce": "0",
            "secretKey": "0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
            "to": "[DESTADDRESS]",
            "value": [
                "[HEX32]",
                "0"
            ]
        }
    }
}

TEMPLATE_VMTest = {
    "randomVMTest": {
        "env": {
            "previousHash": "[HASH32]",
            "currentNumber": "[HEX]",
            "currentGasLimit": "[BLOCKGASLIMIT]",
            "currentDifficulty": "[HEX]",
            "currentTimestamp": "[HEX]",
            "currentCoinbase": "[HASH20]"
        },
        "pre": {
            "0x0f572e5295c57f15886f9b263e2f6d2d6c7b5ec6": {
                "balance": "[HEX]",
                "nonce": "[HEX]",
                "code": "[CODE]",
                "storage": {}
            }
        },
        "exec": {
            "address": "0x0f572e5295c57f15886f9b263e2f6d2d6c7b5ec6",
            "origin": "[HASH20]",
            "caller": "[HASH20]",
            "value": "[HEX]",
            "data": "[CODE]",
            "gasPrice": "[V]",
            "gas": "[HEX]"
        }
    }
}

TEMPLATE_RLPTest = {
    "randomRLPTest": {
        "out": "[RLP]"
    }
}

TEMPLATE_BlockchainTest = {
    "randomBlockTest": {
        "genesisBlockHeader": {
            "bloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            "coinbase": "[HASH20]",
            "difficulty": "131072",
            "extraData": "[CODE]",
            "gasLimit": "4712388",
            "gasUsed": "0",
            "mixHash": "[0xHASH32]",
            "nonce": "0x0102030405060708",
            "number": "0",
            "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "receiptTrie": "[0xHASH32]",
            "stateRoot": "[0xHASH32]",
            "timestamp": "[HEX]",
            "transactionsTrie": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
            "uncleHash": "0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347"
        },
        "pre": {
            "a94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": "[HEX]",
                "nonce": "0",
                "code": "",
                "storage": {}
            },
            "095e7baea6a6c7c4c2dfeb977efac326af552d87": {
                "balance": "[HEX]",
                "nonce": "0",
                "code": "[CODE]",
                "storage": {}
            }
        },
        "blocks": [
            {
                "transactions": [
                    {
                        "data": "[CODE]",
                        "gasLimit": "[HEX]",
                        "gasPrice": "[V]",
                        "nonce": "0",
                        "secretKey": "0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
                        "to": "0x095e7baea6a6c7c4c2dfeb977efac326af552d87",
                        "value": "[V]"
                    }
                ],
                "uncleHeaders": [
                ]
            }
        ]
    }
}
