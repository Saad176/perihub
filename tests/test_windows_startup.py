import sys
import unittest
from unittest.mock import MagicMock, patch

import windows_startup as startup


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.registry = MagicMock()
        self.registry.OpenKey.return_value.__enter__.return_value = "key"
        self.registry.CreateKey.return_value.__enter__.return_value = "key"
        self.registry_patch = patch.dict(sys.modules, winreg=self.registry)
        self.registry_patch.start()
        self.available_patch = patch.object(startup, "available", return_value=True)
        self.available_patch.start()
        self.path_patch = patch.object(sys, "executable", r"C:\My Apps\Devices\Devices.exe")
        self.path_patch.start()
        self.addCleanup(patch.stopall)

    def test_enable_quotes_path_and_starts_hidden(self):
        startup.set_enabled(True)
        self.registry.SetValueEx.assert_called_once_with(
            "key", "Devices", 0, self.registry.REG_SZ,
            '"C:\\My Apps\\Devices\\Devices.exe" --tray')

    def test_disable_only_our_entry(self):
        self.registry.QueryValueEx.return_value = (startup.command(), 1)
        self.assertTrue(startup.enabled())
        startup.set_enabled(False)
        self.registry.DeleteValue.assert_called_once_with("key", "Devices")

    def test_preserve_other_copy(self):
        self.registry.QueryValueEx.return_value = ('"D:\\Devices.exe" --tray', 1)
        self.assertFalse(startup.enabled())
        startup.set_enabled(False)
        self.registry.DeleteValue.assert_not_called()

    def test_absent_entry(self):
        self.registry.QueryValueEx.side_effect = FileNotFoundError
        self.assertFalse(startup.enabled())
        startup.set_enabled(False)
        self.registry.DeleteValue.assert_not_called()

    def test_source_cannot_register_python(self):
        self.available_patch.stop()
        with patch.object(sys, "frozen", False, create=True):
            self.assertFalse(startup.available())
            with self.assertRaises(RuntimeError):
                startup.set_enabled(True)
        self.registry.SetValueEx.assert_not_called()
