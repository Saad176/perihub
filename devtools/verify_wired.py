"""Reversible, explicitly wired-only checks; restores each changed setting."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mouse_direct as m


def wired():
    info = m.find_device()
    if not info or info['connection'] != 'wired':
        raise RuntimeError('Keep the mouse connected by USB for this check')


wired()
before = m.read_state()
print('Original:', before, flush=True)
stage = before['active_stage']
value = before['dpi'][stage - 1]
try:
    m.set_dpi_value(stage, value + 50 if value < 26000 else value - 50)
    expected = value + 50 if value < 26000 else value - 50
    r = m._query(0x8c, stage - 1)
    assert (r[3] + (r[4] << 8) + 1) * 50 == expected
finally:
    wired(); m.set_dpi_value(stage, value)
print('DPI numeric write/read/restore: OK', flush=True)
try:
    other = 1 if stage != 1 else min(2, before['stage_count'])
    m.select_dpi_stage(other)
    assert m._configuration()[1] == other - 1
finally:
    wired(); m.select_dpi_stage(stage)
try:
    count = 5 if before['stage_count'] == 6 else 6
    m.set_stage_count(count)
    assert m._configuration()[0] == count
finally:
    wired(); m.set_stage_count(before['stage_count']); m.select_dpi_stage(stage)
print('DPI stage/count write/read/restore: OK', flush=True)
try:
    for hz, code in m.POLLING_CODES.items():
        wired(); m.set_polling_rate(hz); time.sleep(.6)
        assert m._query(0x8d)[2] == code
        print('Polling', hz, 'readback: OK', flush=True)
finally:
    wired(); m.set_polling_rate(before['polling_hz']); time.sleep(.6)
for name in m.SENSOR_SETTINGS:
    try:
        for value in ((0, 1, 2) if name == 'sensor_mode' else (1 - before[name],)):
            wired(); m.set_sensor_setting(name, value)
            assert m.read_sensor_setting(name) == value
    finally:
        wired(); m.set_sensor_setting(name, before[name])
    print(name, 'write/read/restore: OK', flush=True)
try:
    value = before['debounce_ms'] + 1 if before['debounce_ms'] < 30 else 29
    m.set_debounce(value)
    assert m._query(0x89, 1)[3] == value
finally:
    wired(); m.set_debounce(before['debounce_ms'])
try:
    value = before['dormancy_s'] + 1 if before['dormancy_s'] < 1800 else 1799
    m.set_dormancy(value)
    r = m._query(0x89, 3)
    assert r[3] + (r[4] << 8) == value
finally:
    wired(); m.set_dormancy(before['dormancy_s'])
after = m.read_state()
assert before == after, (before, after)
print('All settings restored and verified:', after, flush=True)
