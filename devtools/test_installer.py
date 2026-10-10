"""Install/update/uninstall in an isolated directory, then check cleanup.

Uses the real per-user installer registration and Start menu entry, so refuses
to run if Devices is already installed. Does not launch the app during setup.
"""
import os
import re
import subprocess
import sys
import time
import uuid
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = re.search(r'^APP_VERSION = "([^"]+)"', (ROOT / 'app.py').read_text(encoding='utf-8'), re.M)[1]
installer = (ROOT / 'Latest build' / f'Devices-{version}-Setup.exe').resolve()
target = (ROOT / 'Old builds' / 'installer-test' / 'Devices').resolve()
assert target.parent == ROOT / 'Old builds' / 'installer-test'
assert not target.exists(), 'Installer test directory already exists'
registration = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C8564F88-8639-44D5-A6C9-4F514386679F}_is1'
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registration):
        raise RuntimeError('Devices is already installed; do not alter the user installation')
except FileNotFoundError:
    pass
menu = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Devices'
assert not menu.exists(), 'Existing Devices Start menu folder must be preserved'
target.parent.mkdir(parents=True, exist_ok=True)
arguments = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', f'/DIR={target}', f'/LOG={target.parent / "install.log"}']
uninstaller = target / 'unins000.exe'
sentinel = 'InstallerSmoke_' + uuid.uuid4().hex
preference_key = r'Software\Devices\Device Control'
startup_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
startup_command = f'"{target / "Devices.exe"}" --tray'
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_key) as key:
        winreg.QueryValueEx(key, 'Devices')
        raise RuntimeError('Existing Devices startup entry must be preserved')
except FileNotFoundError:
    pass
installed = False
try:
    subprocess.run([str(installer), *arguments], check=True, timeout=90)
    installed = True
    assert (target / 'Devices.exe').is_file()
    assert (target / '_internal/assets/sc900-pro-oem.png').is_file()
    assert (menu / 'Devices.lnk').is_file()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registration) as key:
        assert winreg.QueryValueEx(key, 'DisplayVersion')[0] == version
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, preference_key) as key:
        winreg.SetValueEx(key, sentinel, 0, winreg.REG_SZ, 'preserve')
    # Repeat installation to check the in-place update path and preferences.
    subprocess.run([str(installer), *arguments], check=True, timeout=90)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, preference_key) as key:
        assert winreg.QueryValueEx(key, sentinel)[0] == 'preserve'
    # Simulate startup enabled from the tray after setup (not an installer task).
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup_key) as key:
        winreg.SetValueEx(key, 'Devices', 0, winreg.REG_SZ, startup_command)
    subprocess.run([sys.executable, str(ROOT / 'tests/smoke_exe.py'), str(target / 'Devices.exe')], check=True, timeout=30)
    subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], check=True, timeout=60)
    installed = False
    deadline = time.monotonic() + 10
    while uninstaller.exists() and time.monotonic() < deadline:
        time.sleep(.1)
    assert not (target / 'Devices.exe').exists()
    assert not menu.exists()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_key) as key:
        try:
            winreg.QueryValueEx(key, 'Devices')
            raise AssertionError('Startup entry remains after uninstall')
        except FileNotFoundError:
            pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registration):
            raise AssertionError('Uninstaller registration remains')
    except FileNotFoundError:
        pass
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, preference_key) as key:
        assert winreg.QueryValueEx(key, sentinel)[0] == 'preserve'
    print('Install, Start menu, update, launch/quit, uninstall, startup cleanup and preference preservation passed')
finally:
    if installed and uninstaller.exists():
        subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], timeout=60)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup_key) as key:
        try:
            if winreg.QueryValueEx(key, 'Devices')[0] == startup_command:
                winreg.DeleteValue(key, 'Devices')
        except FileNotFoundError:
            pass
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, preference_key, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, sentinel)
        except FileNotFoundError:
            pass
