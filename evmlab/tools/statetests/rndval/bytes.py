
from .base import _RndBase
import binascii

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
                         binascii.hexlify(self.as_bytes()).decode("utf-8"))

    def as_bytes(self):
        return self.randomByteSequence(self.length)

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

