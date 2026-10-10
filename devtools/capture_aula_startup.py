"""Attach to the next AULA process immediately and log its startup HID traffic."""

import json
import sys
import time

import frida
import psutil

from capture_battery import AGENT


device = frida.get_local_device()
deadline = time.monotonic() + 30
pid = None
while time.monotonic() < deadline:
    matches = [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() == 'aula sc900pro.exe']
    if matches:
        pid = matches[0].pid
        break
    time.sleep(0.05)
if pid is None:
    sys.exit('AULA did not launch')

session = device.attach(pid)
script = session.create_script(AGENT)


def report(message, data):
    if message.get('type') != 'send':
        print('ERROR', message, flush=True)
        return
    payload = message['payload']
    if payload.get('data', '').startswith('89504e47'):
        return
    print(json.dumps(payload), flush=True)


script.on('message', report)
script.load()
print('attached', pid, flush=True)
try:
    time.sleep(25)
finally:
    session.detach()
