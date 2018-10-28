#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
from evmlab.tools.statetests import rndval
from types import SimpleNamespace
from evmlab.tools.statetests.rndval.base import WeightedRandomizer
import random
import binascii


class Account(object):

    def __init__(self, address, balance=None, code=None, nonce=None, storage=None):
        self.address = address
        self.balance = balance if balance is not None else rndval.RndHexInt(_min=2**24-1)
        self.code = code if code is not None else ''
        self.nonce = nonce
        self.storage = storage if storage is not None else {}

    @property
    def __dict__(self):
        return {"balance": self.balance,
                "code": self.code,
                "nonce": self.nonce,
                "storage": self.storage}


class StateTest(object):

    def __init__(self, nonce=None, codegenerators={}, codegenerators_weights={}, datalength=None, fill_prestate_for_tx_to=True, fill_prestate_for_args=False):
        ### global settings
        self._nonce = nonce if nonce is not None else str(rndval.RndV())
        self._codegenerators = codegenerators  # available code generators
        self._codegenerators_weighted = WeightedRandomizer({obj:codegenerators_weights[name] for name,obj in codegenerators.items()})
        self._datalength = datalength
        self._fill_prestate_for_tx_to = fill_prestate_for_tx_to
        self._fill_prestate_for_args = fill_prestate_for_args

        ### info
        self._info = SimpleNamespace(fuzzer="evmlab",
                                     comment="evmlab",
                                     filledwith="evmlab randomfuzz")

        ### env
        self._env = SimpleNamespace(currentCoinbase=rndval.RndAddress(),
                                    currentDifficulty="0x20000",
                                    currentGasLimit="0x1312D00",
                                    currentNumber="1",
                                    currentTimestamp="1000",
                                    previousHash=rndval.RndHash32())

        ### post
        self._post = {"Byzantium": [
                            {  # dummy to make statetests happy
                                "hash": "0x00000000000000000000000000000000000000000000000000000000deadc0de",
                                "logs": "0x00000000000000000000000000000000000000000000000000000000deadbeef",
                                "indexes": {"data": 0, "gas": 0, "value": 0}
                            }]
                     }

        ### pre
        self._pre = {}

        ### transaction
        self._transaction = SimpleNamespace(secretKey="0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
                                            data=[self.pick_codegen("bytes").generate(length=self._datalength)],
                                            gasLimit=[rndval.RndTransactionGasLimit(_min=34 * 14000)],
                                            gasPrice= rndval.RndGasPrice(),
                                            nonce=self._nonce,
                                            to=rndval.RndDestAddressOrZero(),
                                            value=[rndval.RndHexInt(_min=0, _max=max(0, 2**24))])

    def _random_storage(self, _min=0, _max=10):
        hx = rndval.RndHex32()
        rnd_vals = (hx.generate() for _ in range(random.randint(_min, _max)))
        return {hx:hx for hx in rnd_vals}


    def _autofill_prestates_from_transaction(self, tx):
        if tx.to in self.pre:
            # already there
            return self

        self._autofill_prestate(tx.to)

        return self

    def _autofill_prestate(self, address):
        if address in self.pre:
            # already there
            return self

        if address.replace("0x","") not in rndval.RndAddress.addresses[rndval.RndAddressType.SENDING_ACCOUNT]+rndval.RndAddress.addresses[rndval.RndAddressType.STATE_ACCOUNT]:
            # skip non state accounts
            return self
        # not a precompiled address?
        # add a random prestate for the address we interact with in the tx
        ### random code
        ### same nonce
        ### random balance
        ### random storage

        self.add_prestate(address="0x%s"%address.replace("0x",""),
                          code=self.pick_codegen().generate(length=random.randint(0,500)),  # limit length, main code is in first prestate
                          storage=self._random_storage(_min=0, _max=2))

        return self

    def _autofill_prestates_from_stack_arguments(self):
        # todo: hacky hack
        try:
            for addr in self.pick_codegen("smart")._addresses_seen:
                self._autofill_prestate(addr)
        except AttributeError as ae:
            pass  # addresses_seen is not available


    def _build(self):
        # clone the tx namespace and replace the generator with a concrete value (we can then refer to that value later)
        tx = SimpleNamespace(**self.transaction.__dict__)
        if isinstance(tx.to, rndval.RndAddress):
            tx.to = tx.to.generate()

        if self._fill_prestate_for_tx_to:
            self._autofill_prestates_from_transaction(tx)

        if self._fill_prestate_for_args:
            self._autofill_prestates_from_stack_arguments()

        return {"randomStatetest": {
                       "_info": self.info.__dict__,
                       "env": self.env.__dict__,
                       "post": self.post,
                       "pre": {address:a.__dict__ for address,a in self.pre.items()},
                       "transaction": tx.__dict__}}

    @property
    def info(self):
        return self._info

    @property
    def env(self):
        return self._env

    @property
    def post(self):
        return self._post

    @property
    def pre(self):
        return self._pre

    @pre.setter
    def pre(self, accounts):
        self._pre = accounts

    @property
    def transaction(self):
        return self._transaction

    @transaction.setter
    def transaction(self, transaction):
        self._transaction = transaction

    def add_prestate(self, address, balance=None, code=None, nonce=None, storage=None):
        acc = Account(address=address,
                      balance=balance,
                      code=code if code is not None else self.pick_codegen().generate(),
                      nonce=nonce if nonce is not None else self._nonce,  # use global nonce if not explicitly set
                      storage=storage)
        self.pre[acc.address] = acc

    def pick_codegen(self, name=None):
        if name:
            return self._codegenerators[name]
        return self._codegenerators_weighted.random()

    @property
    def __dict__(self):
        return self._build()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __iter__(self):
        yield self._build()


if __name__=="__main__":
    st = StateTest(nonce="0x1d",
                   codegenerators={"bytes":rndval.RndCodeBytes(),
                                   "instr":rndval.RndCodeInstr(),
                                   "smart":rndval.RndCode2()},
                   codegenerators_weights={"bytes":20,
                                           "instr":20,
                                           "smart":60},
                   fill_prestate_for_args=True,
                   fill_prestate_for_tx_to=True)
    st.info.fuzzer = "evmlab tin"

    #st.env.currentCoinbase = rndval.RndDestAddress()
    #st.env.previousHash = rndval.RndHash32()

    #st.add_prestate(address="ffffffffffffffffffffffffffffffffffffffff")
    #st.add_prestate(address="1000000000000000000000000000000000000000")
    #st.add_prestate(address="b94f5374fce5edbc8e2a8697c15331677e6ebf0b")
    #st.add_prestate(address="c94f5374fce5edbc8e2a8697c15331677e6ebf0b")
    #st.add_prestate(address="d94f5374fce5edbc8e2a8697c15331677e6ebf0b")
    #st.add_prestate(address="a94f5374fce5edbc8e2a8697c15331677e6ebf0b")

    import pprint

    pprint.pprint(st.__dict__)
    pprint.pprint(st.__dict__)







