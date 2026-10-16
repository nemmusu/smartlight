"""Meaningful contract tests for user rooms and active lighting control."""

from __future__ import annotations

import os
import datetime as dt
import tempfile
import threading
import time
import unittest

from test_ui_contract import MockPC, MockTapo, restore_data_dir, use_data_dir
from service import SmartlightService


class RoomControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_data_dir = use_data_dir(self.temp.name)
        self.service = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)

    def tearDown(self):
        self.service.close()
        restore_data_dir(self.previous_data_dir)
        self.temp.cleanup()

    def call(self, command, params=None):
        result = self.service.invoke(command, params)
        self.assertTrue(result["ok"], result)
        return result["data"]

    def test_room_is_user_defined_and_static_color_only_changes_members(self):
        self.assertEqual(self.call("rooms.list"), [])
        room = self.call("rooms.save", {"name": "Scrivania", "device_ids": ["strip"],
                                        "pc_keys": ["keyboard"]})
        self.assertEqual(self.call("rooms.list"), [room])
        self.call("target.apply", {"target": "room:" + room["id"], "color": "#00ff88",
                                    "brightness": 65})
        tapo = {item["id"]: item for item in self.service.tapo.list_devices()}
        self.assertEqual(tapo["strip"]["brightness"], 65)
        self.assertEqual(tapo["bulb1"]["brightness"], 91)
        self.assertEqual(self.service.pc.state["keyboard"]["color"], [0, 255, 136])
        self.assertEqual(self.service.pc.state["mouse"]["color"], [102, 186, 255])
        self.assertEqual(self.call("modes.status")["mode"], "static")
        fresh = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)
        try:
            self.assertEqual(fresh.invoke("rooms.list")["data"], [room])
        finally:
            fresh.close()

    def test_animation_and_sync_have_one_authority(self):
        animation = self.call("animations.save", {"name": "Flusso test", "colors": ["#ff0000", "#0000ff"],
                                                  "step_ms": 500, "include_pc": True})
        self.call("sync.configure", {"mode": "pc_to_tapo", "source": "keyboard", "interval_ms": 1000})
        self.assertEqual(self.call("modes.status")["mode"], "sync")
        self.call("animations.start", {"id": animation["id"], "target": "all"})
        self.assertEqual(self.call("modes.status")["mode"], "animation")
        self.assertEqual(self.call("sync.status")["mode"], "off")
        self.call("sync.configure", {"mode": "pc_to_tapo", "source": "keyboard", "interval_ms": 1000})
        self.assertEqual(self.call("modes.status")["mode"], "sync")
        self.assertTrue(self.service._animation_stop.is_set())
        self.call("target.apply", {"target": "all", "color": "#112233"})
        self.assertEqual(self.call("sync.status")["mode"], "off")
        self.assertEqual(self.call("modes.status")["mode"], "static")

    def test_continuous_effects_sample_between_steps_and_pulse_fades(self):
        captured = []
        sampled = []
        def capture(ids, stop, frame_at, started, *, duration=None, interval=0.15, **kwargs):
            sampled.append(frame_at)
            captured.extend(frame_at(elapsed, 0) for elapsed in (0, 0.25, 0.5, 0.75, 1.0, 1.5, 1.99))
        self.service.tapo.stream_animation = capture
        for mode in ("pulse", "breathe", "flow", "gradient", "wave", "rainbow", "sequence", "cycle"):
            captured.clear()
            animation = self.call("animations.save", {
                "name": "Smooth " + mode, "colors": ["#ff0000", "#0000ff"],
                "mode": mode, "step_ms": 1000, "speed": 50,
                "brightness": 80, "transition_ms": 500, "loop": False,
            })
            result = self.call("animations.start", {"id": animation["id"], "target": "strip"})
            self.service._animation_thread.join(timeout=2)
            self.assertFalse(self.service._animation_thread.is_alive(), mode)
            self.assertEqual(len(captured), 7, mode)
            self.assertEqual(captured[0]["brightness"], 80, mode)
            if mode in {"pulse", "breathe"}:
                self.assertGreater(captured[1]["brightness"], captured[2]["brightness"])
                self.assertGreater(captured[2]["brightness"], captured[3]["brightness"])
                self.assertLess(sampled[-1](result["period_seconds"] / 2, 0)["brightness"], 25)
            if mode in {"sequence", "cycle"}:
                self.assertEqual(captured[0]["hue"], 0)
                self.assertEqual(captured[1]["hue"], 0)
                self.assertEqual(captured[3]["hue"], 300)
                self.assertEqual(captured[4]["hue"], 240)
            if mode in {"flow", "gradient", "wave", "rainbow"}:
                self.assertNotEqual(captured[0]["hue"], captured[1]["hue"])

    def test_pulse_range_and_speed_control_cycle(self):
        sampled = []
        def capture(ids, stop, frame_at, started, **kwargs):
            sampled.append(frame_at)
        self.service.tapo.stream_animation = capture
        periods = []
        for minimum, speed in ((0, 50), (60, 50), (0, 100)):
            animation = self.call("animations.save", {
                "name": f"Pulse {minimum} {speed}", "colors": ["#0088ff"],
                "mode": "pulse", "step_ms": 1000, "speed": speed,
                "brightness": 100, "min_brightness": minimum, "loop": False,
            })
            result = self.call("animations.start", {"id": animation["id"], "target": "strip"})
            self.service._animation_thread.join(timeout=2)
            periods.append(result["period_seconds"])
            self.assertEqual(sampled[-1](result["period_seconds"] / 2, 0)["brightness"], minimum)
        self.assertLess(periods[2], periods[0])

    def test_alternate_sequence_returns_through_palette(self):
        captured = []
        def capture(ids, stop, frame_at, started, *, duration=None, interval=0.15, **kwargs):
            captured.extend(frame_at(elapsed, 0) for elapsed in (0, 1, 2, 3, 4))
        self.service.tapo.stream_animation = capture
        animation = self.call("animations.save", {
            "name": "Andata ritorno", "colors": ["#ff0000", "#00ff00", "#0000ff"],
            "mode": "sequence", "direction": "alternate", "step_ms": 1000,
            "speed": 50, "transition_ms": 500, "loop": False,
        })
        result = self.call("animations.start", {"id": animation["id"], "target": "strip"})
        self.service._animation_thread.join(timeout=2)
        self.assertEqual(result["period_seconds"], 4)
        self.assertEqual([frame["hue"] for frame in captured], [0, 120, 240, 120, 0])

    def test_custom_theme_static_and_animated_scope(self):
        room = self.call("rooms.save", {"name": "Lampada e mouse", "device_ids": ["bulb2"],
                                        "pc_keys": ["mouse"]})
        theme = self.call("themes.save", {"name": "Mio tema", "colors": ["#fa6010", "#3864e2"],
                                          "mode": "static", "brightness": 43})
        self.assertIn(theme, self.call("themes.list"))
        self.call("theme_apply", {"id": theme["id"], "target": "room:" + room["id"]})
        self.assertEqual(self.service.tapo._states["bulb2"]["brightness"], 43)
        self.assertEqual(self.service.tapo._states["bulb1"]["brightness"], 91)
        self.assertEqual(self.service.pc.state["mouse"]["brightness"], 43)
        self.call("theme_apply", {"id": theme["id"], "target": "room:" + room["id"],
                                  "mode": "animated"})
        self.assertEqual(self.call("modes.status")["mode"], "animation")
        self.call("animations.stop")
        self.assertEqual(self.call("modes.status")["mode"], "idle")

    def test_timer_and_schedule_accept_room(self):
        room = self.call("rooms.save", {"name": "Camera", "device_ids": ["strip", "bulb1"],
                                        "pc_keys": ["keyboard"]})
        target = "room:" + room["id"]
        timer = self.call("timer_set", {"target": target, "minutes": 10, "action": "off"})
        self.assertEqual(timer["id"], target)
        schedule = self.call("schedules.save", {"name": "Sera", "time": "20:30", "days": [1, 2],
                                                  "target": target, "action": {"color": "#ff8811"}})
        self.assertEqual(schedule["device_id"], target)
        self.assertEqual(schedule["action"]["color"], "#ff8811")
        self.call("rooms.delete", {"id": room["id"]})
        self.assertEqual(self.call("schedules.list")[0]["device_id"], ["strip", "bulb1", "keyboard"])
        self.assertEqual(self.service.timer["id"], ["strip", "bulb1", "keyboard"])

    def test_one_time_schedule_keeps_explicit_calendar_date(self):
        date = (dt.date.today() + dt.timedelta(days=3)).isoformat()
        item = self.call("schedule_save", {"name": "Visita", "time": "19:15", "days": [],
                                            "once_date": date, "device_id": "strip",
                                            "action": {"power": False}})
        self.assertEqual(item["once_date"], date)
        edited = self.call("schedule_save", {"id": item["id"], "name": "Visita", "time": "20:00",
                                              "days": [], "device_id": "strip", "action": {"power": False}})
        self.assertEqual(edited["once_date"], date)
        invalid = self.service.invoke("schedule_save", {"name": "Nel passato", "time": "19:15",
                                                        "days": [], "once_date": "2020-01-01",
                                                        "device_id": "strip", "action": {"power": False}})
        self.assertFalse(invalid["ok"])

    def test_scene_and_backup_keep_room_scope(self):
        room = self.call("rooms.save", {"name": "Solo angolo", "device_ids": ["strip"],
                                        "pc_keys": ["keyboard"]})
        target = "room:" + room["id"]
        scene = self.call("scenes.save", {"name": "Lettura", "target": target})
        self.assertEqual(set(scene["states"]["tapo"]), {"strip"})
        self.assertEqual(set(scene["states"]["pc"]), {"keyboard"})
        self.call("target.apply", {"target": target, "color": "#112233"})
        self.call("scenes.apply", {"id": scene["id"]})
        self.assertEqual(self.service.pc.state["keyboard"]["color"], [102, 186, 255])
        self.assertEqual(self.service.pc.state["mouse"]["color"], [102, 186, 255])
        theme = self.call("themes.save", {"name": "Lettura calda", "colors": ["#ffaa55"]})
        backup = self.call("backup.export")
        self.assertTrue(backup["path"].endswith(".json"))
        self.call("rooms.delete", {"id": room["id"]})
        self.call("themes.delete", {"id": theme["id"]})
        self.call("backup.import", {"path": backup["path"]})
        self.assertIn(room, self.call("rooms.list"))
        self.assertIn(theme, self.call("themes.list"))

    def test_mcp_and_ui_commands_share_state_and_stop_continuous_mode(self):
        overview = self.call("lighting.overview")
        self.assertEqual({item["key"] for item in overview["pc"]}, {"keyboard", "mouse"})
        self.assertEqual(overview["target_syntax"], "all | room:<id> | device id/key | list of ids/keys")

        self.call("target.apply", {"target": ["strip", "keyboard"],
                                   "color": "#ee4400", "brightness": 42, "power": True})
        ui_status = self.call("status")
        self.assertEqual(ui_status["devices"][0]["hsv"]["saturation"], 100)
        self.assertEqual(ui_status["pc"]["state"]["keyboard"]["color"], [238, 68, 0])
        self.assertEqual(ui_status["pc"]["state"]["mouse"]["color"], [102, 186, 255])
        self.assertEqual(next(item for item in self.call("lighting.overview")["pc"]
                              if item["key"] == "keyboard")["state"]["color"], [238, 68, 0])

        self.call("target.apply", {"target": "keyboard", "color": "#ee4400", "power": False})
        self.assertFalse(self.call("status")["pc"]["state"]["keyboard"]["on"])

        self.call("sync.configure", {"mode": "pc_to_tapo", "source": "keyboard", "interval_ms": 1000})
        self.call("pc.apply_to", {"devices": ["keyboard"],
                                  "state": {"effect": "statico", "color": [10, 20, 30], "on": True}})
        self.assertEqual(self.call("modes.status")["mode"], "static")
        self.assertEqual(self.call("sync.status")["mode"], "off")
        self.assertEqual(self.call("status")["pc"]["state"]["keyboard"]["color"], [10, 20, 30])

    def test_external_tapo_change_reaches_ui_and_mcp_state(self):
        def external_refresh():
            self.service.tapo._states["bulb1"]["on"] = False
            return self.service.tapo.list_devices()
        self.service.tapo.refresh = external_refresh
        self.service._has_credentials = lambda: True
        self.service._tapo_poll_seconds = 0.02
        worker = threading.Thread(target=self.service._poll_tapo, daemon=True)
        worker.start()
        deadline = time.monotonic() + 1
        while self.service.tapo._states["bulb1"]["on"] and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(next(item for item in self.call("status")["devices"]
                              if item["id"] == "bulb1")["on"])
        self.assertFalse(next(item for item in self.call("lighting.overview")["tapo"]
                              if item["id"] == "bulb1")["on"])
        self.service._stop.set()
        worker.join(timeout=1)

    def test_pc_scene_and_tapo_native_preset_route_to_same_service(self):
        self.service.pc.list_scenes = lambda: [{"id": "keyboard_only", "label": "Solo tastiera"}]
        self.assertEqual(self.call("pc.scenes")[0]["id"], "keyboard_only")
        self.assertEqual(self.call("pc.scene.apply", {"id": "keyboard_only"})["scene"], "keyboard_only")
        self.assertEqual(self.call("modes.status")["mode"], "static")
        self.call("lights.set", {"device": "strip", "device_preset": "Light preset 1"})
        self.assertEqual(self.service.tapo._states["strip"]["device_preset"], "Light preset 1")


if __name__ == "__main__":
    unittest.main()
