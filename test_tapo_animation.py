"""LAN streaming behavior with a simulated Tapo device."""

from __future__ import annotations

import threading
import time
import unittest
import asyncio
import math
from types import SimpleNamespace
from unittest.mock import patch

from kasa import Module

from tapo import NativeEffectConflict, TapoController
from test_tapo_bulb_native import ORIGINAL, _Device as _BulbDevice


class _Light:
    def __init__(self):
        self.frames = []
        self.hsv = SimpleNamespace(hue=238, saturation=95, value=100)

    def has_feature(self, name):
        return name == "hsv"

    async def set_hsv(self, hue, saturation, brightness):
        self.frames.append((time.monotonic(), hue, saturation, brightness))
        self.hsv = SimpleNamespace(hue=hue, saturation=saturation, value=brightness)


class _Effect:
    has_custom_effects = True

    def __init__(self, device, *, accept=True):
        self.device = device
        self.accept = accept
        self.writes = []

    async def set_custom_effect(self, payload):
        self.writes.append(payload.copy())
        if self.accept or not payload["id"].startswith("TapoStrip_"):
            self.device.effect = payload.copy()


class _Device:
    def __init__(self):
        self.light = _Light()
        self.modules = {Module.Light: self.light}
        self.is_on = False
        self.turn_on_calls = 0
        self.disconnect_calls = 0
        self.effect = {"id": "TapoStrip_original", "name": "Mio effetto",
                       "enable": 0, "custom": 1,
                       "sequence": [[175, 93, 100], [237, 99, 100]]}

    async def turn_on(self):
        self.is_on = True
        self.turn_on_calls += 1

    async def turn_off(self):
        self.is_on = False

    async def update(self):
        pass

    async def disconnect(self):
        self.disconnect_calls += 1

    async def _query_helper(self, command):
        assert command == "get_lighting_effect"
        return {command: self.effect.copy()}


