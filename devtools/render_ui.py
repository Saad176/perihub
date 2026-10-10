"""Render the UI with fixture data; never touches connected hardware."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import app

state = {'stage_count': 6, 'active_stage': 2, 'dpi': [400, 800, 1600, 3200, 6400, 26000],
         'polling_hz': 1000, 'debounce_ms': 8, 'dormancy_s': 60,
         'lod': 0, 'ripple': 0, 'angle': 0, 'motion': 1, 'sensor_mode': 1}
qt = QApplication([])
target = Path(__file__).resolve().parents[1] / 'Old builds' / 'previews'
target.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temporary, \
     patch.object(app, 'detect_devices', return_value={'mouse': True, 'keyboard': True}), \
     patch.object(app.MainWindow, 'refresh_mouse_state'), \
     patch.object(app, 'BatteryMonitor'), \
     patch.object(app, 'QSettings', return_value=QSettings(str(Path(temporary) / 'settings.ini'), QSettings.Format.IniFormat)):
    window = app.MainWindow()
    window.on_scan_finished({'mouse': True, 'keyboard': True})
    window.on_mouse_read(state)
    window.show()
    qt.processEvents()
    window.grab().save(str(target / 'mouse.png'))
    for name in ('Polling', 'Sensor', 'Timing'):
        window.show_tab(name)
        qt.processEvents()
        window.grab().save(str(target / f'{name.lower()}.png'))
    window.show_device('keyboard')
    qt.processEvents()
    window.grab().save(str(target / 'keyboard.png'))
    window.stop_scanner()
    window.tray.hide()
    window.close()
print(target)
