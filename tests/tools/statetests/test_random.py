#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>

import unittest
import string
import collections

import evmlab.tools.statetests.rndval as rndval

def testit_times(rndcls, f_condition, times):
    for _ in range(times):
        f_condition(rndcls())


def is_all_hex(s):
    return all(c in string.hexdigits for c in s)


class EthFillerTest(unittest.TestCase):

    def setUp(self):
        self.num_samples = 100

    def test_markers_exist(self):
        marker_attrib_name = "placeholder"
        seen_placeholders = set()
        for clsname in (_ for  _ in dir(rndval) if _.startswith("Rnd") and not _.endswith("Type")):
            cls = getattr(rndval, clsname)
            # check for placeholder attrib
            if self.assertIn(marker_attrib_name, dir(cls)):
                # check that placeholder is set
                # check that placeholder is not dup
                self.assertIsInstance(cls.placeholder, str)
                self.assertNotIn(cls.placeholder, seen_placeholders)
                seen_placeholders.add(cls.placeholder)

    def test_rlp(self):
        raise NotImplementedError

    def test_codebytes(self):
        expect_prefix = "0x"
        r = rndval.RndCodeBytes()
        for _ in range(self.num_samples):
            txt_val = str(r)
            self.assertTrue(txt_val)
            self.assertTrue(len(txt_val) % 2 == 0)  # divsible by 2 (output is bytes)
            # with prefix
            self.assertEqual(expect_prefix, txt_val[:len(expect_prefix)])
            self.assertTrue(is_all_hex(txt_val[len(expect_prefix):]))

            self.assertGreaterEqual((len(txt_val) - len(expect_prefix)) // 2, rndval.RndCodeBytes.MIN_CONTRACT_SIZE)
            self.assertLessEqual((len(txt_val) - len(expect_prefix)) // 2, rndval.RndCodeBytes.MAX_CONTRACT_SIZE)

    def test_codeinstr(self):
        expect_prefix = "0x"
        r = rndval.RndCodeInstr()
        for _ in range(self.num_samples):
            txt_val = str(r)
            self.assertTrue(txt_val)
            self.assertTrue(len(txt_val) % 2 == 0)  # divsible by 2 (output is bytes)
            # with prefix
            self.assertEqual(expect_prefix, txt_val[:len(expect_prefix)])
            self.assertTrue(is_all_hex(txt_val[len(expect_prefix):]))

            #self.assertGreaterEqual((len(txt_val) - len(expect_prefix)) // 2, rndval.RndCodeInstr.MIN_CONTRACT_SIZE)
            self.assertGreaterEqual((len(txt_val) - len(expect_prefix)) // 2, rndval.RndCodeBytes.MAX_CONTRACT_SIZE) # must be greater equal as we insert argument push-codes

    def _test_hex_cls(self, cls=rndval.RndHexInt, _min=0, _max=2 ** 64 - 1):
        min_chars = len(rndval.hex2(_min))
        max_chars = len(rndval.hex2(_max))
        r = cls()
        for _ in range(self.num_samples):
            txt_val = str(r)  # generates new random value
            self.assertGreater(len(txt_val), 2)  # at least 0x<[0-9a-f]+...>
            self.assertEqual("0x", txt_val[:2])
            self.assertLessEqual(len(txt_val), max_chars)
            self.assertGreaterEqual(len(txt_val), min_chars)
            self.assertTrue(is_all_hex(txt_val[2:]))
            self.assertEqual(len(txt_val)%2, 0)
        return False

    def test_hex(self):
        self._test_hex_cls(cls=rndval.RndHexInt,
                           _max=2 ** 64 - 1)

    def test_hex32(self):
        self._test_hex_cls(cls=rndval.RndHex32,
                           _max=2 ** 32 - 1)

    def _test_byteseq_cls(self, cls=rndval.RndHash20, expect_prefix="", constructor_args=[], constructor_kwargs={}, expect_length=None):
        r = cls(*constructor_args, **constructor_kwargs)
        for _ in range(self.num_samples):
            txt_val = str(r)
            self.assertTrue(txt_val)
            self.assertTrue(len(txt_val) % 2 == 0)  # divsible by 2 (output is bytes)
            if expect_prefix is not None:
                # with prefix
                self.assertEqual(expect_prefix, txt_val[:len(expect_prefix)])
                self.assertTrue(is_all_hex(txt_val[len(expect_prefix):]))
            else:
                # no prefix
                self.assertNotIn(expect_prefix, txt_val)
                self.assertTrue(is_all_hex(txt_val))
            self.assertEqual((len(txt_val)-len(expect_prefix)) // 2, r.length)
            if expect_length:
                self.assertEqual((len(txt_val) - len(expect_prefix)) // 2, expect_length)

    def test_hash20(self):
        self._test_byteseq_cls(cls=rndval.RndHash20)

    def test_hash32(self):
        self._test_byteseq_cls(cls=rndval.RndHash32)

    def test_0xhash32(self):
        self._test_byteseq_cls(cls=rndval.Rnd0xHash32,
                               expect_prefix="0x")

    def test_v(self):
        r = rndval.RndV()
        # draw a max of 10 times the sample range to check probabilities
        sig_v = [str(r) for _ in range(self.num_samples * 10)]
        self.assertIn("0x1c", sig_v)
        self.assertIn("0x1d", sig_v)
        # calc probabilities
        total = len(sig_v)
        total_0x1c = sig_v.count("0x1c")/total
        total_0x1d = sig_v.count("0x1d")/total
        self.assertGreaterEqual(total_0x1c, 0.30-0.10)  # 10% error range - entropy
        self.assertGreaterEqual(total_0x1d, 0.30-0.10)  # 10% error range - entropy
        self.assertGreaterEqual(total-total_0x1d-total_0x1c, 0.40-0.10)  # 10% error range - entropy

    def test_blockgaslimit(self):
        self._test_hex_cls(cls=rndval.RndBlockGasLimit,
                           _min=100000, _max=36028797018963967)

    def test_destaddress(self):
        #PrecompiledOrStateOrCreate
        self._test_byteseq_cls(cls=rndval.RndDestAddress,
                               expect_prefix="0x",
                               constructor_kwargs={'_types':[rndval.RndAddressType.SPECIAL_ALL,],
                                                   'prefix':'0x'},
                               expect_length=20)
        self._test_byteseq_cls(cls=rndval.RndDestAddress,
                               expect_prefix="0x",
                               expect_length=20)

        # check probabilities
        # draw 1000 samples
        def addresstype_for_address(address):
            # addresses = {RndAddressType.SENDING_ACCOUNT: ["a94f5374fce5edbc8e2a8697c15331677e6ebf0b"],
            address = address.replace("0x","")
            for addrtype, samples in rndval.RndDestAddress.addresses.items():
                if address in samples:
                    return addrtype

            return None

        cls = rndval.RndDestAddress()
        counter = collections.Counter([addresstype_for_address(str(cls)) for _ in range(self.num_samples*100)])
        for k,v in counter.items():
            print("%-40r: %f%%"%(k,100*v/(self.num_samples*100)))


    def test_address(self):
        for addr_type in rndval.RndAddressType:
            self._test_byteseq_cls(cls=rndval.RndAddress,
                                   expect_prefix="",
                                   constructor_kwargs={'_types':[addr_type,],
                                                       'prefix':''},
                                   expect_length=20)

    def test_0xaddress(self):
        for addr_type in rndval.RndAddressType:
            self._test_byteseq_cls(cls=rndval.RndAddress,
                                   expect_prefix="0x",
                                   constructor_kwargs={'_types':[addr_type,],
                                                       'prefix':'0x'},
                                   expect_length=20)

    def test_transactiongaslimit(self):
        self._test_hex_cls(cls=rndval.RndTransactionGasLimit,
                           _min=25000, _max=10000000)

    def test_gasprice(self):
        self._test_hex_cls(cls=rndval.RndGasPrice,
                           _min=0, _max=10)
