import random
import binascii


class WeightedRandomizer(object):
    # https://stackoverflow.com/a/14993631/1729555
    def __init__(self, weights):
        self.__max = .0
        self.__weights = []
        for value, weight in weights.items():
            if weight == 0:
                # skip disabled items
                continue
            self.__max += weight
            self.__weights.append((self.__max, value))

    def random(self):
        if len(self.__weights) == 1:
            return self.__weights[0][1]  # shortcut: return value

        r = random.random() * self.__max
        for ceil, value in self.__weights:
            if ceil > r:
                return value


def toCompactHex(int):
    raise NotImplementedError

def fromHex(b):
    raise NotImplementedError

def hex2(n):
    # https://stackoverflow.com/questions/4368676/is-there-a-way-to-pad-to-an-even-number-of-digits
    x = '%x' % (n,)
    return "0x" + ('0' * (len(x) % 2)) + x

def int2bytes(i):
    hex_string = '%x' % i
    n = len(hex_string)
    return binascii.unhexlify(hex_string.zfill(n + (n & 1)))

# maybe: numpy.random.randint
# mersenne twister
class _RndBase(object):
    """
    Baseclass that provides interfaces to biased random impelmentations
    """

    QUOTE = "'"

    def __init__(self, seed=None, _config=None):
        self.seed = seed
        self._config = _config

    def __str__(self):
        # for json serialization
        return "%s" % self.generate()

    def __repr__(self):
        # for pprint serialization
        return "%s%s%s" % (_RndBase.QUOTE, self.__str__(), _RndBase.QUOTE)

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
        return self.randomUniInt(1, 32)
        return 1 ##randOpLengGen() ##<1..32 byte string

    def randomSmallMemoryLength(self):
        return self.randomUniInt(0, 1024)
        return 1 ## randomOpSmallMemrGen  ## opSmallMemrDist 0..1kb

    def randomMemoryLength(self):
        return self.randomUniInt(0, 10485760)
        return 1 ## randOpMemrGen  ## opMemrDist <1..10MB byte string

    def randomOpcode(self):
        return self.randomUniInt(0, 255)
        return 1 ## randOpCodeGen ## opCodeDist ## < 0..255 opcodes

    def randomWeightedOpcode(self):
        return self.randomUniInt()
        return 1 ## ..

