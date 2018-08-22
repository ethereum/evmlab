from .base import _RndBase, toCompactHex, fromHex

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
