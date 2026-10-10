import unittest
from unittest.mock import patch

import app


class DetectionTests(unittest.TestCase):
    def test_generic_hardware_does_not_match(self):
        with patch('app.hid.enumerate', return_value=[]), patch('mouse_direct.find_device', return_value=None):
            self.assertEqual(app.detect_devices(), {'mouse': False, 'keyboard': False, 'mouse_connection': None})

    def test_keyboard_requires_supported_configuration_interface(self):
        with patch('app.hid.enumerate', return_value=[{'interface_number': 0, 'usage_page': 1}]) as enumerate_hid, patch('mouse_direct.find_device', return_value=None):
            self.assertFalse(app.detect_devices()['keyboard'])
            enumerate_hid.assert_called_once_with(0x1B1C, 0x1B2D)

    def test_mouse_failure_does_not_hide_valid_keyboard(self):
        with patch('app.hid.enumerate', return_value=[{'interface_number': 1, 'usage_page': 0xFFC2}]), patch('mouse_direct.find_device', side_effect=RuntimeError('Ambiguous mouse')):
            state = app.detect_devices()
            self.assertTrue(state['keyboard'])
            self.assertFalse(state['mouse'])

    def test_keyboard_failure_does_not_hide_valid_mouse(self):
        with patch('app.hid.enumerate', side_effect=OSError), patch('mouse_direct.find_device', return_value={'connection': 'wired'}):
            self.assertEqual(app.detect_devices(), {'mouse': True, 'keyboard': False, 'mouse_connection': 'wired'})
