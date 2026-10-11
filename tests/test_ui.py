"""Focused regressions for the mouse controls and tab layout."""

import os
import tempfile
import unittest
import time
import threading
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import app


class MouseUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        settings_path = str(Path(self.temp.name) / "settings.ini")
        self.settings = QSettings(settings_path, QSettings.Format.IniFormat)
        self.settings.clear()
        self.settings.setValue("mouse/dpi_stage_2", 800)
        self.settings.sync()
        self.settings_patch = patch.object(app, "QSettings", return_value=self.settings)
        self.detect_patch = patch.object(app, "detect_devices", return_value={"mouse": True, "keyboard": True})
        self.read_patch = patch.object(app.MainWindow, "refresh_mouse_state")
        self.battery_patch = patch.object(app, "BatteryMonitor")
        self.battery_patch.start()
        self.command_patch = patch('mouse_commands.execute', side_effect=lambda kind, values, connection: values[-1])
        self.command_patch.start()
        self.settings_patch.start()
        self.detect_patch.start()
        self.read_patch.start()
        self.window = app.MainWindow()
        self.window.on_scan_finished({"mouse": True, "keyboard": True})
        self.window.on_mouse_read({"stage_count": 6, "active_stage": 2, "dpi": [400, 800, 1600, 3200, 6400, 26000],
                                   "polling_hz": 1000, "debounce_ms": 8, "dormancy_s": 60,
                                   "lod": 0, "ripple": 0, "angle": 0, "motion": 1, "sensor_mode": 1})
        self.window.show()
        self.qt.processEvents()

    def tearDown(self):
        self.window.stop_scanner()
        self.window.tray.hide()
        self.window.close()
        self.window.deleteLater()
        self.qt.processEvents()
        self.detect_patch.stop()
        self.read_patch.stop()
        self.battery_patch.stop()
        self.command_patch.stop()

    def wait_commands(self):
        deadline = time.monotonic() + 2
        while self.window.command_pending and time.monotonic() < deadline:
            self.qt.processEvents()
            QTest.qWait(2)
        self.assertEqual(self.window.command_pending, 0)

    def test_absent_supported_devices_hide_cards_and_controls(self):
        self.window.on_scan_finished({'mouse': False, 'keyboard': False})
        self.assertTrue(self.window.mouse_button.isHidden())
        self.assertTrue(self.window.keyboard_button.isHidden())
        self.assertIsNone(self.window.selected)
        self.assertEqual(self.window.header.itemAt(0).widget().text(), 'No supported devices detected')
        self.assertFalse(self.window.battery_tray_action.isVisible())

    def test_only_keyboard_shows_keyboard_and_hotplug_mouse(self):
        self.window.on_scan_finished({'mouse': False, 'keyboard': True})
        self.assertTrue(self.window.mouse_button.isHidden())
        self.assertFalse(self.window.keyboard_button.isHidden())
        self.assertEqual(self.window.selected, 'keyboard')
        self.window.on_scan_finished({'mouse': True, 'keyboard': True})
        self.assertFalse(self.window.mouse_button.isHidden())
        self.window.show_device('mouse')
        self.assertEqual(self.window.selected, 'mouse')
        self.window.on_scan_finished({'mouse': True, 'keyboard': False})
        self.assertTrue(self.window.keyboard_button.isHidden())
        self.assertEqual(self.window.selected, 'mouse')

    def test_slow_command_leaves_ui_responsive_and_handles_page_switch(self):
        release = threading.Event()
        started = threading.Event()
        def slow_command(kind, values, connection):
            started.set()
            release.wait(2)
            return values[-1]
        with patch('mouse_commands.execute', side_effect=slow_command):
            self.window.apply_mouse_dpi_value(2, 900)
            self.assertTrue(started.wait(1))
            heartbeat = []
            QTimer.singleShot(0, lambda: heartbeat.append(True))
            self.window.show_device('keyboard')
            self.qt.processEvents()
            self.assertEqual(heartbeat, [True])
            self.assertEqual(self.window.command_pending, 1)
            release.set()
            self.wait_commands()
        self.assertEqual(self.window.last_dpi_sent[2], 900)

    def test_unavailable_mouse_disables_controls_until_read_recovers(self):
        self.window.on_mouse_read(OSError('Mouse sleeping'))
        self.assertFalse(self.window.mouse_stack.isEnabled())
        self.window.on_mouse_read({"stage_count": 1, "active_stage": 1, "dpi": [800],
                                   "polling_hz": 1000, "debounce_ms": 8, "dormancy_s": 60,
                                   "lod": 0, "ripple": 0, "angle": 0, "motion": 1, "sensor_mode": 1})
        self.assertTrue(self.window.mouse_stack.isEnabled())
        self.assertFalse(self.window.mouse_status_label.isVisible())

    def test_keyboard_effect_restarts_after_reconnect(self):
        self.window.keyboard_mode = 'rainbow'
        self.window.on_keyboard_error('Disconnected')
        self.window.on_scan_finished({'mouse': True, 'keyboard': False})
        with patch.object(self.window.keyboard_animator, 'set_effect') as start:
            self.window.on_scan_finished({'mouse': True, 'keyboard': True})
        start.assert_called_once()
        self.assertEqual(self.window.keyboard_mode, 'rainbow')

    def test_static_keyboard_effect_resumes_without_a_write_error(self):
        self.window.keyboard_mode = 'static'
        with patch.object(self.window.keyboard_animator, 'stop'), patch.object(self.window.keyboard_animator, 'set_effect') as start:
            self.window.on_scan_finished({'mouse': True, 'keyboard': False})
            self.assertEqual(self.window.keyboard_resume_mode, 'static')
            self.window.on_scan_finished({'mouse': True, 'keyboard': True})
            start.assert_called_once()
        self.assertEqual(self.window.keyboard_mode, 'static')

    def test_selected_device_and_tab_are_saved(self):
        self.window.show_tab('Sensor')
        self.window.show_device('keyboard')
        self.assertEqual(self.settings.value('ui/device'), 'keyboard')
        self.assertEqual(self.settings.value('ui/mouse_tab'), 'Sensor')
        self.settings_patch.stop()

    def test_tab_switch_keeps_pages_and_sends_no_hid_command(self):
        stack = self.window.mouse_stack
        with patch("mouse_direct.set_dpi_value") as dpi_write, patch("mouse_direct.set_polling_rate") as polling_write:
            for _ in range(10):
                self.window.show_tab("Polling")
                self.window.show_tab("DPI")
            self.assertIs(self.window.mouse_stack, stack)
            dpi_write.assert_not_called()
            polling_write.assert_not_called()

    def test_battery_status_and_tray_hover_do_not_invent_a_level(self):
        self.assertIn("Level unavailable", self.window.mouse_battery_label.toolTip())
        self.assertEqual(self.window.tray.toolTip(), "SC900 Pro · Battery unavailable · 8K receiver")
        self.assertEqual(self.window.battery_tray_action.text(), "Mouse battery: unavailable")
        self.window.on_scan_finished({"mouse": False, "keyboard": True})
        self.assertIsNone(self.window.mouse_battery_label)
        self.assertFalse(self.window.battery_tray_action.isVisible())
        self.assertEqual(self.window.tray.toolTip(), "PeriHub · K95 Platinum connected")
        self.window.show_device("keyboard")
        self.window.on_scan_finished({"mouse": True, "keyboard": True})
        self.assertIsNone(self.window.mouse_battery_label)
        self.assertIn("8K receiver", self.window.tray.toolTip())

    def test_slider_and_keyboard_arrows_move_exactly_50_dpi(self):
        field = self.window.dpi_fields[2]
        slider = self.window.mouse_stack.widget(0).findChildren(app.ScrollSafeSlider)[1]
        with patch("mouse_commands.execute", side_effect=lambda kind, values, connection: values[-1]) as write:
            slider.sliderPressed.emit()
            slider.setValue(850)
            slider.sliderReleased.emit()
            self.wait_commands()
            self.assertEqual(field.text(), "850")
            write.assert_called_with("dpi", (2, 850), None)
            field.setFocus()
            QTest.keyClick(field, Qt.Key.Key_Up)
            self.wait_commands()
            self.assertEqual(field.text(), "900")
            write.assert_called_with("dpi", (2, 900), None)
            QTest.keyClick(field, Qt.Key.Key_Down)
            self.wait_commands()
            self.assertEqual(field.text(), "850")
            write.assert_called_with("dpi", (2, 850), None)

    def test_battery_updates_panel_and_tray_and_clears_on_disconnect(self):
        self.window.on_battery_read({"percent": 61, "bars": 4})
        self.assertEqual(self.window.mouse_battery_label.text(), "61%")
        self.assertEqual(self.window.tray.toolTip(), "SC900 Pro · 61% · 8K receiver")
        self.window.show_device("keyboard")
        self.window.on_battery_read({"percent": 60, "bars": 4})
        self.assertIn("60%", self.window.battery_tray_action.text())
        self.window.show_device("mouse")
        self.assertEqual(self.window.mouse_battery_label.text(), "60%")
        self.window.on_battery_read(None)
        self.assertIn("unavailable", self.window.tray.toolTip())
        self.window.on_battery_read({"percent": 61, "bars": 4})
        self.window.on_scan_finished({"mouse": False, "keyboard": True})
        self.assertIsNone(self.window.battery_reading)

    def test_no_horizontal_clipping_at_default_and_minimum_sizes(self):
        for width, height in ((620, 800), (620, 640)):
            self.window.resize(width, height)
            self.qt.processEvents()
            self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
            self.window.show_tab("Polling")
            self.qt.processEvents()
            self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
            self.window.show_tab("Sensor")
            self.qt.processEvents()
            self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
            self.window.show_tab("Timing")
            self.qt.processEvents()
            self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
            self.window.show_device("keyboard")
            self.qt.processEvents()
            self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
            self.window.show_device("mouse")

    def test_switching_wired_and_receiver_clears_old_battery(self):
        self.window.on_scan_finished({'mouse': True, 'keyboard': True, 'mouse_connection': 'wired'})
        self.window.on_battery_read({'percent': 76, 'bars': 4, 'connection': 'wired'})
        self.assertEqual(self.window.mouse_specs['Connection'].text(), 'USB wired')
        self.assertEqual(self.window.tray.toolTip(), 'SC900 Pro · 76% · USB wired')
        self.window.on_scan_finished({'mouse': True, 'keyboard': True, 'mouse_connection': 'receiver'})
        self.assertIsNone(self.window.battery_reading)
        self.assertEqual(self.window.mouse_specs['Connection'].text(), '2.4 GHz')
        with patch.object(self.window, 'refresh_devices'):
            self.window.on_battery_read({'percent': 76, 'bars': 4, 'connection': 'wired'})
        self.assertIsNone(self.window.battery_reading)
        self.window.on_battery_read({'percent': 75, 'bars': 4, 'connection': 'receiver'})
        self.assertEqual(self.window.tray.toolTip(), 'SC900 Pro · 75% · 8K receiver')

    def test_connection_errors_and_switching_never_widen_dpi_page(self):
        for width, height in ((620, 800), (620, 640)):
            self.window.resize(width, height)
            for connection in ('wired', None, 'receiver', 'wired', 'receiver'):
                self.window.on_scan_finished({'mouse': connection is not None, 'keyboard': True, 'mouse_connection': connection})
                self.window.show_tab('DPI')
                self.window.on_mouse_read(OSError('No valid SC900 Pro reply for settings query 8B/00; device disconnected while reading settings'))
                self.qt.processEvents()
                self.assertEqual(self.window.width(), width)
                self.assertLessEqual(self.window.content.width(), self.window.content_area.viewport().width())
                for field in self.window.dpi_fields.values():
                    right = field.mapTo(self.window.content_area.viewport(), field.rect().topRight()).x()
                    self.assertLess(right, self.window.content_area.viewport().width())

    def test_drag_moves_50_dpi_without_click_jump_or_extra_writes(self):
        slider = self.window.mouse_stack.widget(0).findChildren(app.DpiSlider)[1]
        start = QPoint(slider.width() // 2, slider.height() // 2)
        with patch("mouse_commands.execute", return_value=850) as write:
            QTest.mousePress(slider, Qt.MouseButton.LeftButton, pos=start)
            self.assertEqual(slider.value(), 800)
            QTest.mouseMove(slider, start + QPoint(4, 0))
            self.assertEqual(slider.value(), 850)
            write.assert_not_called()
            QTest.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=start + QPoint(4, 0))
            self.wait_commands()
            write.assert_called_once_with("dpi", (2, 850), None)

    def test_live_state_populates_all_controls_without_hid_writes(self):
        state = {"stage_count": 3, "active_stage": 2, "dpi": [400, 850, 1600],
                 "polling_hz": 1000, "debounce_ms": 8, "dormancy_s": 60,
                 "lod": 0, "ripple": 0, "angle": 0, "motion": 1, "sensor_mode": 1}
        with patch("mouse_direct.set_stage_count") as write:
            self.window.on_mouse_read(state)
            write.assert_not_called()
        self.assertEqual(self.window.stage_count_combo.currentText(), "3")
        self.assertEqual(self.window.dpi_fields[2].text(), "850")
        self.assertFalse(self.window.dpi_rows[4].isVisible())
        self.assertEqual(self.window.dpi_use[2].text(), "Active")
        self.assertTrue(self.window.poll_buttons[1000].isChecked())
        self.assertTrue(self.window.sensor_buttons["motion"][1].isChecked())
        self.assertEqual(self.window.timing_fields["debounce_ms"].text(), "8")

    def test_sensor_mode_selection_is_exclusive(self):
        self.window.on_mouse_read({"stage_count": 3, "active_stage": 2, "dpi": [400, 800, 1600],
                                   "polling_hz": 1000, "debounce_ms": 8, "dormancy_s": 60,
                                   "lod": 0, "ripple": 0, "angle": 0, "motion": 1, "sensor_mode": 1})
        self.window.show_tab("Sensor")
        with patch.object(self.window, "queue_mouse_command"):
            self.window.sensor_buttons["sensor_mode"][0].click()
        selected = [value for value, button in self.window.sensor_buttons["sensor_mode"].items() if button.isChecked()]
        self.assertEqual(selected, [0])

    def test_polling_selection_exclusive_and_disabled_until_verified(self):
        self.window.show_tab('Polling')
        release = threading.Event()
        def slow(kind, values, connection):
            release.wait(2)
            return values[-1]
        try:
            with patch('mouse_commands.execute', side_effect=slow):
                self.window.poll_buttons[500].click()
                self.assertEqual([hz for hz, b in self.window.poll_buttons.items() if b.isChecked()], [500])
                self.assertTrue(all(not b.isEnabled() for b in self.window.poll_buttons.values()))
                self.window.apply_mouse_polling(250)
                self.assertEqual(self.window.command_pending, 1)
                release.set()
                self.wait_commands()
                self.assertEqual(self.window.mouse_state['polling_hz'], 500)
                self.assertTrue(all(b.isEnabled() for b in self.window.poll_buttons.values()))
        finally:
            release.set()

    def test_sensor_completion_after_transport_change_is_ignored(self):
        self.window.state['mouse_connection'] = 'receiver'
        self.window.show_tab('Sensor')
        release = threading.Event()
        def slow(kind, values, connection):
            release.wait(2)
            return values[-1]
        try:
            with patch('mouse_commands.execute', side_effect=slow):
                self.window.sensor_buttons['motion'][0].click()
                self.window.state['mouse_connection'] = 'wired'
                release.set()
                self.wait_commands()
                self.assertEqual(self.window.mouse_state['motion'], 1)
                self.assertNotIn('motion', self.window.sensor_pending)
        finally:
            release.set()

    def test_sensor_completion_after_page_switch_handles_deleted_widgets(self):
        release = threading.Event()
        def slow(kind, values, connection):
            release.wait(2)
            return values[-1]
        try:
            with patch('mouse_commands.execute', side_effect=slow):
                self.window.apply_sensor('motion', 0)
                self.window.show_device('keyboard')
                self.qt.sendPostedEvents()
                release.set()
                self.wait_commands()
                self.assertEqual(self.window.mouse_state['motion'], 0)
                self.assertNotIn('motion', self.window.sensor_pending)
        finally:
            release.set()

    def test_keyboard_effect_selection_is_exclusive(self):
        self.window.show_device("keyboard")
        with patch.object(self.window.keyboard_animator, "set_effect") as start:
            self.window.effect_buttons["breathe"].click()
            self.window.effect_buttons["rainbow"].click()
            self.assertEqual(start.call_count, 2)
        selected = [name for name, button in self.window.effect_buttons.items() if button.isChecked()]
        self.assertEqual(selected, ["rainbow"])

    def test_keyboard_preferences_survive_restart_and_apply_with_mouse_selected(self):
        self.window.show_device('keyboard')
        with patch.object(self.window.keyboard_animator, 'set_effect'):
            self.window.choose_preset('#ffffff')
            self.window.show_keyboard_brightness(35)
            self.window.show_keyboard_speed(80)
        with patch.object(self.window.keyboard_animator, 'stop') as stop:
            self.window.stop_keyboard()
            stop.assert_called_once_with(restore=True)
        self.assertEqual(self.settings.value('keyboard/mode'), 'static')
        self.settings.setValue('ui/device', 'mouse')
        with patch.object(app.MainWindow, 'refresh_devices'), patch('keyboard_direct.KeyboardAnimator.set_effect') as apply:
            restarted = app.MainWindow()
            try:
                restarted.on_scan_finished({'mouse': True, 'keyboard': True})
                apply.assert_called_once_with('static', (255, 255, 255), .35, 1.6)
                self.assertEqual(restarted.selected, 'mouse')
                self.assertEqual(restarted.keyboard_mode, 'static')
                restarted.on_scan_finished({'mouse': True, 'keyboard': True})
                self.assertEqual(apply.call_count, 1)
            finally:
                restarted.stop_scanner()
                restarted.tray.hide()
                restarted.close()

    def test_saved_lighting_waits_for_keyboard_and_survives_error(self):
        self.settings.setValue('keyboard/mode', 'rainbow')
        with patch.object(app.MainWindow, 'refresh_devices'), patch('keyboard_direct.KeyboardAnimator.set_effect') as apply:
            restarted = app.MainWindow()
            try:
                restarted.on_scan_finished({'mouse': True, 'keyboard': False})
                apply.assert_not_called()
                restarted.on_scan_finished({'mouse': True, 'keyboard': True})
                apply.assert_called_once()
                restarted.on_keyboard_error('Unplugged')
                self.assertEqual(self.settings.value('keyboard/mode'), 'rainbow')
            finally:
                restarted.stop_scanner()
                restarted.tray.hide()
                restarted.close()

    def test_onboard_selection_is_remembered_without_startup_write(self):
        self.window.show_device('keyboard')
        with patch.object(self.window.keyboard_animator, 'set_effect'):
            self.window.apply_keyboard_effect('static')
        with patch.object(self.window, '_restore_keyboard_worker'):
            self.window.restore_keyboard()
        self.assertEqual(self.settings.value('keyboard/mode'), 'onboard')
        with patch.object(app.MainWindow, 'refresh_devices'), patch('keyboard_direct.KeyboardAnimator.set_effect') as apply:
            restarted = app.MainWindow()
            try:
                restarted.on_scan_finished({'mouse': True, 'keyboard': True})
                apply.assert_not_called()
                self.assertEqual(restarted.keyboard_mode, 'onboard')
            finally:
                restarted.stop_scanner()
                restarted.tray.hide()
                restarted.close()

    def test_saved_effect_modes_and_corrupt_preferences(self):
        with patch.object(app.MainWindow, 'refresh_devices'), patch('keyboard_direct.KeyboardAnimator.set_effect') as apply:
            for mode in ('static', 'off', 'breathe', 'rainbow', 'soft_rainbow', 'wave', 'spectrum', 'twinkle'):
                with self.subTest(mode=mode):
                    self.settings.setValue('keyboard/mode', mode)
                    restarted = app.MainWindow()
                    try:
                        restarted.on_scan_finished({'mouse': True, 'keyboard': True})
                        self.assertEqual(restarted.keyboard_mode, mode)
                        self.assertEqual(apply.call_args.args[0], mode)
                    finally:
                        restarted.stop_scanner()
                        restarted.tray.hide()
                        restarted.close()
            for key, value in {'mode': 'invalid', 'color': 'invalid', 'brightness': 'bad', 'speed': 999}.items():
                self.settings.setValue('keyboard/' + key, value)
            restarted = app.MainWindow()
            try:
                self.assertEqual(restarted.keyboard_preferred_mode, 'onboard')
                self.assertEqual(restarted.color.name(), '#4caceb')
                self.assertEqual(restarted.keyboard_brightness, 80)
                self.assertEqual(restarted.keyboard_speed, 100)
            finally:
                restarted.stop_scanner()
                restarted.tray.hide()
                restarted.close()

    def test_onboard_restores_profile_and_disables_software_sliders(self):
        self.window.show_device("keyboard")
        with patch.object(self.window.keyboard_animator, "set_effect"):
            self.window.effect_buttons["soft_rainbow"].click()
        self.assertTrue(self.window.brightness_slider.isEnabled())
        self.assertTrue(self.window.speed_slider.isEnabled())
        with patch.object(self.window, "_restore_keyboard_worker"):
            self.window.effect_buttons["onboard"].click()
        self.window.on_keyboard_restored(None)
        self.assertTrue(self.window.effect_buttons["onboard"].isChecked())
        self.assertFalse(self.window.brightness_slider.isEnabled())
        self.assertFalse(self.window.speed_slider.isEnabled())

    def test_wheel_over_slider_scrolls_page_without_changing_dpi(self):
        self.window.resize(620, 640)
        self.qt.processEvents()
        slider = self.window.mouse_stack.widget(0).findChildren(app.ScrollSafeSlider)[1]
        before = slider.value()
        scroll = self.window.content_area.verticalScrollBar()
        self.assertGreater(scroll.maximum(), 0)
        wheel = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate, False,
        )
        QApplication.sendEvent(slider, wheel)
        self.qt.processEvents()
        self.assertEqual(slider.value(), before)
        self.assertGreater(scroll.value(), 0)


if __name__ == "__main__":
    unittest.main()
