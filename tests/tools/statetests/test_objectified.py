#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>

import unittest
import json
from evmlab.tools.statetests import rndval
import evmlab.tools.statetests.templates


class EthFillerObjectifiedTest(unittest.TestCase):

    def setUp(self):
        rndval.RandomSeed.set_state(None)  # generate new seed
        self.template = evmlab.tools.statetests.templates.new(evmlab.tools.statetests.templates.object_based.TEMPLATE_RandomStateTest)

    def test_pprint(self):
        import pprint
        pprint_str = pprint.pformat(self.template, indent=4)
        self.assertIn(list(self.template.keys())[0], pprint_str)
        print(pprint_str)

    def test_json_dumps_with_default(self):
        print(json.dumps(self.template, default=str))

    def test_json_dumps_with_encoder_class(self):
        import evmlab.tools.statetests.randomtest
        print(json.dumps(self.template, cls=evmlab.tools.statetests.randomtest.RandomTestsJsonEncoder))

