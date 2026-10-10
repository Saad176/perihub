import unittest
from mouse_battery import decode_battery


class BatteryTests(unittest.TestCase):
    def test_real_receiver_capture(self):
        report = bytes.fromhex('09 3d 10 08 00 0f 0f 01') + bytes(25)
        self.assertEqual(decode_battery(report), {"percent": 61, "bars": 4})

    def test_flag_is_not_part_of_percentage(self):
        self.assertEqual(decode_battery(bytes([9, 0xbd]) + bytes(31))["percent"], 61)

    def test_real_wired_report_masks_status_bit(self):
        report = bytes.fromhex('09 cc 10 08 00 0f 0f 01') + bytes(25)
        self.assertEqual(decode_battery(report), {"percent": 76, "bars": 4})

    def test_aula_bar_thresholds(self):
        for percent, bars in [(0, 1), (19, 1), (20, 2), (40, 3), (60, 4), (80, 5), (100, 5)]:
            self.assertEqual(decode_battery(bytes([9, percent]) + bytes(31))["bars"], bars)

    def test_rejects_feature_reply_and_invalid_input(self):
        for report in [b'', bytes([9, 61]), bytes([9, 0x8f]) + bytes(7), bytes([8, 61]) + bytes(31), bytes([9, 101]) + bytes(31)]:
            self.assertIsNone(decode_battery(report))
