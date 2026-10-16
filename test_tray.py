"""Tray lifecycle and quick-action contract without touching real hardware."""

from __future__ import annotations

import threading
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import DesktopApi
from tray import TrayController


class FakeEvents:
    def __init__(self):
        self.closing = FakeEvent()


class FakeEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class FakeWindow:
    def __init__(self):
        self.events = FakeEvents()
        self.calls = []

    def hide(self): self.calls.append("hide")
    def show(self): self.calls.append("show")
    def restore(self): self.calls.append("restore")
    def destroy(self): self.calls.append("destroy")


class FakePC:
    def list_devices(self): return [{"key": "keyboard"}, {"key": "mouse"}]


class FakeService:
    def __init__(self):
        self.settings = {"minimize_to_tray": True}
        self.pc = FakePC()
        self.calls = []

    def invoke(self, command, params=None):
        self.calls.append((command, params))
        return {"ok": True, "data": {}}


class TrayTests(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.window = FakeWindow()
        self.tray = TrayController(self.service, self.window, Path("ui/smartlight.ico"))

    def test_close_hides_only_when_tray_is_ready_and_setting_enabled(self):
        self.assertTrue(self.tray._on_closing())
        self.tray._ready.set()
        self.assertFalse(self.tray._on_closing())
        for _ in range(100):
            if "hide" in self.window.calls:
                break
            threading.Event().wait(0.01)
        self.assertEqual(self.window.calls, ["hide"])
        self.tray.open()
        self.assertEqual(self.window.calls[-2:], ["show", "restore"])
        self.service.settings["minimize_to_tray"] = False
        self.assertTrue(self.tray._on_closing())

    def test_exit_bypasses_close_veto(self):
        self.tray._ready.set()
        self.tray.request_exit()
        self.assertEqual(self.window.calls, ["destroy"])
        self.assertTrue(self.tray._on_closing())

    def test_quick_power_commands_target_correct_devices(self):
        self.tray._set_power("all", False)
        self.tray._set_power("tapo", True)
        self.tray._set_power("pc", False)
        self.assertEqual(self.service.calls, [
            ("target.apply", {"target": "all", "power": False}),
            ("device_set", {"id": "all", "power": True}),
            ("target.apply", {"target": ["keyboard", "mouse"], "power": False}),
        ])

    def test_desktop_exit_returns_before_destroy(self):
        api = DesktopApi(self.service)
        finished = threading.Event()
        api._set_exit_handler(finished.set)
        response = api.invoke("app.exit")
        self.assertEqual(response, {"ok": True, "data": {"exiting": True}})
        self.assertTrue(finished.wait(2))

    def test_power_clicks_execute_in_order_without_overlapping(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []

        def invoke(command, params):
            calls.append(params["power"])
            if len(calls) == 1:
                entered.set()
                self.assertTrue(release.wait(2))
            return {"ok": True}

        self.service.invoke = invoke
        self.tray._submit("pc", False)
        self.assertTrue(entered.wait(2))
        self.tray._submit("pc", True)
        self.tray._submit("pc", False)
        self.assertEqual(calls, [False])
        release.set()
        self.tray._commands.join()
        self.assertEqual(calls, [False, True, False])

    def test_autostart_hides_only_after_tray_icon_is_ready(self):
        class FakeIcon:
            def __init__(self, *args): self.visible = False
            def run_detached(self, setup): setup(self)
            def stop(self): pass

        self.tray.launch_hidden = True
        with patch.dict(os.environ, {"PYSTRAY_BACKEND": "dummy"}), patch("pystray.Icon", FakeIcon):
            self.tray.start()
        self.assertTrue(self.tray._ready.is_set())
        self.assertEqual(self.window.calls, ["hide"])
        self.tray.stop()

        self.window.calls.clear()
        self.service.settings["minimize_to_tray"] = False
        with patch.dict(os.environ, {"PYSTRAY_BACKEND": "dummy"}), patch("pystray.Icon", FakeIcon):
            self.tray.start()
        self.assertEqual(self.window.calls, [])
        self.tray.stop()

    def test_language_change_rebuilds_the_native_menu_without_restart(self):
        updated = threading.Event()
        class FakeIcon:
            def update_menu(self): updated.set()
        icon = FakeIcon()
        self.tray._icon = icon
        self.tray._ready.set()
        # Start from Italian and change preferences as UI/MCP would.
        self.service.settings['language'] = 'it'
        thread = threading.Thread(target=self.tray._watch_language, args=(icon,), daemon=True)
        thread.start()
        self.service.settings['language'] = 'en'
        self.assertTrue(updated.wait(2), 'Native menu must refresh after an external language change')
        self.tray._exiting.set()
        thread.join(1)

if __name__ == "__main__":
    unittest.main()
