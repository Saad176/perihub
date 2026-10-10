"""Temporary AULA HID capture while the mouse battery display loads."""

import json
import sys
import time
from datetime import datetime

import frida


AGENT = r"""
function hex(pointer, length) {
  const bytes = new Uint8Array(pointer.readByteArray(Math.min(length, 128)));
  return Array.from(bytes).map(x => x.toString(16).padStart(2, '0')).join('');
}
for (const name of ['HidD_SetFeature', 'HidD_GetFeature', 'HidD_SetOutputReport', 'WriteFile', 'ReadFile']) {
  const address = Module.getGlobalExportByName(name);
  if (!address) continue;
  Interceptor.attach(address, {
    onEnter(args) {
      this.handle = args[0].toString();
      this.buffer = args[1];
      this.length = args[2].toInt32();
      if (name.startsWith('HidD_Set') || name === 'WriteFile') {
        if (this.length > 0 && this.length <= 128) send({api:name, handle:this.handle, length:this.length, data:hex(this.buffer,this.length)});
      }
    },
    onLeave(result) {
      if (name === 'HidD_GetFeature' || name === 'ReadFile') {
        if (this.length > 0 && this.length <= 128 && result.toInt32() !== 0)
          send({api:name, handle:this.handle, length:this.length, data:hex(this.buffer,this.length)});
      }
    }
  });
}
"""


def main():
    pid = int(sys.argv[1])
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    session = frida.attach(pid)
    script = session.create_script(AGENT)

    def report(message, data):
        if message.get('type') != 'send':
            print(message, flush=True)
            return
        print(datetime.now().isoformat(timespec='milliseconds'), json.dumps(message['payload']), flush=True)

    script.on('message', report)
    script.load()
    print('capture ready', flush=True)
    try:
        time.sleep(duration)
    finally:
        session.detach()


if __name__ == '__main__':
    main()
