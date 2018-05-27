import rlp
from eth_hash.auto import keccak
import binascii

def sha3(seed):
    return keccak(to_string(seed))

def encode_hex(b):
    if isinstance(b, str):
        b = bytes(b, 'utf-8')
    if isinstance(b, (bytes, bytearray)):
        return str(binascii.hexlify(b), 'utf-8')
    raise TypeError('Value must be an instance of str or bytes')

def to_string(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return bytes(value, 'utf-8')
    if isinstance(value, int):
        return bytes(str(value), 'utf-8')

def bytearray_to_bytestr(value):
    return bytes(value)

def decode_hex(s):
    if isinstance(s, str):
        return bytes.fromhex(s)
    if isinstance(s, (bytes, bytearray)):
        return binascii.unhexlify(s)
    raise TypeError('Value must be an instance of str or bytes')

def is_numeric(x): return isinstance(x, int)

def remove_0x_head(s):
    return s[2:] if s[:2] in (b'0x', '0x') else s

def big_endian_to_int(value):
    return int.from_bytes(value, byteorder='big')

def parse_int_or_hex(s):
    if is_numeric(s):
        return s
    elif s[:2] in (b'0x', '0x'):
        s = to_string(s)
        tail = (b'0' if len(s) % 2 else b'') + s[2:]
        return big_endian_to_int(decode_hex(tail))
    else:
        return int(s)

def normalize_address(x, allow_blank=False):
    if is_numeric(x):
        return int_to_addr(x)
    if allow_blank and x in {'', b''}:
        return b''
    if len(x) in (42, 50) and x[:2] in {'0x', b'0x'}:
        x = x[2:]
    if len(x) in (40, 48):
        x = decode_hex(x)
    if len(x) == 24:
        assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
        x = x[:20]
    if len(x) != 20:
        raise Exception("Invalid address format: %r" % x)
    return x

def mk_contract_address(sender, nonce):
    return sha3(rlp.encode([normalize_address(sender), nonce]))[12:]
