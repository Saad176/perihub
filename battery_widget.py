"""Combine PeriHub's adjacent notification slots into one battery readout."""

import sys

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath

from ui_components import draw_symbol


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


class BatteryWidget:
    def __init__(self):
        self.surface = None

    def display(self, area, percent):
        screen = QGuiApplication.screenAt(area.center())
        if sys.platform != "win32" or screen is None:
            return False
        if self.surface is None:
            from windows_battery_surface import BatterySurface
            self.surface = BatterySurface()
        scale = screen.devicePixelRatio()
        # On Windows Qt scales offsets and sizes within each screen, while
        # keeping the virtual desktop coordinates of each screen's origin.
        origin = screen.geometry().topLeft()
        left = origin.x() + round((area.x() - origin.x()) * scale)
        top = origin.y() + round((area.y() - origin.y()) * scale)
        width = round(area.width() * scale)
        height = round(area.height() * scale)
        return self.surface.display(
            (left, top, width, height), (width, height, scale, percent),
            lambda: render_battery(width, height, scale, percent),
        )

    def hide(self):
        if self.surface is not None:
            self.surface.hide()

    def close(self):
        if self.surface is not None:
            self.surface.close()


def render_battery(width, height, scale, percent):
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(scale)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(Qt.GlobalColor.white)
    font = QFont("Segoe UI")
    font.setPixelSize(32)
    text = QPainterPath()
    text.addText(0, 0, font, f"{percent}%")
    bounds = text.boundingRect()

    # The mouse outline occupies 18/36 of its drawing box horizontally.
    # Size the glyphs against the visible outline, not that drawing box.
    gap = 6
    ratio = 18 / 29
    text_ratio = bounds.width() / bounds.height()
    glyph_height = min(17, (height / scale) - 2, ((width / scale) - gap - 2) / (ratio + text_ratio))
    if glyph_height <= 0:
        painter.end()
        return image
    mouse_width = glyph_height * ratio
    text_scale = glyph_height * 0.82 / bounds.height()
    text_width = bounds.width() * text_scale
    left = ((width / scale) - mouse_width - gap - text_width) / 2
    center_y = (height / scale) / 2
    mouse_box = glyph_height * 36 / 29
    draw_symbol(painter, "mouse",
                QRectF(left + (mouse_width - mouse_box) / 2,
                       center_y - mouse_box * 17.5 / 36,
                       mouse_box, mouse_box), color.name())
    painter.translate(left + mouse_width + gap, center_y)
    painter.scale(text_scale, text_scale)
    painter.translate(-bounds.left(), -bounds.center().y())
    painter.fillPath(text, color)
    painter.end()
    return image
