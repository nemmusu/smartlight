"""Native L530 rule safety tests; no physical devices or network calls."""

from __future__ import annotations

import asyncio
import copy
import math
import unittest
from types import SimpleNamespace

from kasa import Module

from tapo_bulb_native import (BulbRuleConflict, make_bulb_rule,
                              restore_native_bulb_effect, start_native_bulb_effect)


ORIGINAL = {
    "id": "L2", "scene_name": "", "change_mode": "bln", "change_time": 2000,
    "color_status_list": [[100, 54, 6, 0], [100, 19, 39, 0]],
}


class _Effects:
    has_custom_effects = False

    def __init__(self, records):
        self.records = records
        self.data = {"enable": False, "rule_list": [
            {"id": "L1", "change_mode": "direct", "change_time": 1000,
             "color_status_list": [[100, 0, 0, 2700]], "scene_name": ""},
            copy.deepcopy(ORIGINAL),
        ]}
        self.calls = []

    async def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == "get_dynamic_light_effect_rules":
            return {method: copy.deepcopy(self.data)}
        if method == "edit_dynamic_light_effect_rule":
            # The device must never receive a write before backup is durable.
            assert "bulb" in self.records
            self.data["rule_list"][1] = copy.deepcopy(params)
            return {method: {}}
        if method == "set_dynamic_light_effect_rule_enable":
            self.data["enable"] = params["enable"]
            if params["enable"]:
                self.data["current_rule_id"] = params["id"]
            else:
                self.data.pop("current_rule_id", None)
            return {method: {}}
        raise AssertionError(method)


class _Light:
    def __init__(self):
        self.hsv = SimpleNamespace(hue=120, saturation=90, value=55)
        self.restored = []

    async def set_hsv(self, hue, saturation, value):
        self.restored.append((hue, saturation, value))


class _Device:
    def __init__(self, records):
        self.effects = _Effects(records)
        self.light = _Light()
        self.modules = {Module.LightEffect: self.effects, Module.Light: self.light}
        self.is_on = True

    async def turn_on(self):
        self.is_on = True

    async def turn_off(self):
        self.is_on = False


class NativeBulbTests(unittest.TestCase):
    item = {"id": "bulb", "host": "127.0.0.1", "model": "L530"}

    @staticmethod
    def frame_at(elapsed, offset):
        return {"hue": 120 + offset, "saturation": 85,
                "brightness": round(100 * (1 + math.cos(2 * math.pi * elapsed / 4)) / 2)}

    def test_rule_samples_zero_and_speed(self):
        fast = make_bulb_rule(ORIGINAL, self.frame_at, 0, 4)
        slow = make_bulb_rule(ORIGINAL, self.frame_at, 0, 8)
        self.assertEqual(fast["change_mode"], "bln")
        self.assertEqual(fast["change_time"], 500)
        self.assertEqual(slow["change_time"], 1000)
        self.assertEqual(len(fast["color_status_list"]), 8)
        self.assertEqual(fast["color_status_list"][4], [0, 120, 85, 0])
        self.assertEqual(ORIGINAL["color_status_list"][0][0], 100)

    def test_start_read_confirm_and_restore_original(self):
        records = {}
        device = _Device(records)
        remember = lambda key, value: records.__setitem__(key, copy.deepcopy(value))
        forget = lambda key: records.pop(key)

        async def run():
            started = await start_native_bulb_effect(self.item, device, self.frame_at,
                                                     0, 4, remember, forget)
            self.assertTrue(started)
            self.assertEqual(records["bulb"]["original_rule"], ORIGINAL)
            self.assertEqual(device.effects.data["current_rule_id"], "L2")
            self.assertEqual(device.effects.data["rule_list"][1]["color_status_list"][4][0], 0)
            await restore_native_bulb_effect(self.item, device, records["bulb"], forget)

        asyncio.run(run())
        self.assertEqual(device.effects.data["rule_list"][1], ORIGINAL)
        self.assertFalse(device.effects.data["enable"])
        self.assertEqual(device.light.restored, [(120, 90, 55)])
        self.assertEqual(records, {})

    def test_phone_edit_is_not_overwritten_and_backup_is_retained(self):
        records = {}
        device = _Device(records)
        remember = lambda key, value: records.__setitem__(key, copy.deepcopy(value))
        forget = lambda key: records.pop(key)

        async def run():
            await start_native_bulb_effect(self.item, device, self.frame_at,
                                           0, 4, remember, forget)
            device.effects.data["rule_list"][1]["scene_name"] = "Modified on phone"
            with self.assertRaises(BulbRuleConflict):
                await restore_native_bulb_effect(self.item, device, records["bulb"], forget)

        asyncio.run(run())
        self.assertEqual(device.effects.data["rule_list"][1]["scene_name"], "Modified on phone")
        self.assertIn("bulb", records)

    def test_phone_power_off_is_not_reversed_by_restore(self):
        records = {}
        device = _Device(records)
        remember = lambda key, value: records.__setitem__(key, copy.deepcopy(value))
        forget = lambda key: records.pop(key)

        async def run():
            await start_native_bulb_effect(self.item, device, self.frame_at,
                                           0, 4, remember, forget)
            device.is_on = False  # A user turned the lamp off in the phone app.
            await restore_native_bulb_effect(self.item, device, records["bulb"], forget)

        asyncio.run(run())
        self.assertFalse(device.is_on)
        self.assertEqual(device.light.restored, [])
        self.assertEqual(device.effects.data["rule_list"][1], ORIGINAL)


if __name__ == "__main__":
    unittest.main()
