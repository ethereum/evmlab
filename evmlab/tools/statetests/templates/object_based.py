#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
from evmlab.tools.statetests import rndval

rnd_nonce = str(rndval.RndV())

# https://github.com/ethereum/testeth/blob/develop/test/tools/fuzzTesting/createRandomTest.cpp#L241
TEMPLATE_RandomStateTest = {
    "randomStatetest": {
        "_fuzz": {
            "compressed_random_state": rndval.RandomSeed(),
        },
        "env": {
            "currentCoinbase": rndval.RndAddress(),
            "currentDifficulty": "0x20000",
            "currentGasLimit": rndval.RndBlockGasLimit(),
            "currentNumber": "1",
            "currentTimestamp": "1000",
            "previousHash": rndval.RndHash32()
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
        "post": {"Byzantium" : [{ "logs" : "1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347"}]},  # dummy to make statetests happy
        "pre": {
            "ffffffffffffffffffffffffffffffffffffffff": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "1000000000000000000000000000000000000000": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "b94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "c94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "d94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "a94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": rndval.RndHexInt(),
                "code": "0x",
                "nonce": "0",
                "storage": {
                }
            }
        },
        "transaction": {
            "data": [
                rndval.RndCode()
            ],
            "gasLimit": [
                rndval.RndTransactionGasLimit(),
                "3000000"
            ],
            "gasPrice": rndval.RndGasPrice(),
            "nonce": rnd_nonce,
            "secretKey": "0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
            "to": rndval.RndDestAddress(),
            "value": [
                rndval.RndHex32(),
                "0"
            ]
        }
    }
}

OLD_TEMPLATE_RandomStateTest = {
    "randomStatetest": {
        "_fuzz": {
            "compressed_random_state": rndval.RandomSeed(),
        },
        "_info": {
            "comment": "",
            "filledwith": "cpp-1.3.0+commit.8fb57c56.Linux.g++",
            "lllcversion": "Version: 0.4.20-develop.2018.1.8+commit.2548228b.Linux.g++",
            "source": "src/GeneralStateTestsFiller/stRandom2/randomStatetest386Filler.json",
            "sourceHash": "c9d4a1fbb5f614cb885897bc4714a4a553e13fa28ef952d975378780b591072c"
        },
        "env": {
            "currentCoinbase": rndval.RndAddress(),
            "currentDifficulty": "0x20000",
            "currentGasLimit": rndval.RndBlockGasLimit(),
            "currentNumber": "0x01",
            "currentTimestamp": "0x03e8",
            "previousHash": rndval.RndHash32(),
        },
        "post": {
            "Byzantium": [
                {
                    "hash": "0x00000000000000000000000000000000000000000000000000000000deadc0de",
                    "indexes": {
                        "data": 0,
                        "gas": 0,
                        "value": 0
                    },
                    "logs": "0x00000000000000000000000000000000000000000000000000000000deadc0de"
                }
            ]
        },
        "pre": {
            "0x095e7baea6a6c7c4c2dfeb977efac326af552d87": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "0x945304eb96065b2a98b57a48a06ae28d285a71b5": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            },
            "0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": {
                "balance": rndval.RndHexInt(),
                "code": rndval.RndCode(),
                "nonce": rnd_nonce,
                "storage": {
                }
            }
        },
        "transaction": {
            "data": [
                "0x7f00000000000000000000000000000000000000000000000000000000000000007f00000000000000000000000000000000000000000000000000000000000000007f000000000000000000000000ffffffffffffffffffffffffffffffffffffffff7f00000000000000000000000000000000000000000000000000000000000000007fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff047f000000000000000000000000000000000000000000000000000000000000000105133641010b8111"
            ],
            "gasLimit": [
                rndval.RndTransactionGasLimit(),
            ],
            "gasPrice": rndval.RndGasPrice(),
            "nonce": rnd_nonce,
            "secretKey": "0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
            "to": rndval.RndDestAddress(),
            "value": [
                rndval.RndHex32(),
            ]
        }
    }
}
