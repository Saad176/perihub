"""Passive SC900 battery input reports, decoded from the supplied AULA driver.

AULA 0x446750 reads 33 bytes; 0x435EF0 uses report byte 1's low seven
bits as charge and maps it to five bars. No feature writes are needed.
"""
import threading
import time

from mouse_direct import _device, find_device


def decode_battery(report):
    if len(report) != 33 or report[0] != 9:
        return None
    percent = report[1] & 0x7f
    if percent > 100:
        return None
    return {"percent": percent, "bars": min(5, percent // 20 + 1)}


class BatteryMonitor:
    def __init__(self, callback):
        self.callback = callback
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, name="mouse-battery", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        while not self.stop_event.is_set():
            device = None
            try:
                info = find_device()
                if info is None:
                    raise OSError("Mouse not connected")
                device = _device(info)
                last_seen = time.monotonic()
                next_connection_check = last_seen + 3
                available = False
                while not self.stop_event.is_set():
                    if time.monotonic() >= next_connection_check:
                        current = find_device()
                        if current is None or current["path"] != info["path"]:
                            self.callback(None)
                            break
                        next_connection_check = time.monotonic() + 3
                    reading = decode_battery(device.read(64, 250))
                    if reading is not None:
                        last_seen = time.monotonic()
                        available = True
                        self.callback({**reading, "connection": info["connection"]})
                    elif available and time.monotonic() - last_seen > 120:
                        available = False
                        self.callback(None)
            except (OSError, RuntimeError):
                if not self.stop_event.is_set():
                    self.callback(None)
            finally:
                if device is not None:
                    device.close()
            self.stop_event.wait(3)
