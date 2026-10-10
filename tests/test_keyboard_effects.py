import unittest
import threading
from unittest.mock import MagicMock, patch

from keyboard_direct import KeyboardAnimator, render_frame


class KeyboardFrameTests(unittest.TestCase):
    def test_static_off_and_breathing_frames(self):
        self.assertEqual(render_frame("off", (255, 50, 0), 1, 0, 1), [(0, 0, 0)] * 168)
        self.assertEqual(render_frame("static", (200, 100, 0), 0.5, 0, 1)[0], (100, 50, 0))
        dim = render_frame("breathe", (200, 100, 0), 1, 0, 1)[0]
        bright = render_frame("breathe", (200, 100, 0), 1, 1.5, 1)[0]
        self.assertLess(dim[0], bright[0])

    def test_rainbow_and_wave_vary_across_keys_and_time(self):
        rainbow = render_frame("rainbow", (255, 0, 0), 1, 0, 1)
        wave = render_frame("wave", (255, 0, 0), 1, 0, 1)
        self.assertEqual(len(rainbow), 168)
        self.assertGreater(len(set(rainbow)), 100)
        self.assertGreater(len(set(wave)), 10)
        self.assertNotEqual(rainbow, render_frame("rainbow", (255, 0, 0), 1, 1, 1))
        soft = render_frame("soft_rainbow", (255, 0, 0), 1, 0, 1)
        self.assertEqual(len(soft), 168)
        self.assertGreater(len(set(soft)), 100)
        self.assertNotEqual(soft, render_frame("soft_rainbow", (255, 0, 0), 1, 1, 1))

    def test_animation_switch_and_restore_close_the_hid_session(self):
        first_frame = threading.Event()
        frames = []
        device = MagicMock()
        def capture(device_handle, pixels):
            frames.append(pixels)
            first_frame.set()
        with patch("keyboard_direct._open_keyboard", return_value=device), \
             patch("keyboard_direct._setup_lighting"), \
             patch("keyboard_direct._write_frame", side_effect=capture), \
             patch("keyboard_direct.restore_hardware_mode") as restore:
            animator = KeyboardAnimator()
            animator.set_effect("static", (100, 50, 0), 1, 1)
            self.assertTrue(first_frame.wait(1))
            animator.set_effect("off", (100, 50, 0), 1, 1)
            animator.stop(restore=True)
            self.assertFalse(animator._thread.is_alive())
            self.assertGreaterEqual(len(frames), 1)
            device.close.assert_called_once()
            restore.assert_called_once()


if __name__ == "__main__":
    unittest.main()
