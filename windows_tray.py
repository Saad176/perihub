"""Give the app menu its own persistent Explorer identity, independent of the battery slots."""

import ctypes
from ctypes import wintypes as w
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QWidget


class NotifyIconData(ctypes.Structure):
    _fields_ = [
        ("cbSize", w.DWORD), ("hWnd", w.HWND), ("uID", w.UINT), ("uFlags", w.UINT),
        ("uCallbackMessage", w.UINT), ("hIcon", w.HICON), ("szTip", w.WCHAR * 128),
        ("dwState", w.DWORD), ("dwStateMask", w.DWORD), ("szInfo", w.WCHAR * 256),
        ("uVersion", w.UINT), ("szInfoTitle", w.WCHAR * 64), ("dwInfoFlags", w.DWORD),
        ("guidItem", ctypes.c_ubyte * 16), ("hBalloonIcon", w.HICON),
    ]


notify = ctypes.windll.shell32.Shell_NotifyIconW
notify.argtypes = [w.DWORD, ctypes.POINTER(NotifyIconData)]
user32 = ctypes.windll.user32
user32.DestroyIcon.argtypes = [w.HICON]
user32.SetForegroundWindow.argtypes = [w.HWND]
TASKBAR_CREATED = user32.RegisterWindowMessageW("TaskbarCreated")
CALLBACK = 0x8001
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO, NIF_GUID, NIF_SHOWTIP = 1, 2, 4, 16, 32, 128


class AppTray(QWidget):
    """A hidden notification receiver. Only its shell icon is displayed."""

    def __init__(self, icon, parent):
        super().__init__(parent, Qt.WindowType.Tool)
        self.icon = icon
        self.menu = None
        self.wanted = False
        self.registered = False
        self.data = NotifyIconData()
        self.data.cbSize = ctypes.sizeof(self.data)
        self.data.hWnd = int(self.winId())
        self.data.uID = 1
        self.data.guidItem[:] = UUID("b8507688-c27b-45ee-a77b-263826d33627").bytes_le
        self.data.uCallbackMessage = CALLBACK
        self.data.szTip = "PeriHub"
        self.retry = QTimer(self, interval=2000)
        self.retry.timeout.connect(self.show)
        QApplication.instance().aboutToQuit.connect(self.hide)

    def setContextMenu(self, menu):
        self.menu = menu

    def show(self):
        self.wanted = True
        if self.registered:
            return
        size = user32.GetSystemMetrics(49) or 32  # SM_CXSMICON
        self.data.hIcon = self.icon.pixmap(size, size).toImage().toHICON()
        self.data.uFlags = NIF_GUID | NIF_ICON | NIF_TIP | NIF_MESSAGE | NIF_SHOWTIP
        try:
            self.registered = bool(notify(0, ctypes.byref(self.data)))  # NIM_ADD
        finally:
            user32.DestroyIcon(self.data.hIcon)
            self.data.hIcon = None
        if self.registered:
            self.retry.stop()
            self.data.uVersion = 4
            notify(4, ctypes.byref(self.data))
        else:
            self.retry.start()

    def hide(self):
        self.wanted = False
        self.retry.stop()
        if self.registered:
            self.data.uFlags = NIF_GUID
            notify(2, ctypes.byref(self.data))
            self.registered = False

    def isVisible(self):
        return self.registered

    def setToolTip(self, text):
        if text != self.data.szTip:
            self.data.szTip = text[:127]
            if self.registered:
                self.data.uFlags = NIF_GUID | NIF_TIP | NIF_SHOWTIP
                notify(1, ctypes.byref(self.data))

    def showMessage(self, title, message, icon, timeout):
        self.data.szInfoTitle = title[:63]
        self.data.szInfo = message[:255]
        self.data.dwInfoFlags = 1  # NIIF_INFO
        self.data.uFlags = NIF_GUID | NIF_INFO
        notify(1, ctypes.byref(self.data))

    def nativeEvent(self, event_type, message):
        msg = w.MSG.from_address(int(message))
        if msg.message == TASKBAR_CREATED and getattr(self, "wanted", False):
            self.registered = False
            QTimer.singleShot(0, self, self.show)
        elif msg.message == CALLBACK:
            action = msg.lParam & 0xffff
            if action in (0x400, 0x401, 0x405):  # NIN_SELECT, KEYSELECT, BALLOONUSERCLICK
                self.parentWidget().show_from_tray()
            elif action == 0x7b and self.menu:  # WM_CONTEXTMENU
                user32.SetForegroundWindow(self.data.hWnd)
                self.menu.popup(QCursor.pos())
            return True, 0
        return super().nativeEvent(event_type, message)
