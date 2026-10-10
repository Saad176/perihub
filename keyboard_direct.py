"""K95 RGB Platinum lighting transport and software effects.

Packet layout follows the published OpenRGB Corsair peripheral controller.
Only the K95 RGB Platinum (1B1C:1B2D) lighting HID interface is opened.
"""

import hid
import colorsys
import math
import threading
import time


VID = 0x1B1C
PID = 0x1B2D
SKIP_ANSI = {0x31, 0x3F, 0x41, 0x42, 0x51, 0x53, 0x55, 0x6F, 0x7E, 0x7F, 0x80, 0x81}


def _packet(command, prop, *values):
    data = bytearray(65)
    data[1] = command
    data[2] = prop
    data[3:3 + len(values)] = bytes(values)
    return data


def _write(device, data):
    sent = device.write(data)
    if sent != 65:
        raise OSError(f"USB lighting write returned {sent} bytes; expected 65")


def _open_keyboard():
    matches = [
        item for item in hid.enumerate(VID, PID)
        if item.get("interface_number") == 1 and item.get("usage_page") == 0xFFC2
    ]
    if not matches:
        raise RuntimeError("K95 lighting interface was not found")
    device = hid.device()
    device.open_path(matches[0]["path"])
    return device


def set_static_color(red, green, blue):
    """Set a single RGB color across the K95's LEDs until hardware mode returns."""
    device = _open_keyboard()
    try:
        _write(device, _packet(0x07, 0x04, 0x02))
        lighting = _packet(0x07, 0x05, 0x02)
        lighting[5] = 0x03
        _write(device, lighting)
        setup = _packet(0x07, 0x05, 0x08)
        setup[5] = 0x01
        _write(device, setup)

        identifier = 0
        for _ in range(4):
            mapping = _packet(0x07, 0x40, 0x1E)
            for position in range(30):
                while identifier in SKIP_ANSI:
                    identifier += 1
                mapping[5 + 2 * position] = identifier
                mapping[6 + 2 * position] = 0xC0
                identifier += 1
            _write(device, mapping)

        for channel, value in enumerate((red, green, blue), 1):
            color_bytes = bytes([value] * 168)
            for packet_number, start, size in ((1, 0, 60), (2, 60, 60), (3, 120, 48)):
                stream = _packet(0x7F, packet_number, size)
                stream[5:5 + size] = color_bytes[start:start + size]
                _write(device, stream)
            _write(device, _packet(0x07, 0x28, channel, 3, 2 if channel == 3 else 1))
    finally:
        device.close()


def _setup_lighting(device):
    _write(device, _packet(0x07, 0x04, 0x02))
    lighting = _packet(0x07, 0x05, 0x02)
    lighting[5] = 0x03
    _write(device, lighting)
    setup = _packet(0x07, 0x05, 0x08)
    setup[5] = 0x01
    _write(device, setup)
    identifier = 0
    for _ in range(4):
        mapping = _packet(0x07, 0x40, 0x1E)
        for position in range(30):
            while identifier in SKIP_ANSI:
                identifier += 1
            mapping[5 + 2 * position] = identifier
            mapping[6 + 2 * position] = 0xC0
            identifier += 1
        _write(device, mapping)


def _write_frame(device, pixels):
    if len(pixels) != 168:
        raise ValueError("K95 lighting frame must have 168 positions")
    for channel in range(3):
        color_bytes = bytes(pixel[channel] for pixel in pixels)
        for packet_number, start, size in ((1, 0, 60), (2, 60, 60), (3, 120, 48)):
            stream = _packet(0x7F, packet_number, size)
            stream[5:5 + size] = color_bytes[start:start + size]
            _write(device, stream)
        _write(device, _packet(0x07, 0x28, channel + 1, 3, 2 if channel == 2 else 1))


def render_frame(mode, color, brightness, elapsed, speed):
    """Generate a software lighting frame from a color and animation settings."""
    brightness = max(0.0, min(1.0, brightness))
    speed = max(0.2, min(3.0, speed))
    if mode == "off":
        return [(0, 0, 0)] * 168
    if mode == "static":
        pixel = tuple(round(component * brightness) for component in color)
        return [pixel] * 168
    if mode == "breathe":
        strength = brightness * (0.08 + 0.92 * (0.5 + 0.5 * math.sin(elapsed * speed * math.tau / 3 - math.pi / 2)))
        pixel = tuple(round(component * strength) for component in color)
        return [pixel] * 168
    if mode == "rainbow":
        return [tuple(round(component * 255 * brightness) for component in colorsys.hsv_to_rgb((index / 168 + elapsed * speed / 7) % 1, 1, 1)) for index in range(168)]
    if mode == "soft_rainbow":
        return [tuple(round(component * 255 * brightness) for component in colorsys.hsv_to_rgb((index / 210 + elapsed * speed / 14) % 1, 0.58, 1)) for index in range(168)]
    if mode == "spectrum":
        pixel = tuple(round(component * 255 * brightness) for component in colorsys.hsv_to_rgb((elapsed * speed / 8) % 1, 1, 1))
        return [pixel] * 168
    if mode == "wave":
        return [tuple(round(component * brightness * (0.08 + 0.92 * (0.5 + 0.5 * math.sin(index * math.tau / 52 - elapsed * speed * math.tau / 3)))) for component in color) for index in range(168)]
    if mode == "twinkle":
        tick = int(elapsed * speed * 9)
        return [tuple(round(component * brightness * (1 if ((index * 1103515245 ^ tick * 12345) & 0xFFFF) % 29 == 0 else 0.10)) for component in color) for index in range(168)]
    raise ValueError(f"Unsupported keyboard effect: {mode}")


class KeyboardAnimator:
    """Own the keyboard HID handle in one worker while an effect runs."""

    def __init__(self, on_error=None):
        self.on_error = on_error
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._thread = None
        self._mode = None
        self._color = (76, 172, 235)
        self._brightness = 1.0
        self._speed = 1.0

    def set_effect(self, mode, color, brightness=1.0, speed=1.0):
        render_frame(mode, color, brightness, 0, speed)
        with self._lock:
            self._mode = mode
            self._color = tuple(color)
            self._brightness = brightness
            self._speed = speed
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
            self._wake.set()

    def stop(self, restore=False):
        with self._lock:
            self._mode = None
            thread = self._thread
            self._wake.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=3)
        if restore:
            restore_hardware_mode()

    def _run(self):
        device = None
        try:
            device = _open_keyboard()
            _setup_lighting(device)
            start = time.monotonic()
            previous_mode = None
            while True:
                with self._lock:
                    mode = self._mode
                    color = self._color
                    brightness = self._brightness
                    speed = self._speed
                if mode is None:
                    break
                if previous_mode != mode:
                    start = time.monotonic()
                    previous_mode = mode
                frame = render_frame(mode, color, brightness, time.monotonic() - start, speed)
                _write_frame(device, frame)
                if mode in ("static", "off"):
                    self._wake.wait()
                else:
                    self._wake.wait(0.1)
                self._wake.clear()
        except Exception as exc:
            if self.on_error:
                self.on_error(exc)
        finally:
            if device is not None:
                device.close()


def restore_hardware_mode():
    device = _open_keyboard()
    try:
        _write(device, _packet(0x07, 0x04, 0x01))
    finally:
        device.close()
