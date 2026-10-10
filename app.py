import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hid

from PySide6.QtCore import Qt, QTimer, QSettings, QObject, Signal
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap, QIntValidator
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QSlider,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget, QComboBox, QButtonGroup,
    QGridLayout, QSizeGrip, QSizePolicy,
)
from ui_components import DeviceButton, IconButton, StageButton, Symbol, TitleBar
from mouse_battery import BatteryMonitor


BG = "#050b0d"
PANEL = "#071013"
LINE = "#526065"
MUTED = "#a4acb0"
BLUE = "#4caceb"
GREEN = "#55d076"
APP_VERSION = "0.6.2"
_FONTS_LOADED = False


def load_system_fonts():
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return
    for filename in ("consola.ttf", "consolab.ttf"):
        path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    _FONTS_LOADED = True


class ScanEvents(QObject):
    finished = Signal(dict)


class MouseEvents(QObject):
    finished = Signal(object)


class SensorEvents(QObject):
    finished = Signal(str, object)


class CommandEvents(QObject):
    finished = Signal(str, object, object, object)


class KeyboardEvents(QObject):
    error = Signal(str)
    restored = Signal(object)


class ScrollSafeCombo(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class ScrollSafeSlider(QSlider):
    def wheelEvent(self, event):
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if parent is not None:
            bar = parent.verticalScrollBar()
            bar.setValue(bar.value() - event.angleDelta().y() // 3)
            event.accept()
        else:
            event.ignore()


class DpiSlider(ScrollSafeSlider):
    """Show the actual DPI position, with a fine 50-DPI drag rather than jumps."""
    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(50, 26000)
        self.setSingleStep(50)
        self.setPageStep(50)
        self.anchor = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.anchor = (event.position().x(), self.value())
            self.setSliderDown(True)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.anchor is not None:
            offset = round((event.position().x() - self.anchor[0]) / 4) * 50
            self.setValue(max(50, min(26000, self.anchor[1] + offset)))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.anchor is not None:
            self.anchor = None
            self.setSliderDown(False)
            event.accept()


class KeyboardPreview(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.started = time.monotonic()
        self.setFixedHeight(54)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.set_mode(owner.keyboard_mode)

    def set_mode(self, mode):
        self.started = time.monotonic()
        if mode in ("breathe", "rainbow", "soft_rainbow", "wave", "spectrum", "twinkle"):
            self.timer.start(100)
        else:
            self.timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101920"))
        painter.setPen(QPen(QColor(LINE), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        mode = self.owner.keyboard_mode
        if mode in (None, "onboard"):
            painter.setPen(QColor(MUTED))
            painter.setFont(QFont("Consolas", 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "ONBOARD PROFILE")
            return
        from keyboard_direct import render_frame
        color = self.owner.color
        pixels = render_frame(mode, (color.red(), color.green(), color.blue()),
                              self.owner.keyboard_brightness / 100,
                              time.monotonic() - self.started,
                              self.owner.keyboard_speed / 50)
        count = 28
        gap = 2
        width = (self.width() - 20 - gap * (count - 1)) / count
        for column in range(count):
            red, green, blue = pixels[min(167, column * 6)]
            painter.fillRect(int(10 + column * (width + gap)), 10, max(1, int(width)), 34, QColor(red, green, blue))


class DpiEdit(QLineEdit):
    step_requested = Signal(int)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.step_requested.emit(50)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.step_requested.emit(-50)
            event.accept()
        else:
            super().keyPressEvent(event)


def detect_devices():
    keyboard_found = False
    mouse = None
    try:
        keyboard = hid.enumerate(0x1B1C, 0x1B2D)
        keyboard_found = any(d.get("interface_number") == 1 and d.get("usage_page") == 0xFFC2 for d in keyboard)
    except (OSError, RuntimeError):
        pass
    try:
        from mouse_direct import find_device
        mouse = find_device()
    except (OSError, RuntimeError):
        pass
    return {
        "keyboard": keyboard_found,
        "mouse": mouse is not None,
        "mouse_connection": mouse["connection"] if mouse else None,
    }


def icon():
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(BLUE), 4))
    p.setBrush(QColor(BG))
    p.drawRoundedRect(5, 5, 54, 54, 8, 8)
    p.drawLine(17, 23, 47, 23)
    p.drawLine(17, 33, 47, 33)
    p.drawLine(17, 43, 38, 43)
    p.end()
    return QIcon(pix)


def tray_icon():
    """Monochrome outline, with transparent interior and DPI-sized rasters."""
    result = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 16, size / 16)
        pen = QPen(QColor("#ffffff"), 1.25)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(1.75, 1.75, 12.5, 12.5, 2, 2)
        painter.drawLine(5, 5, 11, 5)
        painter.drawLine(5, 8, 11, 8)
        painter.drawLine(5, 11, 9, 11)
        painter.end()
        result.addPixmap(pix)
    return result


def label(text, size=12, color="#e7ebee", weight=False):
    widget = QLabel(text)
    f = QFont("Consolas")
    f.setPixelSize(round(size * 1.17))
    f.setBold(weight)
    widget.setFont(f)
    widget.setStyleSheet(f"color: {color};")
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        load_system_fonts()
        self.setWindowTitle(f"Devices {APP_VERSION}")
        self.setWindowIcon(icon())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.resize(620, 800)
        self.setMinimumSize(620, 640)
        self.selected = "mouse"
        self.color = QColor("#4caceb")
        self.keyboard_mode = "onboard"
        self.keyboard_resume_mode = None
        self.keyboard_brightness = 80
        self.keyboard_speed = 50
        self.keyboard_events = KeyboardEvents()
        self.keyboard_events.error.connect(self.on_keyboard_error)
        self.keyboard_events.restored.connect(self.on_keyboard_restored)
        from keyboard_direct import KeyboardAnimator
        self.keyboard_animator = KeyboardAnimator(lambda exc: self.keyboard_events.error.emit(str(exc)))
        self.mouse_message = ""
        self.mouse_battery_label = None
        self.battery_reading = None
        self.battery_events = MouseEvents()
        self.battery_events.finished.connect(self.on_battery_read)
        self.battery_monitor = BatteryMonitor(self.battery_events.finished.emit)
        self.last_dpi_sent = {}
        self.settings = QSettings("Devices", "Device Control")
        self.selected = str(self.settings.value("ui/device", "mouse"))
        if self.selected not in ("mouse", "keyboard"):
            self.selected = "mouse"
        self.preferred_device = self.selected
        self.mouse_tab = str(self.settings.value("ui/mouse_tab", "DPI"))
        if self.mouse_tab not in ("DPI", "Polling", "Sensor", "Timing"):
            self.mouse_tab = "DPI"
        self.state = {"keyboard": False, "mouse": False}
        self.scan_events = ScanEvents()
        self.scan_events.finished.connect(self.on_scan_finished)
        self.mouse_events = MouseEvents()
        self.mouse_events.finished.connect(self.on_mouse_read)
        self.sensor_events = SensorEvents()
        self.sensor_events.finished.connect(self.on_sensor_written)
        self.sensor_pending = set()
        self.mouse_reading = False
        self.mouse_ready = False
        self.next_mouse_retry = 0
        self.command_events = CommandEvents()
        self.command_events.finished.connect(self.on_mouse_command)
        self.command_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mouse-command")
        self.command_pending = 0
        self.mouse_read_thread = None
        self.mouse_state = None
        self.scanning = False
        self.scan_stop = threading.Event()
        self.scan_thread = None
        QApplication.instance().aboutToQuit.connect(self.stop_scanner)
        QApplication.instance().aboutToQuit.connect(self.stop_keyboard)

        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet("""
            QWidget#root { background:#050b0d; color:#e7ebee; font:13px Consolas; border:1px solid #9ca7aa; }
            QWidget#content, QScrollArea, QScrollArea > QWidget > QWidget { background:#050b0d; color:#e7ebee; border:0; }
            QWidget#titlebar { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0b1113,stop:1 #020607); border:0; border-bottom:1px solid #7d888c; }
            QFrame#sidebar { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #070f12,stop:1 #030809); border:0; border-right:1px solid #657276; }
            QFrame#rule { background:#4c585c; border:0; max-height:1px; }
            QPushButton { color:#d8dfe2; font:12px Consolas; }
            QPushButton#tab { color:#b5bdc1; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #101618,stop:1 #05090a); border:1px solid #616c70; border-radius:2px; padding:7px 3px; }
            QPushButton#tab:checked { color:#04121c; background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #69baf0,stop:1 #2996db); border-color:#4caceb; }
            QPushButton#tab:hover, QPushButton#action:hover, QPushButton#smallAction:hover { border-color:#78bde8; }
            QPushButton#action { color:#dce3e6; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #171e21,stop:1 #080d0f); border:1px solid #738087; border-radius:2px; padding:6px 10px; }
            QPushButton#action:disabled, QPushButton#smallAction:disabled { color:#68737a; border-color:#354048; }
            QPushButton#smallAction { color:#dce3e6; background:#0b1215; border:1px solid #566367; border-radius:2px; padding:3px 5px; font:12px Consolas; }
            QPushButton#overflow { color:#bac4c9; background:transparent; border:0; padding:0; font:18px Consolas; }
            QComboBox { color:#dfe5e8; background:#080e10; border:1px solid #59656b; border-radius:2px; padding:3px 6px; font:12px Consolas; }
            QComboBox QAbstractItemView { background:#111a20; color:#e7ebee; selection-background-color:#153447; }
            QLineEdit { color:#e7ebee; background:#080e10; border:1px solid #59656b; border-radius:2px; padding:3px 4px; font:12px Consolas; }
            QLineEdit:focus { border-color:#4caceb; }
            QScrollBar:vertical { background:#060c0f; width:5px; margin:0; }
            QScrollBar::handle:vertical { background:#3a484f; min-height:24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QSlider::groove:horizontal { height:5px; background:#42494c; }
            QSlider::sub-page:horizontal { background:#4caceb; }
            QSlider::handle:horizontal { background:#e0e9ef; width:11px; margin:-3px 0; border-radius:5px; }
            QFrame#dpiRow { border:0; border-bottom:1px solid #344146; background:transparent; }
            QFrame#dpiRow[active="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #081116,stop:.5 #102b3b,stop:1 #07151d); }
            QLabel { background:transparent; border:0; }
        """)
        self.setCentralWidget(root)
        frame = QVBoxLayout(root)
        frame.setContentsMargins(1, 1, 1, 1)
        frame.setSpacing(0)
        self.titlebar = TitleBar(self)
        frame.addWidget(self.titlebar)
        body = QWidget()
        outer = QHBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        frame.addWidget(body, 1)
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(12, 12)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(6, 12, 6, 12)
        side.setSpacing(8)
        self.mouse_button = DeviceButton("◉", "Aula SC900 Pro", "Mouse")
        self.keyboard_button = DeviceButton("▦", "Corsair K95 Platinum", "Keyboard")
        self.mouse_button.clicked.connect(lambda: self.show_device("mouse"))
        self.keyboard_button.clicked.connect(lambda: self.show_device("keyboard"))
        side.addWidget(self.mouse_button)
        side.addWidget(self.keyboard_button)
        self.mouse_button.hide()
        self.keyboard_button.hide()
        scan = QPushButton("     Add Device (Scanner)")
        scan.setStyleSheet("QPushButton {color:#dce3e6; background:transparent; border:0; text-align:left; font:14px Consolas; padding:10px 0;}")
        scan_symbol = Symbol("scan", 30, 30, scan)
        scan_symbol.move(10, 4)
        scan.clicked.connect(self.refresh_devices)
        side.addSpacing(20)
        side.addWidget(scan)
        side.addStretch()
        outer.addWidget(sidebar)

        right_panel = QWidget()
        right_panel.setObjectName("content")
        right = QVBoxLayout(right_panel)
        right.setContentsMargins(8, 10, 8, 10)
        right.setSpacing(6)
        header_host = QWidget()
        self.header = QVBoxLayout(header_host)
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.setSpacing(5)
        right.addWidget(header_host)

        content = QScrollArea()
        self.content_area = content
        content.setWidgetResizable(True)
        content.setFrameShape(QFrame.Shape.NoFrame)
        content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("content")
        self.detail = QVBoxLayout(self.content)
        self.detail.setContentsMargins(0, 4, 0, 0)
        self.detail.setSpacing(5)
        content.setWidget(self.content)
        right.addWidget(content, 1)
        outer.addWidget(right_panel, 1)

        self.tray = QSystemTrayIcon(tray_icon(), self)
        menu = QMenu()
        show_action = QAction("Open Devices", self)
        show_action.triggered.connect(self.show_from_tray)
        self.battery_tray_action = QAction("Mouse battery: unavailable", self)
        self.battery_tray_action.setEnabled(False)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(self.battery_tray_action)
        menu.addSeparator()
        import windows_startup
        self.startup_action = QAction("Start with Windows", self)
        self.startup_action.setCheckable(True)
        self.startup_action.setEnabled(windows_startup.available())
        self.startup_action.triggered.connect(self.set_windows_startup)
        menu.addAction(self.startup_action)
        menu.aboutToShow.connect(self.refresh_windows_startup)
        self.refresh_windows_startup()
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.update_mouse_battery_display()
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_devices)
        self.timer.start(3000)
        self.show_device(self.selected)
        self.refresh_devices()
        self.battery_monitor.start()

    def refresh_windows_startup(self):
        import windows_startup
        try:
            self.startup_action.setChecked(windows_startup.enabled())
        except OSError:
            self.startup_action.setChecked(False)

    def set_windows_startup(self, enabled):
        import windows_startup
        try:
            windows_startup.set_enabled(enabled)
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(self, "Windows startup", f"Could not change Windows startup: {exc}")
        self.refresh_windows_startup()

    def rule(self):
        r = QFrame()
        r.setObjectName("rule")
        r.setFixedHeight(1)
        return r

    def clear_detail(self):
        self.mouse_battery_label = None
        self.clear_layout(self.header)
        self.clear_layout(self.detail)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def refresh_devices(self):
        if self.scanning:
            return
        self.scanning = True
        self.scan_thread = threading.Thread(target=self._scan_worker)
        self.scan_thread.start()

    def _scan_worker(self):
        try:
            result = detect_devices()
        except Exception:
            result = {"keyboard": False, "mouse": False}
        if not self.scan_stop.is_set():
            self.scan_events.finished.emit(result)

    def stop_scanner(self):
        self.scan_stop.set()
        self.command_executor.shutdown(wait=True, cancel_futures=True)
        self.battery_monitor.stop()
        if self.scan_thread is not None and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)
        if self.mouse_read_thread is not None and self.mouse_read_thread.is_alive():
            self.mouse_read_thread.join(timeout=5)

    def on_scan_finished(self, new_state):
        self.scanning = False
        changed = new_state != self.state
        keyboard_reconnected = new_state["keyboard"] and not self.state["keyboard"]
        if self.state["keyboard"] and not new_state["keyboard"] and self.keyboard_mode not in (None, "onboard"):
            self.keyboard_resume_mode = self.keyboard_mode
            self.keyboard_mode = None
            threading.Thread(target=self.keyboard_animator.stop, daemon=True).start()
        if new_state.get("mouse_connection") != self.state.get("mouse_connection"):
            self.battery_reading = None
            self.mouse_state = None
            self.mouse_ready = False
            self.last_dpi_sent.clear()
            self.mouse_message = ""
        self.state = new_state
        if not new_state["mouse"]:
            self.battery_reading = None
        self.mouse_button.connected = new_state["mouse"]
        self.keyboard_button.connected = new_state["keyboard"]
        self.mouse_button.setVisible(new_state["mouse"])
        self.keyboard_button.setVisible(new_state["keyboard"])
        self.mouse_button.update_appearance()
        self.keyboard_button.update_appearance()
        self.update_mouse_battery_display()
        if changed or self.header.count() == 0:
            self.show_device(self.selected)
        if keyboard_reconnected and self.keyboard_resume_mode is not None:
            mode = self.keyboard_resume_mode
            self.keyboard_resume_mode = None
            self.keyboard_animator.set_effect(mode, (self.color.red(), self.color.green(), self.color.blue()), self.keyboard_brightness / 100, self.keyboard_speed / 50)
            self.keyboard_mode = mode
            if self.selected == "keyboard":
                self.show_device("keyboard")
        if new_state["mouse"] and not self.mouse_ready and time.monotonic() >= self.next_mouse_retry:
            self.refresh_mouse_state()

    def on_battery_read(self, reading):
        if reading is not None and reading.get("connection") not in (None, self.state.get("mouse_connection")):
            self.refresh_devices()
            return
        if reading == self.battery_reading:
            return
        self.battery_reading = reading
        self.update_mouse_battery_display()

    def update_mouse_battery_display(self):
        """Report only the battery information verified for this receiver."""
        receiver_found = self.state["mouse"]
        battery_text = "Level unavailable" if receiver_found else "Mouse unavailable"
        reading = self.battery_reading if receiver_found else None
        if reading is not None:
            battery_text = f"{reading['percent']}% ({reading['bars']}/5 bars)"
        if self.mouse_battery_label is not None:
            self.mouse_battery_label.setText(f"{reading['percent']}%" if reading is not None else "—")
            self.mouse_battery_label.setToolTip(battery_text)
            self.mouse_battery_label.setAccessibleName(f"Mouse battery: {battery_text}")
        status = battery_text if reading is not None else "unavailable"
        self.battery_tray_action.setText(f"Mouse battery: {status}")
        self.battery_tray_action.setVisible(receiver_found)
        if receiver_found:
            charge = f"{reading['percent']}%" if reading is not None else "Battery unavailable"
            connection = "USB wired" if self.state.get("mouse_connection") == "wired" else "8K receiver"
            self.tray.setToolTip(f"SC900 Pro · {charge} · {connection}")
        else:
            self.tray.setToolTip("PeriHub · K95 Platinum connected" if self.state["keyboard"] else "PeriHub · No supported devices detected")

    def show_device(self, name):
        if not self.state.get(name, False):
            name = self.preferred_device if self.state.get(self.preferred_device) else next((device for device in ("mouse", "keyboard") if self.state.get(device)), None)
        self.selected = name
        if name is not None:
            self.preferred_device = name
            self.settings.setValue("ui/device", name)
        self.mouse_button.selected = name == "mouse"
        self.keyboard_button.selected = name == "keyboard"
        self.mouse_button.update_appearance()
        self.keyboard_button.update_appearance()
        self.clear_detail()
        if name == "mouse":
            self.mouse_page()
            if self.state["mouse"]:
                self.refresh_mouse_state()
        elif name == "keyboard":
            self.keyboard_page()
        else:
            self.header.addWidget(label("No supported devices detected", 15))
            message = label("Connect an AULA SC900 Pro or Corsair K95 RGB Platinum.\n\nOther mice and keyboards are not supported by this version.", 12, MUTED)
            message.setWordWrap(True)
            message.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.detail.addWidget(message)
            self.detail.addStretch()
        self.content_area.verticalScrollBar().setValue(0)

    def heading(self, title, connected, receiver_only=False):
        self.header.addWidget(label(title, 19))
        row = QHBoxLayout()
        state_text = "●  Receiver detected" if receiver_only and connected else "●  Connected" if connected else "○  Not detected"
        self.connection_label = label(state_text, 12, GREEN if connected else MUTED)
        row.addWidget(self.connection_label)
        row.addStretch()
        if receiver_only:
            row.addWidget(Symbol("battery", 24, 24))
            self.mouse_battery_label = label("—", 11, MUTED)
            self.mouse_battery_label.setAccessibleName("Mouse battery unavailable")
            row.addWidget(self.mouse_battery_label)
            self.update_mouse_battery_display()
        self.header.addLayout(row)

    def tabs(self, names, active):
        row = QHBoxLayout()
        row.setSpacing(3)
        self.tab_buttons = {}
        for name in names:
            button = QPushButton(name)
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setChecked(name == active)
            button.clicked.connect(lambda checked=False, value=name: self.show_tab(value))
            self.tab_buttons[name] = button
            row.addWidget(button)
        holder = QWidget()
        holder.setLayout(row)
        self.header.addWidget(holder)

    def show_tab(self, tab):
        if self.selected == "mouse":
            self.mouse_tab = tab
            self.settings.setValue("ui/mouse_tab", tab)
            self.mouse_stack.setCurrentIndex(["DPI", "Polling", "Sensor", "Timing"].index(tab))
            for name, button in self.tab_buttons.items():
                button.setChecked(name == tab)
        else:
            self.keyboard_tab = tab

    def mouse_page(self):
        self.heading("Aula SC900 Pro", self.state["mouse"], receiver_only=True)
        if self.state["mouse"] and self.state.get("mouse_connection") == "wired":
            self.connection_label.setText("● Connected via USB")
        hero = QWidget()
        hero.setFixedHeight(220)
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(6)
        mouse_image = Path(__file__).parent / "assets" / "sc900-pro-oem.png"
        photo = QLabel()
        photo.setFixedWidth(168)
        photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if mouse_image.is_file():
            photo.setPixmap(QPixmap(str(mouse_image)).scaled(168, 210, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        hero_row.addWidget(photo)
        specs = QGridLayout()
        specs.setContentsMargins(0, 18, 0, 42)
        specs.setHorizontalSpacing(5)
        specs.setVerticalSpacing(7)
        self.mouse_specs = {}
        connection = "USB wired" if self.state.get("mouse_connection") == "wired" else "2.4 GHz"
        for index, (name, value) in enumerate((("Model", "SC900 Pro"), ("Connection", connection), ("Sensor", "PAW3395"), ("Max DPI", "26000"), ("Polling Rate", "—"), ("LOD", "—"))):
            specs.addWidget(label(name, 11, MUTED), index, 0)
            field = label(value, 11)
            self.mouse_specs[name] = field
            specs.addWidget(field, index, 1)
        hero_row.addLayout(specs, 1)
        self.header.addWidget(hero)
        self.tabs(["DPI", "Polling", "Sensor", "Timing"], getattr(self, "mouse_tab", "DPI"))
        self.header.addWidget(self.rule())
        self.mouse_stack = QStackedWidget()
        self.mouse_stack.setEnabled(self.mouse_ready)
        dpi_page = QWidget()
        dpi_layout = QVBoxLayout(dpi_page)
        dpi_layout.setContentsMargins(0, 2, 0, 0)
        dpi_layout.setSpacing(3)
        section_heading = QHBoxLayout()
        section_heading.addWidget(label("DPI Stages (Up to 6)", 12))
        section_heading.addStretch()
        reload_button = QPushButton("Refresh")
        reload_button.setObjectName("overflow")
        reload_button.setStyleSheet("QPushButton {font:11px Consolas; color:#b2bec5; background:transparent; border:0;}")
        reload_button.clicked.connect(self.refresh_mouse_state)
        section_heading.addWidget(reload_button)
        dpi_layout.addLayout(section_heading)
        dpi_layout.addWidget(self.rule())
        self.dpi_fields = {}
        self.dpi_rows = {}
        self.dpi_use = {}
        self.dpi_value_labels = {}
        for number, (value, color) in enumerate([(400, "#e53b2d"), (800, "#1499ed"), (1600, "#52d86a"), (3200, "#f2cd45"), (6400, "#b451e9"), (26000, "#e7ebee")], 1):
            value = int(self.settings.value(f"mouse/dpi_stage_{number}", value))
            dpi_layout.addWidget(self.make_dpi_row(number, value, color))
        dpi_layout.addSpacing(18)
        dpi_layout.addWidget(label("DPI Configuration", 12))
        stage_row = QHBoxLayout()
        stage_row.addWidget(label("Enabled stages :", 11, MUTED))
        self.stage_count_combo = ScrollSafeCombo()
        self.stage_count_combo.addItems([str(n) for n in range(1, 7)])
        self.stage_count_combo.setEnabled(self.state["mouse"])
        self.stage_count_combo.currentIndexChanged.connect(lambda index: self.apply_stage_count(index + 1))
        stage_row.addWidget(self.stage_count_combo, 1)
        dpi_layout.addLayout(stage_row)
        dpi_layout.addSpacing(10)
        note = label("Use the mouse DPI button to cycle stages.\nDrag finely in 50 DPI steps, or type a value.", 10, MUTED)
        note.setWordWrap(True)
        dpi_layout.addWidget(note)
        dpi_layout.addStretch()
        polling_page = QWidget()
        polling_layout = QVBoxLayout(polling_page)
        polling_layout.setContentsMargins(0, 8, 0, 0)
        polling_layout.setSpacing(10)
        polling_layout.addWidget(label("POLLING RATE", 13, weight=True))
        polling_layout.addWidget(label("Select the mouse report rate", 10, MUTED))
        self.poll_buttons = {}
        for rates in ((125, 250, 500), (1000, 2000), (4000, 8000)):
            rate_row = QHBoxLayout()
            for hz in rates:
                button = QPushButton(f"{hz} Hz")
                button.setObjectName("tab")
                button.setCheckable(True)
                button.setEnabled(self.state["mouse"])
                button.clicked.connect(lambda checked=False, value=hz: self.apply_mouse_polling(value))
                rate_row.addWidget(button)
                self.poll_buttons[hz] = button
            polling_layout.addLayout(rate_row)
        polling_layout.addWidget(label("Rate changes briefly pause the mouse", 9, MUTED))
        polling_layout.addStretch()
        sensor_page = QWidget()
        sensor_layout = QVBoxLayout(sensor_page)
        sensor_layout.setContentsMargins(0, 8, 0, 0)
        sensor_layout.setSpacing(8)
        sensor_layout.addWidget(label("SENSOR", 13, weight=True))
        self.sensor_buttons = {}
        self.sensor_groups = {}
        for title, key, options in (("Sensor mode", "sensor_mode", (("LP", 0), ("HP", 1), ("Corded", 2))), ("Lift-off distance", "lod", (("1 mm", 0), ("2 mm", 1))), ("Ripple control", "ripple", (("Off", 0), ("On", 1))), ("Angle snapping", "angle", (("Off", 0), ("On", 1))), ("Motion Sync", "motion", (("Off", 0), ("On", 1)))):
            sensor_layout.addWidget(label(title, 10, MUTED))
            row = QHBoxLayout()
            self.sensor_buttons[key] = {}
            group = QButtonGroup(sensor_page)
            group.setExclusive(True)
            self.sensor_groups[key] = group
            for text_value, value in options:
                button = QPushButton(text_value)
                button.setObjectName("tab")
                button.setCheckable(True)
                button.setEnabled(self.state["mouse"])
                button.clicked.connect(lambda checked=False, setting=key, selection=value: self.apply_sensor(setting, selection))
                row.addWidget(button)
                self.sensor_buttons[key][value] = button
                group.addButton(button, value)
            sensor_layout.addLayout(row)
        sensor_layout.addStretch()
        timing_page = QWidget()
        timing_layout = QVBoxLayout(timing_page)
        timing_layout.setContentsMargins(0, 8, 0, 0)
        timing_layout.setSpacing(10)
        timing_layout.addWidget(label("TIMING", 13, weight=True))
        self.timing_fields = {}
        for title, key, unit, minimum, maximum in (("Debounce", "debounce_ms", "ms", 1, 30), ("Dormancy", "dormancy_s", "seconds", 15, 1800)):
            row = QHBoxLayout()
            row.addWidget(label(title, 11, MUTED), 1)
            field = QLineEdit()
            field.setValidator(QIntValidator(minimum, maximum, field))
            field.setFixedWidth(75)
            field.setEnabled(self.state["mouse"])
            self.timing_fields[key] = field
            row.addWidget(field)
            row.addWidget(label(unit, 10, MUTED))
            button = QPushButton("Apply")
            button.setObjectName("smallAction")
            button.setEnabled(self.state["mouse"])
            button.clicked.connect(lambda checked=False, setting=key: self.apply_timing(setting))
            row.addWidget(button)
            timing_layout.addLayout(row)
        timing_layout.addStretch()
        self.mouse_stack.addWidget(dpi_page)
        self.mouse_stack.addWidget(polling_page)
        self.mouse_stack.addWidget(sensor_page)
        self.mouse_stack.addWidget(timing_page)
        self.mouse_stack.setCurrentIndex(["DPI", "Polling", "Sensor", "Timing"].index(getattr(self, "mouse_tab", "DPI")))
        self.detail.addWidget(self.mouse_stack, 1)
        self.mouse_status_label = label(self.mouse_message, 11, GREEN, True)
        self.mouse_status_label.setWordWrap(True)
        self.mouse_status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.mouse_status_label.setVisible(bool(self.mouse_message))
        self.detail.addWidget(self.mouse_status_label)
        if self.mouse_state:
            self.populate_mouse_state(self.mouse_state)

    def make_dpi_row(self, stage, value, color):
        holder = QFrame()
        holder.setObjectName("dpiRow")
        holder.setFixedHeight(36)
        self.dpi_rows[stage] = holder
        row = QHBoxLayout(holder)
        row.setContentsMargins(4, 2, 3, 2)
        row.setSpacing(4)
        use_button = StageButton(color)
        use_button.setText("Use")
        use_button.setToolTip(f"Select DPI stage {stage}")
        use_button.setEnabled(self.state["mouse"])
        use_button.clicked.connect(lambda checked=False, s=stage: self.apply_mouse_stage(s))
        row.addWidget(use_button)
        self.dpi_use[stage] = use_button
        number = label(str(stage), 12)
        number.setFixedWidth(15)
        row.addWidget(number)
        summary = label(str(value), 11)
        summary.setFixedWidth(101)
        self.dpi_value_labels[stage] = summary
        row.addWidget(summary)
        field = DpiEdit(str(value))
        field.setValidator(QIntValidator(50, 26000, field))
        field.setFixedWidth(49)
        field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        field.setEnabled(self.state["mouse"])
        self.dpi_fields[stage] = field
        slider = DpiSlider()
        slider.setValue(value)
        slider.setEnabled(self.state["mouse"])
        slider.setToolTip("Drag: 50 DPI per 4 pixels. Arrow keys: 50 DPI.")
        slider.valueChanged.connect(lambda dpi, f=field, l=summary: (f.setText(str(dpi)), l.setText(str(dpi))))
        slider.sliderReleased.connect(lambda s=stage, f=field, c=slider: self.commit_dpi(s, f, c))
        row.addWidget(slider, 1)
        row.addWidget(field)
        more = IconButton("more", "Stage actions")
        more.setObjectName("overflow")
        more.setFixedSize(16, 26)
        more.setEnabled(self.state["mouse"])
        more.setToolTip("Stage actions")
        menu = QMenu(more)
        for title, delta in (("Increase by 50 DPI", 50), ("Decrease by 50 DPI", -50)):
            action = menu.addAction(title)
            action.triggered.connect(lambda checked=False, s=stage, f=field, c=slider, step=delta: self.commit_dpi(s, f, c, int(f.text() or 50) + step))
        select = menu.addAction("Use this stage")
        select.triggered.connect(lambda checked=False, s=stage: self.apply_mouse_stage(s))
        more.clicked.connect(lambda: menu.exec(more.mapToGlobal(more.rect().bottomLeft())))
        row.addWidget(more)
        field.editingFinished.connect(lambda s=stage, f=field, c=slider: self.commit_dpi(s, f, c))
        field.step_requested.connect(lambda step, s=stage, f=field, c=slider: self.commit_dpi(s, f, c, int(f.text() or 50) + step))
        return holder

    def apply_mouse_stage(self, stage):
        self.queue_mouse_command("stage", (stage,))

    def apply_mouse_polling(self, hz):
        self.queue_mouse_command("polling", (hz,))

    def queue_mouse_command(self, kind, values):
        if not self.state["mouse"] or self.scan_stop.is_set():
            return
        from mouse_commands import execute
        connection = self.state.get("mouse_connection")
        self.command_pending += 1
        self.set_mouse_message("Applying mouse settings…")
        future = self.command_executor.submit(execute, kind, values, connection)
        def completed(task):
            if self.scan_stop.is_set():
                return
            try:
                result = task.result()
            except Exception as exc:
                result = exc
            self.command_events.finished.emit(kind, values, connection, result)
        future.add_done_callback(completed)

    def on_mouse_command(self, kind, values, connection, result):
        self.command_pending = max(0, self.command_pending - 1)
        if connection != self.state.get("mouse_connection"):
            return
        if isinstance(result, Exception):
            self.set_mouse_message(f"Could not apply mouse setting: {result}")
        else:
            if kind == "dpi":
                stage, dpi = values
                self.last_dpi_sent[stage] = dpi
                self.settings.setValue(f"mouse/dpi_stage_{stage}", dpi)
            if self.command_pending == 0:
                self.set_mouse_message("Mouse setting verified")
        if self.command_pending == 0:
            self.refresh_mouse_state()

    def set_mouse_message(self, message):
        self.mouse_message = message
        if self.selected == "mouse":
            self.mouse_status_label.setText(message)
            self.mouse_status_label.setVisible(bool(message))

    def apply_mouse_dpi_value(self, stage, dpi):
        self.queue_mouse_command("dpi", (stage, dpi))

    def commit_dpi(self, stage, field, slider, requested=None):
        try:
            raw = int(field.text()) if requested is None else requested
        except ValueError:
            raw = int(self.settings.value(f"mouse/dpi_stage_{stage}", 800))
        dpi = max(50, min(26000, round(raw / 50) * 50))
        field.setText(str(dpi))
        slider.blockSignals(True)
        slider.setValue(dpi)
        slider.blockSignals(False)
        self.dpi_value_labels[stage].setText(str(dpi))
        if self.last_dpi_sent.get(stage) == dpi:
            return
        self.apply_mouse_dpi_value(stage, dpi)

    def refresh_mouse_state(self):
        if not self.state["mouse"] or self.mouse_reading or self.command_pending:
            return
        self.mouse_reading = True
        self.next_mouse_retry = time.monotonic() + 10
        self.mouse_read_thread = threading.Thread(target=self._mouse_read_worker, args=(self.state.get("mouse_connection"),), daemon=True)
        self.mouse_read_thread.start()

    def _mouse_read_worker(self, connection):
        try:
            from mouse_direct import read_state
            result = read_state()
        except Exception as exc:
            result = exc
        self.mouse_events.finished.emit({"_connection": connection, "_result": result})

    def on_mouse_read(self, result):
        self.mouse_reading = False
        if self.command_pending:
            return
        if isinstance(result, dict) and "_result" in result:
            if result["_connection"] != self.state.get("mouse_connection"):
                self.refresh_mouse_state()
                return
            result = result["_result"]
        if isinstance(result, Exception):
            self.mouse_ready = False
            self.mouse_state = None
            self.last_dpi_sent.clear()
            if self.selected == "mouse":
                self.mouse_stack.setEnabled(False)
                self.connection_label.setText("○ Mouse unavailable")
                self.set_mouse_message(f"Could not read mouse settings: {result}")
            return
        self.mouse_ready = True
        self.mouse_state = result
        if self.mouse_message.startswith("Could not read mouse settings:"):
            self.mouse_message = ""
            if self.selected == "mouse":
                self.mouse_status_label.clear()
                self.mouse_status_label.hide()
        self.last_dpi_sent = {index + 1: value for index, value in enumerate(result["dpi"])}
        if self.selected == "mouse":
            self.mouse_stack.setEnabled(True)
            self.populate_mouse_state(result)

    def populate_mouse_state(self, state):
        self.connection_label.setText("●  Connected")
        self.mouse_specs["Polling Rate"].setText(f"{state['polling_hz']} Hz")
        self.mouse_specs["LOD"].setText("1 mm" if state["lod"] == 0 else "2 mm")
        self.stage_count_combo.blockSignals(True)
        self.stage_count_combo.setCurrentIndex(state["stage_count"] - 1)
        self.stage_count_combo.blockSignals(False)
        for stage, row in self.dpi_rows.items():
            row.setVisible(stage <= state["stage_count"])
            if stage <= len(state["dpi"]):
                self.dpi_fields[stage].setText(str(state["dpi"][stage - 1]))
            active = stage == state["active_stage"]
            row.setProperty("active", active)
            row.style().unpolish(row)
            row.style().polish(row)
            if stage <= len(state["dpi"]):
                value = state["dpi"][stage - 1]
                self.dpi_value_labels[stage].setText(f"{value} (Current)" if active else str(value))
                self.dpi_value_labels[stage].setStyleSheet(f"color: {BLUE if active else '#e7ebee'};")
                slider = row.findChild(DpiSlider)
                if slider is not None and not slider.isSliderDown():
                    slider.blockSignals(True)
                    slider.setValue(value)
                    slider.blockSignals(False)
            self.dpi_use[stage].setText("Active" if active else "Use")
            self.dpi_use[stage].setEnabled(self.state["mouse"] and stage != state["active_stage"])
        for hz, button in self.poll_buttons.items():
            button.setChecked(hz == state["polling_hz"])
        for key, options in self.sensor_buttons.items():
            if key in self.sensor_pending:
                continue
            for value, button in options.items():
                button.setChecked(value == state[key])
        for key, field in self.timing_fields.items():
            if not field.hasFocus():
                field.setText(str(state[key]))

    def apply_stage_count(self, count):
        if not self.state["mouse"] or not self.mouse_state or count == self.mouse_state["stage_count"]:
            return
        self.queue_mouse_command("count", (count,))

    def apply_sensor(self, key, value):
        if key in self.sensor_pending:
            return
        self.sensor_pending.add(key)
        for button in self.sensor_buttons[key].values():
            button.setEnabled(False)
        threading.Thread(target=self._sensor_write_worker, args=(key, value), daemon=True).start()

    def _sensor_write_worker(self, key, value):
        try:
            from mouse_direct import set_sensor_setting, read_sensor_setting
            set_sensor_setting(key, value)
            result = read_sensor_setting(key)
        except Exception as exc:
            result = exc
        self.sensor_events.finished.emit(key, result)

    def on_sensor_written(self, key, result):
        self.sensor_pending.discard(key)
        if self.selected != "mouse":
            if not isinstance(result, Exception) and self.mouse_state:
                self.mouse_state[key] = result
            return
        for button in self.sensor_buttons[key].values():
            button.setEnabled(self.state["mouse"])
        if isinstance(result, Exception):
            if self.mouse_state:
                self.sensor_buttons[key][self.mouse_state[key]].setChecked(True)
            QMessageBox.warning(self, "Mouse unavailable", str(result))
            return
        if self.mouse_state:
            self.mouse_state[key] = result
        if result in self.sensor_buttons[key]:
            self.sensor_buttons[key][result].setChecked(True)
        self.set_mouse_message("Sensor setting applied")

    def apply_timing(self, key):
        field = self.timing_fields[key]
        try:
            value = int(field.text())
            self.queue_mouse_command(key, (value,))
        except Exception as exc:
            QMessageBox.warning(self, "Mouse unavailable", str(exc))

    def keyboard_page(self):
        self.heading("Corsair K95 RGB Platinum", self.state["keyboard"])
        keyboard_image = Path(__file__).parent / "assets" / "k95-platinum.png"
        photo = QLabel()
        photo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        photo.setPixmap(QPixmap(str(keyboard_image)).scaled(344, 145, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.header.addWidget(photo)
        self.header.addWidget(label("K95 Platinum  ·  USB 1B1C:1B2D", 10, MUTED))
        self.header.addWidget(self.rule())
        self.detail.addWidget(label("LIGHTING EFFECTS", 14, weight=True))
        self.detail.addWidget(label("Runs in tray; Quit restores profile", 9, MUTED))
        self.effect_buttons = {}
        self.effect_group = QButtonGroup(self.content)
        self.effect_group.setExclusive(True)
        for modes in (("onboard", "soft_rainbow", "static"), ("breathe", "rainbow", "wave"), ("spectrum", "twinkle", "off")):
            row = QHBoxLayout()
            for mode in modes:
                button = QPushButton(mode.replace("_", " ").title())
                button.setObjectName("tab")
                button.setCheckable(True)
                button.setEnabled(self.state["keyboard"])
                button.setChecked(mode == self.keyboard_mode)
                button.clicked.connect(lambda checked=False, choice=mode: self.apply_keyboard_effect(choice))
                self.effect_group.addButton(button)
                self.effect_buttons[mode] = button
                row.addWidget(button)
            self.detail.addLayout(row)
        self.keyboard_preview = KeyboardPreview(self)
        self.detail.addWidget(self.keyboard_preview)
        self.keyboard_effect_note = label("Onboard: use the keyboard brightness key; speed is saved in its profile.", 9, MUTED)
        self.keyboard_effect_note.setWordWrap(True)
        self.detail.addWidget(self.keyboard_effect_note)
        self.detail.addWidget(label("COLOR", 11, weight=True))
        color_row = QHBoxLayout()
        self.color_swatch = QLabel()
        self.color_swatch.setFixedSize(44, 38)
        self.color_swatch.setStyleSheet(f"background:{self.color.name()}; border:1px solid #65727a;")
        color_row.addWidget(self.color_swatch)
        color_button = QPushButton("Choose color")
        color_button.setObjectName("action")
        color_button.clicked.connect(self.choose_color)
        color_row.addWidget(color_button, 1)
        set_button = QPushButton("Apply static")
        set_button.setObjectName("action")
        set_button.setEnabled(self.state["keyboard"])
        set_button.clicked.connect(lambda: self.apply_keyboard_color(self.color))
        color_row.addWidget(set_button, 1)
        self.detail.addLayout(color_row)
        preset_row = QHBoxLayout()
        for hex_color in ("#4caceb", "#e34b59", "#f7bf46", "#55d076", "#a869e8", "#ffffff"):
            preset = QPushButton()
            preset.setFixedHeight(27)
            preset.setToolTip(hex_color)
            preset.setEnabled(self.state["keyboard"])
            preset.setStyleSheet(f"QPushButton {{ background:{hex_color}; border:1px solid #65727a; }} QPushButton:hover {{ border:2px solid white; }}")
            preset.clicked.connect(lambda checked=False, value=hex_color: self.choose_preset(value))
            preset_row.addWidget(preset, 1)
        self.detail.addLayout(preset_row)
        self.detail.addWidget(label("BRIGHTNESS", 11, weight=True))
        brightness_row = QHBoxLayout()
        self.brightness_slider = ScrollSafeSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(5, 100)
        self.brightness_slider.setValue(self.keyboard_brightness)
        self.brightness_slider.setEnabled(self.state["keyboard"] and self.keyboard_mode != "onboard")
        self.brightness_slider.valueChanged.connect(self.show_keyboard_brightness)
        self.brightness_slider.sliderReleased.connect(self.update_keyboard_effect)
        brightness_row.addWidget(self.brightness_slider, 1)
        self.brightness_value = label(f"{self.keyboard_brightness}%", 10, MUTED)
        self.brightness_value.setFixedWidth(42)
        brightness_row.addWidget(self.brightness_value)
        self.detail.addLayout(brightness_row)
        self.detail.addWidget(label("ANIMATION SPEED", 11, weight=True))
        speed_row = QHBoxLayout()
        self.speed_slider = ScrollSafeSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 100)
        self.speed_slider.setValue(self.keyboard_speed)
        self.speed_slider.setEnabled(self.state["keyboard"])
        self.speed_slider.valueChanged.connect(self.show_keyboard_speed)
        self.speed_slider.sliderReleased.connect(self.update_keyboard_effect)
        self.speed_slider.setEnabled(self.state["keyboard"] and self.keyboard_mode in ("breathe", "rainbow", "soft_rainbow", "wave", "spectrum", "twinkle"))
        speed_row.addWidget(self.speed_slider, 1)
        self.speed_value = label(f"{self.keyboard_speed}%", 10, MUTED)
        self.speed_value.setFixedWidth(42)
        speed_row.addWidget(self.speed_value)
        self.detail.addLayout(speed_row)
        self.keyboard_status_label = label("", 10, GREEN)
        self.keyboard_status_label.setWordWrap(True)
        self.keyboard_status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.detail.addWidget(self.keyboard_status_label)
        self.detail.addWidget(label("Direct USB lighting · no server", 9, MUTED))
        self.detail.addStretch()

    def choose_color(self):
        chosen = QColorDialog.getColor(self.color, self, "Keyboard color")
        if chosen.isValid():
            self.color = chosen
            self.color_swatch.setStyleSheet(f"background:{chosen.name()}; border:1px solid #65727a;")
            self.update_keyboard_effect()

    def choose_preset(self, hex_color):
        self.color = QColor(hex_color)
        self.color_swatch.setStyleSheet(f"background:{self.color.name()}; border:1px solid #65727a;")
        self.apply_keyboard_effect(self.keyboard_mode if self.keyboard_mode not in (None, "off", "onboard") else "static")

    def show_keyboard_brightness(self, value):
        self.keyboard_brightness = value
        self.brightness_value.setText(f"{value}%")

    def show_keyboard_speed(self, value):
        self.keyboard_speed = value
        self.speed_value.setText(f"{value}%")

    def update_keyboard_effect(self):
        if self.keyboard_mode and self.keyboard_mode != "onboard":
            self.apply_keyboard_effect(self.keyboard_mode)

    def apply_keyboard_effect(self, mode):
        if not self.state["keyboard"]:
            return
        if mode == "onboard":
            self.restore_keyboard()
            return
        self.keyboard_resume_mode = None
        try:
            self.keyboard_animator.set_effect(
                mode, (self.color.red(), self.color.green(), self.color.blue()),
                self.keyboard_brightness / 100, self.keyboard_speed / 50,
            )
            self.keyboard_mode = mode
            self.keyboard_preview.set_mode(mode)
            self.brightness_slider.setEnabled(True)
            self.speed_slider.setEnabled(mode in ("breathe", "rainbow", "soft_rainbow", "wave", "spectrum", "twinkle"))
            self.keyboard_effect_note.setText("Software effect runs in the tray; Quit restores onboard lighting")
            for name, button in self.effect_buttons.items():
                button.setChecked(name == mode)
            self.keyboard_status_label.setText(f"{mode.replace('_', ' ').title()} effect active")
        except Exception as exc:
            QMessageBox.warning(self, "Lighting unavailable", str(exc))

    def apply_keyboard_color(self, color):
        if color == QColor("#000000"):
            self.apply_keyboard_effect("off")
        else:
            self.color = QColor(color)
            self.color_swatch.setStyleSheet(f"background:{self.color.name()}; border:1px solid #65727a;")
            self.apply_keyboard_effect("static")

    def restore_keyboard(self):
        self.keyboard_resume_mode = None
        self.keyboard_mode = "onboard"
        self.keyboard_preview.set_mode("onboard")
        for button in self.effect_buttons.values():
            button.setEnabled(False)
        self.keyboard_status_label.setText("Restoring keyboard profile…")
        threading.Thread(target=self._restore_keyboard_worker, daemon=True).start()

    def _restore_keyboard_worker(self):
        try:
            self.keyboard_animator.stop(restore=True)
            result = None
        except Exception as exc:
            result = exc
        self.keyboard_events.restored.emit(result)

    def on_keyboard_restored(self, result):
        if self.selected == "keyboard":
            for button in self.effect_buttons.values():
                button.setEnabled(self.state["keyboard"])
        if isinstance(result, Exception):
            QMessageBox.warning(self, "Keyboard unavailable", str(result))
        elif self.selected == "keyboard":
            self.effect_buttons["onboard"].setChecked(True)
            self.brightness_slider.setEnabled(False)
            self.speed_slider.setEnabled(False)
            self.keyboard_effect_note.setText("Onboard: use the keyboard brightness key; speed is saved in its profile.")
            self.keyboard_status_label.setText("Keyboard profile restored")

    def on_keyboard_error(self, message):
        if self.keyboard_mode not in (None, "onboard"):
            self.keyboard_resume_mode = self.keyboard_mode
        self.keyboard_mode = None
        if self.selected == "keyboard":
            self.effect_group.setExclusive(False)
            for button in self.effect_buttons.values():
                button.setChecked(False)
            self.effect_group.setExclusive(True)
            self.keyboard_status_label.setText(f"Lighting error: {message}")

    def stop_keyboard(self):
        try:
            self.keyboard_animator.stop(restore=self.keyboard_mode not in (None, "onboard"))
        except Exception:
            pass

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "size_grip"):
            self.size_grip.move(self.width() - 14, self.height() - 14)
            self.size_grip.setVisible(not self.isMaximized())
            self.size_grip.raise_()

    def closeEvent(self, event):
        if self.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            if not self.settings.value("ui/tray_hint_seen", False, type=bool):
                self.settings.setValue("ui/tray_hint_seen", True)
                self.tray.showMessage("Devices is in the tray", "Click the tray icon to reopen. Use its menu to quit.", QSystemTrayIcon.MessageIcon.Information, 4000)
            event.ignore()
        else:
            event.accept()
            QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    server_name = "Devices_SC900_K95_single_instance"
    existing = QLocalSocket()
    existing.connectToServer(server_name)
    if existing.waitForConnected(300):
        existing.write(b"quit" if "--quit" in sys.argv else b"show")
        existing.waitForBytesWritten(300)
        running_version = bytes(existing.readAll()).decode(errors="replace") if existing.waitForReadyRead(300) else ""
        if "--quit" not in sys.argv and running_version != f"Devices/{APP_VERSION}":
            QMessageBox.information(
                None, "Devices update",
                "Another Devices version is already running. Quit it from the tray menu, then open this build again.",
            )
        sys.exit(0)
    if "--quit" in sys.argv:
        sys.exit(0)
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(server_name):
        QMessageBox.warning(None, "Devices", "Could not start the app's single-instance listener.")
        sys.exit(1)
    window = MainWindow()
    def show_existing_window():
        client = server.nextPendingConnection()
        if client is not None:
            def process_request():
                request = bytes(client.readAll())
                if not request:
                    return
                client.readyRead.disconnect(process_request)
                client.write(f"Devices/{APP_VERSION}".encode())
                client.flush()
                if request == b"quit":
                    QTimer.singleShot(100, app.quit)
                else:
                    window.show_from_tray()
            client.readyRead.connect(process_request)
            if client.bytesAvailable():
                process_request()
            client.disconnected.connect(client.deleteLater)
    server.newConnection.connect(show_existing_window)
    if "--tray" not in sys.argv or not QSystemTrayIcon.isSystemTrayAvailable():
        window.show()
    sys.exit(app.exec())
