import random
import binascii

from .base import _RndBase, WeightedRandomizer, int2bytes
from .code import _RndCodeBase
from .address import RndAddress, RndDestAddress, RndAddressType

from evmdasm.registry import registry as asm_registry

opcodes = {
    0x00: ['STOP', 0, 0, 0],
    0x01: ['ADD', 2, 1, 3],
    0x02: ['MUL', 2, 1, 5],
    0x03: ['SUB', 2, 1, 3],
    0x04: ['DIV', 2, 1, 5],
    0x05: ['SDIV', 2, 1, 5],
    0x06: ['MOD', 2, 1, 5],
    0x07: ['SMOD', 2, 1, 5],
    0x08: ['ADDMOD', 3, 1, 8],
    0x09: ['MULMOD', 3, 1, 8],
    0x0a: ['EXP', 2, 1, 10],
    0x0b: ['SIGNEXTEND', 2, 1, 5],
    0x10: ['LT', 2, 1, 3],
    0x11: ['GT', 2, 1, 3],
    0x12: ['SLT', 2, 1, 3],
    0x13: ['SGT', 2, 1, 3],
    0x14: ['EQ', 2, 1, 3],
    0x15: ['ISZERO', 1, 1, 3],
    0x16: ['AND', 2, 1, 3],
    0x17: ['OR', 2, 1, 3],
    0x18: ['XOR', 2, 1, 3],
    0x19: ['NOT', 1, 1, 3],
    0x1a: ['BYTE', 2, 1, 3],
    0x1b: ['SHL', 2, 1, 3],
    0x1c: ['SHR', 2, 1, 3],
    0x1d: ['SAR', 2, 1, 3],
    0x20: ['SHA3', 2, 1, 30],
    0x30: ['ADDRESS', 0, 1, 2],
    0x31: ['BALANCE', 1, 1, 20],
    0x32: ['ORIGIN', 0, 1, 2],
    0x33: ['CALLER', 0, 1, 2],
    0x34: ['CALLVALUE', 0, 1, 2],
    0x35: ['CALLDATALOAD', 1, 1, 3],
    0x36: ['CALLDATASIZE', 0, 1, 2],
    0x37: ['CALLDATACOPY', 3, 0, 3],
    0x38: ['CODESIZE', 0, 1, 2],
    0x39: ['CODECOPY', 3, 0, 3],
    0x3a: ['GASPRICE', 0, 1, 2],
    0x3b: ['EXTCODESIZE', 1, 1, 20],
    0x3c: ['EXTCODECOPY', 4, 0, 20],
    0x3d: ['RETURNDATASIZE', 0, 1, 2],
    0x3e: ['RETURNDATACOPY', 3, 0, 3],
    0x3f: ['EXTCODEHASH', 1, 1, 400],
    0x40: ['BLOCKHASH', 1, 1, 20],
    0x41: ['COINBASE', 0, 1, 2],
    0x42: ['TIMESTAMP', 0, 1, 2],
    0x43: ['NUMBER', 0, 1, 2],
    0x44: ['DIFFICULTY', 0, 1, 2],
    0x45: ['GASLIMIT', 0, 1, 2],
    0x50: ['POP', 1, 0, 2],
    0x51: ['MLOAD', 1, 1, 3],
    0x52: ['MSTORE', 2, 0, 3],
    0x53: ['MSTORE8', 2, 0, 3],
    0x54: ['SLOAD', 1, 1, 50],
    0x55: ['SSTORE', 2, 0, 0],
    0x56: ['JUMP', 1, 0, 8],
    0x57: ['JUMPI', 2, 0, 10],
    0x58: ['PC', 0, 1, 2],
    0x59: ['MSIZE', 0, 1, 2],
    0x5a: ['GAS', 0, 1, 2],
    0x5b: ['JUMPDEST', 0, 0, 1],
    0xa0: ['LOG0', 2, 0, 375],
    0xa1: ['LOG1', 3, 0, 750],
    0xa2: ['LOG2', 4, 0, 1125],
    0xa3: ['LOG3', 5, 0, 1500],
    0xa4: ['LOG4', 6, 0, 1875],
    0xf0: ['CREATE', 3, 1, 32000],
    0xf1: ['CALL', 7, 1, 40],
    0xf2: ['CALLCODE', 7, 1, 40],
    0xf3: ['RETURN', 2, 0, 0],
    0xf4: ['DELEGATECALL', 6, 0, 40],
    0xf5: ['CREATE2', 4, 1, 32000],
    0xfa: ['STATICCALL', 6, 1, 40],
    0xfd: ['REVERT', 2, 0, 0],
    0xff: ['SUICIDE', 1, 0, 0],
}
valid_opcodes = list(opcodes.keys())
const_opcodes = [0x1b, #: ['SHL', 2, 1, 3],
                    0x1c, #: ['SHR', 2, 1, 3],
                    0x1d, #: ['SAR', 2, 1, 3],
                    0xf4, #: ['DELEGATECALL', 6, 0, 40], use more delegatecalls
                    0x54, #: ['SLOAD', 1, 1, 50],
                    0x55, 0x55, 0x55, 0x55, 0x55, #: ['SSTORE', 2, 0, 0], use more SSTOREs to cover the Net SSTORE gas EIP
                    0xf5, #: ['CREATE2', 4, 1, 32000],
                    0x3f] #: ['EXTCODEHASH', 1, 1, 400],

