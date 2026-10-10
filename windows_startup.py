"""Optional per-user startup for the packaged Windows application."""
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Devices"


def available():
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def command():
    return f'"{sys.executable}" --tray'


def enabled():
    if not available():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, VALUE_NAME)[0].casefold() == command().casefold()
    except FileNotFoundError:
        return False


def set_enabled(enable):
    if not available():
        raise RuntimeError("Windows startup requires the packaged Devices app.")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enable:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())
        else:
            # Do not remove an entry pointing at a different copy of the app.
            try:
                value = winreg.QueryValueEx(key, VALUE_NAME)[0]
                if value.casefold() == command().casefold():
                    winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
