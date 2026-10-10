"""Trace HID DeviceIoControl calls in the user's AULA process."""

import json
import sys
import time

import frida


AGENT = r"""
function hex(pointer, length) {
  if (pointer.isNull() || length <= 0) return '';
  const bytes = new Uint8Array(pointer.readByteArray(Math.min(length, 64)));
  return Array.from(bytes).map(x => x.toString(16).padStart(2, '0')).join('');
}
const address = Module.getGlobalExportByName('DeviceIoControl');
Interceptor.attach(address, {
  onEnter(args) {
    this.handle = args[0].toString();
    this.code = args[1].toUInt32();
    this.input = args[2];
    this.inputLength = args[3].toInt32();
    this.output = args[4];
    this.outputLength = args[5].toInt32();
    this.isHid = (this.code & 0xffff0000) === 0x000b0000;
    if (this.isHid) this.before = hex(this.input, this.inputLength);
  },
  onLeave(result) {
    if (!this.isHid) return;
    send({handle:this.handle, code:'0x'+this.code.toString(16), ok:result.toInt32(), input:this.before, output:hex(this.output,this.outputLength)});
  }
});
"""


def main():
    session = frida.attach(int(sys.argv[1]))
    script = session.create_script(AGENT)
    script.on('message', lambda message, data: print(json.dumps(message.get('payload', message)), flush=True))
    script.load()
    print('capture ready', flush=True)
    try:
        time.sleep(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    finally:
        session.detach()


if __name__ == '__main__':
    main()