constantinople_skewed_set = valid_opcodes + const_opcodes + const_opcodes  + const_opcodes 

from evmlab import decode_hex
def as_bytes(s):
    return decode_hex(s)

class RndCodeInstr(_RndCodeBase):
    """
    Random bytecode based on stat spread of instructions
    """
    placeholder = "[CODE]"

    # analyzed based on statedump.json
    LIKELYHOOD_BY_OPCODE_INT = {0: 0.002369013615135901, 1: 0.05201276925472314, 2: 0.010047411230279087, 3: 0.019639467049331536, 4: 0.009320354049986206, 5: 2.394690524947121e-05, 6: 0.000147323546363667, 7: 1.4113195109003945e-05, 8: 2.00316317676185e-06, 9: 4.6072753065522554e-05, 10: 0.013049606515015074, 11: 9.469498653783292e-05, 12: 1.0015815883809252e-05, 13: 1.0562133113835211e-05, 14: 6.28264814529853e-06, 15: 2.5494804067878094e-06, 16: 0.004698510283966591, 17: 0.0031919494692983375, 18: 9.332919346276802e-05, 19: 8.986918433927028e-05, 20: 0.011943951494314204, 21: 0.018605561691507407, 22: 0.02246256133549068, 23: 0.002151579357585569, 24: 1.0562133113835211e-05, 25: 0.0039370351181820746, 26: 3.4691144106648405e-05, 27: 4.55264358354966e-06, 28: 6.009489530285551e-06, 29: 6.191595273627537e-06, 30: 7.284229733679456e-07, 31: 4.55264358354966e-07, 32: 0.007498021876362948, 33: 2.1579530586025387e-05, 34: 5.007907941904626e-06, 35: 2.0851107612657443e-05, 36: 4.188432096865687e-06, 37: 1.4568459467358912e-06, 38: 2.6405332784588028e-06, 39: 3.642114866839728e-07, 40: 2.185268920103837e-06, 41: 7.011071118666476e-06, 42: 4.55264358354966e-07, 43: 3.824220610181715e-06, 44: 5.463172300259592e-07, 45: 5.190013685246612e-06, 46: 1.001581588380925e-06, 47: 3.277903380155755e-06, 48: 0.00040427475021920977, 49: 0.0002957397271873859, 50: 0.00012738296746771948, 51: 0.004011880578695631, 52: 0.0009803662692815837, 53: 0.006301587142606097, 54: 0.0015678393973028318, 55: 0.001392835777951183, 56: 1.0106868755480245e-05, 57: 0.000482124955497909, 58: 1.484161808237189e-05, 59: 2.185268920103837e-06, 60: 3.642114866839728e-06, 61: 3.5510619951687345e-06, 62: 1.001581588380925e-06, 63: 1.821057433419864e-07, 64: 6.319069293966928e-05, 65: 1.7300045617488708e-06, 66: 0.0005120813502776658, 67: 0.0007339771985398762, 68: 6.191595273627537e-06, 69: 1.1472661830545142e-05, 70: 1.0926344600519185e-06, 71: 1.4568459467358912e-06, 72: 4.55264358354966e-07, 73: 3.733167738510721e-06, 74: 3.186850508484762e-06, 75: 1.6389516900778775e-06, 76: 5.2810665569176056e-06, 77: 2.458427535116816e-06, 78: 5.463172300259592e-07, 79: 5.918436658614558e-06, 80: 0.07515485817149445, 81: 0.022783158496644248, 82: 0.0340294628882153, 83: 4.2248532455340845e-05, 84: 0.02040822644484973, 85: 0.007825721161506852, 86: 0.02073009834620669, 87: 0.02606270082849008, 88: 1.1836873317229116e-06, 89: 0.00049505446327519, 90: 0.002477548638167725, 91: 0.036403757569908116, 92: 1.4568459467358912e-06, 93: 4.55264358354966e-07, 94: 1.2747402033939047e-06, 95: 9.469498653783293e-06, 96: 0.17098117663983944, 97: 0.06338263239315173, 98: 0.0007466335477021442, 99: 0.010683961856131, 100: 4.916855070233633e-05, 101: 3.460009123497741e-05, 102: 4.643696455220653e-05, 103: 0.0007694878184915635, 104: 0.00026578333240762916, 105: 7.402598466851747e-05, 106: 2.458427535116816e-06, 107: 4.0882739380275944e-05, 108: 7.566493635859534e-05, 109: 8.650022808744353e-06, 110: 2.449322247949717e-05, 111: 0.00010516606677999714, 112: 4.698328178223249e-05, 113: 1.8483732949211617e-05, 114: 2.422006386448419e-05, 115: 0.008246749640113524, 116: 0.00023109218830098073, 117: 4.844012772896838e-05, 118: 4.0063263535237e-06, 119: 1.0197921627151238e-05, 120: 4.9441709317349306e-05, 121: 1.7846362847514667e-05, 122: 2.330953514777426e-05, 123: 4.188432096865687e-06, 124: 0.000601313164515239, 125: 1.1745820445558122e-05, 126: 7.375282605350449e-06, 127: 0.0027523462048707824, 128: 0.045281139399214944, 129: 0.053209841358581686, 130: 0.028744025793457487, 131: 0.01687601239411689, 132: 0.009120401943796704, 133: 0.004559290443181642, 134: 0.0025354582645504766, 135: 0.003690554994568696, 136: 0.0015595535859807715, 137: 0.0005049792262873283, 138: 0.0005750899374739931, 139: 0.00023855852377800216, 140: 0.00015979778978259305, 141: 0.00011026502759357276, 142: 6.528490898810212e-05, 143: 1.4022142237332952e-05, 144: 0.07030975276413755, 145: 0.028096548823005055, 146: 0.010750612558194166, 147: 0.004197355278289444, 148: 0.0023631862313489575, 149: 0.001350040928265816, 150: 0.0010319021946473658, 151: 0.0005945752520115856, 152: 0.00037677678297456984, 153: 0.00015424356461066248, 154: 0.00010798870580179793, 155: 3.35074567749255e-05, 156: 1.0653185985506204e-05, 157: 6.920018246995483e-06, 158: 8.467917065402367e-06, 159: 2.00316317676185e-06, 160: 1.7208992745817713e-05, 161: 0.0009144439901917847, 162: 0.00010771554718678495, 163: 0.0002369195720879243, 164: 3.714957164176522e-05, 165: 1.821057433419864e-06, 166: 6.920018246995483e-06, 167: 2.0942160484328436e-06, 168: 3.651220154006827e-05, 169: 1.4113195109003945e-05, 170: 4.097379225194694e-06, 171: 1.1836873317229116e-06, 172: 8.376864193731374e-06, 173: 5.2810665569176056e-06, 174: 9.651604397125279e-06, 175: 1.7300045617488708e-06, 176: 4.825802198562639e-06, 177: 4.55264358354966e-06, 178: 9.10528716709932e-08, 179: 2.367374663445823e-06, 180: 1.1836873317229116e-06, 181: 4.825802198562639e-06, 182: 3.642114866839728e-07, 183: 2.8863760319704844e-05, 184: 2.5494804067878094e-06, 185: 1.9121103050908573e-06, 187: 5.463172300259592e-07, 188: 4.55264358354966e-07, 189: 3.733167738510721e-06, 190: 2.5494804067878094e-06, 191: 2.731586150129796e-07, 192: 1.028897449882223e-05, 193: 1.511477669738487e-05, 194: 3.642114866839728e-06, 195: 2.731586150129796e-07, 196: 3.3689562518267483e-06, 197: 2.00316317676185e-06, 198: 2.27632179177483e-06, 199: 6.373701016969524e-07, 200: 6.7379125036534965e-06, 201: 6.7379125036534965e-06, 202: 1.87568915642246e-05, 203: 2.5494804067878094e-06, 204: 1.2747402033939047e-06, 205: 9.10528716709932e-08, 206: 1.1836873317229116e-06, 207: 1.4568459467358912e-06, 208: 9.10528716709932e-07, 209: 9.10528716709932e-08, 210: 1.3657930750648979e-06, 211: 4.55264358354966e-06, 212: 1.001581588380925e-06, 213: 4.55264358354966e-07, 214: 1.821057433419864e-07, 215: 2.0942160484328436e-06, 216: 1.5478988184068843e-06, 217: 7.830546963705415e-06, 218: 1.4568459467358912e-06, 219: 3.642114866839728e-06, 220: 1.821057433419864e-07, 221: 4.461590711878667e-06, 222: 3.5510619951687345e-06, 223: 1.821057433419864e-07, 224: 2.394690524947121e-05, 225: 3.642114866839728e-07, 226: 3.5510619951687345e-06, 227: 1.5478988184068843e-06, 229: 1.2747402033939047e-06, 230: 6.191595273627537e-06, 231: 4.55264358354966e-07, 232: 4.916855070233632e-06, 233: 2.00316317676185e-06, 234: 1.1836873317229116e-06, 235: 1.821057433419864e-07, 236: 7.466335477021442e-06, 237: 2.7315861501297957e-06, 238: 2.822639021800789e-06, 239: 2.367374663445823e-06, 240: 9.469498653783293e-06, 241: 0.002343700916811365, 242: 0.0013962047342030097, 243: 0.00298316523455675, 244: 1.6389516900778775e-06, 245: 4.370537840207674e-06, 246: 5.098960813575619e-06, 247: 1.9121103050908573e-06, 248: 1.028897449882223e-05, 249: 1.9121103050908573e-06, 250: 4.5799594450509575e-05, 251: 8.55896993707336e-06, 252: 3.0957976368137687e-06, 253: 2.0942160484328436e-06, 254: 8.650022808744353e-06, 255: 0.0005190924213963322}
    LIKELYHOOD_PROLOG_BY_OPCODE_INT = {0: 0.01665479334165359, 129: 0.023200298529314614, 130: 0.009489732698422902, 3: 0.008530939385336712, 4: 0.01893839976146222, 133: 0.00042851097791561546, 134: 5.1778409831470204e-05, 1: 0.009243338886121423, 136: 6.963303391128752e-05, 128: 0.09992697458751355, 11: 1.4283699263853849e-05, 2: 0.0012980311706027186, 144: 0.01951153319442436, 145: 0.0043136771776838626, 146: 0.00018568809043010003, 131: 0.004161912873005416, 20: 0.08421311993486633, 21: 0.01805816679432723, 22: 0.005004651129572792, 23: 4.820748501550674e-05, 127: 0.0019782923480437583, 132: 0.00035887794400432795, 68: 1.785462407981731e-06, 150: 1.6069161671835582e-05, 5: 7.141849631926924e-06, 32: 0.0003963726545719443, 161: 2.8567398527707697e-05, 162: 0.0001321242181906481, 164: 1.2498236855872117e-05, 6: 4.463656019954328e-05, 116: 1.785462407981731e-06, 135: 1.7854624079817313e-05, 242: 0.004335102726579643, 48: 8.748765799110482e-05, 49: 5.892025946339713e-05, 50: 3.570924815963462e-06, 51: 0.003079922653768486, 52: 0.007804256185288147, 53: 0.023748435488565006, 54: 0.018733071584544323, 55: 0.00437259743714726, 57: 1.9640086487799044e-05, 10: 0.009871821653730992, 64: 3.2138323343671163e-05, 19: 0.00013033875578266637, 66: 0.0001839026280221183, 67: 0.00019818632728597216, 147: 0.00019104447765404525, 80: 0.014358688684989082, 81: 0.007132922319887016, 82: 0.027130101289282404, 83: 0.0001892590152460635, 84: 0.0034209459736929968, 85: 0.000332096007884602, 86: 0.016106656382403196, 87: 0.09819507605177127, 89: 6.784757150330578e-05, 90: 0.004340459113803589, 91: 0.03544142879843736, 96: 0.1568403743043392, 97: 0.12410927744121811, 98: 0.00018033170320615484, 99: 0.08800365662701155, 100: 7.141849631926924e-06, 101: 9.998589484697694e-05, 16: 0.0003088849965808395, 17: 0.00152657035882438, 104: 3.570924815963462e-06, 106: 3.570924815963462e-06, 103: 1.4283699263853849e-05, 108: 1.9640086487799044e-05, 115: 0.007734623151376859, 240: 1.6069161671835582e-05, 241: 6.784757150330578e-05, 114: 3.570924815963462e-06, 243: 0.00506357138903619, 25: 0.00012319690615073944, 120: 1.785462407981731e-06, 148: 0.00017140439116624618, 255: 0.00035887794400432795, 124: 0.009370106717088125, 102: 8.927312039908657e-06, 149: 5.7134797055415395e-05}
    LIKELYHOOD_EPILOG_BY_OPCODE_INT = {0: 0.0019461540247000869, 1: 0.04056749137175291, 2: 0.006277685826463767, 3: 0.025819571881823815, 4: 0.006656203856955894, 5: 3.5709248159634626e-05, 6: 0.00015890615431037408, 7: 1.9640086487799044e-05, 8: 7.141849631926924e-06, 9: 1.0712774447890386e-05, 10: 0.013767700627947129, 11: 0.00013926606782257503, 12: 0.0001267678309667029, 13: 0.00012855329337468465, 14: 0.00011962598133477598, 16: 0.0007391814369044367, 17: 0.006554432499700935, 18: 0.00039815811697992604, 19: 5.1778409831470204e-05, 20: 0.0043208190273157894, 21: 0.01755466639527638, 22: 0.028503121881020357, 23: 0.003947657384047607, 24: 3.928017297559809e-05, 25: 0.00448686703125809, 26: 0.0002696048236052414, 27: 7.141849631926925e-05, 28: 1.9640086487799044e-05, 29: 4.999294742348847e-05, 30: 5.356387223945193e-06, 32: 0.009911101826706589, 33: 0.0004213691282836886, 34: 8.03458083591779e-05, 35: 0.0004070854290198347, 36: 3.570924815963462e-06, 38: 3.5709248159634626e-05, 39: 7.141849631926924e-06, 40: 3.928017297559809e-05, 41: 0.0001267678309667029, 42: 7.141849631926924e-06, 43: 7.498942113523271e-05, 44: 1.0712774447890386e-05, 45: 8.391673317514137e-05, 46: 1.2498236855872117e-05, 47: 3.928017297559809e-05, 48: 0.002024714370651283, 49: 0.0018747355283808176, 50: 0.0001767607783901914, 51: 0.006366958946862854, 52: 0.004651129572792409, 53: 0.0016961892875826446, 54: 0.00874519487429452, 55: 0.004360099200291388, 56: 0.0001892590152460635, 57: 0.000405299966611853, 58: 5.356387223945193e-06, 59: 3.928017297559809e-05, 60: 7.141849631926925e-05, 61: 1.0712774447890386e-05, 62: 1.4283699263853849e-05, 63: 3.570924815963462e-06, 64: 0.00041601274105974336, 65: 1.785462407981731e-06, 66: 0.0014033734526736406, 67: 0.0001321242181906481, 68: 6.606210909532405e-05, 69: 0.00019104447765404525, 70: 8.927312039908657e-06, 71: 2.6781936119725966e-05, 72: 5.356387223945193e-06, 73: 7.141849631926925e-05, 74: 5.7134797055415395e-05, 75: 2.6781936119725966e-05, 76: 0.00010355681966294041, 77: 4.1065635383579817e-05, 78: 3.570924815963462e-06, 79: 6.249118427936059e-05, 80: 0.10038226750154888, 81: 0.0149139674938714, 82: 0.024828640245393954, 83: 0.00012141144374275771, 84: 0.016076303521467508, 85: 0.00960221683012575, 86: 0.03695371545799789, 87: 0.021707651956241886, 88: 3.570924815963462e-06, 89: 0.000332096007884602, 90: 0.006599069059900479, 91: 0.044231260232931426, 92: 1.4283699263853849e-05, 93: 5.356387223945193e-06, 94: 8.927312039908657e-06, 95: 0.00018568809043010003, 96: 0.16128260477539777, 97: 0.04402950298082949, 98: 0.0011569796403721618, 99: 0.00229967558148047, 100: 9.998589484697694e-05, 101: 0.00010712774447890386, 102: 2.8567398527707697e-05, 103: 0.0008605928806471945, 104: 0.00013569514300661157, 105: 0.00015890615431037408, 106: 1.785462407981731e-06, 107: 0.00013569514300661157, 108: 0.00021425548895780773, 109: 3.2138323343671163e-05, 110: 6.249118427936059e-05, 111: 0.0003624488688202914, 112: 5.892025946339713e-05, 113: 1.785462407981731e-06, 114: 0.00027496121082918657, 115: 0.018933043374238276, 116: 0.0001267678309667029, 117: 0.0004945730870109396, 118: 6.427664668734233e-05, 119: 1.9640086487799044e-05, 120: 0.00015712069190239235, 121: 0.0001267678309667029, 122: 1.7854624079817313e-05, 123: 5.7134797055415395e-05, 124: 7.856034595119618e-05, 125: 0.00016961892875826446, 126: 2.6781936119725966e-05, 127: 0.0032245451088150066, 128: 0.02818709503480759, 129: 0.03960869805866672, 130: 0.028865570749840648, 131: 0.014183713369006873, 132: 0.0038155331658569595, 133: 0.004219047670060831, 134: 0.0003660197936362549, 135: 0.0026871209240125053, 136: 0.004802893877470857, 137: 8.391673317514137e-05, 138: 0.0001767607783901914, 139: 0.0005731334329621357, 140: 0.00015354976708642889, 141: 4.1065635383579817e-05, 142: 3.2138323343671163e-05, 143: 8.927312039908657e-06, 144: 0.08225089674849441, 145: 0.02886914167465661, 146: 0.008641638054631579, 147: 0.0036155613761630055, 148: 0.0008230981700795781, 149: 0.0005035003990508482, 150: 0.00023568103785358852, 151: 0.00019282994006202697, 152: 0.00012141144374275771, 153: 9.462950762303175e-05, 154: 4.820748501550674e-05, 155: 0.00011784051892679426, 156: 7.677488354321444e-05, 157: 2.8567398527707697e-05, 158: 5.356387223945193e-05, 159: 3.570924815963462e-06, 160: 4.642202260752501e-05, 161: 0.001758680471862005, 162: 0.0003267396206606568, 163: 0.001421228076753458, 164: 0.00013390968059862984, 165: 2.8567398527707697e-05, 166: 7.320395872725097e-05, 167: 2.3211011303762504e-05, 168: 0.0007123995007847107, 169: 0.00021604095136578948, 170: 8.03458083591779e-05, 171: 2.3211011303762504e-05, 172: 0.00016247707912633754, 173: 4.2851097791561544e-05, 174: 0.00018747355283808178, 175: 3.392378575165289e-05, 176: 8.213127076715963e-05, 177: 6.784757150330578e-05, 179: 4.1065635383579817e-05, 180: 2.1425548895780772e-05, 181: 9.462950762303175e-05, 182: 3.570924815963462e-06, 183: 0.000564206120922227, 184: 2.8567398527707697e-05, 185: 3.392378575165289e-05, 187: 3.570924815963462e-06, 188: 8.927312039908657e-06, 189: 3.392378575165289e-05, 190: 3.392378575165289e-05, 191: 1.785462407981731e-06, 192: 7.856034595119618e-05, 193: 0.0002803175980531318, 194: 6.784757150330578e-05, 195: 3.570924815963462e-06, 196: 5.7134797055415395e-05, 197: 3.928017297559809e-05, 198: 3.928017297559809e-05, 199: 1.785462407981731e-06, 200: 5.1778409831470204e-05, 201: 0.00011962598133477598, 202: 0.0003678052560442366, 203: 4.642202260752501e-05, 204: 2.1425548895780772e-05, 205: 1.785462407981731e-06, 206: 2.1425548895780772e-05, 207: 2.8567398527707697e-05, 208: 1.7854624079817313e-05, 210: 1.2498236855872117e-05, 211: 3.5709248159634626e-05, 212: 1.7854624079817313e-05, 213: 5.356387223945193e-06, 214: 3.570924815963462e-06, 215: 3.928017297559809e-05, 216: 2.8567398527707697e-05, 217: 0.00015354976708642889, 218: 2.8567398527707697e-05, 219: 6.784757150330578e-05, 220: 1.785462407981731e-06, 221: 2.6781936119725966e-05, 222: 3.570924815963462e-06, 223: 3.570924815963462e-06, 224: 0.000378518030492127, 225: 5.356387223945193e-06, 226: 6.963303391128752e-05, 227: 2.4996473711744235e-05, 229: 2.1425548895780772e-05, 230: 0.00010534228207092214, 231: 5.356387223945193e-06, 232: 7.677488354321444e-05, 233: 3.5709248159634626e-05, 234: 2.1425548895780772e-05, 236: 0.00012855329337468465, 237: 5.356387223945193e-05, 238: 3.7494710567616354e-05, 239: 4.463656019954328e-05, 240: 3.570924815963462e-06, 241: 0.0036334160002428227, 242: 0.006215194642184406, 243: 0.0070436491994879296, 244: 2.4996473711744235e-05, 245: 8.213127076715963e-05, 246: 9.820043243899522e-05, 247: 3.035286093568943e-05, 248: 0.00019640086487799044, 249: 3.7494710567616354e-05, 250: 0.0008980875912148107, 251: 0.00015176430467844714, 252: 3.035286093568943e-05, 253: 3.2138323343671163e-05, 254: 2.3211011303762504e-05, 255: 0.0009712915499420617}
    AVERAGE_CONTRACT_SIZE = 857
    MIN_CONTRACT_SIZE = 4
    MAX_CONTRACT_SIZE = 8816


    def random_code_byte_sequence(self, length=None):
        # todo: add gauss histogramm random.randgauss(min,max,avg) - triangle is not really correct here
        length = length or int(random.triangular(self.MIN_CONTRACT_SIZE, 2 * self.AVERAGE_CONTRACT_SIZE + self.MIN_CONTRACT_SIZE))  # use gauss

