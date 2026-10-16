"""Single command router shared by the desktop UI and authenticated MCP bridge."""

from __future__ import annotations

import colorsys
import copy
import datetime as dt
import json
import math
import os
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pc import PCController
from storage import data_dir, read_json, write_json
from startup import WindowsAutoStart, default_autostart
from tapo import TapoController


THEMES = [
    {"id": "aurora", "name": "Aurora", "description": "Blu, turchese e viola in movimento",
     "colors": ["#126de8", "#26dbc9", "#8c4ee8"], "pc_scene": "sc_aurora", "brightness": 75},
    {"id": "tramonto", "name": "Tramonto", "description": "Ambra e rosa caldi",
     "colors": ["#ff9a3d", "#e64d7d", "#703b9c"], "pc_scene": "sc_tramonto", "brightness": 70},
    {"id": "festa", "name": "Festa", "description": "Colori vividi e ritmo alto",
     "colors": ["#ff3c8e", "#ffbd3f", "#36d7e8"], "pc_scene": "sc_festa", "brightness": 100},
    {"id": "notte", "name": "Notte", "description": "Luce soffusa viola e blu",
     "colors": ["#381373", "#133885"], "pc_scene": "sc_notte", "brightness": 22},
    {"id": "ghiaccio", "name": "Ghiaccio", "description": "Azzurri freddi e bianco",
     "colors": ["#4fc7ff", "#b5efff", "#2364d5"], "pc_scene": "sc_ghiaccio", "brightness": 85},
]


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _valid_name(value) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise ValueError("Nome obbligatorio (massimo 80 caratteri)")
    return value.strip()


def _pick(items: list[dict], identifier: str) -> dict:
    for item in items:
        if item.get("id") == identifier or item.get("name") == identifier:
            return item
    raise ValueError("Elemento non trovato")


def _hex_hsv(color: str) -> tuple[int, int, int]:
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        raise ValueError("Colore HEX non valido")
    try:
        rgb = [int(color[n:n+2], 16) / 255 for n in (1, 3, 5)]
    except ValueError as exc:
        raise ValueError("Colore HEX non valido") from exc
    hue, sat, val = colorsys.rgb_to_hsv(*rgb)
    return round(hue * 360), round(sat * 100), max(1, round(val * 100))


def _smooth_pulse_level(elapsed: float, period: float, mode: str,
                        minimum: float | None = None) -> float:
    """A continuous envelope shared by the Tapo and PC animation engines."""
    floor = (0.25 if mode == "pulse" else 0.15) if minimum is None else minimum
    return floor + (1.0 - floor) * (1.0 + math.cos(2.0 * math.pi * elapsed / period)) / 2.0


