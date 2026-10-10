"""Temporary developer tool: log SC900 Pro vendor-app HID writes for protocol research."""

import json
import sys
import time
from datetime import datetime

import frida


AGENT = r"""
function hex(pointer, length) {
  const bytes = new Uint8Array(pointer.readByteArray(Math.min(length, 256)));
  return Array.from(bytes).map(x => x.toString(16).padStart(2, '0')).join('');
}
for (const name of ['WriteFile', 'HidD_SetFeature', 'HidD_SetOutputReport']) {
  const address = Module.getGlobalExportByName(name);
  if (!address) continue;
  Interceptor.attach(address, {
    onEnter(args) {
      this.handle = args[0].toString();
      this.buffer = args[1];
      this.length = args[2].toInt32();
      if (this.length > 0 && this.length <= 256) {
        send({api:name, handle:this.handle, length:this.length, data:hex(this.buffer,this.length)});
      }
    }
  });
}
for (const name of ['HidD_GetFeature', 'HidD_GetInputReport']) {
  const address = Module.getGlobalExportByName(name);
  if (!address) continue;
  Interceptor.attach(address, {
    onEnter(args) {
      this.handle = args[0].toString();
      this.buffer = args[1];
      this.length = args[2].toInt32();
    },
    onLeave(result) {
      if (this.length > 0 && this.length <= 256) {
        send({api:name, handle:this.handle, length:this.length, result:result.toInt32(), data:hex(this.buffer,this.length)});
      }
    }
  });
}
"""


def main():
    pid = int(sys.argv[1])
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    session = frida.attach(pid)
    script = session.create_script(AGENT)
    def report(message, data):
        payload = message.get("payload", {})
        raw = payload.get("data", "")
        if raw.startswith(("0981", "098f")) and message.get("type") != "error":
            return
        print(datetime.now().isoformat(timespec="milliseconds"), json.dumps(message), flush=True)

    script.on("message", report)
    script.load()
    print("capture ready", flush=True)
    try:
        time.sleep(duration)
    finally:
        session.detach()


if __name__ == "__main__":
    main()