#        rnd_prolog = WeightedRandomizer(self.LIKELYHOOD_PROLOG_BY_OPCODE_INT)
#        rnd_epilog = WeightedRandomizer(self.LIKELYHOOD_EPILOG_BY_OPCODE_INT)  # not completely true as this incorps. pro/epilog
#        rnd_corpus = WeightedRandomizer(self.LIKELYHOOD_BY_OPCODE_INT)
#       
        b = []
        for _ in range(length):
#            b.append(valid_opcodes[random.randint(0,len(valid_opcodes)-1)])
            b.append(random.choice(constantinople_skewed_set))

#        for _ in range(128):
#            b.append(rnd_prolog.random())
#            #  hack ahead -
#            if self.FLAG_FOCUS_CONSTANTINOPLE in self.flags:
#                # 10% chance of inserting a constantinople instr
#                if self.randomPercent() < 5:
#                    b.append(random.choice([asm_registry.INSTRUCTIONS_BY_NAME["CREATE2"].opcode,
#                                           asm_registry.INSTRUCTIONS_BY_NAME["EXTCODEHASH"].opcode]))
#
#        for _ in range(length - 128 * 2):
#            b.append(rnd_corpus.random())
#            if self.FLAG_FOCUS_CONSTANTINOPLE in self.flags:
#                # 10% chance of inserting a constantinople instr
#                if self.randomPercent() < 5:
#                    b.append(random.choice([asm_registry.INSTRUCTIONS_BY_NAME["CREATE2"].opcode,
#                                           asm_registry.INSTRUCTIONS_BY_NAME["EXTCODEHASH"].opcode]))
#
#        for _ in range(128):
#            b.append(rnd_epilog.random())
#            if self.FLAG_FOCUS_CONSTANTINOPLE in self.flags:
#                # 10% chance of inserting a constantinople instr
#                if self.randomPercent() < 5:
#                    b.append(random.choice([asm_registry.INSTRUCTIONS_BY_NAME["CREATE2"].opcode,
#                                           asm_registry.INSTRUCTIONS_BY_NAME["EXTCODEHASH"].opcode]))
#
        return bytes(b)

    def _track_address(self, address):
        self._addresses_seen.add(binascii.hexlify(address).decode("utf-8"))
        return address

    def _fill_arguments(self, instructions):
        #https://github.com/ethereum/testeth/blob/7cbbb6fed4941420fbae738828fa1339c990e3d3/test/tools/fuzzTesting/fuzzHelper.cpp#L391
        def create_push_for_data(data):
            # expect bytes but silently convert int2bytes
            if isinstance(data, int):
                data = int2bytes(data)

            instr = asm_registry.create_instruction("PUSH%d"%len(data))
            instr.operand_bytes = data
            return instr

        for instr in instructions:
            args_filled = False
            if self.randomPercent() < self._config_getint("engine.RndCodeInstr.smartCodeProbability.p", 990)/10:
                # push arguments code
                if instr.name.startswith("PUSH"):
                    instr.randomize_operand()
                elif instr.name.startswith("SWAP"):
                    times = instr.opcode - asm_registry.create_instruction("SWAP1").opcode +2
                    for _ in range(times):
                        yield asm_registry.create_instruction("PUSH%s"%self.randomUniInt(1,32)).randomize_operand()
                    args_filled = True
                elif instr.name.startswith("DUP"):
                    times = instr.opcode - asm_registry.create_instruction("DUP1").opcode + 1
                    for _ in range(times):
                        yield asm_registry.create_instruction("PUSH%s"%self.randomUniInt(1,32)).randomize_operand()
                    args_filled = True
                elif instr.name.startswith("LOG"):
                    # There can be any number of topics, 
                    # followed by memstart and memsize, which must be reasonable
                    yield create_push_for_data(self.randomSmallMemoryLength()) # msize
                    yield create_push_for_data(self.randomSmallMemoryLength()) # mstart
                    args_filled = True
                elif instr.name=="MLOAD":
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    args_filled = True
                elif instr.name=="MSTORE":
                    yield create_push_for_data(self.randomByteSequence(self.randomLength32()))
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    args_filled = True
                elif instr.name=="MSTORE8":
                    #yield create_push_for_data(self.randomByteSequence(self.randomLength32())) # value
                    # We skip pushing the value, and use whatever is already on the stack
                    # Only set a reasonable offset
                    yield create_push_for_data(self.randomSmallMemoryLength()) # offset
                    args_filled = True
                elif instr.name=="RETURNDATACOPY":
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    args_filled = True
                elif instr.name=="EXTCODECOPY":
                    yield create_push_for_data(self.randomSmallMemoryLength())   # length
                    yield create_push_for_data(self.randomMemoryLength())        # codeoffset
                    yield create_push_for_data(self.randomSmallMemoryLength())   # memoffset
                    yield create_push_for_data(self._track_address(RndDestAddress().as_bytes()))      # address
                    args_filled = True
                elif instr.name=="CODECOPY":
                    yield create_push_for_data(self.randomSmallMemoryLength())   # length
                    yield create_push_for_data(self.randomMemoryLength())        # codeoffset
                    yield create_push_for_data(self.randomSmallMemoryLength())   # memoffset
                    args_filled = True
                elif instr.name=="CREATE":
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomUniInt(max=255))
                    args_filled = True
                elif instr.name in ("CALL", "CALLCODE"):
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomUniInt(max=255))   # value
                    yield create_push_for_data(self._track_address(RndDestAddress().as_bytes()))  # address
                    yield create_push_for_data(self.randomUniInt())          # gas 
                    args_filled = True
                elif instr.name in ("STATICCALL","DELEGATECALL"):
                    yield create_push_for_data(self.randomSmallMemoryLength()) # retsize
                    yield create_push_for_data(self.randomSmallMemoryLength()) # retoffset
                    yield create_push_for_data(self.randomSmallMemoryLength()) # insize
                    yield create_push_for_data(self.randomSmallMemoryLength()) # inoffset
                    yield create_push_for_data(self._track_address(RndDestAddress().as_bytes()))
                    yield create_push_for_data(self.randomUniInt())            # gas
                    args_filled = True
                elif instr.name=="SUICIDE":
                    yield create_push_for_data(self._track_address(RndDestAddress().as_bytes()))
                    args_filled = True
                elif instr.name in ("RETURN","REVERT"):
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    args_filled = True
                elif instr.name=="CREATE2":
                    # todo: rework
                    yield create_push_for_data(self.randomUniInt()) # salt
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomSmallMemoryLength())
                    yield create_push_for_data(self.randomUniInt(max=255)) # value
                    args_filled = True
                elif instr.name=="SSTORE":
                    # use 0-3 for storage keys/vals, to do overwrites and no-change writes.
                    yield create_push_for_data(self.randomUniInt(max=3))
                    yield create_push_for_data(self.randomUniInt(max=3))
                    args_filled = True
                elif instr.name=="SLOAD":
                    # sstore mostly at 0-3, but want some sloads on empty locations
                    yield create_push_for_data(self.randomUniInt(max=8))
                    args_filled = True
                elif instr.name in ["EXTCODEHASH", "EXTCODESIZE"]:
                    # todo: rework                    
                    yield create_push_for_data(self._track_address(RndDestAddress().as_bytes()))  # address
                    args_filled = True
                elif instr.category in ("bitwise-logic","comparison"):
                    for _ in instr.args:
                        yield create_push_for_data(self.randomUniInt())
                    args_filled = True


            #  create random args for all other instructions.
            if not args_filled:
                # if args have not been pushed create random args.
                for _ in instr.args:
                    yield create_push_for_data(self.randomByteSequence(self.randomLength32()))

            # finally push instruction
            yield instr

    def generate(self, length=50):
        if self.fill_arguments:
            length = length // 2

        self._addresses_seen = set([])  # todo: hacky

        instructions = [asm_registry.create_instruction(opcode=opcode) for opcode in self.random_code_byte_sequence(length)]
        if self.fill_arguments:
            instructions = self._fill_arguments(instructions)

        serialized = ''.join(e.serialize() for e in instructions)     
#        asm = ' '.join(str(e) for e in instructions)
#        print(asm)

        return "%s%s" % (self.prefix, serialized)
