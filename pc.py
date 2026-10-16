"""PC RGB controller integrated from the user-provided HWLight application.

The desktop app owns one instance of :class:`PCController`. UI and MCP requests
must call that instance, so only one engine writes to iCUE and OpenRGB devices.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import queue
import tempfile
import threading
from typing import Any

from legacy_hwlight.backends import ICueBackend, OpenRGBBackend
from legacy_hwlight.engine import DEFAULT_DEVICE, EFFECTS, Engine, effects_info, normalize_device_state
from pc_scenes import SCENES
from storage import data_dir as default_data_dir
from mystic_light import MysticBackend
from pc_discovery import detect_msi_environment


DEFAULT_LEGACY_DIR = Path.home() / "Desktop" / "hwlight"
SCENE_MAP = {scene_id: (label, spec) for scene_id, label, spec in SCENES}
QUICK_PRESETS = {
    "all_on": "Tutto acceso",
    "all_off": "Tutto spento",
    "keyboard_only": "Tutto spento, tastiera accesa",
}
PATCH_FIELDS = frozenset(DEFAULT_DEVICE)


def _read_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8-sig") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    """Keep the previous file intact if the process exits during a write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _valid_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Il nome del profilo deve essere una stringa")
    name = name.strip()
    if not name or len(name) > 80 or any(ord(ch) < 32 for ch in name):
        raise ValueError("Nome profilo non valido (1-80 caratteri)")
    return name


def _valid_patch(patch: dict) -> dict:
    if not isinstance(patch, dict) or not patch:
        raise ValueError("La modifica deve essere un oggetto non vuoto")
    unknown = set(patch) - PATCH_FIELDS
    if unknown:
        raise ValueError(f"Campi non supportati: {', '.join(sorted(unknown))}")
    clean = {}
    for key, value in patch.items():
        if key == "on":
            if not isinstance(value, bool):
                raise ValueError("on deve essere true o false")
        elif key == "effect":
            if not isinstance(value, str) or value not in EFFECTS:
                raise ValueError("Effetto sconosciuto")
        elif key in ("color", "color2"):
            if (not isinstance(value, (list, tuple)) or len(value) != 3
                    or any(isinstance(channel, bool) or not isinstance(channel, int)
                           or not 0 <= channel <= 255 for channel in value)):
                raise ValueError(f"{key} deve contenere tre interi RGB da 0 a 255")
            value = list(value)
        elif key == "speed":
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0.2 <= value <= 4.0):
                raise ValueError("speed deve essere tra 0.2 e 4.0")
            value = float(value)
        elif key == "brightness":
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError("brightness deve essere un intero da 0 a 100")
        clean[key] = value
    return clean


