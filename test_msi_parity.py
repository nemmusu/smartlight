"""MSI parity through the real controller, engine and service, without hardware."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pc import PCController
from legacy_hwlight.engine import EFFECTS
from service import SmartlightService
from test_ui_contract import MockTapo, use_data_dir, restore_data_dir


class SimulatedMSILight:
    source = "Mystic Light (experimental)"
    kind = "MOTHERBOARD"
    category = "Scheda madre"
    led_count = 1
    supports_software_effects = True

    def __init__(self, key="msi:test"):
        self.key = key
        self.name = key
        self.zone = {"max_speed": 5, "max_brightness": 10}
        self.calls = []

    def native_effects(self):
        return [{"style": "Breathing", **self.zone}]

    def set_native_effect(self, style, **parameters):
        self.calls.append(("native", style, parameters))
        return {"unsupported": []}

    def get_native_state(self):
        return {"style": "Breathing", "brightness": 5, "speed": 2,
                "color": [12, 34, 56], "source": "msi_sdk"}

    def set_leds(self, colors):
        self.calls.append(("frame", list(colors)))

    def off(self):
        self.calls.append(("off",))


class MSIParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = use_data_dir(self.temp.name)
        with patch("pc.Engine.start"):
            self.pc = PCController(self.temp.name, Path(self.temp.name) / "legacy")
        self.pc._save_later = lambda: None
        self.pc._mystic = SimpleNamespace(healthy=True, failed=False, status="Simulation")
        self.pc._mystic_active = True
        self.light = SimulatedMSILight()
        self.pc._engine.set_lights({self.light.key: self.light})
        self.service = SmartlightService(pc=self.pc, tapo=MockTapo(), start_workers=False)

    def tearDown(self):
        self.service.close()
        restore_data_dir(self.previous)
        self.temp.cleanup()

    def render(self, t=0):
        engine = self.pc._engine
        engine._render(self.light.key, self.light, engine.state[self.light.key],
                       t, engine.global_brightness / 100)

    def test_all_common_effects_and_flow_render_on_static_capable_zone(self):
        for effect in EFFECTS:
            with self.subTest(effect=effect):
                self.pc.set_device(self.light.key, {"effect": effect})
                self.render(0.6)
                self.assertEqual(self.light.calls[-1][0], "frame")
        self.pc.start_flow([[255, 0, 0], [0, 0, 255]], 4, [self.light.key],
                           time.monotonic(), mode="pulse", min_brightness=0)
        self.render()
        self.assertEqual(self.light.calls[-1][0], "frame")

    def test_native_writer_skips_software_frames_and_has_real_observed_state(self):
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing"})
        self.render()
        self.render()
        self.assertEqual(len(self.light.calls), 1)
        parameters = self.light.calls[0][2]
        self.assertIsNone(parameters["color"])
        self.assertIsNone(parameters["normalized_speed"])
        self.assertNotIn(self.light.key, self.pc.get_frames())
        state = self.pc.get_state()["devices"][self.light.key]
        self.assertEqual(state["native_observed"]["color"], [12, 34, 56])
        self.assertEqual(state["effect"], "msi:Breathing")

    def test_native_power_twice_global_zero_and_brightness_restore(self):
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing", "speed": 4,
                                           "brightness": 80, "color": [90, 20, 10]})
        self.render()
        self.assertEqual(self.light.calls[-1][2]["normalized_speed"], 1)
        for _ in range(2):
            self.pc.set_device(self.light.key, {"on": False})
            self.render()
            self.assertEqual(self.light.calls[-1], ("off",))
            self.pc.set_device(self.light.key, {"on": True})
            self.render()
            self.assertEqual(self.light.calls[-1][1], "Breathing")
        self.pc.set_global_brightness(0)
        self.render()
        self.assertEqual(self.light.calls[-1], ("off",))
        self.pc.set_global_brightness(50)
        self.render()
        self.assertEqual(self.light.calls[-1][2]["normalized_brightness"], 0.4)
        self.pc.set_global_brightness(100)
        self.render()
        self.assertEqual(self.light.calls[-1][2]["normalized_brightness"], 0.8)

    def test_native_profiles_round_trip_and_resume_software_control(self):
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing", "speed": 2})
        self.pc.save_profile("Evening")
        self.pc.set_device(self.light.key, {"effect": "respiro"})
        self.render()
        self.assertEqual(self.light.calls[-1][0], "frame")
        self.pc.load_profile("Evening")
        self.render()
        self.assertEqual(self.light.calls[-1][0], "native")
        self.assertEqual(self.pc.get_state()["devices"][self.light.key]["native_controls"], ["speed"])

    def test_group_validation_rejects_incompatible_native_style_before_mutation(self):
        other = SimulatedMSILight("msi:other")
        other.native_effects = lambda: []
        self.pc._engine.set_lights({self.light.key: self.light, other.key: other})
        before = self.pc.get_state()
        result = self.service.invoke("pc.apply_to", {"keys": [self.light.key, other.key],
                                                      "patch": {"effect": "msi:Breathing"}})
        self.assertFalse(result["ok"])
        self.assertEqual(before, self.pc.get_state())
        self.assertEqual(self.light.calls, [])

    def test_native_preset_schedule_uses_same_target_and_effect(self):
        room = self.service.invoke("rooms.save", {"name": "Study", "device_ids": [],
                                                   "pc_keys": [self.light.key]})
        self.assertTrue(room["ok"], room)
        preset = self.service.invoke("presets.save", {"name": "Soft light", "kind": "pc_effect",
                                                      "effect": "msi:Breathing"})
        self.assertTrue(preset["ok"], preset)
        self.assertNotIn("color2", preset["data"])
        self.assertNotIn("speed", preset["data"])
        schedule = self.service.invoke("schedules.save", {"name": "Evening", "time": "20:30",
            "target": "room:" + room["data"]["id"], "days": [1, 2, 3], "action": {"preset_id": preset["data"]["id"]}})
        self.assertTrue(schedule["ok"], schedule)
        self.service._run_schedule(schedule["data"])
        self.render()
        self.assertEqual(self.light.calls[-1][1], "Breathing")

    def test_native_only_zone_filters_software_and_rejects_flow(self):
        self.light.supports_software_effects = False
        static = next(item for item in self.pc.get_effects() if item["id"] == "statico")
        self.assertNotIn(self.light.key, static["supported_keys"])
        with self.assertRaisesRegex(ValueError, "native MSI effects only"):
            self.pc.start_flow([[255, 0, 0], [0, 0, 255]], 4, [self.light.key], time.monotonic())
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing"})
        self.render()
        self.assertEqual(self.light.calls[-1][0], "native")

    def test_native_sync_fails_with_actionable_reason(self):
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing"})
        result = self.service.invoke("sync.configure", {"mode": "pc_to_tapo", "source": self.light.key})
        self.assertFalse(result["ok"])
        self.assertIn("live RGB frames", result["error"]["message"])

    def test_off_style_is_power_only_and_startup_selects_runnable_style(self):
        self.light.supports_software_effects = False
        self.light.native_effects = lambda: [{"style": "Off"}, {"style": "Breathing"}]
        self.pc._backend_mode = "mystic"
        self.pc._platform = "nt"
        self.pc._mystic_path = "test-sdk.dll"
        self.pc._mystic_active = False
        self.pc._icue = None
        self.pc._mystic.connect = lambda **kwargs: [self.light]
        with patch("pc.detect_msi_environment", return_value={}):
            self.pc._connect()
        state = self.pc.get_state()["devices"][self.light.key]
        self.assertEqual(state["effect"], "msi:Breathing")
        self.assertNotIn("msi:Off", [item["id"] for item in self.pc.get_effects()])
        with self.assertRaisesRegex(ValueError, "power control"):
            self.pc.set_device(self.light.key, {"effect": "msi:Off"})
        self.pc.set_device(self.light.key, {"on": False})
        self.render()
        self.pc.set_device(self.light.key, {"on": True})
        self.render()
        self.assertEqual(self.light.calls[-1][1], "Breathing")

    def test_external_native_power_is_observed_without_echo_writes(self):
        self.pc.set_device(self.light.key, {"effect": "msi:Breathing"})
        with patch("legacy_hwlight.engine.time.monotonic", return_value=100):
            self.render()
        calls = len(self.light.calls)
        self.light.get_native_state = lambda: {"style": "Off", "brightness": 0}
        with patch("legacy_hwlight.engine.time.monotonic", return_value=104):
            self.render()
        state = self.pc.get_state()["devices"][self.light.key]
        self.assertTrue(state["on"])
        self.assertFalse(state["native_observed"]["power"])
        self.assertEqual(len(self.light.calls), calls)
        self.pc.set_device(self.light.key, {"on": False})
        with patch("legacy_hwlight.engine.time.monotonic", return_value=105):
            self.render()
        calls = len(self.light.calls)
        self.light.get_native_state = lambda: {"style": "Breathing", "brightness": 7}
        with patch("legacy_hwlight.engine.time.monotonic", return_value=109):
            self.render()
        state = self.pc.get_state()["devices"][self.light.key]
        self.assertFalse(state["on"])
        self.assertTrue(state["native_observed"]["power"])
        self.assertEqual(len(self.light.calls), calls)
        self.light.get_native_state = lambda: {"style": None, "brightness": None}
        with patch("legacy_hwlight.engine.time.monotonic", return_value=113):
            self.render()
        self.assertIsNone(self.pc.get_state()["devices"][self.light.key]["native_observed"]["power"])


if __name__ == "__main__":
    unittest.main()
