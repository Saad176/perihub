"""SC900 Pro wired/2.4 GHz HID settings recovered from AULA and readback.

See PROTOCOL_NOTES.md for packet provenance and remaining unsupported features.
"""

import threading
import time

import hid


VID = 0x093A
PID = 0x522C
WIRED_PID = 0x622C
PRODUCT = "SC900PRO"
POLLING_CODES = {1000: 0, 500: 1, 250: 2, 125: 3, 2000: 4, 4000: 5, 8000: 6}
CODE_POLLING = {code: hz for hz, code in POLLING_CODES.items()}
SENSOR_MODES = {"LP": 0, "HP": 1, "Corded": 2}
SENSOR_SETTINGS = {"lod": 1, "ripple": 2, "angle": 3, "motion": 4, "sensor_mode": 5}
_LOCK = threading.RLock()


def find_device():
    """Choose the direct USB mouse before its receiver when both are present."""
    candidates = [
        info for info in hid.enumerate(VID, 0)
        if info.get("product_id") in (WIRED_PID, PID)
        and info.get("interface_number") == 3
        and info.get("usage_page") == 0xFF05
        and (info.get("product_string") or "").upper() == PRODUCT
    ]
    wired = [info for info in candidates if info["product_id"] == WIRED_PID]
    candidates = wired or candidates
    if not candidates:
        return None
    if len(candidates) > 1:
        raise RuntimeError("Multiple SC900 Pro devices found; connect only one mouse")
    return {**candidates[0], "connection": "wired" if wired else "receiver"}


def _device(info=None):
    info = info or find_device()
    if info is None:
        raise RuntimeError("SC900 Pro configuration interface was not found")
    device = hid.device()
    device.open_path(info["path"])
    return device


def _send(report):
    if len(report) != 9:
        raise ValueError("SC900 Pro feature reports must be nine bytes")
    with _LOCK:
        device = _device()
        try:
            written = device.send_feature_report(bytes(report))
            if written != 9:
                raise OSError(f"Mouse command returned {written} bytes; expected 9")
        finally:
            device.close()


def _query(command, argument=0):
    """AULA's request/reply pair; the brief delay is required on this receiver."""
    with _LOCK:
        for attempt in range(4):
            device = _device()
            try:
                written = device.send_feature_report(bytes([9, command, argument, 0, 0, 0, 0, 0, 0]))
                if written != 9:
                    raise OSError("Mouse settings query was not accepted")
                time.sleep(0.1)
                result = bytes(device.get_feature_report(9, 9))
            finally:
                device.close()
            expects_argument = command in (0x89, 0x8A, 0x8C) or argument != 0
            if len(result) == 9 and result[:2] == bytes([9, command]) and (not expects_argument or result[2] == argument):
                return result
            time.sleep(0.15 * (attempt + 1))
    raise OSError(f"No valid SC900 Pro reply for settings query {command:02X}/{argument:02X}")


def _configuration():
    report = _query(0x8B)
    if not 1 <= report[2] <= 6 or report[3] >= report[2]:
        raise OSError(f"Invalid DPI-stage configuration: {report.hex(' ')}")
    return list(report[2:7])


def read_state():
    """Read live mouse settings. Receiver presence alone is insufficient."""
    with _LOCK:
        config = _configuration()
        count, selected = config[:2]
        dpi = []
        for index in range(count):
            report = _query(0x8C, index)
            encoded = report[3] | report[4] << 8
            value = (encoded + 1) * 50
            if not 50 <= value <= 26000:
                raise OSError(f"Invalid DPI value at stage {index + 1}")
            dpi.append(value)
        poll = _query(0x8D)[2]
        if poll not in CODE_POLLING:
            raise OSError(f"Unknown polling code {poll}")
        settings = {name: _query(0x8A, sub)[3] for name, sub in SENSOR_SETTINGS.items()}
        debounce = _query(0x89, 1)[3]
        sleep_report = _query(0x89, 3)
        dormancy = sleep_report[3] | sleep_report[4] << 8
        return {
            "stage_count": count,
            "active_stage": selected + 1,
            "dpi": dpi,
            "polling_hz": CODE_POLLING[poll],
            "debounce_ms": debounce,
            "dormancy_s": dormancy,
            **settings,
        }


def select_dpi_stage(stage):
    with _LOCK:
        config = _configuration()
        if not 1 <= stage <= config[0]:
            raise ValueError("Stage is outside the configured DPI-stage count")
        config[1] = stage - 1
        _send([9, 0x0B, *config, 0, 0])


def set_stage_count(count):
    if not 1 <= count <= 6:
        raise ValueError("Stage count must be 1 through 6")
    with _LOCK:
        config = _configuration()
        config[0] = count
        config[1] = min(config[1], count - 1)
        _send([9, 0x0B, *config, 0, 0])


def set_dpi_value(stage, dpi):
    if not 1 <= stage <= 6:
        raise ValueError("DPI stage must be 1 through 6")
    if not 50 <= dpi <= 26000 or dpi % 50:
        raise ValueError("DPI must be between 50 and 26000 in steps of 50")
    encoded = dpi // 50 - 1
    _send([9, 0x0C, stage - 1, encoded & 0xFF, encoded >> 8, 0, 0, 0, 0])


def set_polling_rate(hz):
    if hz not in POLLING_CODES:
        raise ValueError("Unsupported polling rate")
    _send([9, 0x0D, POLLING_CODES[hz], 0, 0, 0, 0, 0, 0])


def set_sensor_setting(name, value):
    if name not in SENSOR_SETTINGS:
        raise ValueError("Unknown sensor setting")
    if name == "sensor_mode":
        if value not in SENSOR_MODES.values():
            raise ValueError("Unsupported sensor mode")
    elif value not in (0, 1):
        raise ValueError("Setting must be off/on")
    _send([9, 0x0A, SENSOR_SETTINGS[name], value, 0, 0, 0, 0, 0])


def read_sensor_setting(name):
    if name not in SENSOR_SETTINGS:
        raise ValueError("Unknown sensor setting")
    return _query(0x8A, SENSOR_SETTINGS[name])[3]


def set_debounce(ms):
    if not 1 <= ms <= 30:
        raise ValueError("Debounce must be 1–30 ms")
    _send([9, 0x09, 1, ms, 0, 0, 0, 0, 0])


def set_dormancy(seconds):
    if not 15 <= seconds <= 1800:
        raise ValueError("Dormancy must be 15–1800 seconds")
    _send([9, 0x09, 3, seconds & 0xFF, seconds >> 8, 0, 0, 0, 0])