def _valid_snapshot(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Snapshot non valido")
    devices = raw.get("devices", raw.get("lights", {}))
    if not isinstance(devices, dict):
        raise ValueError("Elenco dispositivi non valido")
    brightness = raw.get("global_brightness", raw.get("brightness", 100))
    if isinstance(brightness, bool) or not isinstance(brightness, int) or not 0 <= brightness <= 100:
        raise ValueError("Luminosità globale non valida")
    clean_devices = {}
    for key, state in devices.items():
        if not isinstance(key, str) or not isinstance(state, dict):
            raise ValueError("Stato dispositivo non valido")
        # Legacy snapshots may omit fields, but present fields must be valid.
        supplied = {field: value for field, value in state.items() if field in PATCH_FIELDS}
        if supplied:
            _valid_patch(supplied)
        clean_devices[key] = normalize_device_state(state)
    return {"devices": clean_devices, "global_brightness": brightness}


class PCController:
    """Thread-safe shared command surface for PC lighting and its profiles."""

    def __init__(self, data_dir: str | Path | None = None, legacy_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
        self.legacy_dir = Path(legacy_dir) if legacy_dir is not None else DEFAULT_LEGACY_DIR
        self.state_path = self.data_dir / "pc_state.json"
        self.profiles_path = self.data_dir / "pc_profiles.json"
        self._lock = threading.RLock()
        self._connect_lock = threading.Lock()
        self._ready = False
        self._busy = False
        self._message = ""
        self._autoapply = True
        self._save_timer: threading.Timer | None = None
        self._engine = Engine()
        self._platform = os.name
        settings = _read_json(self.data_dir / "settings.json")
        mystic_path = os.environ.get("SMARTLIGHT_MYSTIC_LIGHT_DLL", "")
        self._backend_mode = settings.get("pc_backend_mode", "auto")
        if self._backend_mode not in {"auto", "openrgb", "icue", "mystic"}:
            self._backend_mode = "auto"
        if os.name != "nt" and self._backend_mode in {"icue", "mystic"}:
            self._backend_mode = "auto"
        self._mystic_path = mystic_path or settings.get("mystic_light_dll", "")
        self._mystic_auto = (settings.get("mystic_light_mode", "auto") != "off"
                             and not ("pc_backend_mode" not in settings and
                                      settings.get("mystic_light_enabled") is False))
        self._mystic = None
        self._mystic_evidence = {}
        self._mystic_status = "Experimental MSI fallback awaits automatic hardware/software detection"
        self._openrgb = OpenRGBBackend(include_corsair=os.name != "nt" or self._backend_mode == "openrgb")
        self._mystic_active = False
        self._openrgb_owns_corsair = False
        self._icue = ICueBackend() if os.name == "nt" and self._backend_mode in {"auto", "icue"} else None
        if self._icue is not None:
            self._icue.on_reconnect = self._on_icue_reconnect
        self._migrate_legacy()
        saved = _read_json(self.state_path)
        try:
            snap = _valid_snapshot(saved)
        except ValueError:
            snap = {"devices": {}, "global_brightness": 100}
        self._engine.state = snap["devices"]
        self._engine.global_brightness = snap["global_brightness"]
        self._autoapply = bool(saved.get("autoapply", True))
        self._engine.start()

    def _migrate_legacy(self) -> None:
        """Copy legacy preferences once; never change the original HWLight files."""
        for source_name, destination in (("hwlight_state.json", self.state_path),
                                         ("hwlight_profili.json", self.profiles_path)):
            if destination.exists():
                continue
            source = self.legacy_dir / source_name
            if not source.is_file():
                continue
            raw = _read_json(source)
            try:
                if source_name == "hwlight_state.json":
                    migrated = {"version": 2, **_valid_snapshot(raw), "autoapply": bool(raw.get("autoapply", True))}
                else:
                    migrated = {str(name): _valid_snapshot(profile) for name, profile in raw.items()
                                if isinstance(name, str) and isinstance(profile, dict)}
            except ValueError:
                continue
            _write_json(destination, migrated)

    def _notify(self, message: str) -> None:
        self._message = message

    def _connect(self, rescan: bool = False) -> None:
        with self._connect_lock:
            self._busy = True
            try:
                found = {}
                if self._mystic_active:
                    # Stop SDK writes before attempting normal-backend discovery.
                    self._engine.set_lights({})
                    self._mystic.close()
                    self._mystic_active = False
                hold_openrgb_corsair = self._openrgb_owns_corsair and not rescan
                if self._icue is not None and not hold_openrgb_corsair:
                    try:
                        for light in self._icue.connect(log=self._notify):
                            found[light.key] = light
                    except Exception as exc:
                        self._icue.status = f"errore: {exc}"
                if self._backend_mode in {"auto", "openrgb"}:
                    # Windows normally reserves Corsair for iCUE. If that SDK
                    # finds no lights, OpenRGB may provide those devices itself.
                    # Keep a successful owner until an explicit rescan.
                    icue_found = bool(found)
                    self._openrgb.include_corsair = (self._platform != "nt" or
                                                     self._backend_mode == "openrgb" or not icue_found)
                    if self._backend_mode == "auto" and not icue_found and self._icue is not None:
                        with self._engine.lock:
                            retained = {key: light for key, light in self._engine.lights.items()
                                        if light.source != "iCUE"}
                        self._engine.set_lights(retained)
                        self._icue.release_all()
                    try:
                        lights = (self._openrgb.rescan() if rescan and self._openrgb.client
                                  else self._openrgb.connect(log=self._notify))
                        for light in lights:
                            found[light.key] = light
                    except Exception as exc:
                        self._openrgb.status = f"errore: {exc}"
                else:
                    self._openrgb.status = "Disabled: another PC backend was selected"
                self._openrgb_owns_corsair = any(
                    getattr(light, "source", "") == "OpenRGB" and
                    getattr(getattr(light, "dev", None), "name", getattr(light, "name", "")).lower().startswith("corsair")
                    for light in found.values())
                try_mystic = self._platform == "nt" and (self._backend_mode == "mystic" or
                             self._backend_mode == "auto" and (self._mystic_auto or bool(self._mystic_path)))
                if try_mystic:
                    if found and self._mystic is not None:
                        self._mystic.status = "Experimental MSI fallback idle: OpenRGB/iCUE already provide lights"
                    elif not found:
                        try:
                            self._mystic_evidence = detect_msi_environment()
                            if not self._mystic_path and not self._mystic_evidence.get("software_present"):
                                self._mystic_status = ("MSI hardware detected. Install MSI Center with Mystic Light, then search again."
                                                       if self._mystic_evidence.get("hardware_present") else
                                                       "No MSI Mystic Light installation or MSI hardware detected; automatic SDK download skipped")
                                if self._mystic is not None:
                                    self._mystic.status = self._mystic_status
                            else:
                                if self._mystic is None:
                                    self._mystic = MysticBackend(self._mystic_path, directory=self.data_dir,
                                                                evidence=self._mystic_evidence)
                                else:
                                    self._mystic.evidence = self._mystic_evidence
                                found = {light.key: light for light in self._mystic.connect(log=self._notify)}
                            self._mystic_active = bool(found)
                            with self._engine.lock:
                                for key in found:
                                    if key in self._engine.state:
                                        self._engine.state[key]["effect"] = "statico"
                            if not found and self._mystic is not None:
                                self._mystic.close()
                        except Exception as exc:
                            self._mystic_status = f"Experimental MSI backend unavailable: {exc}"
                            if self._mystic is not None:
                                self._mystic.status = self._mystic_status
                self._engine.set_lights(found)
                self._ready = True
                self._notify(f"Trovati {len(found)} blocchi luminosi PC")
            finally:
                self._busy = False

    def _on_icue_reconnect(self) -> None:
        with self._connect_lock:
            if self._mystic_active or self._openrgb_owns_corsair:
                return
            self._refresh_icue()

    def _refresh_icue(self) -> None:
        if self._icue is None:
            return
        try:
            lights = self._icue.connect(autostart=False)
            with self._engine.lock:
                found = dict(self._engine.lights)
            found.update({light.key: light for light in lights})
            self._engine.set_lights(found)
        except Exception as exc:
            self._icue.status = f"errore: {exc}"

    def connect_async(self) -> dict:
        if self._busy:
            return {"ok": False, "busy": True}
        self._busy = True
        threading.Thread(target=self._connect, daemon=True, name="smartlight-pc-connect").start()
        return {"ok": True}

    def rescan_async(self) -> dict:
        if self._busy:
            return {"ok": False, "busy": True}
        self._busy = True
        threading.Thread(target=self._connect, kwargs={"rescan": True}, daemon=True,
                         name="smartlight-pc-rescan").start()
        return {"ok": True}

    def get_status(self) -> dict:
        mystic_online = bool(self._mystic_active and self._mystic and self._mystic.healthy)
        return {"ready": self._ready, "busy": self._busy, "openrgb": self._openrgb.status,
                "backend_mode": self._backend_mode,
                "mystic_light": self._mystic.status if self._mystic else self._mystic_status,
                "mystic_light_enabled": self._mystic is not None,
                "mystic_light_detection": self._mystic_evidence,
                "mystic_light_active": mystic_online,
                "mystic_light_failed": bool(self._mystic and (self._mystic.failed or
                                                              self._mystic_active and not mystic_online)),
                "icue": self._icue.status if self._icue else "non disponibile su questo sistema", "message": self._message, "writes": self._engine.writes}

    def list_devices(self) -> list[dict]:
        with self._engine.lock:
            lights = list(self._engine.lights.values())
        order = {"Raffreddamento": 0, "Memoria": 1, "Scheda madre": 2, "Scheda video": 3, "Periferiche": 4}
        lights.sort(key=lambda light: (order.get(light.category, 9), light.name))
        return [{"key": light.key, "name": light.name, "source": light.source, "kind": light.kind,
                 "category": light.category, "led_count": light.led_count,
                 **({"experimental": True, "hardware_validated": False,
                     "online": bool(self._mystic and self._mystic.healthy),
                     "capabilities": ["static_color", "brightness", "power"]}
                    if light.source == "Mystic Light (experimental)" else {})} for light in lights]

    def get_effects(self) -> list[dict]:
        return [effect for effect in effects_info() if effect["id"] == "statico"] if self._mystic_active else effects_info()

    def get_state(self) -> dict:
        with self._engine.lock:
            return {"devices": {key: dict(state) for key, state in self._engine.state.items()},
                    "global_brightness": self._engine.global_brightness,
                    "autoapply": self._autoapply}

    def get_frames(self) -> dict:
        with self._engine.lock:
            return {key: ["#%02x%02x%02x" % tuple(color) for color in frame]
                    for key, frame in self._engine.frames.items()}

    def start_flow(self, colors: list[list[int]], period: float, keys: list[str] | None,
                   started: float, direction: str = "forward", *,
                   mode: str = "flow", brightness: int = 100,
                   transition_ms: float | None = None,
                   min_brightness: int | None = None) -> dict:
        if getattr(self, "_mystic_active", False):
            raise ValueError("Experimental MSI backend supports static colors, brightness and on/off only")
        if not isinstance(colors, list) or not 2 <= len(colors) <= 20:
            raise ValueError("Il flusso richiede da 2 a 20 colori")
        palette = []
        for color in colors:
            palette.append(tuple(_valid_patch({"color": color})["color"]))
        if (isinstance(period, bool) or not isinstance(period, (int, float))
                or not math.isfinite(period) or not 0.25 <= period <= 600):
            raise ValueError("Periodo flusso non valido")
        if direction not in {"forward", "reverse", "alternate"}:
            raise ValueError("Direzione flusso non valida")
        if isinstance(brightness, bool) or not isinstance(brightness, int) or not 0 <= brightness <= 100:
            raise ValueError("Luminosità animazione non valida")
        if min_brightness is not None and (
            isinstance(min_brightness, bool) or not isinstance(min_brightness, int)
            or not 0 <= min_brightness <= brightness
        ):
            raise ValueError("Luminosità minima animazione: 0..luminosità massima")
        if transition_ms is not None and (
            isinstance(transition_ms, bool) or not isinstance(transition_ms, (int, float))
            or not math.isfinite(transition_ms) or transition_ms < 0
        ):
            raise ValueError("Durata transizione non valida")
        available = [item["key"] for item in self.list_devices()]
        targets = keys or available
        self._check_keys(targets)
        self._engine.start_flow(palette, float(period), targets, float(started), direction,
                                mode=mode, brightness=brightness,
                                transition_ms=transition_ms,
                                min_brightness=min_brightness)
        return {"running": True, "pc_devices": len(targets)}

    def stop_flow(self) -> dict:
        self._engine.stop_flow()
        return {"running": False}

    def _check_keys(self, keys: list[str]) -> None:
        with self._engine.lock:
            unknown = set(keys) - set(self._engine.lights)
        if unknown:
            raise ValueError(f"Dispositivo PC sconosciuto: {', '.join(sorted(unknown))}")

    def set_device(self, key: str, patch: dict) -> dict:
        if not isinstance(key, str):
            raise ValueError("La chiave dispositivo deve essere una stringa")
        self._check_keys([key])
        clean = _valid_patch(patch)
        self._check_mystic_patch(clean)
        state = self._engine.update_device(key, clean)
        self._save_later()
        return dict(state)

    def apply_to(self, keys: list[str], patch: dict) -> dict:
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            raise ValueError("keys deve essere un elenco di dispositivi")
        self._check_keys(keys)
        clean = _valid_patch(patch)
        self._check_mystic_patch(clean)
        for key in dict.fromkeys(keys):
            self._engine.update_device(key, clean)
        self._save_later()
        return {"count": len(set(keys))}

    def _check_mystic_patch(self, patch: dict) -> None:
        if self._mystic_active and patch.get("effect", "statico") != "statico":
            raise ValueError("Experimental MSI backend supports static colors, brightness and on/off only")

    def set_global_brightness(self, value: int) -> dict:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise ValueError("La luminosità globale deve essere un intero da 0 a 100")
        with self._engine.lock:
            self._engine.global_brightness = value
            self._engine.invalidate()
        self._save_later()
        return {"global_brightness": value}

    def list_scenes(self) -> list[dict]:
        return ([{"id": key, "label": label, "kind": "scene"} for key, label, _ in SCENES if not self._mystic_active]
                + [{"id": key, "label": label, "kind": "quick"} for key, label in QUICK_PRESETS.items()])

    def apply_scene(self, scene_id: str) -> dict:
        if self._mystic_active and scene_id in SCENE_MAP:
            raise ValueError("Experimental MSI backend does not support animated PC scenes")
        if scene_id not in SCENE_MAP and scene_id not in QUICK_PRESETS:
            raise ValueError("Scena PC sconosciuta")
        with self._engine.lock:
            lights = dict(self._engine.lights)
        if not lights:
            return {"ok": False, "error": "Nessun dispositivo PC collegato"}
        for key, light in lights.items():
            if scene_id in SCENE_MAP:
                _, spec = SCENE_MAP[scene_id]
                patch = {**spec.get("*", {}), **spec.get(light.category, {}), "on": True}
            else:
                patch = {"on": scene_id == "all_on" or
                         (scene_id == "keyboard_only" and (light.kind or "").upper() == "KEYBOARD")}
            self._engine.update_device(key, _valid_patch(patch))
        self._save_later()
        return {"ok": True, "count": len(lights)}

    def release_icue(self) -> dict:
        if self._icue is None:
            raise ValueError("Su Linux tutti i dispositivi RGB sono controllati tramite OpenRGB")
        self._engine.submit(self._icue.release_all)
        return {"ok": True}

    def _snapshot(self) -> dict:
        state = self.get_state()
        return {"devices": state["devices"], "global_brightness": state["global_brightness"]}

    def list_profiles(self) -> list[str]:
        return sorted(_read_json(self.profiles_path))

    def save_profile(self, name: str) -> dict:
        name = _valid_name(name)
        with self._lock:
            profiles = _read_json(self.profiles_path)
            profiles[name] = self._snapshot()
            _write_json(self.profiles_path, profiles)
        return {"ok": True, "name": name}

    def load_profile(self, name: str) -> dict:
        name = _valid_name(name)
        profiles = _read_json(self.profiles_path)
        if name not in profiles:
            raise ValueError("Profilo PC inesistente")
        snapshot = _valid_snapshot(profiles[name])
        if self._mystic_active:
            for state in snapshot["devices"].values():
                self._check_mystic_patch(state)
        with self._engine.lock:
            self._engine.state.update(snapshot["devices"])
            self._engine.global_brightness = snapshot["global_brightness"]
            self._engine.invalidate()
        self._save_later()
        return {"ok": True, "name": name}

    def delete_profile(self, name: str) -> dict:
        name = _valid_name(name)
        with self._lock:
            profiles = _read_json(self.profiles_path)
            if name not in profiles:
                raise ValueError("Profilo PC inesistente")
            del profiles[name]
            _write_json(self.profiles_path, profiles)
        return {"ok": True}

    def export_data(self) -> dict:
        """Portable, credential-free PC settings for Smartlight backup bundles."""
        return {"version": 1, "state": self.get_state(), "profiles": _read_json(self.profiles_path)}

    def import_data(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Backup PC non valido")
        snapshot = _valid_snapshot(data.get("state", {}))
        if self._mystic_active:
            for state in snapshot["devices"].values():
                self._check_mystic_patch(state)
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError("Profili PC non validi")
        clean_profiles = {_valid_name(name): _valid_snapshot(profile) for name, profile in profiles.items()}
        with self._lock:
            _write_json(self.profiles_path, clean_profiles)
            with self._engine.lock:
                self._engine.state = snapshot["devices"]
                self._engine.global_brightness = snapshot["global_brightness"]
                self._engine.invalidate()
            self.save_now()
        return {"ok": True, "profiles": len(clean_profiles)}

    def _save_later(self) -> None:
        with self._lock:
            if self._save_timer:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(0.8, self.save_now)
            self._save_timer.daemon = True
            self._save_timer.start()

    def save_now(self) -> None:
        with self._lock:
            _write_json(self.state_path, {"version": 2, **self._snapshot(), "autoapply": self._autoapply})

    def drain_errors(self) -> list[str]:
        errors = []
        try:
            while True:
                errors.append(self._engine.errors.get_nowait())
        except queue.Empty:
            return errors
