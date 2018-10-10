from .code import _RndCodeBase
from .address import RndAddress, RndDestAddress, RndAddressType
import evmdasm
import evmcodegen
from evmcodegen.codegen import Rnd


VALUEMAP ={
    evmdasm.argtypes.Address: lambda: RndDestAddress().as_bytes(),
    evmdasm.argtypes.Word: lambda: Rnd.byte_sequence(32),
    evmdasm.argtypes.Timestamp: lambda: Rnd.byte_sequence(4),
    evmdasm.argtypes.Data: lambda: Rnd.byte_sequence(Rnd.uni_integer(0, Rnd.opcode())),
    evmdasm.argtypes.CallValue: lambda: Rnd.uni_integer(0,1024),
    evmdasm.argtypes.Gas: lambda: Rnd.uni_integer(0,1024),
    evmdasm.argtypes.Length: lambda: Rnd.small_memory_length_1024(),
    evmdasm.argtypes.MemOffset: lambda: Rnd.small_memory_length_1024(),
    evmdasm.argtypes.Index256: lambda: Rnd.uni_integer(1,256),
    evmdasm.argtypes.Index64: lambda: Rnd.uni_integer(1,64),
    evmdasm.argtypes.Index32: lambda: Rnd.length_32(),
    evmdasm.argtypes.Byte: lambda: Rnd.byte_sequence(1),
    evmdasm.argtypes.Bool: lambda: Rnd.byte_sequence(1),
    evmdasm.argtypes.Value: lambda: Rnd.uni_integer(),
    #evmdasm.argtypes.Label: lambda: 0xc0fefefe,  # this is handled by fix_code_layout (fix jumps)
}

class RndCode2(_RndCodeBase):
    """
    Random bytecode based on stat spread of instructions
    """
    placeholder = "[CODE]"

    # analyzed based on statedump.json

    def generate(self, length=None):
        distribution = evmcodegen.distributions.EVM_CATEGORY  # override this in here to adjust weights
        generator = evmcodegen.generators.distribution.GaussDistrCodeGen(distribution=distribution)
        codegen = evmcodegen.codegen.CodeGen(generator=generator, valuemap=VALUEMAP)
        return str(codegen.generate(length=length))
