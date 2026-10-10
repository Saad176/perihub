import unittest
from unittest.mock import patch
import mouse_commands
import mouse_direct


class CommandTests(unittest.TestCase):
    def test_sensor_readback_must_match_requested_value(self):
        with patch.object(mouse_direct, 'set_sensor_setting'), patch.object(mouse_direct, 'read_sensor_setting', return_value=1):
            self.assertEqual(mouse_commands.execute('sensor', ('motion', 1), None), 1)
            with self.assertRaises(OSError):
                mouse_commands.execute('sensor', ('motion', 0), None)

    def test_sensor_rejects_connection_switch_before_writing(self):
        with patch.object(mouse_direct, 'find_device', return_value={'connection': 'wired'}), patch.object(mouse_direct, 'set_sensor_setting') as write:
            with self.assertRaises(OSError):
                mouse_commands.execute('sensor', ('lod', 1), 'receiver')
            write.assert_not_called()

    def test_rejects_connection_switch_during_readback(self):
        with patch.object(mouse_direct, 'find_device', side_effect=[{'connection': 'receiver'}, {'connection': 'wired'}]), patch.object(mouse_direct, 'set_sensor_setting'), patch.object(mouse_direct, 'read_sensor_setting', return_value=1):
            with self.assertRaises(OSError):
                mouse_commands.execute('sensor', ('motion', 1), 'receiver')

    def test_rejects_connection_switch_before_writing(self):
        with patch.object(mouse_direct, 'find_device', return_value={'connection': 'receiver'}), patch.object(mouse_direct, 'set_dpi_value') as write:
            with self.assertRaises(OSError):
                mouse_commands.execute('dpi', (2, 900), 'wired')
            write.assert_not_called()

    def test_dpi_readback_must_match_requested_value(self):
        with patch.object(mouse_direct, 'set_dpi_value'), patch.object(mouse_direct, '_query', return_value=bytes([9, 0x8c, 1, 15, 0, 0, 0, 0, 0])):
            self.assertEqual(mouse_commands.execute('dpi', (2, 800), None), 800)
            with self.assertRaises(OSError):
                mouse_commands.execute('dpi', (2, 900), None)
