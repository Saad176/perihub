"""Reversible checks of the AULA 0A/8A setting pairs."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mouse_direct import _device, _send


def read_value(sub):
    device = _device()
    try:
        device.send_feature_report(bytes([9, 0x8A, sub, 0, 0, 0, 0, 0, 0]))
        time.sleep(0.04)
        result = bytes(device.get_feature_report(9, 9))
        if result[:3] != bytes([9, 0x8A, sub]):
            raise RuntimeError(result.hex(" "))
        return result[3]
    finally:
        device.close()


for sub in range(1, 6):
    original = read_value(sub)
    alternate = 0 if original else 1
    try:
        _send([9, 0x0A, sub, alternate, 0, 0, 0, 0, 0])
        time.sleep(0.08)
        changed = read_value(sub)
        print(f"{sub}: {original} -> {changed}", flush=True)
    finally:
        _send([9, 0x0A, sub, original, 0, 0, 0, 0, 0])
        time.sleep(0.08)
        print(f"{sub}: restored {read_value(sub)}", flush=True)
