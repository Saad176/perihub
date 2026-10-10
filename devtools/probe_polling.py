"""Temporarily try AULA's polling codes and restore the original code."""

import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mouse_direct import _device, _send


def read_code():
    for attempt in range(5):
        device = _device()
        try:
            device.send_feature_report(bytes([9, 0x8D, 0, 0, 0, 0, 0, 0, 0]))
            time.sleep(0.08)
            report = bytes(device.get_feature_report(9, 9))
            if report[:2] == b"\x09\x8d":
                return report[2]
        finally:
            device.close()
        time.sleep(0.3)
    raise RuntimeError(f"No valid polling reply after {attempt + 1} attempts")


original = read_code()
print("original code", original, flush=True)
try:
    for code in (3, 4, 5, 6):
        _send([9, 0x0D, code, 0, 0, 0, 0, 0, 0])
        time.sleep(0.8)
        print("sent", code, "read", read_code(), flush=True)
finally:
    _send([9, 0x0D, original, 0, 0, 0, 0, 0, 0])
    time.sleep(0.8)
    print("restored", read_code(), flush=True)
