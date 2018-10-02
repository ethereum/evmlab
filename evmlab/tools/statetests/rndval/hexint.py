from .base import _RndBase, hex2


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
        return hex2(self.randomUniInt(self.min, self.max))


class RndHex32(RndHexInt):
    """
    Random hex value string 0x...  max value uint32
    """
    placeholder = "[HEX32]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 0, _max=_max or 2 ** 32 - 1)


class RndBlockGasLimit(RndHexInt):
    """
    Random block gas limit with max of 2**55-1
    """
    placeholder = "[BLOCKGASLIMIT]"

    def __init__(self, seed=None, _min=None, _max=None):
        super().__init__(seed=seed, _min=_min or 2**50, _max=_max or 2 ** 64 - 1)


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

