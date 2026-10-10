import unittest
from unittest.mock import patch
import mouse_commands
import mouse_direct


class CommandTests(unittest.TestCase):
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
