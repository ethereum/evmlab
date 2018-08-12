#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>

#
#
# https://github.com/ethereum/testeth/blob/ee0c6776c01b09045a379220c7e490000dae9377/test/tools/fuzzTesting/createRandomTest.cpp
#
import random
import binascii
import enum

def toCompactHex(int):
    raise NotImplementedError

def fromHex(b):
    raise NotImplementedError

# maybe: numpy.random.randint
# mersenne twister
class _RndBase(object):
    """
    Baseclass that provides interfaces to biased random impelmentations
    """
    def __init__(self, seed=None):
        if seed:
            random.seed(seed)

    def __str__(self):
        return "'%s'" % (self.generate())

    def __repr__(self):
        return self.__str__()

    def generate(self):
        raise NotImplementedError()

    def randomUniInt(self, min=None, max=None):
        min = min or 0
        max = max or 2**64-1
        assert(min <= max)
        # numpy.random.randint
        return min + random.randint(min, max) % (max-min)  # uniIntDist 0..0x7fffffff

    def randomByteSequence(self, length):
        return bytearray(random.getrandbits(8) for _ in range(length))

    def randomPercent(self):
        return self.randomUniInt(0,100)  ## percentDist 0..100 percent

    def randomSmallUniInt(self):
        return self.randomUniInt() ## opMemrDist(gen)  <1..10MB byte string

    def randomLength32(self):
        return 1 ##randOpLengGen() ##<1..32 byte string

    def randomSmallMemoryLength(self):
        return 1 ## randomOpSmallMemrGen  ## opSmallMemrDist 0..1kb

    def randomMemoryLength(self):
        return 1 ## randOpMemrGen  ## opMemrDist <1..10MB byte string

    def randomOpcode(self):
        return 1 ## randOpCodeGen ## opCodeDist ## < 0..255 opcodes

    def randomWeightedOpcode(self):
        return 1 ## ..


class RndRlp(_RndBase):
    """
    Random RLP String
    """
    placeholder = "[RLP]"

    def generate(self, depth=2):
        """
        :return:
        """
        assert(1 <= depth <= 7)
        return 1

    def recursive_rlp(self, depth):
        result = ''
        header = ''

        if depth > 1:

            # create RLP blocks
            size = 1 + self.randomSmallUniInt() % 4
            res_block = []
            for i in range(size):
                res_block.append(self.recursive_rlp(depth=depth-1))

            result += ''.join(res_block)

            # make RLP header
            length = len(result) / 2

            if self.randomPercent() < 10:

                # make header as array
                if length <= 55:
                    header = toCompactHex(128 + length)
                    rtype = 1
                else:
                    hexlength = toCompactHex(length)
                    header = toCompactHex(183 + len(hexlength) / 2) + hexlength # todo fixit
                    rtype = 2

            else:

                # make header as list
                if length <= 55:
                    header = toCompactHex(192+length)
                    rtype = 3
                else:
                    hexlength = toCompactHex(length,1)
                    header = toCompactHex(247 + len(hexlength)/2) + hexlength
                    rtype = 4

            return header + result


        if depth == 1:
            generate_valid_rlp = False if self.randomPercent() < 80 else True

            genbug_1 = True if not generate_valid_rlp and self.randomPercent() < 50 else False
            genbug_2 = True if not generate_valid_rlp and self.randomPercent() < 50 else False

            emptyZeros = emptyZeros2 = ""
            if not generate_valid_rlp:
                emptyZeros = "00" if genbug_1 else ""
                emptyZeros2 = "00" if genbug_2 else ""

            rnd = self.randomSmallUniInt() % 5

            if rnd == 0:
                # // single byte [0x00, 0x7f]
                rlp = emptyZeros + toCompactHex(self.randomSmallUniInt()%255 if genbug_1 else self.randomSmallUniInt() % 128, 1)
                return rlp + result

            elif rnd == 1:
                # string 0-55 [0x80, 0xb7] + string
                length = self.randomSmallUniInt() % 255 if genbug_1 else self.randomSmallUniInt() % 55
                _hex = self.randomByteSequence(length)
                if length == 1:
                    if generate_valid_rlp and fromHex(hex)[0] < 128:
                        _hex = toCompactHex(128)
                return toCompactHex(128+length) + emptyZeros + _hex

            elif rnd == 2:
                # string more 55 [0xb8, 0xbf] + length + string
                length = self.randomPercent()
                if length < 56 and generate_valid_rlp:
                    length = 56

                _hex = self.randomByteSequence(length)
                hexlen = emptyZeros2 + toCompactHex(length, 1)
                rlpblock = toCompactHex(183 + len(hexlen) / 2) + hexlen + emptyZeros + hex;
                return rlpblock + result

            elif rnd == 3:
                # list 0-55 [0xc0, 0xf7] + data
                length = self.randomSmallUniInt() % 255 if genbug_1 else self.randomSmallUniInt() % 55
                _hex = emptyZeros + self.randomByteSequence(length)
                return toCompactHex(192 + length) + _hex

            elif rnd == 4:
                # list more 55 [0xf8, 0xff] + length + data

                length = self.randomPercent()
                if generate_valid_rlp and length < 56:
                    length = 56

                hexlen = emptyZeros2 + toCompactHex(length, 1)
                rlpblock = toCompactHex(247 + len(hexlen)/2) + hexlen + emptyZeros + self.randomByteSequence(length)
                return rlpblock + result


