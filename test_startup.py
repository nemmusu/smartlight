"""Windows Run registration and service settings tested with an isolated registry."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from service import SmartlightService
from startup import DESKTOP_FILE_NAME, RUN_KEY, VALUE_NAME, LinuxAutoStart, WindowsAutoStart, default_autostart
from test_ui_contract import MockPC, MockTapo, restore_data_dir, use_data_dir


class FakeKey:
    def __enter__(self): return self
    def __exit__(self, *args): return False


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def OpenKey(self, root, path, reserved, access):
        assert root is self.HKEY_CURRENT_USER and path == RUN_KEY
        assert access in (self.KEY_READ, self.KEY_SET_VALUE)
        return FakeKey()

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.registry = FakeRegistry()
        self.executable = r"C:\Program Files\Smartlight\Smartlight.exe"
        self.manager = WindowsAutoStart(executable=self.executable, installed=True,
                                        registry=self.registry)

    def test_register_start_hidden_then_visible_and_remove(self):
        state = self.manager.set(True, minimized=True)
        self.assertTrue(state["auto_start"])
        self.assertTrue(state["auto_start_minimized"])
        self.assertIn("--minimized-to-tray", self.registry.values[VALUE_NAME])
        state = self.manager.set(True, minimized=False)
        self.assertTrue(state["auto_start"])
        self.assertFalse(state["auto_start_minimized"])
        self.assertNotIn("--minimized-to-tray", self.registry.values[VALUE_NAME])
        state = self.manager.set(False)
        self.assertFalse(state["auto_start"])
        self.assertNotIn(VALUE_NAME, self.registry.values)

    def test_never_remove_unrelated_run_entry(self):
        self.registry.values[VALUE_NAME] = '"C:\\Other\\Smartlight.exe" --minimized-to-tray'
        self.manager.set(False)
        self.assertIn(VALUE_NAME, self.registry.values)
        self.assertFalse(self.manager.status()["auto_start"])

    def test_source_mode_cannot_enable_autostart(self):
        source = WindowsAutoStart(executable=self.executable, installed=False,
                                  registry=self.registry)
        self.assertFalse(source.status()["auto_start_available"])
        with self.assertRaisesRegex(ValueError, "Installa Smartlight"):
            source.set(True)
        source.set(False)
        self.assertEqual(self.registry.values, {})

    def test_portable_binary_is_not_treated_as_installed(self):
        with tempfile.TemporaryDirectory() as root, patch.object(sys, "frozen", True, create=True):
            application = Path(root) / "Smartlight"
            application.mkdir()
            executable = application / "Smartlight.exe"
            executable.touch()
            portable = WindowsAutoStart(executable=executable, registry=self.registry)
            self.assertFalse(portable.status()["auto_start_available"])
            (Path(root) / "Uninstall.exe").touch()
            installed = WindowsAutoStart(executable=executable, registry=self.registry)
            self.assertTrue(installed.status()["auto_start_available"])

    def test_service_status_reads_registry_and_tray_toggle_updates_command(self):
        with tempfile.TemporaryDirectory() as appdata:
            previous = use_data_dir(appdata)
            service = SmartlightService(pc=MockPC(), tapo=MockTapo(),
                                        start_workers=False, autostart=self.manager)
            try:
                self.assertFalse(service.status()["settings"]["auto_start"])
                result = service.invoke("settings_set", {"auto_start": True,
                                                         "minimize_to_tray": True})
                self.assertTrue(result["ok"], result)
                self.assertTrue(result["data"]["auto_start_minimized"])
                result = service.invoke("settings_set", {"minimize_to_tray": False})
                self.assertTrue(result["ok"], result)
                self.assertTrue(result["data"]["auto_start"])
                self.assertFalse(result["data"]["auto_start_minimized"])
                self.registry.values.pop(VALUE_NAME)
                self.assertFalse(service.status()["settings"]["auto_start"])
            finally:
                service.close()
                restore_data_dir(previous)


class LinuxAutoStartTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name) / "autostart"
        self.command = ["/usr/bin/python3", "/opt/smartlight/app.py"]
        self.manager = LinuxAutoStart(command=self.command, autostart_dir=self.directory)
        self.entry = self.directory / DESKTOP_FILE_NAME

    def test_register_start_hidden_then_visible_and_remove(self):
        state = self.manager.set(True, minimized=True)
        self.assertTrue(state["auto_start_available"])
        self.assertTrue(state["auto_start"])
        self.assertTrue(state["auto_start_minimized"])
        text = self.entry.read_text(encoding="utf-8")
        self.assertIn("Exec=/usr/bin/python3 /opt/smartlight/app.py --minimized-to-tray\n", text)
        self.assertIn("Hidden=false\n", text)
        state = self.manager.set(True, minimized=False)
        self.assertTrue(state["auto_start"])
        self.assertFalse(state["auto_start_minimized"])
        self.assertNotIn("--minimized-to-tray", self.entry.read_text(encoding="utf-8"))
        state = self.manager.set(False)
        self.assertFalse(state["auto_start"])
        self.assertFalse(self.entry.exists())

    def test_disable_when_entry_missing_is_harmless(self):
        self.assertFalse(self.manager.set(False)["auto_start"])
        self.assertFalse(self.entry.exists())

    def test_exec_quotes_paths_with_spaces_and_escapes_special_characters(self):
        manager = LinuxAutoStart(command=["/home/me/My Apps/python", "/srv/app $x.py"],
                                 autostart_dir=self.directory)
        manager.set(True, minimized=True)
        line = next(item for item in self.entry.read_text(encoding="utf-8").splitlines()
                    if item.startswith("Exec="))
        self.assertEqual(line, 'Exec="/home/me/My Apps/python" "/srv/app \\\\$x.py" --minimized-to-tray')

    def test_percent_is_escaped_for_desktop_exec(self):
        manager = LinuxAutoStart(command=["/opt/100%/python"], autostart_dir=self.directory)
        manager.set(True, minimized=False)
        self.assertIn('Exec="/opt/100%%/python"\n', self.entry.read_text(encoding="utf-8"))

    def test_unrelated_entry_without_minimized_flag_reports_visible(self):
        self.directory.mkdir(parents=True)
        self.entry.write_text("[Desktop Entry]\nExec=/usr/bin/smartlight\nHidden=false\n", encoding="utf-8")
        state = self.manager.status()
        self.assertTrue(state["auto_start"])
        self.assertFalse(state["auto_start_minimized"])

    def test_hidden_entry_is_reported_disabled(self):
        self.directory.mkdir(parents=True)
        self.entry.write_text("[Desktop Entry]\nExec=/usr/bin/smartlight --minimized-to-tray\nHidden=true\n",
                              encoding="utf-8")
        state = self.manager.status()
        self.assertFalse(state["auto_start"])
        self.assertFalse(state["auto_start_minimized"])

    def test_default_autostart_uses_xdg_config_home_on_linux(self):
        with tempfile.TemporaryDirectory() as config_home, \
                patch.object(sys, "platform", "linux"), \
                patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}):
            manager = default_autostart()
            self.assertIsInstance(manager, LinuxAutoStart)
            manager.set(True, minimized=True)
            self.assertTrue((Path(config_home) / "autostart" / DESKTOP_FILE_NAME).is_file())

    def test_default_autostart_uses_windows_backend_elsewhere(self):
        with patch.object(sys, "platform", "win32"):
            self.assertIsInstance(default_autostart(), WindowsAutoStart)

    def test_service_toggle_writes_linux_entry(self):
        with tempfile.TemporaryDirectory() as appdata:
            previous = use_data_dir(appdata)
            service = SmartlightService(pc=MockPC(), tapo=MockTapo(),
                                        start_workers=False, autostart=self.manager)
            try:
                result = service.invoke("settings_set", {"auto_start": True, "minimize_to_tray": True})
                self.assertTrue(result["ok"], result)
                self.assertTrue(result["data"]["auto_start_available"])
                self.assertTrue(result["data"]["auto_start"])
                self.assertTrue(result["data"]["auto_start_minimized"])
                self.assertTrue(self.entry.is_file())
                result = service.invoke("settings_set", {"auto_start": False})
                self.assertTrue(result["ok"], result)
                self.assertFalse(result["data"]["auto_start"])
                self.assertFalse(self.entry.exists())
            finally:
                service.close()
                restore_data_dir(previous)


if __name__ == "__main__":
    unittest.main()
