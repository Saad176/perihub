"""Packet checks for settings that carry other configuration bytes."""

import unittest
from unittest.mock import patch

import mouse_direct


class MousePacketTests(unittest.TestCase):
    def device_info(self, pid, path):
        return {'product_id': pid, 'interface_number': 3, 'usage_page': 0xff05,
                'product_string': 'SC900PRO', 'path': path}

    def test_wired_has_priority_when_receiver_is_also_present(self):
        receiver = self.device_info(mouse_direct.PID, b'receiver')
        wired = self.device_info(mouse_direct.WIRED_PID, b'wire')
        with patch.object(mouse_direct.hid, 'enumerate', return_value=[receiver, wired]):
            info = mouse_direct.find_device()
        self.assertEqual(info['path'], b'wire')
        self.assertEqual(info['connection'], 'wired')

    def test_receiver_remains_supported(self):
        receiver = self.device_info(mouse_direct.PID, b'receiver')
        with patch.object(mouse_direct.hid, 'enumerate', return_value=[receiver]):
            self.assertEqual(mouse_direct.find_device()['connection'], 'receiver')

    def test_unknown_device_or_interface_is_not_opened(self):
        unknown = self.device_info(0x1234, b'unknown')
        wrong_interface = {**self.device_info(mouse_direct.WIRED_PID, b'keyboard'), 'interface_number': 2}
        with patch.object(mouse_direct.hid, 'enumerate', return_value=[unknown, wrong_interface]):
            self.assertIsNone(mouse_direct.find_device())

    def test_ambiguous_mice_are_rejected(self):
        with patch.object(mouse_direct.hid, 'enumerate', return_value=[self.device_info(mouse_direct.WIRED_PID, b'a'), self.device_info(mouse_direct.WIRED_PID, b'b')]):
            with self.assertRaises(RuntimeError):
                mouse_direct.find_device()

    def test_stage_selection_preserves_device_configuration(self):
        with patch.object(mouse_direct, "_configuration", return_value=[6, 1, 0, 1, 1]), patch.object(mouse_direct, "_send") as send:
            mouse_direct.select_dpi_stage(3)
            send.assert_called_once_with([9, 0x0B, 6, 2, 0, 1, 1, 0, 0])

    def test_stage_count_clamps_selected_stage(self):
        with patch.object(mouse_direct, "_configuration", return_value=[6, 5, 0, 1, 1]), patch.object(mouse_direct, "_send") as send:
            mouse_direct.set_stage_count(2)
            send.assert_called_once_with([9, 0x0B, 2, 1, 0, 1, 1, 0, 0])

    def test_all_aula_polling_choices_have_unique_codes(self):
        self.assertEqual(set(mouse_direct.POLLING_CODES), {125, 250, 500, 1000, 2000, 4000, 8000})
        self.assertEqual(set(mouse_direct.POLLING_CODES.values()), set(range(7)))


if __name__ == "__main__":
    unittest.main()