class RndCode(_RndBase):
    """
    Random bytecode (could be empty string)
    """
    placeholder = "[CODE]"

    def generate(self, length=50):
        raise NotImplementedError


class RndHexInt(_RndBase):
    """
    Random hex value string 0x...  max value uint64
    """
    placeholder = "[HEX]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed)
        self.min = _min or 0
        self.max = _max or 2**64-1  # max int 64

    def generate(self):
        return hex(self.randomUniInt(self.min, self.max))


class RndHex32(RndHexInt):
    """
    Random hex value string 0x...  max value uint32
    """
    placeholder = "[HEX32]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 0, _max=_max or 2 ** 32 - 1)


class RndByteSequence(_RndBase):
    """
    Random byte sequence
    """
    placeholder = "[BYTES]"

    def __init__(self, seed=None, length=None, prefix=""):
        super().__init__(seed=seed)
        assert(length > 0)
        self.length = length
        self.prefix = prefix

    def generate(self):
        return "%s%s" % (self.prefix,
                         binascii.hexlify(self.randomByteSequence(self.length)).decode("utf-8"))


class RndHash20(RndByteSequence):
    """
    Random hash 20 byte length
    """
    placeholder = "[HASH20]"

    def __init__(self, seed=None, length=20, prefix=""):
        super().__init__(seed=seed, length=length, prefix=prefix)


class RndHash32(RndByteSequence):
    """
    Random hash 32 byte length
    """
    placeholder = "[HASH32]"

    def __init__(self, seed=None, length=32, prefix=""):
        super().__init__(seed=seed, length=length, prefix=prefix)


class Rnd0xHash32(RndByteSequence):
    """
    Random hash string 0x...  32 byte length
    """
    placeholder = "[0xHASH32]"

    def __init__(self, seed=None, length=32, prefix="0x"):
        super().__init__(seed=seed, length=length, prefix=prefix)


class RndV(_RndBase):
    """
    "[V]",					//Random V value for transaction sig. could be invalid.
    """
    placeholder = "[V]"

    def generate(self):
        chance = self.randomPercent()
        if chance < 30:  # todo: false assumption that this is a probability. rework code for that
            return "0x1c"
        elif chance < 60:
            return "0x1d"
        else:
            return "0x%s" % binascii.hexlify(self.randomByteSequence(1)).decode("utf-8")


class RndBlockGasLimit(RndHexInt):
    """
    Random block gas limit with max of 2**55-1
    """
    placeholder = "[BLOCKGASLIMIT]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 100000, _max=_max or 2 ** 55 - 1)


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
    addresses = {RndAddressType.SENDING_ACCOUNT: ["a94f5374fce5edbc8e2a8697c15331677e6ebf0b"],
                 RndAddressType.STATE_ACCOUNT: ["ffffffffffffffffffffffffffffffffffffffff",
                                                "1000000000000000000000000000000000000000",
                                                "b94f5374fce5edbc8e2a8697c15331677e6ebf0b",
                                                "c94f5374fce5edbc8e2a8697c15331677e6ebf0b",
                                                "d94f5374fce5edbc8e2a8697c15331677e6ebf0b"],
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
        probabilities = {"precompiledDestProbability":30,
                         "byzPrecompiledAddressProbability":30,
                         "emptyAddressProbability":30,
                         "randomAddressProbability":5,
                         "sendingAddressProbability":5,
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

        # multiple (OR) linked
        # get all lists
        addrlist = {t:self.addresses.get(t) for t in self.types}

        # todo: add probabilities
        if any(t in self.types for t in (RndAddressType.PRECOMPILED, RndAddressType.STATE_ACCOUNT,
                                         RndAddressType.SPECIAL_ALL, RndAddressType.SPECIAL_CREATE)):
            # precompiled or state or create OR all
            if self.randomPercent()<probabilities["precompiledDestProbability"]:
                if self.randomPercent()<probabilities["byzPrecompiledAddressProbability"]:
                    return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.BYZANTIUM_PRECOMPILED))
                return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.PRECOMPILED))

            # CREATE
            if all(t not in self.types for t in (RndAddressType.PRECOMPILED, RndAddressType.STATE_ACCOUNT)):
                if self.randomPercent()<probabilities["emptyAddressProbability"]:
                    return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.SPECIAL_CREATE))

            # RANDOM
            if self.randomPercent()<probabilities["randomAddressProbability"]:
                return super().generate()  # generate 20byte default random

            # RETURN SENDERS address
            if self.randomPercent() < probabilities["sendingAddressProbability"]:
                return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.SENDING_ACCOUNT))

            # FALLBACK - state account
            return self._get_rnd_address_from_list(self.addresses.get(RndAddressType.STATE_ACCOUNT))

        # RANDOM
        return super().generate()  # generate 20byte default random


class RndTransactionGasLimit(RndHexInt):
    """
    "[TRANSACTIONGASLIMIT]", //Random reasonable gas limit for a transaction
    """
    placeholder = "[TRANSACTIONGASLIMIT]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 25000, _max=_max or 10000000)


class RndGasPrice(RndHexInt):
    """
    "[GASPRICE]"			//Random reasonable gas price for transaction (could be 0)
    """
    placeholder = "[GASPRICE]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 0, _max=_max or 10)