class TapoAnimationTests(unittest.TestCase):
    def test_stream_reuses_connection_and_updates_visible_state(self):
        controller = TapoController()
        controller.devices = [{"id": "bulb", "name": "Bulb", "model": "L530", "host": "127.0.0.1"}]
        device = _Device()
        connects = []

        async def connect(item):
            connects.append(item["id"])
            return device

        controller._connect = connect
        controller._snapshot = lambda item, dev: {**item, "online": True, "on": dev.is_on,
                                                 "hsv": None, "brightness": None}
        started = time.monotonic()
        worker = threading.Thread(target=controller.stream_animation,
                                  args=(["bulb"], threading.Event(),
                                        lambda elapsed, offset: {"hue": round(elapsed * 100),
                                                                 "saturation": 90, "brightness": 75},
                                        started),
                                  kwargs={"duration": 0.55, "interval": 0.1})
        worker.start()
        time.sleep(0.25)
        live_state = controller.list_devices()[0]
        self.assertEqual(live_state["brightness"], 75)
        self.assertEqual(live_state["hsv"]["saturation"], 90)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())

        self.assertEqual(connects, ["bulb"])
        self.assertEqual(device.turn_on_calls, 1)
        self.assertEqual(device.disconnect_calls, 1)
        self.assertGreaterEqual(len(device.light.frames), 4)
        self.assertLessEqual(len(device.light.frames), 7)
        self.assertTrue(all(a[1] <= b[1] for a, b in zip(device.light.frames, device.light.frames[1:])))
        self.assertTrue(controller.list_devices()[0]["on"])

    def test_phone_timer_power_off_stops_software_animation(self):
        with patch("tapo.read_json", side_effect=lambda name, default: default):
            controller = TapoController()
        controller.devices = [{"id": "bulb", "name": "Bulb", "model": "L530", "host": "127.0.0.1"}]
        device = _Device()

        async def connect(item):
            return device

        controller._connect = connect
        controller._snapshot = lambda item, dev: {**item, "online": True, "on": dev.is_on,
                                                 "brightness": 75, "effect": "Off"}
        worker = threading.Thread(
            target=controller.stream_animation,
            args=(["bulb"], threading.Event(),
                  lambda elapsed, offset: {"hue": 238, "saturation": 95, "brightness": 75},
                  time.monotonic()),
            kwargs={"duration": 0.7, "interval": 0.1, "external_probe_interval": 0.1})
        worker.start()
        time.sleep(0.25)
        device.is_on = False  # The official app's timer switched the bulb off.
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(controller.list_devices()[0]["on"])
        self.assertEqual(device.turn_on_calls, 1)

    def test_native_strip_changes_color_and_brightness_then_restores_user_effect(self):
        saved = {}
        with patch("tapo.read_json", side_effect=lambda name, default: saved.get(name, default)), \
             patch("tapo.write_json", side_effect=lambda name, value: saved.update({name: value.copy()})):
            controller = TapoController()
            controller.devices = [{"id": "strip", "name": "Strip", "model": "L900-10", "host": "127.0.0.1"}]
            device = _Device()
            original = device.effect.copy()
            device.modules[Module.LightEffect] = _Effect(device)

            async def connect(item):
                return device

            controller._connect = connect
            controller._snapshot = lambda item, dev: {**item, "online": True, "on": dev.is_on,
                                                      "effect": dev.effect["name"] if dev.effect["enable"] else "Off"}
            frames = lambda elapsed, offset: {
                "hue": round(elapsed * 60) % 360, "saturation": 95,
                "brightness": 50 if elapsed % 2 else 100,
            }
            controller.stream_animation(["strip"], threading.Event(), frames, time.monotonic(),
                                        duration=0.22, interval=0.1,
                                        native={"period": 4, "brightness": 100,
                                                "mode": "pulse", "min_brightness": 0})

            writes = device.modules[Module.LightEffect].writes
            self.assertEqual(len(writes), 3)
            self.assertEqual(writes[0]["name"], controller._NATIVE_NAME)
            self.assertEqual(writes[0]["sequence"], [[0, 95, 100], [60, 95, 50],
                                                       [120, 95, 0], [180, 95, 50]])
            self.assertEqual(writes[0]["transition"], 1000)
            self.assertEqual(writes[1]["name"], "Mio effetto")
            self.assertEqual(writes[1]["enable"], 1)
            self.assertEqual(writes[2]["enable"], 0)
            self.assertEqual(device.effect, original)
            self.assertEqual(device.light.hsv.hue, 238)
            self.assertEqual(len(device.light.frames), 1)  # static-color restoration only
            self.assertEqual(saved[controller._NATIVE_RECOVERY_FILE], {})

    def test_rejected_native_pulse_reports_error_without_lan_frames(self):
        saved = {}
        with patch("tapo.read_json", side_effect=lambda name, default: saved.get(name, default)), \
             patch("tapo.write_json", side_effect=lambda name, value: saved.update({name: value.copy()})):
            controller = TapoController()
            controller.devices = [{"id": "strip", "name": "Strip", "model": "L900-10", "host": "127.0.0.1"}]
            device = _Device()
            original = device.effect.copy()
            device.modules[Module.LightEffect] = _Effect(device, accept=False)

            async def connect(item):
                return device

            controller._connect = connect
            controller._snapshot = lambda item, dev: {**item, "online": True, "on": dev.is_on}
            errors = []
            controller.stream_animation(
                ["strip"], threading.Event(),
                lambda elapsed, offset: {"hue": 238, "saturation": 95, "brightness": 0},
                time.monotonic(), duration=0.32, interval=0.1,
                native={"period": 4, "brightness": 100, "mode": "pulse",
                        "on_error": lambda device_id, message: errors.append((device_id, message))})
            self.assertEqual(device.effect, original)
            self.assertEqual(device.light.frames, [])
            self.assertEqual(errors[0][0], "strip")
            self.assertIn("nativo", controller.list_devices()[0]["animation_error"])
            self.assertEqual(saved[controller._NATIVE_RECOVERY_FILE], {})

    def test_external_static_color_is_not_overwritten_by_native_recovery(self):
        saved = {}
        with patch("tapo.read_json", side_effect=lambda name, default: saved.get(name, default)), \
             patch("tapo.write_json", side_effect=lambda name, value: saved.update({name: value.copy()})):
            controller = TapoController()
            controller.devices = [{"id": "strip", "name": "Strip", "model": "L900-10", "host": "127.0.0.1"}]
            device = _Device()
            device.modules[Module.LightEffect] = _Effect(device)
            backup = {"temporary_id": "TapoStrip_temp", "temporary_sequence": [[238, 95, 100]],
                      "effect": device.effect.copy(),
                      "hsv": {"hue": 238, "saturation": 95, "value": 100}, "on": True}
            controller._remember_native("strip", backup)
            device.effect = {"id": "TapoStrip_temp", "name": controller._NATIVE_NAME,
                             "enable": 0, "sequence": [[238, 95, 100]]}
            device.light.hsv = SimpleNamespace(hue=120, saturation=100, value=50)
            async def no_wait(seconds):
                return None
            with patch("tapo.asyncio.sleep", side_effect=no_wait):
                asyncio.run(controller._restore_native(controller.devices[0], device, backup))
            self.assertEqual(device.light.hsv.hue, 120)
            self.assertEqual(device.effect["enable"], 0)
            self.assertEqual(len(device.modules[Module.LightEffect].writes), 2)
            self.assertEqual(device.modules[Module.LightEffect].writes[0]["name"], "Mio effetto")
            self.assertEqual(device.modules[Module.LightEffect].writes[0]["enable"], 1)
            self.assertEqual(device.modules[Module.LightEffect].writes[1]["enable"], 0)
            self.assertEqual(saved[controller._NATIVE_RECOVERY_FILE], {})

    def test_phone_effect_edit_keeps_backup_and_does_not_overwrite(self):
        saved = {}
        with patch("tapo.read_json", side_effect=lambda name, default: saved.get(name, default)), \
             patch("tapo.write_json", side_effect=lambda name, value: saved.update({name: value.copy()})):
            controller = TapoController()
            item = {"id": "strip", "name": "Strip", "model": "L900-10", "host": "127.0.0.1"}
            controller.devices = [item]
            device = _Device()
            device.modules[Module.LightEffect] = _Effect(device)
            backup = {"temporary_id": device.effect["id"],
                      "temporary_sequence": [[238, 95, 100]], "temporary_brightness": 100,
                      "effect": device.effect.copy(), "hsv": {"hue": 238, "saturation": 95,
                                                            "value": 100}, "on": True}
            controller._remember_native("strip", backup)
            device.effect = {"id": backup["temporary_id"], "name": "Nuovo effetto telefono",
                             "enable": 1, "brightness": 100,
                             "sequence": [[120, 100, 100]]}
            with self.assertRaises(NativeEffectConflict):
                asyncio.run(controller._restore_native(item, device, backup))
            self.assertEqual(device.modules[Module.LightEffect].writes, [])
            self.assertIn("strip", controller._native_recovery)

    def test_l530_native_rule_is_integrated_and_restored(self):
        saved = {}
        with patch("tapo.read_json", side_effect=lambda name, default: saved.get(name, default)), \
             patch("tapo.write_json", side_effect=lambda name, value: saved.update({name: value.copy()})):
            controller = TapoController()
            item = {"id": "bulb", "name": "Bulb", "model": "L530", "host": "127.0.0.1"}
            controller.devices = [item]
            device = _BulbDevice(controller._native_recovery)
            frame = lambda elapsed, offset: {"hue": 238, "saturation": 95,
                                             "brightness": round(50 * (1 + math.cos(
                                                 2 * math.pi * elapsed / 4)))}

            async def run():
                started = await controller._start_native_animation(
                    item, device, device.light, device.effects, frame, 0, 4, 100, "pulse", 0)
                self.assertTrue(started)
                self.assertTrue(await controller._native_still_selected(
                    device, controller._native_recovery["bulb"]))
                await controller._restore_native(item, device,
                                                 controller._native_recovery["bulb"])

            asyncio.run(run())
            self.assertEqual(device.effects.data["rule_list"][1], ORIGINAL)
            self.assertEqual(controller._native_recovery, {})
            self.assertEqual(saved[controller._NATIVE_RECOVERY_FILE], {})


if __name__ == "__main__":
    unittest.main()
