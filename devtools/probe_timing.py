"""Reversible checks of debounce and dormancy commands."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mouse_direct import _device, _send


def read_value(sub):
    device = _device()
    try:
        device.send_feature_report(bytes([9, 0x89, sub, 0, 0, 0, 0, 0, 0]))
        time.sleep(0.04)
        result = bytes(device.get_feature_report(9, 9))
        if result[:3] != bytes([9, 0x89, sub]):
            raise RuntimeError(result.hex(" "))
        return result[3] | result[4] << 8
    finally:
        device.close()


for sub, command in ((1, 1), (3, 3)):
    original = read_value(sub)
    alternate = original + 1
    try:
        _send([9, 0x09, command, alternate & 255, alternate >> 8, 0, 0, 0, 0])
        time.sleep(0.06)
        print(sub, original, "->", read_value(sub), flush=True)
    finally:
        _send([9, 0x09, command, original & 255, original >> 8, 0, 0, 0, 0])
        time.sleep(0.06)
        print(sub, "restored", read_value(sub), flush=True)
