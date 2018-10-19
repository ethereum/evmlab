import unittest
from evmlab.genesis import Genesis


ADDRESS = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
# Greeter
CODE = "0xFFFFFFFFFFFFFFFFFFF"

class GenesisTest(unittest.TestCase):
    def test_uneven_storage(self):
        g = Genesis()
        
        storage = {
            "0x00": "0x692a",
            "0x1": "0x4",
        }
        g.addPrestateAccount({'code': CODE, 'balance': "0x00", "nonce":"0x01",
            "address":ADDRESS, "storage": storage})

        correct_storage = {
                '0x0000000000000000000000000000000000000000000000000000000000000000':
                '0x000000000000000000000000000000000000000000000000000000000000692a',
                '0x0000000000000000000000000000000000000000000000000000000000000001':
                '0x0000000000000000000000000000000000000000000000000000000000000004',
        }
        self.assertDictEqual(g.alloc[ADDRESS.lower()]["storage"], correct_storage)
