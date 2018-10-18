import enum
import random
from .bytes import RndByteSequence
from evmlab import decode_hex


class RndAddressType(enum.Enum):
    """
    BitFlag Type Enum
    """
    RANDOM = 1
    PRECOMPILED = 2
    BYZANTIUM_PRECOMPILED = 3
    STATE_ACCOUNT = 4
    SENDING_ACCOUNT = 5

    SPECIAL_ALL = 101
    SPECIAL_CREATE = 102


class RndAddress(RndByteSequence):
    """
    "[ADDRESS]",			//Random account address
    """
    placeholder = "[ADDRESS]"

    # some static addresses from: https://github.com/ethereum/testeth/blob/ee0c6776c01b09045a379220c7e490000dae9377/test/tools/fuzzTesting/fuzzHelper.cpp
    addresses = {RndAddressType.SENDING_ACCOUNT: ["a94f5374fce5edbc8e2a8697c15331677e6ebf0b"],  # dup
                 RndAddressType.STATE_ACCOUNT: ["ffffffffffffffffffffffffffffffffffffffff",
                                                "1000000000000000000000000000000000000000",
                                                #"a94f5374fce5edbc8e2a8697c15331677e6ebf0b", # dup sending account
                                                "b94f5374fce5edbc8e2a8697c15331677e6ebf0b",
                                                "c94f5374fce5edbc8e2a8697c15331677e6ebf0b",
                                                "d94f5374fce5edbc8e2a8697c15331677e6ebf0b",],
                 RndAddressType.PRECOMPILED: ["0000000000000000000000000000000000000001",
                                              "0000000000000000000000000000000000000002",
                                              "0000000000000000000000000000000000000003",
                                              "0000000000000000000000000000000000000004",
                                              "0000000000000000000000000000000000000005",
                                              "0000000000000000000000000000000000000006",
                                              "0000000000000000000000000000000000000007",
                                              "0000000000000000000000000000000000000008",],
                 RndAddressType.BYZANTIUM_PRECOMPILED: ["0000000000000000000000000000000000000005",
                                                        "0000000000000000000000000000000000000006",
                                                        "0000000000000000000000000000000000000007",
                                                        "0000000000000000000000000000000000000008"],
                 RndAddressType.SPECIAL_CREATE: ["0000000000000000000000000000000000000000"]}

    def __init__(self, seed=None, length=20, prefix="0x", _types=[RndAddressType.RANDOM]):
        super().__init__(seed=seed, length=length, prefix=prefix)
        self.types = _types

    def _get_rnd_address_from_list(self, addrlist):
        if addrlist is None:
            raise KeyError("AddressType.%s does not exist!" % self.types)
        elif not addrlist:
            raise KeyError("AddressType.%s is empty!" % self.types)

        hex_addr = random.choice(addrlist)
        if hex_addr.startswith("0x"):
            hex_addr = hex_addr[2:]  # skip 0x. will be generically added by prefix
        return "%s%s" % (self.prefix, hex_addr)

    def generate(self):
        # taken from: https://github.com/ethereum/testeth/blob/ee0c6776c01b09045a379220c7e490000dae9377/test/tools/fuzzTesting/fuzzHelper.cpp#L427
        probabilities = {"precompiledDestProbability": 2,
                         "byzPrecompiledAddressProbability": 10,
                         "emptyAddressProbability": 15,
                         "randomAddressProbability": 3,
                         "sendingAddressProbability": 3,
                         }
        if len(self.types)==1:
            # only one given, return random
            _type = self.types.pop()
            if _type == RndAddressType.RANDOM:
                return super().generate()  # generate 20byte default random

            if not _type.name.startswith("SPECIAL"):
                # pick from list
                return self._get_rnd_address_from_list(self.addresses.get(_type))
            # otherwise fallthrough to multilist selection
        # todo: add probabilities
        types_set = set(self.types)
        if types_set.issubset([RndAddressType.PRECOMPILED, RndAddressType.STATE_ACCOUNT,
                               RndAddressType.SPECIAL_ALL, RndAddressType.SPECIAL_CREATE]):
            # precompiled or state or create OR all
            if self.randomPercent()<probabilities["precompiledDestProbability"]:
                if self.randomPercent()<probabilities["byzPrecompiledAddressProbability"]:
                    return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.BYZANTIUM_PRECOMPILED))
                return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.PRECOMPILED))

# CREATE is disabled for now -- the logic below could fill the template with to: "0x", which is not correct. The correct
# transaction would either have to: None, or no to-field present. 
            # CREATE  (if all or create is set)
            #if types_set != set([RndAddressType.PRECOMPILED, RndAddressType.STATE_ACCOUNT]):
#            if types_set.intersection([RndAddressType.SPECIAL_ALL, RndAddressType.SPECIAL_CREATE]):
#                if self.randomPercent()<probabilities["emptyAddressProbability"]:
#                    return ""

            # RANDOM
            if self.randomPercent()<probabilities["randomAddressProbability"]:
                a = super().generate()  # generate 20byte default random
                return a

            # RETURN SENDERS address
            if self.randomPercent() < probabilities["sendingAddressProbability"]:
                return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.SENDING_ACCOUNT))

            # FALLBACK - state account
            a  = self._get_rnd_address_from_list(self.addresses.get(RndAddressType.STATE_ACCOUNT))
            return a
        # RANDOM
        return super().generate()  # generate 20byte default random

    def as_bytes(self):
        data = self.generate()
        if data is not None:
            if data.startswith("0x"):
                data = data[2:]
            return decode_hex(data)
       

class RndDestAddress(RndAddress):

    placeholder = "[DESTADDRESS]"

    def __init__(self, seed=None, length=20, prefix="0x", _types=[RndAddressType.PRECOMPILED,
                                                                  RndAddressType.STATE_ACCOUNT]):
        super().__init__(seed=seed, length=length, prefix=prefix)
        self.types = _types

class RndDestAddressOrZero(RndAddress):

    placeholder = "[DESTADDRESS]"

    def __init__(self, seed=None, length=20, prefix="0x", _types=[RndAddressType.PRECOMPILED,
                                                                  RndAddressType.STATE_ACCOUNT,
                                                                  RndAddressType.SPECIAL_CREATE]):
        super().__init__(seed=seed, length=length, prefix=prefix)
        self.types = _types
