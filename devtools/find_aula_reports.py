"""List AULA SetFeature call sites and nearby report-byte constants."""

import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = pefile.PE(r"helping stuff\Aula SC900PRO.exe")
data = pe.__data__[:]
target = b"\xFF\x15" + struct.pack("<I", 0x5721F4)
engine = Cs(CS_ARCH_X86, CS_MODE_32)
for offset in range(len(data)):
    if not data.startswith(target, offset):
        continue
    address = pe.OPTIONAL_HEADER.ImageBase + pe.get_rva_from_offset(offset)
    start = max(0, offset - 110)
    instructions = list(engine.disasm(data[start : offset + 6], address - (offset - start)))
    matches = [f"{x.mnemonic} {x.op_str}" for x in instructions if
               x.mnemonic == "mov" and any(k in x.op_str for k in ("0xd", "0x0d", "0x181", "0x182"))]
    if matches:
        print(hex(address), " | ".join(matches[-5:]))