class SmartlightService:
    def __init__(self, *, pc: PCController | None = None, tapo: TapoController | None = None,
                 start_workers: bool = True, autostart: WindowsAutoStart | None = None):
        self.pc = pc or PCController()
        self.tapo = tapo or TapoController()
        self.autostart = autostart or default_autostart()
        self._lock = threading.RLock()
        self.presets = read_json("presets.json", [])
        self.animations = read_json("animations.json", [])
        self.scenes = read_json("scenes.json", [])
        self.schedules = read_json("schedules.json", [])
        self.rooms = read_json("rooms.json", [])
        self.custom_themes = read_json("custom_themes.json", [])
        self.settings = read_json("settings.json", {
            "auto_start": False, "minimize_to_tray": True, "restore_scene": False,
            "mcp_auto_start": False, "mcp_scope": "local", "language": "en"})
        self.settings.setdefault("language", "en")
        self.settings.setdefault("pc_backend_mode", "auto")
        self.sync = read_json("sync.json", {"mode": "off", "source": "auto", "interval_ms": 1000})
        self.timer: dict = {}
        self.away: dict = {}
        self._animation_stop = threading.Event()
        self._animation_thread: threading.Thread | None = None
        self._mode_write_lock = threading.RLock()
        self.controller = {"mode": "idle", "label": "Nessun controllo continuo"}
        if self.sync.get("mode") == "pc_to_tapo":
            self.controller = {"mode": "sync", "label": "PC → Tapo",
                               "source": self.sync.get("source", "auto"),
                               "target": self.sync.get("target", "all")}
        self._stop = threading.Event()
        self._last_schedule: dict[str, str] = {}
        self._last_sync = 0.0
        self._next_away = 0.0
        self._tapo_poll_seconds = 10.0
        if start_workers:
            self.pc.connect_async()
            threading.Thread(target=self.tapo.refresh, daemon=True, name="smartlight-tapo-refresh").start()
            threading.Thread(target=self._poll_tapo, daemon=True, name="smartlight-tapo-poll").start()
            threading.Thread(target=self._worker, daemon=True, name="smartlight-automation").start()
            if self.settings.get("restore_scene"):
                threading.Thread(target=self._restore_last_scene, daemon=True,
                                 name="smartlight-restore-scene").start()

    def close(self):
        self._stop.set()
        self._animation_stop.set()
        self.pc.save_now()

    def _mystic_static_only(self):
        state = self.pc.get_status()
        return state.get("mystic_light_active") or state.get("mystic_light_failed")

    def _poll_tapo(self):
        """Reconcile changes made by the Tapo app, timers, or physical switches."""
        while not self._stop.wait(self._tapo_poll_seconds):
            if self.controller.get("mode") == "animation" or not self._has_credentials():
                continue
            try:
                self.tapo.refresh()
            except Exception:
                pass

    def _restore_last_scene(self):
        record = read_json("last_scene.json", {})
        if record.get("id"):
            time.sleep(4)
            try:
                self._apply_scene(record["id"])
            except Exception:
                pass

    def _pc_data(self) -> dict:
        return {"devices": self.pc.list_devices(), "status": self.pc.get_status(),
                "state": self.pc.get_state(), "effects": self.pc.get_effects(),
                "profiles": self.pc.list_profiles(), "scenes": self.pc.list_scenes(),
                "frames": self.pc.get_frames()}

    def status(self) -> dict:
        return {"devices": self.tapo.list_devices(), "pc": self._pc_data(),
                "presets": self.presets, "animations": self.animations,
                "scenes": self.scenes, "themes": self._themes(), "schedules": self.schedules,
                "rooms": self.rooms, "controller": self.controller,
                "sync": self.sync, "timer": self.timer, "away": self.away,
                "settings": {**self.settings, **self.autostart.status(),
                             "tapo_account_configured": self._has_credentials(), "os": os.name}}

    def _has_credentials(self) -> bool:
        try:
            self.tapo.credentials()
            return True
        except Exception:
            return False

    def _themes(self) -> list[dict]:
        return [*THEMES, *self.custom_themes]

    def _resolve_target(self, target) -> dict[str, list[str]]:
        """Resolve a saved room or a selection into unique Tapo and PC identifiers."""
        if target is None:
            target = "all"
        if isinstance(target, list):
            if not target or len(target) > 64:
                raise ValueError("Seleziona almeno un dispositivo")
            parts = [self._resolve_target(item) for item in target]
            return {kind: list(dict.fromkeys(value for part in parts for value in part[kind]))
                    for kind in ("tapo", "pc")}
        if not isinstance(target, str):
            raise ValueError("Destinazione non valida")
        if target == "all":
            return {"tapo": [item["id"] for item in self.tapo.devices],
                    "pc": [item["key"] for item in self.pc.list_devices()]}
        if target.startswith("room:"):
            room = _pick(self.rooms, target[5:])
            available_tapo = {item["id"] for item in self.tapo.devices}
            available_pc = {item["key"] for item in self.pc.list_devices()}
            return {"tapo": [key for key in room["device_ids"] if key in available_tapo],
                    "pc": [key for key in room["pc_keys"] if key in available_pc]}
        if target in {item["id"] for item in self.tapo.devices}:
            return {"tapo": [target], "pc": []}
        if target in {item["key"] for item in self.pc.list_devices()}:
            return {"tapo": [], "pc": [target]}
        raise ValueError(f"Dispositivo o stanza sconosciuti: {target}")

    def _targets(self, identifier) -> list[str]:
        return self._resolve_target(identifier)["tapo"]

    def _save_room(self, p: dict) -> dict:
        device_ids = p.get("device_ids", [])
        pc_keys = p.get("pc_keys", [])
        if not isinstance(device_ids, list) or not isinstance(pc_keys, list):
            raise ValueError("Dispositivi della stanza non validi")
        if len(device_ids) + len(pc_keys) > 64:
            raise ValueError("Massimo 64 dispositivi per stanza")
        if any(not isinstance(key, str) for key in [*device_ids, *pc_keys]):
            raise ValueError("Dispositivi della stanza non validi")
        available_tapo = {item["id"] for item in self.tapo.devices}
        available_pc = {item["key"] for item in self.pc.list_devices()}
        pc_state = self.pc.get_state()
        if isinstance(pc_state, dict) and isinstance(pc_state.get("devices"), dict):
            available_pc.update(pc_state["devices"])
        if p.get("id"):
            previous = next((room for room in self.rooms if room["id"] == p["id"]), None)
            if previous:
                available_pc.update(previous.get("pc_keys", []))
        unknown = (set(device_ids) - available_tapo) | (set(pc_keys) - available_pc)
        if unknown:
            raise ValueError("Dispositivi sconosciuti: " + ", ".join(sorted(unknown)))
        if not device_ids and not pc_keys:
            raise ValueError("Aggiungi almeno un dispositivo alla stanza")
        name = _valid_name(p.get("name"))
        if any(room["name"].casefold() == name.casefold() and room["id"] != p.get("id")
               for room in self.rooms):
            raise ValueError("Esiste già una stanza con questo nome")
        if p.get("id") and not any(room["id"] == p["id"] for room in self.rooms):
            raise ValueError("Stanza da modificare non trovata")
        item = {"id": p.get("id"), "name": name,
                "device_ids": list(dict.fromkeys(device_ids)), "pc_keys": list(dict.fromkeys(pc_keys))}
        return self._save_collection("rooms.json", item, self.rooms)

    def _delete_room(self, identifier: str) -> dict:
        room = _pick(self.rooms, identifier)
        token = "room:" + room["id"]
        members = list(dict.fromkeys([*room["device_ids"], *room["pc_keys"]]))
        # Preserve existing automations as an explicit selection when their room is removed.
        for schedule in self.schedules:
            if schedule.get("device_id") == token:
                schedule["device_id"] = members
        write_json("schedules.json", self.schedules)
        for scene in self.scenes:
            if scene.get("target") == token:
                scene["target"] = members
        write_json("scenes.json", self.scenes)
        for preset in self.presets:
            if preset.get("device_id") == token:
                preset["device_id"] = members
        write_json("presets.json", self.presets)
        for runtime in (self.timer, self.away):
            if runtime.get("id") == token:
                runtime["id"] = members
        if self.sync.get("target") == token:
            self.sync["target"] = members
            write_json("sync.json", self.sync)
        if self.controller.get("target") == token:
            self.controller["target"] = members
        return self._delete_collection("rooms.json", room["id"], self.rooms)

    def _stop_continuous(self):
        self._animation_stop.set()
        running = self._animation_thread
        if running and running.is_alive() and threading.current_thread() is not running:
            running.join(timeout=12)
        self.pc.stop_flow()
        with self._mode_write_lock:
            if self.sync.get("mode") != "off":
                self.sync["mode"] = "off"
                write_json("sync.json", self.sync)
        self.controller = {"mode": "idle", "label": "Nessun controllo continuo"}

    def _apply_target(self, target, patch: dict) -> dict:
        resolved = self._resolve_target(target)
        if not any(resolved.values()):
            raise ValueError("La destinazione non contiene dispositivi disponibili")
        color = patch.get("color")
        if color is not None:
            hue, saturation, _ = _hex_hsv(color)
            rgb = [int(color[n:n+2], 16) for n in (1, 3, 5)]
        elif "hue" in patch or "saturation" in patch:
            rgbf = colorsys.hsv_to_rgb(patch.get("hue", 0) / 360,
                                       patch.get("saturation", 100) / 100, 1)
            rgb = [round(channel * 255) for channel in rgbf]
        tapo_patch = {key: value for key, value in patch.items()
                      if key in {"power", "brightness", "hue", "saturation", "temperature", "effect", "device_preset"}}
        if color is not None:
            tapo_patch.update({"hue": hue, "saturation": saturation})
        pc_patch = {}
        if "power" in patch: pc_patch["on"] = patch["power"]
        if "brightness" in patch: pc_patch["brightness"] = patch["brightness"]
        if color is not None or "hue" in patch or "saturation" in patch:
            pc_patch.update({"color": rgb, "effect": "statico", "on": patch.get("power", True)})
        result = {"target": target, "tapo": {}, "pc": None}
        if resolved["tapo"] and tapo_patch:
            result["tapo"] = self.tapo.set_group(resolved["tapo"], tapo_patch)
        if resolved["pc"] and pc_patch:
            result["pc"] = self.pc.apply_to(resolved["pc"], pc_patch)
        if any(not item["ok"] for item in result["tapo"].values()):
            failures = [f"{key}: {item.get('error', 'errore sconosciuto')}"
                        for key, item in result["tapo"].items() if not item["ok"]]
            raise RuntimeError("; ".join(failures))
        return result

    def _apply_light(self, target: str, patch: dict) -> dict:
        ids = self._targets(target)
        if not ids:
            raise ValueError("La destinazione non contiene luci Tapo")
        result = self.tapo.set_group(ids, patch)
        if any(not item["ok"] for item in result.values()):
            failures = [f"{key}: {value['error']}" for key, value in result.items() if not value["ok"]]
            raise RuntimeError("; ".join(failures))
        return result

    def _save_collection(self, filename: str, item: dict, current: list[dict]) -> dict:
        with self._lock:
            item = dict(item)
            item["id"] = item.get("id") or _id()
            matches = [existing for existing in current if existing.get("id") == item["id"]]
            if matches:
                current[current.index(matches[0])] = item
            else:
                current.append(item)
            write_json(filename, current)
        return item

    def _delete_collection(self, filename: str, identifier: str, current: list[dict]) -> dict:
        item = _pick(current, identifier)
        current.remove(item)
        write_json(filename, current)
        return {"deleted": item["id"]}

    def _save_preset(self, p: dict) -> dict:
        name = _valid_name(p.get("name"))
        state = p.get("state") or {}
        kind = p.get("kind", state.get("kind", "color"))
        if kind == "native_effect":
            effect = p.get("effect") or state.get("effect")
            available = {label for device in self.tapo.list_devices()
                         for label in device.get("effects", []) if label != "Off"}
            if not isinstance(effect, str) or effect not in available:
                raise ValueError("Scegli un effetto Tapo disponibile")
            return self._save_collection("presets.json", {"id": p.get("id"), "name": name,
                "kind": kind, "effect": effect}, self.presets)
        if kind == "pc_effect":
            effect = p.get("effect") or state.get("effect")
            if effect not in {item["id"] for item in self.pc.get_effects()}:
                raise ValueError("Scegli un effetto PC disponibile")
            color = p.get("color", state.get("color", "#64b6ff"))
            color2 = p.get("color2", state.get("color2", "#ffb86b"))
            _hex_hsv(color); _hex_hsv(color2)
            speed = p.get("speed", state.get("speed", 1))
            brightness = p.get("brightness", state.get("brightness", 100))
            if (isinstance(speed, bool) or not isinstance(speed, (int, float))
                    or not math.isfinite(speed) or not 0.2 <= speed <= 4):
                raise ValueError("Velocità PC non valida (0,2–4)")
            if (isinstance(brightness, bool) or not isinstance(brightness, int)
                    or not 0 <= brightness <= 100):
                raise ValueError("Luminosità PC non valida (0–100)")
            return self._save_collection("presets.json", {"id": p.get("id"), "name": name,
                "kind": kind, "effect": effect, "color": color, "color2": color2,
                "speed": float(speed), "brightness": brightness}, self.presets)
        if kind == "animation":
            animation = _pick(self.animations, p.get("animation_id") or state["animation_id"])
            return self._save_collection("presets.json", {"id": p.get("id"), "name": name,
                "kind": kind, "animation_id": animation["id"], "color": animation["colors"][0]}, self.presets)
        if kind == "theme":
            theme = _pick(self._themes(), p.get("theme_id") or state["theme_id"])
            return self._save_collection("presets.json", {"id": p.get("id"), "name": name,
                "kind": kind, "theme_id": theme["id"], "color": theme["colors"][0]}, self.presets)
        if kind != "color":
            raise ValueError("Tipo di preset non valido")
        hue = p.get("hue", state.get("hue"))
        sat = p.get("saturation", state.get("saturation"))
        bright = p.get("brightness", state.get("brightness", 100))
        color = p.get("color", state.get("color"))
        if color:
            hue, sat, _ = _hex_hsv(color)
        if hue is None or sat is None:
            raise ValueError("Seleziona un colore per il preset")
        if not (isinstance(hue, int) and 0 <= hue <= 360 and isinstance(sat, int) and 0 <= sat <= 100
                and isinstance(bright, int) and 1 <= bright <= 100):
            raise ValueError("Colore o luminosità del preset non validi")
        return self._save_collection("presets.json", {"id": p.get("id"), "name": name,
                                      "device_id": p.get("device_id") or p.get("device") or "all",
                                      "color": color, "hue": hue, "saturation": sat,
                                      "brightness": bright}, self.presets)

    def _save_animation(self, p: dict) -> dict:
        definition = p.get("definition", p)
        if not isinstance(definition, dict):
            raise ValueError("Definizione animazione non valida")
        colors = definition.get("colors") or definition.get("palette")
        if not isinstance(colors, list) or not 1 <= len(colors) <= 20:
            raise ValueError("L'animazione richiede da 1 a 20 colori")
        for color in colors:
            _hex_hsv(color)
        step_ms = int(definition.get("step_ms", 1000))
        if not 500 <= step_ms <= 60000:
            raise ValueError("Intervallo animazione: 500–60000 ms")
        transition_ms = definition.get("transition_ms", 500)
        if (isinstance(transition_ms, bool) or not isinstance(transition_ms, int)
                or not 0 <= transition_ms <= 10000):
            raise ValueError("Transizione: 0–10000 ms")
        mode = definition.get("mode", "cycle")
        if mode not in {"flow", "cycle", "pulse", "random", "wave", "static", "sequence", "breathe", "gradient", "rainbow", "flash"}:
            raise ValueError("Tipo di animazione non supportato")
        speed = definition.get("speed", 50)
        brightness = definition.get("brightness", 100)
        direction = definition.get("direction", "forward")
        if not isinstance(speed, (int, float)) or not 1 <= speed <= 100:
            raise ValueError("Velocità animazione: 1–100")
        if not isinstance(brightness, int) or not 1 <= brightness <= 100:
            raise ValueError("Luminosità animazione: 1–100")
        min_brightness = definition.get("min_brightness", 0)
        if (isinstance(min_brightness, bool) or not isinstance(min_brightness, int)
                or not 0 <= min_brightness <= brightness):
            raise ValueError("Luminosità minima animazione: 0–luminosità massima")
        if direction not in {"forward", "reverse", "alternate"}:
            raise ValueError("Direzione animazione non valida")
        item = {"id": p.get("id") or definition.get("id"), "name": _valid_name(p.get("name") or definition.get("name")),
                "colors": colors, "step_ms": step_ms, "mode": mode,
                "speed": speed, "brightness": brightness,
                "min_brightness": min_brightness,
                "direction": direction, "loop": bool(definition.get("loop", True)),
                "transition_ms": transition_ms,
                "include_pc": bool(definition.get("include_pc", False))}
        return self._save_collection("animations.json", item, self.animations)

    def _save_theme(self, p: dict) -> dict:
        name = _valid_name(p.get("name"))
        if p.get("id") and any(theme["id"] == p["id"] for theme in THEMES):
            raise ValueError("I temi predefiniti non si modificano")
        if p.get("id") and not any(theme["id"] == p["id"] for theme in self.custom_themes):
            raise ValueError("Tema da modificare non trovato")
        colors = p.get("colors")
        if not isinstance(colors, list) or not 1 <= len(colors) <= 20:
            raise ValueError("Il tema richiede da 1 a 20 colori")
        for color in colors:
            _hex_hsv(color)
        mode = p.get("mode", "static")
        if mode not in {"static", "animated"}:
            raise ValueError("Modalità tema non valida")
        brightness = p.get("brightness", 100)
        if isinstance(brightness, bool) or not isinstance(brightness, int) or not 1 <= brightness <= 100:
            raise ValueError("Luminosità tema non valida")
        step_ms = p.get("step_ms", 1000)
        speed = p.get("speed", 50)
        if isinstance(step_ms, bool) or not isinstance(step_ms, int) or not 500 <= step_ms <= 60000:
            raise ValueError("Intervallo tema non valido")
        if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 1 <= speed <= 100:
            raise ValueError("Velocità tema non valida")
        item = {"id": p.get("id"), "name": name, "description": str(p.get("description", ""))[:160],
                "colors": colors, "brightness": brightness, "mode": mode,
                "step_ms": step_ms, "speed": speed, "custom": True}
        return self._save_collection("custom_themes.json", item, self.custom_themes)

    def _start_animation(self, identifier: str | dict, target):
        animation = identifier if isinstance(identifier, dict) else _pick(self.animations, identifier)
        resolved = self._resolve_target(target)
        targets = resolved["tapo"]
        pc_keys = resolved["pc"] if animation.get("include_pc") else []
        if not targets and not pc_keys:
            raise ValueError("Nessuna luce disponibile per questa animazione")
        if pc_keys and self._mystic_static_only():
            raise ValueError("Experimental MSI backend supports static colors, brightness and on/off only")
        self._stop_continuous()
        self._animation_stop = threading.Event()
        stop = self._animation_stop
        self.controller = {"mode": "animation", "label": animation["name"],
                           "id": animation["id"], "target": target,
                           "tapo": targets, "pc": pc_keys}
        started = time.monotonic()
        colors = animation["colors"]
        raw_period = animation["step_ms"] * max(2, len(colors)) / 1000 * 50 / animation["speed"]
        period = max(2.0, min(600.0, raw_period))
        if animation["mode"] in {"pulse", "breathe"}:
            # LAN bulbs show individual brightness writes. A longer cycle
            # keeps the change per accepted write small enough to look soft.
            period = min(600.0, max(2.0, raw_period * 3.0))
        if animation["mode"] in {"sequence", "cycle"}:
            steps = (max(1, 2 * (len(colors) - 1)) if animation["direction"] == "alternate"
                     else len(colors))
            period = animation["step_ms"] / 1000 * 50 / animation["speed"] * steps
        if pc_keys:
            palette = [[int(color[n:n+2], 16) for n in (1, 3, 5)] for color in colors]
            if len(palette) == 1:
                palette.append(palette[0])
            self.pc.start_flow(palette, period, pc_keys, started, animation["direction"],
                               mode=animation["mode"], brightness=animation["brightness"],
                               min_brightness=animation.get("min_brightness"),
                               transition_ms=animation.get("transition_ms", 500))

        def sampled_color(phase: float):
            phase %= 1.0
            position = phase * len(colors)
            index = int(position)
            left = [int(colors[index % len(colors)][n:n+2], 16) for n in (1, 3, 5)]
            right = [int(colors[(index + 1) % len(colors)][n:n+2], 16) for n in (1, 3, 5)]
            blend = position - index
            return "#" + "".join(f"{round(left[c] + (right[c] - left[c]) * blend):02x}" for c in range(3))

        def report_native_error(device_id: str, message: str) -> None:
            with self._lock:
                if self._animation_stop is stop:
                    self.controller.setdefault("errors", {})[device_id] = message

        def run():
            mode = animation["mode"]
            transition = min(animation.get("transition_ms", 500), animation["step_ms"]) / 1000
            if mode in {"pulse", "breathe", "flow", "gradient", "wave", "rainbow"} or (mode in {"sequence", "cycle"} and transition):
                def smooth_frame(elapsed: float, offset: int) -> dict:
                    phase = elapsed / period + offset / max(1, len(targets) + 1)
                    if animation["direction"] == "reverse":
                        phase = -phase
                    elif animation["direction"] == "alternate" and mode not in {"sequence", "cycle"}:
                        phase %= 2.0
                        phase = phase if phase <= 1.0 else 2.0 - phase
                    if mode == "rainbow":
                        rgb = colorsys.hsv_to_rgb(phase % 1.0, 1, 1)
                        color = "#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)
                    elif mode in {"sequence", "cycle"}:
                        step_duration = animation["step_ms"] / 1000 * 50 / animation["speed"]
                        position = elapsed / step_duration
                        step = int(position)
                        fraction = position - step
                        if animation["direction"] == "alternate":
                            span = max(1, 2 * (len(colors) - 1))
                            def bounce(value):
                                position = value % span
                                return min(position, span - position)
                            color_index = bounce(step + offset)
                            next_index = bounce(step + offset + 1)
                        else:
                            color_index = step + offset
                            if animation["direction"] == "reverse":
                                color_index = -color_index
                            next_index = color_index + (-1 if animation["direction"] == "reverse" else 1)
                        transition_fraction = min(1.0, transition / step_duration)
                        blend = max(0.0, min(1.0, (fraction - (1.0 - transition_fraction)) /
                                             transition_fraction))
                        blend = blend * blend * (3 - 2 * blend)
                        left, right = colors[color_index % len(colors)], colors[next_index % len(colors)]
                        color = "#" + "".join(f"{round(int(left[n:n+2], 16) * (1-blend) + int(right[n:n+2], 16) * blend):02x}"
                                              for n in (1, 3, 5))
                    else:
                        color = sampled_color(phase)
                    hue, saturation, _ = _hex_hsv(color)
                    brightness = animation["brightness"]
                    if mode in {"pulse", "breathe"}:
                        minimum = animation.get("min_brightness")
                        fraction = None if minimum is None else minimum / brightness
                        brightness = round(brightness * _smooth_pulse_level(elapsed, period, mode, fraction))
                    return {"hue": hue, "saturation": saturation, "brightness": brightness}

                try:
                    duration = period
                    if targets:
                        self.tapo.stream_animation(targets, stop, smooth_frame, started,
                                                   duration=None if animation["loop"] else duration,
                                                   native={"period": period,
                                                           "brightness": animation["brightness"],
                                                           "min_brightness": animation.get(
                                                               "min_brightness",
                                                               round(animation["brightness"] *
                                                                     (0.25 if mode == "pulse" else 0.15))),
                                                           "mode": mode,
                                                           "on_error": report_native_error}
                                                   if mode in {"pulse", "breathe", "flow", "gradient",
                                                               "wave", "rainbow"} else None)
                    elif animation["loop"]:
                        stop.wait()
                    else:
                        stop.wait(duration)
                finally:
                    if pc_keys and self._animation_stop is stop:
                        self.pc.stop_flow()
                    if self._animation_stop is stop:
                        errors = self.controller.get("errors")
                        self.controller = {"mode": "idle", "label": "Nessun controllo continuo"}
                        if errors:
                            self.controller["errors"] = errors
                return
            index = 0
            with ThreadPoolExecutor(max_workers=max(1, min(4, len(targets)))) as pool:
              while not stop.is_set():
                updates = []
                for offset, target in enumerate(targets):
                    if mode == "random":
                        color = random.choice(colors)
                    else:
                        position = index + offset
                        if animation["direction"] == "reverse":
                            position = -position
                        elif animation["direction"] == "alternate" and mode in {"sequence", "cycle"}:
                            span = max(1, 2 * (len(colors) - 1))
                            position %= span
                            position = min(position, span - position)
                        color = colors[position % len(colors)]
                    hue, sat, _ = _hex_hsv(color)
                    brightness = animation["brightness"]
                    if mode == "flash" and index % 2:
                        brightness = 1
                    updates.append((target, {"hue": hue, "saturation": sat,
                                             "brightness": brightness}))
                for future in [pool.submit(self._apply_light, target, patch)
                               for target, patch in updates]:
                    try:
                        future.result()
                    except Exception:
                        pass
                index += 1
                total_steps = max(1, 2 * (len(colors) - 1)) if animation["direction"] == "alternate" and mode in {"sequence", "cycle"} else len(colors)
                if mode == "static" or (not animation["loop"] and index >= total_steps):
                    break
                step_duration = animation["step_ms"] / 1000 * 50 / animation["speed"]
                stop.wait(max(0.0, started + index * step_duration - time.monotonic()))
            if pc_keys and self._animation_stop is stop:
                self.pc.stop_flow()
            if self._animation_stop is stop:
                self.controller = {"mode": "idle", "label": "Nessun controllo continuo"}
        self._animation_thread = threading.Thread(target=run, daemon=True, name="smartlight-animation")
        self._animation_thread.start()
        return {"animation": animation["id"], "targets": targets,
                "pc": pc_keys, "running": True,
                "period_seconds": round(period, 2)}

    def _apply_theme(self, identifier: str, target="all", mode: str | None = None) -> dict:
        theme = _pick(self._themes(), identifier)
        selected_mode = mode or theme.get("mode", "static")
        if selected_mode not in {"static", "animated"}:
            raise ValueError("Modalità tema non valida")
        if selected_mode == "animated":
            animation = {"id": "theme:" + theme["id"], "name": theme["name"],
                         "colors": theme["colors"], "brightness": theme["brightness"],
                         "step_ms": theme.get("step_ms", 1000), "speed": theme.get("speed", 50),
                         "mode": "flow", "direction": "forward", "loop": True,
                         "include_pc": True}
            return {"theme": theme["id"], "mode": "animated",
                    **self._start_animation(animation, target)}
        self._stop_continuous()
        resolved = self._resolve_target(target)
        if not any(resolved.values()):
            raise ValueError("La destinazione non contiene dispositivi disponibili")
        result = {"theme": theme["id"], "mode": "static", "target": target, "tapo": {}, "pc": {}}
        for index, device_id in enumerate(resolved["tapo"]):
            color = theme["colors"][index % len(theme["colors"])]
            result["tapo"][device_id] = self._apply_target(device_id, {"color": color,
                                                           "brightness": theme["brightness"]})["tapo"]
        for index, key in enumerate(resolved["pc"]):
            color = theme["colors"][(index + len(resolved["tapo"])) % len(theme["colors"])]
            result["pc"][key] = self._apply_target(key, {"color": color,
                                                         "brightness": theme["brightness"]})["pc"]
        self.controller = {"mode": "static", "label": theme["name"], "id": theme["id"], "target": target}
        return result

    def _save_scene(self, p: dict) -> dict:
        states = p.get("states")
        target = p.get("target", "all")
        resolved = self._resolve_target(target)
        if states is None:
            states = {"tapo": {}, "pc": {}}
            if p.get("include_tapo", True):
                for item in self.tapo.list_devices():
                    if item.get("online") and item["id"] in resolved["tapo"]:
                        states["tapo"][item["id"]] = {"power": item.get("on", False),
                            **({"hue": item["hsv"]["hue"], "saturation": item["hsv"]["saturation"],
                                "brightness": item["brightness"]} if item.get("hsv") else {})}
            if p.get("include_pc", True):
                pc_state = self.pc.get_state()
                if "devices" in pc_state:
                    states["pc"] = {"devices": {key: value for key, value in pc_state["devices"].items()
                                                if key in resolved["pc"]},
                                    "global_brightness": pc_state.get("global_brightness", 100)}
                else:
                    states["pc"] = {key: value for key, value in pc_state.items()
                                    if key in resolved["pc"]}
        if not isinstance(states, dict):
            raise ValueError("Stati scena non validi")
        states = copy.deepcopy(states)
        return self._save_collection("scenes.json", {"id": p.get("id"), "name": _valid_name(p.get("name")),
              "description": str(p.get("description", ""))[:200], "target": target,
              "states": states}, self.scenes)

    def _apply_scene(self, identifier: str, target=None) -> dict:
        scene = _pick(self.scenes, identifier)
        write_json("last_scene.json", {"id": scene["id"]})
        selected = self._resolve_target(target or scene.get("target", "all"))
        output = {"tapo": {}, "pc": {}}
        for device_id, patch in scene["states"].get("tapo", {}).items():
            if device_id not in selected["tapo"]:
                continue
            try:
                output["tapo"][device_id] = self._apply_light(device_id, patch)
            except Exception as exc:
                output["tapo"][device_id] = {"error": str(exc)}
        pc_state = scene["states"].get("pc")
        if pc_state:
            states = pc_state.get("devices", pc_state)
            for key, state in states.items():
                if key in selected["pc"]:
                    try:
                        output["pc"][key] = self.pc.apply_to([key], state)
                    except Exception as exc:
                        output["pc"][key] = {"error": str(exc)}
        return output

    def _save_schedule(self, p: dict) -> dict:
        definition = p.get("definition", p)
        when = definition.get("time")
        try:
            dt.time.fromisoformat(when)
        except Exception as exc:
            raise ValueError("Orario programmazione non valido") from exc
        days = definition.get("days", list(range(1, 8)))
        if not isinstance(days, list) or any(day not in range(1, 8) for day in days):
            raise ValueError("Giorni programmazione non validi")
        action = dict(definition.get("action", {"power": True}))
        if not action or set(action) - {"power", "brightness", "hue", "saturation", "temperature", "color"}:
            raise ValueError("Azione programmazione non valida")
        if "color" in action: _hex_hsv(action["color"])
        when_time = dt.time.fromisoformat(when)
        now = dt.datetime.now().astimezone()
        once_date = None
        if not days:
            requested_date = definition.get("once_date")
            if requested_date is None and (p.get("id") or definition.get("id")):
                old_id = p.get("id") or definition.get("id")
                prior = next((item for item in self.schedules if item.get("id") == old_id), None)
                if prior and not prior.get("days"):
                    requested_date = prior.get("once_date")
            if requested_date:
                try:
                    selected_date = dt.date.fromisoformat(requested_date)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Data programmazione non valida: usa AAAA-MM-GG") from exc
                if "once_date" in definition and (selected_date < now.date() or (selected_date == now.date() and when_time <= now.time())):
                    raise ValueError("Scegli una data e un'ora future")
            else:
                selected_date = now.date() + dt.timedelta(days=1) if when_time <= now.time() else now.date()
            once_date = selected_date.isoformat()
        item = {"id": p.get("id") or definition.get("id"),
                "name": _valid_name(p.get("name") or definition.get("name")),
                "device_id": definition.get("target", definition.get("device_id", "all")), "time": when_time.strftime("%H:%M"),
                "days": days, "enabled": bool(definition.get("enabled", True)),
                "once_date": once_date, "action": action}
        self._resolve_target(item["device_id"])
        return self._save_collection("schedules.json", item, self.schedules)

    def _worker(self):
        while not self._stop.wait(1):
            now = dt.datetime.now().astimezone()
            key = now.strftime("%Y-%m-%d %H:%M")
            for schedule in list(self.schedules):
                matches_day = (now.isoweekday() in schedule.get("days", []) if schedule.get("days")
                               else schedule.get("once_date") == now.date().isoformat())
                if (schedule.get("enabled") and matches_day
                    and schedule.get("time") == now.strftime("%H:%M")
                    and self._last_schedule.get(schedule["id"]) != key):
                    self._last_schedule[schedule["id"]] = key
                    try:
                        self._stop_continuous()
                        self._apply_target(schedule["device_id"], schedule["action"])
                    except Exception:
                        pass
                    if not schedule.get("days"):
                        schedule["enabled"] = False
                        write_json("schedules.json", self.schedules)
            if self.timer.get("active") and time.monotonic() >= self.timer.get("deadline", float("inf")):
                timer = self.timer
                self.timer = {}
                try:
                    self._stop_continuous()
                    self._apply_target(timer["id"], {"power": timer["action"] == "on"})
                except Exception:
                    pass
            if self.away.get("active") and time.monotonic() >= self._next_away:
                self._next_away = time.monotonic() + random.uniform(15 * 60, 45 * 60)
                start = dt.time.fromisoformat(self.away.get("from") or "00:00")
                end = dt.time.fromisoformat(self.away.get("to") or "23:59")
                current = now.time()
                inside = start <= current <= end if start <= end else current >= start or current <= end
                if inside:
                    try:
                        self._stop_continuous()
                        self._apply_target(self.away["id"], {"power": bool(random.getrandbits(1))})
                    except Exception:
                        pass
            if self.sync.get("mode") == "pc_to_tapo" and self.controller.get("mode") == "sync" and time.monotonic() - self._last_sync >= self.sync.get("interval_ms", 1000) / 1000:
                self._last_sync = time.monotonic()
                frames = self.pc.get_frames()
                source = self.sync.get("source")
                colors = frames.get(source) or next(iter(frames.values()), [])
                if colors:
                    try:
                        hue, sat, val = _hex_hsv(colors[0])
                        with self._mode_write_lock:
                            if self.sync.get("mode") == "pc_to_tapo" and self.controller.get("mode") == "sync":
                                self._apply_light(self.sync.get("target", "all"),
                                                  {"hue": hue, "saturation": sat, "brightness": val})
                    except Exception:
                        pass

    def invoke(self, command: str, params: dict | None = None) -> dict:
        p = params or {}
        try:
            return {"ok": True, "data": self._dispatch(command, p)}
        except (ValueError, KeyError, TypeError) as exc:
            return {"ok": False, "error": {"code": "invalid_request", "message": str(exc)}}
        except Exception as exc:
            return {"ok": False, "error": {"code": "operation_failed", "message": str(exc)}}

    def _dispatch(self, command: str, p: dict):
        if command == "status": return self.status()
        if command == "setup.status":
            from pc_discovery import discover_pc_setup
            report = discover_pc_setup()
            report.update(backend=self.pc.get_status(), devices_count=len(self.pc.list_devices()),
                          settings={key:self.settings.get(key) for key in ("pc_backend_mode", "mystic_light_dll")})
            return report
        if command == "modes.status": return self.controller
        if command == "rooms.list": return self.rooms
        if command == "rooms.save": return self._save_room(p)
        if command == "rooms.delete": return self._delete_room(p["id"])
        if command == "targets.list":
            return {"all": self._resolve_target("all"), "rooms": self.rooms,
                    "tapo": self.tapo.list_devices(), "pc": self.pc.list_devices()}
        if command == "lighting.overview":
            pc_snapshot = self.pc.get_state()
            pc_states = pc_snapshot.get("devices", pc_snapshot)
            return {"targets": {"all": self._resolve_target("all"), "rooms": self.rooms},
                    "tapo": [{key: value for key, value in item.items()
                              if key in {"id", "name", "model", "online", "on", "brightness",
                                         "hsv", "color_temp", "effect", "effects", "device_presets",
                                         "capabilities"}}
                             for item in self.tapo.list_devices()],
                    "pc": [{**item, "state": pc_states.get(item["key"])}
                           for item in self.pc.list_devices()],
                    "pc_effects": self.pc.get_effects(), "pc_scenes": self.pc.list_scenes(),
                    "control_mode": self.controller,
                    "target_syntax": "all | room:<id> | device id/key | list of ids/keys"}
        if command == "target.apply":
            patch = p.get("patch") if isinstance(p.get("patch"), dict) else p
            patch = {key: value for key, value in patch.items()
                     if key in {"power", "brightness", "hue", "saturation", "temperature", "color"}}
            if not patch: raise ValueError("Seleziona un'azione per le luci")
            self._stop_continuous()
            target = p.get("target", "all")
            result = self._apply_target(target, patch)
            self.controller = {"mode": "static", "label": "Colore o stato manuale", "target": target}
            return result
        if command in {"refresh", "devices.rescan"}:
            devices = self.tapo.refresh()
            self.pc.rescan_async()
            return {"devices": devices, "pc": self.pc.get_status()}
        if command == "devices.list": return {"tapo": self.tapo.list_devices(), "pc": self.pc.list_devices()}
        if command == "devices.status": return self.tapo._states.get(p["device"]) or self.tapo.refresh()[[i["id"] for i in self.tapo.devices].index(p["device"])]
        if command == "devices.capabilities": return self._dispatch("devices.status", p)["capabilities"]
        if command in {"device_set", "lights.set"}:
            patch = {key: value for key, value in p.items() if key in {"power", "brightness", "hue", "saturation", "temperature", "effect", "device_preset"}}
            if "kelvin" in p: patch["temperature"] = p["kelvin"]
            self._stop_continuous()
            target = p.get("target") or p.get("id") or p.get("device")
            result = self._apply_light(target, patch)
            self.controller = {"mode": "static", "label": "Controllo luce manuale", "target": target}
            return result
        if command == "group_set":
            self._stop_continuous()
            targets = self._targets(p.get("ids", []))
            result = self.tapo.set_group(targets, {k: v for k, v in p.items() if k not in {"ids"}})
            if any(not value["ok"] for value in result.values()):
                raise RuntimeError("; ".join(f"{key}: {value['error']}" for key, value in result.items() if not value["ok"]))
            self.controller = {"mode": "static", "label": "Controllo gruppo manuale", "target": p.get("ids", [])}
            return result
        if command in {"effect_apply", "effects.apply"}:
            target = p.get("target") or p.get("id") or p.get("device")
            if p.get("animation_id"): return self._start_animation(p["animation_id"], target)
            effect_names = {
                "Calderone Ribollente": "Bubbling Cauldron", "Bastoncini di Zucchero": "Candy Cane",
                "Natale": "Christmas", "Tremolio": "Flicker", "Luci di Natale": "Grandma's Christmas Lights",
                "Casa Stregata": "Haunted Mansion", "Ghiaccio": "Icicle", "Fulmine": "Lightning",
                "Oceano": "Ocean", "Arcobaleno": "Rainbow", "Gocce di Pioggia": "Raindrop",
                "Primavera": "Spring", "Alba": "Sunrise", "Tramonto": "Sunset", "San Valentino": "Valentines",
            }
            self._stop_continuous()
            result = self._apply_light(target, {"effect": effect_names.get(p["effect"], p["effect"]),
                                      **({"brightness": p["brightness"]} if p.get("brightness") else {})})
            self.controller = {"mode": "static", "label": p["effect"], "target": target}
            return result
        if command == "effects.list":
            state = self._dispatch("devices.status", p)
            return {"built_in": state.get("effects", []), "animations": self.animations}
        if command in {"custom_effect_save", "animations.save"}: return self._save_animation(p)
        if command in {"custom_effect_delete", "animations.delete"}: return self._delete_collection("animations.json", p.get("id") or p.get("name"), self.animations)
        if command == "animations.list": return self.animations
        if command == "animations.start": return self._start_animation(p.get("id") or p.get("name"), p.get("target") or p.get("devices") or "all")
        if command == "animations.stop":
            self._stop_continuous()
            return {"running": False}
        if command in {"preset_save", "presets.save"}: return self._save_preset(p)
        if command in {"preset_delete", "presets.delete"}: return self._delete_collection("presets.json", p.get("id") or p.get("name"), self.presets)
        if command in {"preset_apply", "presets.apply"}:
            item = _pick(self.presets, p.get("id") or p.get("name"))
            target = p.get("target") or p.get("device_id") or p.get("device") or item.get("device_id") or "all"
            if item.get("kind") == "native_effect":
                selected = self._resolve_target(target)["tapo"]
                supported = {device["id"] for device in self.tapo.list_devices()
                             if item["effect"] in device.get("effects", [])}
                compatible = [device_id for device_id in selected if device_id in supported]
                if not compatible:
                    raise ValueError("Nessuna luce Tapo selezionata supporta questo effetto")
                return self._dispatch("effect_apply", {"target": compatible, "effect": item["effect"]})
            if item.get("kind") == "pc_effect":
                keys = self._resolve_target(target)["pc"]
                if not keys:
                    raise ValueError("La destinazione non contiene luci PC")
                patch = {"effect": item["effect"], "on": True,
                         "color": [int(item["color"][n:n+2], 16) for n in (1, 3, 5)],
                         "color2": [int(item["color2"][n:n+2], 16) for n in (1, 3, 5)],
                         "speed": item["speed"], "brightness": item["brightness"]}
                return self._dispatch("pc_apply", {"keys": keys, "patch": patch})
            if item.get("kind") == "animation":
                return self._start_animation(item["animation_id"], target)
            if item.get("kind") == "theme":
                return self._apply_theme(item["theme_id"], target)
            self._stop_continuous()
            patch = {"hue": item["hue"], "saturation": item["saturation"],
                     "brightness": item["brightness"]}
            if item.get("color"):
                patch["color"] = item["color"]
            else:
                rgb = colorsys.hsv_to_rgb(item["hue"] / 360, item["saturation"] / 100, 1)
                patch["color"] = "#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)
            result = self._apply_target(target, patch)
            self.controller = {"mode": "static", "label": item["name"], "target": target}
            return result
        if command == "presets.list": return self.presets
        if command in {"scene_save", "scenes.save"}: return self._save_scene(p)
        if command in {"scene_delete", "scenes.delete"}: return self._delete_collection("scenes.json", p.get("id") or p.get("name"), self.scenes)
        if command in {"scene_apply", "scenes.apply"}:
            self._stop_continuous()
            result = self._apply_scene(p.get("id") or p.get("name"), p.get("target"))
            self.controller = {"mode": "static", "label": p.get("name") or p.get("id"), "target": "scene"}
            return result
        if command == "scenes.list": return self.scenes
        if command == "themes.list": return self._themes()
        if command == "themes.save": return self._save_theme(p)
        if command == "themes.delete":
            return self._delete_collection("custom_themes.json", p["id"], self.custom_themes)
        if command == "theme_apply": return self._apply_theme(p["id"], p.get("target", "all"), p.get("mode"))
        if command in {"schedule_save", "schedules.save"}: return self._save_schedule(p)
        if command in {"schedule_delete", "schedules.delete"}: return self._delete_collection("schedules.json", p.get("id") or p.get("name"), self.schedules)
        if command == "schedule_toggle":
            item = _pick(self.schedules, p["id"]); item["enabled"] = bool(p["enabled"])
            write_json("schedules.json", self.schedules); return item
        if command == "schedules.list": return self.schedules
        if command == "timer_set":
            minutes = int(p["minutes"])
            if not 1 <= minutes <= 10080: raise ValueError("Timer: 1–10080 minuti")
            if p["action"] not in {"on", "off"}: raise ValueError("Azione timer non valida")
            target = p.get("target") or p.get("id")
            self._resolve_target(target)
            self.timer = {"id": target, "minutes": minutes, "action": p["action"],
                          "deadline": time.monotonic() + minutes * 60, "active": True}
            return {k: v for k, v in self.timer.items() if k != "deadline"}
        if command == "away_set":
            target = p.get("target") or p.get("id")
            self._resolve_target(target)
            for field in ("from", "to"):
                if p.get(field): dt.time.fromisoformat(p[field])
            self.away = {"id": target, "active": bool(p["enabled"]), "from": p.get("from"), "to": p.get("to")}
            self._next_away = time.monotonic() + random.uniform(60, 180)
            return self.away
        if command == "energy":
            return self.tapo.energy(p["id"], p.get("period", "today"))
        if command in {"pc_status", "pc.devices"}: return self._pc_data()
        if command == "pc.effects": return self.pc.get_effects()
        if command == "pc.scenes": return self.pc.list_scenes()
        if command == "pc.scene.apply":
            if self._mystic_static_only() and p["id"] not in {"all_on", "all_off", "keyboard_only"}:
                raise ValueError("Experimental MSI backend does not support animated PC scenes")
            self._stop_continuous()
            result = self.pc.apply_scene(p["id"])
            self.controller = {"mode": "static", "label": p["id"], "target": "pc"}
            return result
        if command in {"pc_apply", "pc.apply_to"}:
            if self._mystic_static_only() and (p.get("patch") or p.get("state") or {}).get("effect", "statico") != "statico":
                raise ValueError("Experimental MSI backend supports static colors, brightness and on/off only")
            self._stop_continuous()
            result = self.pc.apply_to(p.get("keys") or p.get("devices"), p.get("patch") or p.get("state"))
            self.controller = {"mode": "static", "label": "Controllo RGB PC manuale", "target": "pc"}
            return result
        if command == "pc.set_device":
            if self._mystic_static_only() and p["state"].get("effect", "statico") != "statico":
                raise ValueError("Experimental MSI backend supports static colors, brightness and on/off only")
            self._stop_continuous()
            result = self.pc.set_device(p["device"], p["state"])
            self.controller = {"mode": "static", "label": "Controllo RGB PC manuale", "target": p["device"]}
            return result
        if command == "pc.set_global": return self.pc.set_global_brightness(p["state"].get("brightness"))
        if command == "pc.profiles.list": return self.pc.list_profiles()
        if command == "pc.profiles.save": return self.pc.save_profile(p["name"])
        if command == "pc.profiles.load":
            self._stop_continuous()
            result = self.pc.load_profile(p["name"])
            self.controller = {"mode": "static", "label": p["name"], "target": "pc"}
            return result
        if command == "pc.profiles.delete": return self.pc.delete_profile(p["name"])
        if command == "pc.rescan": return self.pc.rescan_async()
        if command == "pc.release_icue": return self.pc.release_icue()
        if command == "pc.errors": return {"errors": self.pc.drain_errors()}
        if command in {"sync_set", "sync.configure"}:
            config = p.get("config", p)
            mode = config.get("mode", "off")
            if mode not in {"off", "pc_to_tapo"}:
                raise ValueError("Al momento è disponibile la sincronizzazione PC → Tapo")
            interval = int(config.get("interval_ms", 1000))
            if not 1000 <= interval <= 60000: raise ValueError("Intervallo: 1000–60000 ms")
            target = config.get("target", "all")
            if mode != "off" and not self._targets(target):
                raise ValueError("La sincronizzazione richiede almeno una luce Tapo nella destinazione")
            self._stop_continuous()
            self.sync = {"mode": mode, "source": config.get("source", "auto"),
                         "interval_ms": interval, "target": target}
            if mode != "off":
                self.controller = {"mode": "sync", "label": "PC → Tapo", "target": target,
                                   "source": self.sync["source"]}
            write_json("sync.json", self.sync); return self.sync
        if command == "sync.stop":
            self._stop_continuous(); return self.sync
        if command == "sync.status": return self.sync
        if command == "settings_get": return self.status()["settings"]
        if command == "settings_set":
            next_settings = dict(self.settings)
            if "pc_backend_mode" in p:
                mode = p["pc_backend_mode"]
                if mode not in ("auto", "openrgb", "icue", "mystic"):
                    raise ValueError("PC backend: choose auto, openrgb, icue or mystic")
                if os.name != "nt" and mode not in ("auto", "openrgb"):
                    raise ValueError("Linux uses OpenRGB: choose auto or openrgb")
                next_settings["pc_backend_mode"] = mode
                # Selecting Auto is an explicit request to use automatic fallback.
                next_settings.pop("mystic_light_enabled", None)
            if "language" in p:
                if p["language"] not in {"it", "en"}:
                    raise ValueError("Lingua non valida / Invalid language: it, en")
                next_settings["language"] = p["language"]
            if "mystic_light_enabled" in p:
                if not isinstance(p["mystic_light_enabled"], bool):
                    raise ValueError("Mystic Light: enabled must be true or false")
                next_settings["mystic_light_enabled"] = p["mystic_light_enabled"]
            if "mystic_light_dll" in p:
                if not isinstance(p["mystic_light_dll"], str):
                    raise ValueError("Mystic Light: DLL path must be a string")
                next_settings["mystic_light_dll"] = p["mystic_light_dll"].strip()
            if next_settings.get("mystic_light_enabled") and {"mystic_light_enabled", "mystic_light_dll"}.intersection(p):
                dll = Path(next_settings.get("mystic_light_dll", ""))
                if os.name != "nt":
                    raise ValueError("Mystic Light SDK is experimental and Windows only")
                if next_settings.get("mystic_light_dll") and (not dll.is_absolute() or dll.suffix.lower() != ".dll" or not dll.is_file()):
                    raise ValueError("Mystic Light: choose an existing absolute MSI SDK DLL path")
            for key in ("auto_start", "minimize_to_tray", "restore_scene", "mcp_auto_start"):
                if key in p: next_settings[key] = bool(p[key])
            if "mcp_scope" in p:
                if p["mcp_scope"] not in {"local", "lan"}:
                    raise ValueError("Ambito MCP non valido")
                next_settings["mcp_scope"] = p["mcp_scope"]
            registered = self.autostart.status()["auto_start"]
            if "auto_start" in p or ("minimize_to_tray" in p and registered):
                self.autostart.set(bool(p.get("auto_start", registered)),
                                   minimized=next_settings.get("minimize_to_tray", True))
            if p.get("username") and p.get("password"):
                self.tapo.save_credentials(p["username"], p["password"])
            if p.get("add_ip"):
                import ipaddress
                host = str(ipaddress.ip_address(p["add_ip"]))
                entry = {"id": "tapo-" + _id(), "name": "Nuova luce Tapo", "host": host,
                         "model": "Tapo", "room": "Altro"}
                self.tapo.devices.append(entry); write_json("devices.json", self.tapo.devices)
            self.settings = next_settings
            write_json("settings.json", self.settings)
            return self.status()["settings"]
        if command in {"backup_export", "backup.export"}:
            path = Path(p.get("path") or (data_dir() / f"Smartlight-backup-{dt.date.today().isoformat()}.json"))
            bundle = {"format": "smartlight-backup-v1", "devices": self.tapo.devices,
                      "presets": self.presets, "animations": self.animations, "scenes": self.scenes,
                      "schedules": self.schedules, "rooms": self.rooms,
                      "custom_themes": self.custom_themes,
                      "settings": self.settings, "pc": self.pc.export_data()}
            path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"path": str(path)}
        if command in {"backup_import", "backup.import"}:
            bundle = json.loads(Path(p["path"]).read_text(encoding="utf-8"))
            if bundle.get("format") != "smartlight-backup-v1": raise ValueError("Backup Smartlight non valido")
            self.pc.import_data(bundle["pc"])
            for attr, filename in (("presets", "presets.json"), ("animations", "animations.json"),
                                   ("scenes", "scenes.json"), ("schedules", "schedules.json"),
                                   ("rooms", "rooms.json"), ("custom_themes", "custom_themes.json")):
                values = bundle.get(attr, [] if attr in {"rooms", "custom_themes"} else None)
                if not isinstance(values, list): raise ValueError(f"{attr} non valido")
                setattr(self, attr, values); write_json(filename, values)
            self.tapo.devices = bundle["devices"]; write_json("devices.json", self.tapo.devices)
            imported_settings = dict(bundle["settings"])
            # A shared backup must never opt this machine into loading native code.
            for key in ("mystic_light_enabled", "mystic_light_dll", "pc_backend_mode"):
                imported_settings.pop(key, None)
                if key in self.settings:
                    imported_settings[key] = self.settings[key]
            if imported_settings.get("language") not in {"it", "en"}:
                imported_settings["language"] = "en"
            self.settings = imported_settings; write_json("settings.json", self.settings)
            return {"imported": True}
        raise ValueError(f"Comando sconosciuto: {command}")
