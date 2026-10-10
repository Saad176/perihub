"""Small vector controls for the reference-style Devices window."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


def draw_symbol(painter, kind, rect, color="#e3e8ea"):
    painter.save()
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 36, rect.height() / 36)
    painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "mouse":
        painter.drawRoundedRect(QRectF(9, 3, 18, 29), 9, 9)
        painter.drawLine(QPointF(18, 3), QPointF(18, 11))
        painter.drawRoundedRect(QRectF(16.8, 8, 2.4, 6), 1.2, 1.2)
    elif kind == "keyboard":
        painter.drawRoundedRect(QRectF(3, 8, 30, 20), 2, 2)
        painter.setPen(QPen(QColor(color), 1.4))
        for y in (13, 17, 21):
            for x in (8, 13, 18, 23, 28):
                painter.drawPoint(QPointF(x, y))
        painter.drawLine(QPointF(10, 25), QPointF(26, 25))
    elif kind == "battery":
        painter.drawRect(QRectF(4, 11, 25, 14))
        painter.drawRect(QRectF(29, 15, 3, 6))
        painter.drawLine(QPointF(12, 18), QPointF(21, 18))
    elif kind == "info":
        painter.drawEllipse(QRectF(5, 5, 26, 26))
        painter.drawPoint(QPointF(18, 12))
        painter.drawLine(QPointF(18, 17), QPointF(18, 25))
    elif kind == "scan":
        painter.drawLine(QPointF(18, 6), QPointF(18, 30))
        painter.drawLine(QPointF(6, 18), QPointF(30, 18))
    elif kind == "more":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        for y in (10, 18, 26):
            painter.drawEllipse(QPointF(18, y), 1.5, 1.5)
    elif kind == "close":
        painter.drawLine(QPointF(10, 10), QPointF(26, 26))
        painter.drawLine(QPointF(26, 10), QPointF(10, 26))
    elif kind == "minimize":
        painter.drawLine(QPointF(10, 25), QPointF(26, 25))
    elif kind == "maximize":
        painter.drawRect(QRectF(10, 10, 16, 16))
    elif kind == "pin":
        path = QPainterPath(QPointF(21, 7))
        for x, y in ((28, 14), (24, 15), (20, 21), (17, 18), (13, 22), (11, 20), (15, 16), (12, 13), (18, 10), (21, 7)):
            path.lineTo(x, y)
        painter.drawPath(path)
        painter.drawLine(QPointF(15, 22), QPointF(9, 29))
    painter.restore()


class Symbol(QWidget):
    def __init__(self, kind, width=30, height=30, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_symbol(painter, self.kind, QRectF(self.rect()))


class IconButton(QPushButton):
    def __init__(self, kind, tooltip, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setToolTip(tooltip)
        self.setFixedSize(34, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.underMouse() or self.isChecked():
            painter.fillRect(self.rect(), QColor("#713038" if self.kind == "close" else "#13232b"))
        side = min(22, self.width(), self.height())
        draw_symbol(painter, self.kind, QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side), "#e0e6e9" if self.underMouse() else "#aeb7bc")


class TitleBar(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setFixedHeight(34)
        self.setObjectName("titlebar")
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 2, 0)
        row.setSpacing(0)
        title = QLabel("DEVICES")
        title.setStyleSheet("color:#e5e8ea; font:16px Consolas;")
        row.addWidget(title)
        row.addStretch()
        self.pin = IconButton("pin", "Keep on top", self)
        self.pin.setCheckable(True)
        self.pin.toggled.connect(self.set_pinned)
        self.minimize = IconButton("minimize", "Minimize", self)
        self.minimize.clicked.connect(owner.showMinimized)
        self.maximize = IconButton("maximize", "Maximize / restore", self)
        self.maximize.clicked.connect(self.toggle_maximized)
        self.close_button = IconButton("close", "Hide in tray", self)
        self.close_button.clicked.connect(owner.close)
        for button in (self.pin, self.minimize, self.maximize, self.close_button):
            row.addWidget(button)

    def set_pinned(self, pinned):
        self.owner.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, pinned)
        self.owner.show()

    def toggle_maximized(self):
        self.owner.showNormal() if self.owner.isMaximized() else self.owner.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.owner.windowHandle():
            self.owner.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()


class DeviceButton(QPushButton):
    def __init__(self, symbol, name, kind):
        super().__init__()
        self.name, self.kind = name, kind
        self.connected = False
        self.selected = False
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(name)

    def update_appearance(self):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.selected:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor("#0b2231"))
            gradient.setColorAt(1, QColor("#06131b"))
            p.setBrush(gradient)
            p.setPen(QPen(QColor("#4caceb"), 1))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 1, 1)
        elif self.underMouse():
            p.fillRect(self.rect(), QColor("#0a171c"))
        color = "#e2e7e9" if self.connected else "#929a9d"
        draw_symbol(p, "mouse" if self.kind == "Mouse" else "keyboard", QRectF(9, 13, 34, 34), color)
        font = QFont("Consolas")
        font.setPixelSize(14)
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(QRectF(57, 9, self.width() - 63, 22), Qt.AlignmentFlag.AlignVCenter, self.name)
        p.setPen(QColor("#abb3b7" if self.connected else "#747d82"))
        p.drawText(QRectF(57, 31, self.width() - 63, 20), Qt.AlignmentFlag.AlignVCenter, self.kind)


class StageButton(QPushButton):
    def __init__(self, color):
        super().__init__()
        self.color = color
        self.setFixedSize(18, 22)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self.color if self.isEnabled() or self.text() == "Active" else "#4c585e"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(2, 4, 14, 14), 1, 1)
        if self.text() == "Active":
            p.setPen(QPen(QColor("#d2ecff"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(1, 3, 16, 16), 2, 2)
