"""Smoke test a packaged EXE and its single-instance handoff."""

import os
import subprocess
import sys
import time
from pathlib import Path

exe = Path(sys.argv[1]).resolve()
assert exe.is_file(), exe
assert (exe.parent / "_internal" / "assets" / "sc900-pro-oem.png").is_file()
env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
first = subprocess.Popen([str(exe)], env=env)
try:
    time.sleep(2)
    assert first.poll() is None, "first instance exited during startup"
    second = subprocess.run([str(exe)], env=env, timeout=10)
    assert second.returncode == 0, f"second instance returned {second.returncode}"
    assert first.poll() is None, "second launch terminated the first instance"
    quit_request = subprocess.run([str(exe), '--quit'], env=env, timeout=10)
    assert quit_request.returncode == 0
    assert first.wait(timeout=10) == 0, 'app did not quit cleanly'
    print("packaged startup, single-instance handoff and graceful quit passed")
finally:
    if first.poll() is None:
        first.terminate()
        first.wait(timeout=10)
