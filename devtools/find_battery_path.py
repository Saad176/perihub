"""Find AULA feature-report handlers near HID GetFeature call sites."""

import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = pefile.PE(r"helping stuff\Aula SC900PRO.exe")
data = bytes(pe.__data__)
engine = Cs(CS_ARCH_X86, CS_MODE_32)
target = b"\xFF\x15" + struct.pack("<I", 0x5721F8)
for offset in range(len(data)):
    if not data.startswith(target, offset):
        continue
    address = pe.OPTIONAL_HEADER.ImageBase + pe.get_rva_from_offset(offset)
    start = max(0, offset - 220)
    nearby = list(engine.disasm(data[start:offset + 80], address - (offset - start)))
    interesting = [ins for ins in nearby if any(code in ins.op_str for code in ("0x8f", "0x81", "0x82", "0x83", "0x84", "0x85", "0x86", "0x87", "0x88"))]
    if interesting:
        print(hex(address), " | ".join(f"{ins.address:08x} {ins.mnemonic} {ins.op_str}" for ins in interesting[-8:]))
