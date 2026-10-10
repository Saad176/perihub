"""Inspect a small address range in the user's AULA executable."""

import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = pefile.PE(r"helping stuff\Aula SC900PRO.exe")
start = int(sys.argv[1], 0)
length = int(sys.argv[2], 0) if len(sys.argv) > 2 else 256
offset = pe.get_offset_from_rva(start - pe.OPTIONAL_HEADER.ImageBase)
blob = pe.__data__[offset : offset + length]
engine = Cs(CS_ARCH_X86, CS_MODE_32)
for instruction in engine.disasm(blob, start):
    print(f"{instruction.address:08X}  {instruction.mnemonic:7} {instruction.op_str}")
