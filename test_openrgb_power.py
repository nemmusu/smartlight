"""Power regressions for OpenRGB's Logitech per-key cache, without hardware."""
from types import SimpleNamespace
import unittest

from legacy_hwlight.backends import OpenRGBLight
from legacy_hwlight.engine import Engine


def rgb(color):
    return (color.red, color.green, color.blue)


class CachedKeyboard:
    """Emulate the G512/G815 driver cache surviving native mode changes."""
    def __init__(self, color=(0, 120, 255)):
        self.name = "Logitech G512 RGB"
        self.type = SimpleNamespace(name="KEYBOARD")
        self.leds = list(range(117))
        self.modes = [SimpleNamespace(name=name, brightness_max=None, speed_max=None)
                      for name in ("Direct", "Static", "Off")]
        self.active_mode = 0
        self.cached = [color] * len(self.leds)
        self.hardware = list(self.cached)
        self.mode_writes = []
        self.color_writes = []
        self.fail_final = False

    def set_mode(self, mode):
        self.active_mode = self.modes.index(mode)
        self.mode_writes.append(mode.name)
        if mode.name == "Direct":
            # Direct initialization changes physical keys while the driver
            # retains its previous per-key cache. Off is a native no-op.
            self.hardware = [(0, 0, 0)] * len(self.leds)

    def set_color(self, color, fast=False):
        self.set_colors([color] * len(self.leds), fast=fast)

    def set_colors(self, colors, fast=False):
        frame = list(map(rgb, colors))
        if self.fail_final and self.color_writes:
            raise OSError("USB write failed")
        self.color_writes.append(frame)
        for i, color in enumerate(frame):
            if color != self.cached[i]:
                self.hardware[i] = color
        self.cached = frame


class OpenRGBPowerTests(unittest.TestCase):
    def test_direct_entry_refreshes_every_key_even_if_target_matches_driver_cache(self):
        dev = CachedKeyboard()
        light = OpenRGBLight(dev)
        light.set_color((0, 120, 255))
        self.assertEqual(dev.hardware, [(0, 120, 255)] * 117)
        self.assertEqual(dev.mode_writes, ["Direct"])
        self.assertEqual(len(dev.color_writes), 2)
        self.assertLessEqual(max(abs(a - b) for pre, final in zip(*dev.color_writes)
                                 for a, b in zip(pre, final)), 1)

    def test_engine_repeated_power_cycles_restore_the_entire_keyboard(self):
        dev = CachedKeyboard()
        light = OpenRGBLight(dev)
        engine = Engine()
        engine.set_lights({light.key: light})
        for enabled in (False, True, False, True, True, False, False, True):
            state = engine.update_device(light.key, {"on": enabled})
            engine._render(light.key, light, state, 0, 1)
            self.assertEqual(dev.hardware, [(0, 120, 255) if enabled else (0, 0, 0)] * 117)
        self.assertEqual(dev.mode_writes, ["Direct"])

    def test_startup_off_rewrites_black_keys_even_when_cached_black(self):
        dev = CachedKeyboard((0, 0, 0))
        dev.hardware = [(50, 50, 50)] * 117
        OpenRGBLight(dev).off()
        self.assertEqual(dev.hardware, [(0, 0, 0)] * 117)
        self.assertNotIn("Off", dev.mode_writes)

    def test_failed_final_refresh_is_retried(self):
        dev = CachedKeyboard()
        dev.fail_final = True
        light = OpenRGBLight(dev)
        with self.assertRaises(OSError):
            light.set_color((0, 120, 255))
        self.assertTrue(light._full_frame_pending)
        dev.fail_final = False
        light.set_color((0, 120, 255))
        self.assertEqual(dev.hardware, [(0, 120, 255)] * 117)
        self.assertFalse(light._full_frame_pending)

    def test_other_devices_keep_their_native_off(self):
        dev = CachedKeyboard()
        dev.name = "Palit GeForce RTX 5090 Gamerock"
        dev.type = SimpleNamespace(name="GPU")
        OpenRGBLight(dev).off()
        self.assertEqual(dev.mode_writes, ["Off"])


if __name__ == "__main__":
    unittest.main()
