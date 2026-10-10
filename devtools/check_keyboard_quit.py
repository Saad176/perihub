"""One-time hardware check: a software effect must yield to onboard lighting on quit."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app
import keyboard_direct
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


packets = []
original_write = keyboard_direct._write


def record_write(device, data):
    original_write(device, data)
    packets.append(bytes(data))


with patch.object(keyboard_direct, "_write", side_effect=record_write):
    qt = QApplication([])
    window = app.MainWindow()
    window.state["keyboard"] = True
    window.show_device("keyboard")
    window.apply_keyboard_effect("rainbow")
    QTimer.singleShot(1500, qt.quit)
    qt.exec()

restore_packets = [i for i, data in enumerate(packets) if data[1:4] == bytes((7, 4, 1))]
assert restore_packets, "No onboard restore command was sent"
assert restore_packets[-1] == len(packets) - 1, "Lighting writes continued after restore"
print(f"Quit restored onboard lighting after {len(packets) - 1} effect packets")
