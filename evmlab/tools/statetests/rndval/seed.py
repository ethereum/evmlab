import random, pickle, zlib, base64
from .base import _RndBase

class RandomSeed(_RndBase):

    SEED = None

    def generate(self):
        return RandomSeed.SEED

    @staticmethod
    def set_state(state=None):
        if state is None:
            state = RandomSeed.get_compressed_random_state()
            RandomSeed.SEED = state
        else:
            RandomSeed.set_compressed_random_state(state)
            RandomSeed.SEED = state

    @staticmethod
    def get_compressed_random_state():
        return base64.b64encode(zlib.compress(pickle.dumps(random.getstate()), 9)).decode("utf-8")

    @staticmethod
    def set_compressed_random_state(state):
        random.setstate(pickle.loads(zlib.decompress(base64.b64decode(state))))
