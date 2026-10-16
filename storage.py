"""Small atomic JSON store. Secrets are deliberately excluded from backups."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Variables that decide the data directory; %APPDATA% on Windows, XDG_DATA_HOME
# elsewhere. Child processes must receive them so every Smartlight instance
# reads and writes the same folder.
DATA_DIR_ENV = ("APPDATA", "XDG_DATA_HOME")


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / "Smartlight"
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        # I file qui dentro includono segreti (token MCP): sola lettura dell'utente.
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
    return path


def data_dir_overrides() -> dict[str, str]:
    """Data-directory variables to forward to a child process, if set."""
    return {name: value for name in DATA_DIR_ENV if (value := os.environ.get(name))}


def write_secret(name: str, value: str) -> None:
    """Write a secret (token) that only the current user can read."""
    path = data_dir() / name
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            if os.name != "nt":
                os.fchmod(handle.fileno(), 0o600)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(name: str, default):
    path = data_dir() / name
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def write_json(name: str, value) -> None:
    path = data_dir() / name
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
