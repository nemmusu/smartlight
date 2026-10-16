"""Preset effect categories should retain their device scope and parameters."""

from __future__ import annotations

import os
import tempfile
import unittest

from service import SmartlightService
from test_ui_contract import MockPC, MockTapo, restore_data_dir, use_data_dir


class EffectPresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_data_dir = use_data_dir(self.temp.name)
        self.service = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)

    def tearDown(self):
        self.service.close()
        restore_data_dir(self.previous_data_dir)
        self.temp.cleanup()

    def call(self, name, params):
        reply = self.service.invoke(name, params)
        self.assertTrue(reply["ok"], reply)
        return reply["data"]

    def test_native_preset_applies_only_to_compatible_tapo(self):
        preset = self.call("presets.save", {"name": "Relax originale", "kind": "native_effect", "effect": "Relax"})
        self.call("presets.apply", {"id": preset["id"], "target": "all"})
        states = {d["id"]: d for d in self.service.tapo.list_devices()}
        self.assertEqual(states["strip"]["effect"], "Off")
        self.assertEqual(states["bulb1"]["effect"], "Relax")
        self.assertEqual(states["bulb2"]["effect"], "Relax")
        reply = self.service.invoke("presets.apply", {"id": preset["id"], "target": "strip"})
        self.assertFalse(reply["ok"])
        self.assertIn("supporta", reply["error"]["message"])

    def test_pc_preset_restores_effect_and_parameters_only_on_pc(self):
        preset = self.call("presets.save", {"name": "Onda blu", "kind": "pc_effect",
            "effect": "onda", "color": "#112233", "color2": "#aabbcc",
            "speed": 1.5, "brightness": 42})
        self.call("presets.apply", {"id": preset["id"], "target": "keyboard"})
        state = self.service.pc.state["keyboard"]
        self.assertEqual(state["effect"], "onda")
        self.assertEqual(state["color"], [17, 34, 51])
        self.assertEqual(state["color2"], [170, 187, 204])
        self.assertEqual(state["speed"], 1.5)
        self.assertEqual(state["brightness"], 42)
        self.assertEqual(self.service.pc.state["mouse"]["effect"], "statico")
        edited = self.call("presets.save", {"id": preset["id"], "name": "Onda tenue",
            "kind": "pc_effect", "effect": "onda", "color": "#112233",
            "color2": "#aabbcc", "speed": 0.8, "brightness": 20})
        self.assertEqual(edited["id"], preset["id"])
        self.assertEqual(len(self.call("presets.list", {})), 1)

    def test_invalid_effect_preset_is_rejected(self):
        for data in ({"kind": "native_effect", "effect": "Does not exist"},
                     {"kind": "pc_effect", "effect": "onda", "speed": 9},
                     {"kind": "pc_effect", "effect": "onda", "color": "not a color"}):
            reply = self.service.invoke("presets.save", {"name": "Bad", **data})
            self.assertFalse(reply["ok"], reply)


if __name__ == "__main__":
    unittest.main()
