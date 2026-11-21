"""Combine PeriHub's adjacent notification slots into one battery readout."""

import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from ui_components import draw_symbol


if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32")
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]


def covers_taskbar(window_id):
    """Avoid drawing over other apps when the taskbar is obscured."""
    if sys.platform != "win32":
        return False
    rect = wintypes.RECT()
    if not user32.GetWindowRect(window_id, ctypes.byref(rect)):
        return False
    point = wintypes.POINT((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
    hit = user32.WindowFromPoint(point)
    if not hit:
        return False
    root = user32.GetAncestor(hit, 2) or hit  # GA_ROOT
    if root == window_id:
        return True
    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(root, name, len(name))
    if name.value not in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        return False
    # Explorer can raise the taskbar above an already-visible tool window when
    # the overflow opens. Hit testing skips our click-through window either way.
    above = user32.GetWindow(window_id, 3)  # GW_HWNDPREV
    while above:
        if above == root:
            user32.SetWindowPos(window_id, -1, 0, 0, 0, 0, 0x13)  # TOPMOST, no move/size/activation
            break
        above = user32.GetWindow(above, 3)
    return True


def adjacent_tray_area(first, second, screen, work_area):
    """Return a horizontal span only when both slots are on the taskbar."""
    left, right = sorted((first, second), key=lambda rect: rect.x())
    if left.isEmpty() or right.isEmpty() or left.right() >= right.left():
        return QRect()
    area = left.united(right)
    if not screen.contains(area) or work_area.intersects(area):
        return QRect()
    if area.height() > max(left.height(), right.height()) + 2:
        return QRect()
    if right.left() - left.right() - 1 > 4:
        return QRect()
    return area


def tray_area(icons):
    if sys.platform != "win32":
        return QRect()
    first, second = (icon.geometry() for icon in icons)
    screen = QGuiApplication.screenAt(first.center()) if not first.isEmpty() else None
    if screen is None:
        return QRect()
    return adjacent_tray_area(first, second, screen.geometry(), screen.availableGeometry())


class BatteryWidget(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("PeriHub battery widget")
        self.percent = None

    def display(self, area, percent):
        if self.geometry() != area:
            self.setGeometry(area)
        if not covers_taskbar(int(self.winId())):
            return False
        if self.percent != percent:
            self.percent = percent
            self.update()
        if not self.isVisible():
            self.show()
        return True

    def paintEvent(self, event):
        if self.percent is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(Qt.GlobalColor.white)
        font = QFont("Segoe UI")
        font.setPixelSize(32)
        text = QPainterPath()
        text.addText(0, 0, font, f"{self.percent}%")
        bounds = text.boundingRect()

        # The mouse outline occupies 18/36 of its drawing box horizontally.
        # Size the glyphs against the visible outline, not that drawing box.
        gap = 6
        ratio = 18 / 29
        text_ratio = bounds.width() / bounds.height()
        glyph_height = min(19, self.height() - 2, (self.width() - gap - 2) / (ratio + text_ratio))
        if glyph_height <= 0:
            painter.end()
            return
        mouse_width = glyph_height * ratio
        text_scale = glyph_height * 0.82 / bounds.height()
        text_width = bounds.width() * text_scale
        left = (self.width() - mouse_width - gap - text_width) / 2
        center_y = self.height() / 2
        mouse_box = glyph_height * 36 / 29
        draw_symbol(painter, "mouse",
                    QRectF(left + (mouse_width - mouse_box) / 2,
                           center_y - mouse_box * 17.5 / 36,
                           mouse_box, mouse_box), color.name())
        painter.translate(left + mouse_width + gap, center_y)
        painter.scale(text_scale, text_scale)
        painter.translate(-bounds.left(), -bounds.center().y())
        painter.fillPath(text, color)
