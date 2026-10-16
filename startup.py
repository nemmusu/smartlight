"""Per-user autostart: Windows Run key (installed EXE) and XDG autostart entry (Linux)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Smartlight"
TRAY_ARG = "--minimized-to-tray"


class WindowsAutoStart:
    def __init__(self, *, executable: str | Path | None = None,
                 installed: bool | None = None, registry=None):
        self.executable = Path(executable or sys.executable).resolve()
        # The portable build also has a frozen executable. Only a setup install
        # contains the uninstaller beside the Smartlight application directory.
        self.installed = (bool(installed) if installed is not None else
                          bool(getattr(sys, "frozen", False)) and
                          (self.executable.parent.parent / "Uninstall.exe").is_file())
        if registry is None:
            try:
                import winreg
                registry = winreg
            except ImportError:  # Linux/macOS: nessun registro Windows.
                registry = None
        self.registry = registry

    def _read_value(self) -> str | None:
        try:
            with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, RUN_KEY, 0,
                                       self.registry.KEY_READ) as key:
                value, _ = self.registry.QueryValueEx(key, VALUE_NAME)
                return value if isinstance(value, str) else None
        except FileNotFoundError:
            return None

    def _is_ours(self, value: str | None) -> bool:
        if not value:
            return False
        match = re.match(r'^\s*"([^"]+)"(?:\s+|$)', value)
        if not match:
            return False
        try:
            return str(Path(match.group(1)).resolve()).casefold() == str(self.executable).casefold()
        except (OSError, ValueError):
            return False

    def status(self) -> dict:
        try:
            value = self._read_value() if self.registry is not None else None
            ours = self.installed and self._is_ours(value)
            return {"auto_start_available": self.installed,
                    "auto_start": ours,
                    "auto_start_minimized": bool(ours and TRAY_ARG in value.split())}
        except OSError as exc:
            return {"auto_start_available": False, "auto_start": False,
                    "auto_start_minimized": False, "auto_start_error": str(exc)}

    def set(self, enabled: bool, *, minimized: bool = True) -> dict:
        if self.registry is None:
            raise ValueError("L'avvio automatico con il sistema non è disponibile su questo sistema operativo")
        if not self.installed:
            if enabled:
                raise ValueError("Installa Smartlight con il setup per attivare l'avvio con Windows")
            return self.status()
        value = self._read_value()
        if enabled:
            command = f'"{self.executable}"' + (f" {TRAY_ARG}" if minimized else "")
            with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, RUN_KEY, 0,
                                       self.registry.KEY_SET_VALUE) as key:
                self.registry.SetValueEx(key, VALUE_NAME, 0, self.registry.REG_SZ, command)
        elif self._is_ours(value):
            with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, RUN_KEY, 0,
                                       self.registry.KEY_SET_VALUE) as key:
                try:
                    self.registry.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return self.status()


DESKTOP_FILE_NAME = "smartlight.desktop"
_SAFE_EXEC_ARG = re.compile(r"^[A-Za-z0-9_./:=,+@-]+$")
_QUOTED_EXEC_SPECIAL = re.compile(r'(["`$\\])')


def _desktop_exec(args: list[str]) -> str:
    """Build an Exec= value: quote arguments as needed, then escape backslashes for the file."""
    parts = []
    for arg in args:
        if _SAFE_EXEC_ARG.match(arg):
            parts.append(arg)
        else:
            escaped = _QUOTED_EXEC_SPECIAL.sub(r"\\\1", arg).replace("%", "%%")
            parts.append(f'"{escaped}"')
    return " ".join(parts).replace("\\", "\\\\")


def _linux_launch_command() -> list[str]:
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        # In an AppImage sys.executable points inside the temporary mount, so use the file itself.
        return [appimage]
    return [os.path.abspath(sys.executable), str(Path(__file__).resolve().parent / "app.py")]


class LinuxAutoStart:
    """Start Smartlight with the desktop session through an XDG autostart entry."""

    def __init__(self, *, command: list[str] | None = None,
                 autostart_dir: str | Path | None = None):
        self.command = list(command) if command else _linux_launch_command()
        config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
        self.directory = Path(autostart_dir) if autostart_dir else Path(config_home) / "autostart"
        self.path = self.directory / DESKTOP_FILE_NAME

    def _read_entry(self) -> dict | None:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        entry: dict[str, str] = {}
        for line in text.splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() and key.strip() not in entry:
                entry[key.strip()] = value.strip()
        return entry

    def status(self) -> dict:
        try:
            entry = self._read_entry()
            enabled = entry is not None and entry.get("Hidden", "false").lower() != "true"
            minimized = enabled and TRAY_ARG in entry.get("Exec", "").split()
            return {"auto_start_available": True, "auto_start": enabled,
                    "auto_start_minimized": minimized}
        except OSError as exc:
            return {"auto_start_available": False, "auto_start": False,
                    "auto_start_minimized": False, "auto_start_error": str(exc)}

    def set(self, enabled: bool, *, minimized: bool = True) -> dict:
        if not enabled:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            return self.status()
        args = self.command + ([TRAY_ARG] if minimized else [])
        text = ("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Smartlight\n"
                "GenericName=Luci e RGB\n"
                "Comment=Avvio di Smartlight all'accesso\n"
                f"Exec={_desktop_exec(args)}\n"
                "Icon=smartlight\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Hidden=false\n")
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(DESKTOP_FILE_NAME + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, self.path)
        return self.status()


def default_autostart():
    """Pick the autostart backend for the running platform."""
    if sys.platform.startswith("linux"):
        return LinuxAutoStart()
    return WindowsAutoStart()
