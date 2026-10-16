"""Focused checks for smooth PC animation frames without hardware access."""
import unittest
from unittest.mock import Mock, patch

from legacy_hwlight.engine import (
    Engine, fx_batticuore, fx_caramella, fx_cometa, fx_inseguimento, fx_pioggia,
    smooth_pulse_level,
)
from pc import PCController


class FakeLight:
    led_count = 1

    def __init__(self):
        self.sent = []

    def set_leds(self, frame):
        self.sent.append(frame)


class SmoothPCAnimationTests(unittest.TestCase):
    def test_envelope_is_periodic_and_has_soft_turning_points(self):
        for mode, floor in (("pulse", 0.25), ("breathe", 0.15)):
            with self.subTest(mode=mode):
                self.assertAlmostEqual(smooth_pulse_level(0, 4, mode), 1.0)
                self.assertAlmostEqual(smooth_pulse_level(2, 4, mode), floor)
                self.assertAlmostEqual(smooth_pulse_level(4, 4, mode), 1.0)
                self.assertLess(abs(smooth_pulse_level(0.01, 4, mode)
                                    - smooth_pulse_level(0, 4, mode)), 0.001)

    def test_flow_renders_pulse_and_animation_brightness(self):
        for mode, floor in (("pulse", 0.25), ("breathe", 0.15), ("flow", 1.0)):
            with self.subTest(mode=mode):
                engine = Engine()
                light = FakeLight()
                state = engine.device_state("pc")
                engine.start_flow([(255, 0, 0), (255, 0, 0)], 4, ["pc"], 100,
                                  mode=mode, brightness=80)
                with patch("legacy_hwlight.engine.time.monotonic", return_value=100):
                    engine._render("pc", light, state, 0, 1.0)
                peak = engine.frames["pc"][0][0]
                with patch("legacy_hwlight.engine.time.monotonic", return_value=102):
                    engine._render("pc", light, state, 2, 1.0)
                trough = engine.frames["pc"][0][0]
                self.assertEqual(peak, 204)
                self.assertEqual(trough, round(204 * floor))

    def test_configured_minimum_can_reach_black_or_partial_light(self):
        for minimum, expected in ((0, 0), (40, 102)):
            with self.subTest(minimum=minimum):
                engine = Engine()
                light = FakeLight()
                state = engine.device_state("pc")
                engine.start_flow([(255, 0, 0), (255, 0, 0)], 4, ["pc"], 100,
                                  mode="pulse", brightness=100, min_brightness=minimum)
                with patch("legacy_hwlight.engine.time.monotonic", return_value=102):
                    engine._render("pc", light, state, 2, 1.0)
                self.assertEqual(engine.frames["pc"][0], (expected, 0, 0))

    def test_controller_forwards_mode_and_brightness(self):
        controller = PCController.__new__(PCController)
        controller._engine = Mock()
        controller.list_devices = Mock(return_value=[{"key": "pc"}])
        controller._check_keys = Mock()
        controller.start_flow([[255, 0, 0], [0, 0, 255]], 4, ["pc"], 100,
                              mode="pulse", brightness=70, min_brightness=20,
                              transition_ms=500)
        controller._engine.start_flow.assert_called_once_with(
            [(255, 0, 0), (0, 0, 255)], 4.0, ["pc"], 100.0, "forward",
            mode="pulse", brightness=70, transition_ms=500, min_brightness=20)

    def test_controller_rejects_minimum_above_maximum(self):
        controller = PCController.__new__(PCController)
        with self.assertRaisesRegex(ValueError, "Luminosità minima"):
            controller.start_flow([[255, 0, 0], [0, 0, 255]], 4, ["pc"], 100,
                                  mode="pulse", brightness=70, min_brightness=71)

    def test_controller_accepts_short_valid_animation_period(self):
        controller = PCController.__new__(PCController)
        controller._engine = Mock()
        controller.list_devices = Mock(return_value=[{"key": "pc"}])
        controller._check_keys = Mock()
        controller.start_flow([[255, 0, 0], [0, 0, 255]], 0.5, ["pc"], 100,
                              mode="sequence", transition_ms=100)
        self.assertEqual(controller._engine.start_flow.call_args.args[1], 0.5)

    def test_sequence_holds_then_fades_at_end_of_each_step(self):
        engine = Engine()
        light = FakeLight()
        state = engine.device_state("pc")
        engine.start_flow([(255, 0, 0), (0, 0, 255)], 4, ["pc"], 100,
                          mode="sequence", transition_ms=500)
        samples = []
        for elapsed in (0, 1.0, 1.5, 1.75, 2.0):
            with patch("legacy_hwlight.engine.time.monotonic", return_value=100 + elapsed):
                engine._render("pc", light, state, elapsed, 1.0)
            samples.append(engine.frames["pc"][0])
        self.assertEqual(samples[:3], [(255, 0, 0)] * 3)
        self.assertEqual(samples[3], (128, 0, 128))
        self.assertEqual(samples[4], (0, 0, 255))

    def test_reverse_sequence_starts_without_a_jump_and_visits_colors_backwards(self):
        engine = Engine()
        light = FakeLight()
        state = engine.device_state("pc")
        engine.start_flow([(255, 0, 0), (0, 255, 0), (0, 0, 255)], 6, ["pc"], 100,
                          direction="reverse", mode="sequence", transition_ms=500)
        samples = []
        for elapsed in (0, 0.001, 2, 4):
            with patch("legacy_hwlight.engine.time.monotonic", return_value=100 + elapsed):
                engine._render("pc", light, state, elapsed, 1.0)
            samples.append(engine.frames["pc"][0])
        self.assertEqual(samples, [(255, 0, 0), (255, 0, 0),
                                   (0, 0, 255), (0, 255, 0)])

    def test_reverse_flow_moves_toward_previous_palette_color(self):
        engine = Engine()
        light = FakeLight()
        state = engine.device_state("pc")
        engine.start_flow([(255, 0, 0), (0, 255, 0), (0, 0, 255)], 6, ["pc"], 100,
                          direction="reverse")
        with patch("legacy_hwlight.engine.time.monotonic", return_value=100.5):
            engine._render("pc", light, state, 0.5, 1.0)
        red, green, blue = engine.frames["pc"][0]
        self.assertGreater(red, 0)
        self.assertEqual(green, 0)
        self.assertGreater(blue, 0)

    def test_alternate_sequence_traverses_back_without_end_jump(self):
        engine = Engine()
        light = FakeLight()
        state = engine.device_state("pc")
        # Four alternate steps at one second each: the service supplies the
        # full four-second period, not the three-color forward duration.
        engine.start_flow([(255, 0, 0), (0, 255, 0), (0, 0, 255)], 4, ["pc"], 100,
                          direction="alternate", mode="sequence", transition_ms=250)
        samples = []
        for elapsed in (0, 1, 2, 3, 4, 3.999, 4.001):
            with patch("legacy_hwlight.engine.time.monotonic", return_value=100 + elapsed):
                engine._render("pc", light, state, elapsed, 1.0)
            samples.append(engine.frames["pc"][0])
        self.assertEqual(samples[:5], [(255, 0, 0), (0, 255, 0), (0, 0, 255),
                                       (0, 255, 0), (255, 0, 0)])
        self.assertLess(max(abs(a - b) for a, b in zip(samples[5], samples[6])), 3)

    def test_alternate_continuous_flow_reverses_phase_smoothly(self):
        engine = Engine()
        light = FakeLight()
        state = engine.device_state("pc")
        engine.start_flow([(255, 0, 0), (0, 255, 0), (0, 0, 255)], 3, ["pc"], 100,
                          direction="alternate")
        samples = []
        for elapsed in (2.9, 3.1, 4.0, 5.0, 6.0):
            with patch("legacy_hwlight.engine.time.monotonic", return_value=100 + elapsed):
                engine._render("pc", light, state, elapsed, 1.0)
            samples.append(engine.frames["pc"][0])
        self.assertEqual(samples[0], samples[1])
        self.assertEqual(samples[2:], [(0, 0, 255), (0, 255, 0), (255, 0, 0)])

    def test_comet_wrap_and_chase_phase_are_continuous(self):
        p = {"color": (255, 0, 0), "speed": 1.0}
        span = 1 + max(3, 1 // 4) + 1
        wrap = span / 6.0
        before = fx_cometa(1, wrap - 0.001, p, {})[0][0]
        after = fx_cometa(1, wrap + 0.001, p, {})[0][0]
        self.assertLess(abs(before - after), 2)
        boundary = 4 / 6.0  # Old implementation switched intensity here.
        before = fx_inseguimento(1, boundary - 0.001, p, {})[0][0]
        after = fx_inseguimento(1, boundary + 0.001, p, {})[0][0]
        self.assertLess(abs(before - after), 3)

    def test_candy_stripes_change_color_without_a_step(self):
        p = {"color": (255, 0, 0), "color2": (0, 0, 255), "speed": 1.0}
        before = fx_caramella(12, 0.499, p, {})[0]
        after = fx_caramella(12, 0.501, p, {})[0]
        self.assertLess(max(abs(a - b) for a, b in zip(before, after)), 3)

    def test_heartbeat_and_rain_enter_without_full_brightness_jump(self):
        p = {"color": (255, 0, 0), "speed": 1.0}
        before = fx_batticuore(1, 1.6 - 0.0001, p, {})[0][0]
        after = fx_batticuore(1, 1.6 + 0.0001, p, {})[0][0]
        self.assertLess(abs(before - after), 8)

        rain = {"color": (0, 0, 0), "color2": (255, 0, 0), "speed": 1.0}
        with patch("legacy_hwlight.engine.random.random", return_value=1.0):
            before = fx_pioggia(1, 0, rain, {"drops": [-0.001]})[0][0]
            after = fx_pioggia(1, 0, rain, {"drops": [0.001]})[0][0]
        self.assertLess(abs(before - after), 3)


if __name__ == "__main__":
    unittest.main()
