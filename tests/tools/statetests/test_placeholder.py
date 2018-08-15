#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>

import unittest
from pprint import pprint

import evmlab.tools.statetests.templates as templates
import evmlab.tools.statetests.randomtest as randomtest


class EthSubstituationTransactionTemplateTest(unittest.TestCase):

    def setUp(self):
        self.num_samples = 100

    def _test_template(self, template):
        new_template = templates.new(template)

        pprint(new_template)
        randomtest.process_template(new_template)
        pprint(new_template)

        for _ in range(self.num_samples):
            # randomizes everytime its printed
            self.assertNotIn(str(new_template), "'[")
            self.assertNotIn(str(new_template), "]'")

        pprint(template)

    def test_substitute_transaction_template(self):
        self._test_template(templates.text_based.TEMPLATE_TransactionTest)

    def test_substitute_blockchain_template(self):
        self._test_template(templates.text_based.TEMPLATE_BlockchainTest)

    def test_substitute_rlp_template(self):
        self._test_template(templates.text_based.TEMPLATE_RLPTest)

    def test_substitute_state_template(self):
        self._test_template(templates.text_based.TEMPLATE_STATETest)

    def test_substitute_vmtest_template(self):
        self._test_template(templates.text_based.TEMPLATE_VMTest)
