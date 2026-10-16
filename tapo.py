"""Capability-aware Tapo LAN controller using the tested TPAP python-kasa branch."""

from __future__ import annotations

import asyncio
import copy
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from kasa import Discover, Module

from storage import read_json, write_json
from tapo_bulb_native import (BulbRuleConflict, restore_native_bulb_effect,
                              start_native_bulb_effect)


DEFAULT_DEVICES = [
    {"id": "striscia", "name": "Striscia L900", "host": "192.168.1.53", "model": "L900-10", "room": "Stanza"},
    {"id": "lampadina1", "name": "Lampadina 1", "host": "192.168.1.58", "model": "L530", "room": "Stanza"},
    {"id": "lampadina2", "name": "Lampadina 2", "host": "192.168.1.59", "model": "L530", "room": "Stanza"},
]


class NativeEffectConflict(RuntimeError):
    """The phone changed the temporary L900 effect or its settings."""


class TapoController:
    _NATIVE_RECOVERY_FILE = "native_effect_recovery.json"
    _NATIVE_NAME = "Smartlight transizione fluida"

    def __init__(self):
        self.devices = read_json("devices.json", DEFAULT_DEVICES)
        self._lock = threading.RLock()
        self._device_locks = {item["id"]: threading.RLock() for item in self.devices}
        self._states: dict[str, dict] = {}
        self._native_recovery: dict[str, dict] = read_json(self._NATIVE_RECOVERY_FILE, {})
        self._active_native: set[str] = set()

    @staticmethod
    def _raw_effect(reply: dict) -> dict:
        effect = reply.get("get_lighting_effect", reply)
        if not isinstance(effect, dict) or "id" not in effect or "enable" not in effect:
            raise ValueError("La striscia non ha restituito lo stato dell'effetto")
        return effect

    async def _read_raw_effect(self, device) -> dict:
        return self._raw_effect(await device._query_helper("get_lighting_effect"))

    def _remember_native(self, device_id: str, backup: dict) -> None:
        with self._lock:
            self._native_recovery[device_id] = backup
            write_json(self._NATIVE_RECOVERY_FILE, self._native_recovery)

    def _forget_native(self, device_id: str) -> None:
        with self._lock:
            self._native_recovery.pop(device_id, None)
            write_json(self._NATIVE_RECOVERY_FILE, self._native_recovery)

    async def _restore_native(self, item: dict, device, backup: dict) -> None:
        """Restore only if our temporary effect is still selected.

        A change made in the Tapo app takes precedence over this animation.
        A durable backup allows recovery after an unexpected app shutdown.
        """
        if backup.get("kind") == "l530_rule":
            await restore_native_bulb_effect(item, device, backup, self._forget_native)
            return
        await device.update()
        current = await self._read_raw_effect(device)
        same_schema = (current.get("id") == backup["temporary_id"]
                       and current.get("name") == self._NATIVE_NAME
                       and current.get("sequence") == backup.get("temporary_sequence"))
        if not same_schema:
            raise NativeEffectConflict("Effetto L900 modificato dall'app Tapo; backup conservato")
        manually_stopped = current.get("enable") == 0
        if not manually_stopped and (current.get("enable") != 1 or
                                     current.get("brightness") != backup["temporary_brightness"]):
            raise NativeEffectConflict("Luminosità L900 modificata dall'app Tapo; backup conservato")

        current_on = bool(device.is_on)
        light = device.modules.get(Module.Light)
        phone_hsv = light.hsv if current_on and light is not None else None
        original = copy.deepcopy(backup["effect"])
        if manually_stopped:
            original["enable"] = 0
        effects = device.modules[Module.LightEffect]
        if not original["enable"]:
            # This firmware treats enable=0 as only an on/off command. Load
            # the saved schema while enabled, then disable it separately.
            await effects.set_custom_effect({**original, "enable": 1})
            await device.update()
            active_original = await self._read_raw_effect(device)
            if any(active_original.get(key) != original.get(key)
                   for key in ("id", "name", "sequence")):
                raise RuntimeError("Schema originale Tapo non ripristinato")
            await effects.set_custom_effect(original)
        else:
            await effects.set_custom_effect(original)
        await device.update()
        restored = await self._read_raw_effect(device)
        if any(restored.get(key) != original.get(key) for key in ("id", "name", "enable", "sequence")):
            raise RuntimeError("Ripristino dell'effetto Tapo non confermato")
        if not original["enable"] and current_on:
            hsv = ({"hue": phone_hsv.hue, "saturation": phone_hsv.saturation,
                    "value": phone_hsv.value} if manually_stopped and phone_hsv
                   else backup.get("hsv"))
            if hsv and light is not None and hsv["value"] >= 1:
                # The strip can apply one last frame after disabling an
                # effect. Reapply the correct static color after that frame.
                await asyncio.sleep(2.0)
                for attempt in range(3):
                    if attempt:
                        await asyncio.sleep(0.35)
                    await light.set_hsv(hsv["hue"], hsv["saturation"], hsv["value"])
                    await asyncio.sleep(0.75)
                    await device.update()
                    actual = light.hsv
                    if (actual.hue, actual.saturation, actual.value) == (
                            hsv["hue"], hsv["saturation"], hsv["value"]):
                        break
                else:
                    raise RuntimeError("Ripristino del colore statico Tapo non confermato")
        if not current_on or (not manually_stopped and not backup.get("on", True)):
            await device.turn_off()
        await device.update()
        self._forget_native(item["id"])

    async def _recover_native_if_needed(self, item: dict, device) -> None:
        with self._lock:
            if item["id"] in self._active_native:
                return
        backup = self._native_recovery.get(item["id"])
        if backup:
            try:
                await self._restore_native(item, device, backup)
            except (BulbRuleConflict, NativeEffectConflict):
                # The user's phone edited L2. Keep the backup for inspection,
                # but the light remains readable and controllable.
                pass

    async def _native_still_selected(self, device, backup: dict) -> bool:
        if not device.is_on:
            return False
        if backup.get("kind") == "l530_rule":
            effects = device.modules.get(Module.LightEffect)
            reply = await effects.call("get_dynamic_light_effect_rules", {"start_index": 0})
            data = reply.get("get_dynamic_light_effect_rules", reply)
            rules = [rule for rule in data.get("rule_list", []) if rule.get("id") == "L2"]
            expected = backup["temporary_rule"]
            return bool(data.get("enable") and data.get("current_rule_id") == "L2"
                        and len(rules) == 1 and all(
                            rules[0].get(key) == expected.get(key)
                            for key in ("id", "change_mode", "change_time",
                                        "color_status_list", "scene_name")))
        current = await self._read_raw_effect(device)
        return bool(current.get("enable") == 1
                    and current.get("id") == backup["temporary_id"]
                    and current.get("name") == self._NATIVE_NAME
                    and current.get("sequence") == backup["temporary_sequence"]
                    and current.get("brightness") == backup["temporary_brightness"])

    def credentials(self) -> tuple[str, str]:
        username = os.environ.get("KASA_USERNAME", "")
        password = os.environ.get("KASA_PASSWORD", "")
        if not (username and password):
            try:
                import keyring
                username = keyring.get_password("Smartlight Tapo", "username") or ""
                password = keyring.get_password("Smartlight Tapo", "password") or ""
            except Exception:
                pass
        if not (username and password):
            raise ValueError("Configura l'account Tapo nelle impostazioni.")
        return username, password

    def save_credentials(self, username: str, password: str) -> None:
        if not username or not password:
            raise ValueError("Email e password Tapo sono obbligatorie")
        import keyring
        keyring.set_password("Smartlight Tapo", "username", username)
        keyring.set_password("Smartlight Tapo", "password", password)

    def _entry(self, device_id: str) -> dict:
        for item in self.devices:
            if item["id"] == device_id:
                return item
        raise ValueError(f"Luce sconosciuta: {device_id}")

    async def _connect(self, item: dict):
        username, password = self.credentials()
        device = await Discover.discover_single(item["host"], username=username, password=password)
        if device is None:
            raise ConnectionError(f"Nessuna risposta da {item['name']}")
        await device.update()
        return device

    @staticmethod
    def _snapshot(item: dict, device) -> dict:
        light = device.modules.get(Module.Light)
        effects = device.modules.get(Module.LightEffect)
        presets = device.modules.get(Module.LightPreset)
        hsv = None
        temperature = None
        brightness = None
        if light:
            if light.has_feature("brightness"):
                brightness = light.brightness
            if light.has_feature("hsv"):
                val = light.hsv
                hsv = {"hue": val.hue, "saturation": val.saturation, "value": val.value}
            if light.has_feature("color_temp"):
                temperature = light.color_temp
        effect_names = list(effects.effect_list) if effects else []
        preset_names = list(presets.preset_list) if presets else []
        return {
            **item,
            "type": "tapo", "online": True, "on": bool(device.is_on),
            "brightness": brightness, "hsv": hsv, "color_temp": temperature,
            "effect": effects.effect if effects else None,
            "effects": effect_names, "device_presets": preset_names,
            "capabilities": {
                "power": True, "brightness": brightness is not None,
                "color": hsv is not None, "temperature": temperature is not None,
                "effects": bool(effects),
                "custom_effects_native": bool(effects and effects.has_custom_effects),
                "device_presets": bool(presets),
            },
        }

    async def _read(self, item: dict) -> dict:
        device = await self._connect(item)
        try:
            await self._recover_native_if_needed(item, device)
            return self._snapshot(item, device)
        finally:
            await device.disconnect()

    def refresh(self) -> list[dict]:
        states = []
        for item in list(self.devices):
            with self._device_locks.setdefault(item["id"], threading.RLock()):
                try:
                    state = asyncio.run(self._read(item))
                except Exception as exc:
                    state = {**item, "type": "tapo", "online": False, "error": str(exc),
                             "capabilities": {}}
                with self._lock:
                    self._states[item["id"]] = state
            states.append(state)
        return states

    def list_devices(self) -> list[dict]:
        with self._lock:
            return [self._states.get(i["id"], {**i, "type": "tapo", "online": None,
                                                   "capabilities": {}}) for i in self.devices]

    @staticmethod
    def _number(value: Any, name: str, lo: int, hi: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
            raise ValueError(f"{name} deve essere tra {lo} e {hi}")
        return value

    async def _set(self, item: dict, patch: dict) -> dict:
        device = await self._connect(item)
        try:
            light = device.modules.get(Module.Light)
            if "power" in patch:
                if not isinstance(patch["power"], bool):
                    raise ValueError("power deve essere booleano")
                await (device.turn_on() if patch["power"] else device.turn_off())
            if "hue" in patch or "saturation" in patch:
                if light is None or not light.has_feature("hsv"):
                    raise ValueError("Questo dispositivo non supporta i colori")
                hue = self._number(patch.get("hue", light.hsv.hue), "hue", 0, 360)
                saturation = self._number(patch.get("saturation", light.hsv.saturation), "saturation", 0, 100)
                brightness = self._number(patch.get("brightness", light.brightness), "brightness", 1, 100)
                await light.set_hsv(hue, saturation, brightness)
            elif "temperature" in patch:
                if light is None or not light.has_feature("color_temp"):
                    raise ValueError("Questo dispositivo non supporta il bianco regolabile")
                low, high = (2500, 9000) if item["model"].startswith("L900") else (2500, 6500)
                temperature = self._number(patch["temperature"], "temperature", low, high)
                await light.set_color_temp(temperature, brightness=patch.get("brightness"))
            elif "brightness" in patch:
                if light is None:
                    raise ValueError("Controllo luminosità non disponibile")
                await light.set_brightness(self._number(patch["brightness"], "brightness", 1, 100))
            if "effect" in patch:
                effects = device.modules.get(Module.LightEffect)
                if effects is None or patch["effect"] not in effects.effect_list:
                    raise ValueError("Effetto non supportato dal dispositivo")
                await effects.set_effect(patch["effect"])
            if "device_preset" in patch:
                presets = device.modules.get(Module.LightPreset)
                if presets is None or patch["device_preset"] not in presets.preset_list:
                    raise ValueError("Preset del dispositivo non disponibile")
                await presets.set_preset(patch["device_preset"])
            await device.update()
            return self._snapshot(item, device)
        finally:
            await device.disconnect()

    def set(self, device_id: str, patch: dict) -> dict:
        if not patch or set(patch) - {"power", "hue", "saturation", "temperature", "brightness", "effect", "device_preset"}:
            raise ValueError("Parametri luce non validi")
        with self._device_locks.setdefault(device_id, threading.RLock()):
            state = asyncio.run(self._set(self._entry(device_id), patch))
            with self._lock:
                self._states[device_id] = state
            return state

    def set_group(self, device_ids: list[str], patch: dict) -> dict:
        def one(device_id):
            try:
                return device_id, {"ok": True, "state": self.set(device_id, patch)}
            except Exception as exc:
                return device_id, {"ok": False, "error": str(exc)}
        if not isinstance(device_ids, list) or len(device_ids) > 32:
            raise ValueError("Gruppo non valido")
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(device_ids)))) as pool:
            return dict(pool.map(one, device_ids))

    @staticmethod
    def _native_sequence(frame_at: Callable[[float, int], dict], offset: int,
                         period: float, brightness: int, mode: str,
                         min_brightness: int = 0) -> list[list[int]]:
        sequence = []
        # L900 firmware accepts the four-point sequence used by its own
        # custom effects; longer sampled sequences are not reliable.
        steps = 4
        for step in range(steps):
            frame = frame_at(period * step / steps, offset)
            minimum = round(100 * min_brightness / brightness)
            level = (round(minimum + (100 - minimum) *
                           (1 + math.cos(2 * math.pi * step / steps)) / 2)
                     if mode in {"pulse", "breathe"}
                     else max(0, min(100, round(100 * frame["brightness"] / brightness))))
            sequence.append([frame["hue"], frame["saturation"],
                             level])
        return sequence

    async def _start_native_animation(self, item: dict, device, light, effects,
                                      frame_at: Callable[[float, int], dict], offset: int,
                                      period: float, brightness: int, mode: str,
                                      min_brightness: int) -> bool:
        """Start an L900 transition and verify that the device accepted it.

        Reuse the device's current ID, which its firmware accepts. The exact
        previous payload is saved before the edit and restored afterward.
        """
        if item["model"].startswith("L530"):
            with self._lock:
                self._active_native.add(item["id"])
            started_native = False
            try:
                try:
                    started_native = await start_native_bulb_effect(
                        item, device, frame_at, offset, period,
                        self._remember_native, self._forget_native)
                except Exception:
                    # Some L530 firmware may reject zero in a native rule.
                    # Retry with 1%, still using the bulb's smooth transition.
                    # Never retry while a failed restoration has a backup.
                    if (item["id"] in self._native_recovery or
                            not any(frame_at(period * step / 8, offset)["brightness"] == 0
                                    for step in range(8))):
                        raise
                    def with_nonzero_floor(elapsed: float, frame_offset: int) -> dict:
                        frame = frame_at(elapsed, frame_offset)
                        return {**frame, "brightness": max(1, frame["brightness"])}
                    started_native = await start_native_bulb_effect(
                        item, device, with_nonzero_floor, offset, period,
                        self._remember_native, self._forget_native)
                return started_native
            finally:
                if not started_native:
                    with self._lock:
                        self._active_native.discard(item["id"])
        if not item["model"].startswith("L900") or not effects or not effects.has_custom_effects:
            return False
        if not 2 <= period <= 20 or not 1 <= brightness <= 100:
            return False
        original = await self._read_raw_effect(device)
        hsv = light.hsv
        # L900 firmware accepts edits to the current effect ID, but may
        # acknowledge a new ID without applying it. The exact prior payload
        # is persisted before the edit and restored when the animation ends.
        temporary_id = original.get("id", "")
        if not isinstance(temporary_id, str) or not temporary_id.startswith("TapoStrip_"):
            raise ValueError("La striscia non ha un identificativo effetto riutilizzabile")
        sequence = self._native_sequence(frame_at, offset, period, brightness, mode,
                                         min_brightness)
        payload = {
            "custom": 1, "id": temporary_id, "brightness": brightness,
            "name": self._NATIVE_NAME, "enable": 1, "segments": [0],
            "expansion_strategy": 1, "display_colors": sequence,
            "type": "sequence", "duration": 0,
            "transition": round(period * 1000 / len(sequence)),
            "direction": 4, "spread": 7, "repeat_times": 0,
            "sequence": sequence,
        }
        backup = {"temporary_id": temporary_id, "temporary_sequence": sequence,
                  "temporary_brightness": brightness,
                  "effect": copy.deepcopy(original),
                  "hsv": {"hue": hsv.hue, "saturation": hsv.saturation, "value": hsv.value},
                  "on": bool(device.is_on)}
        self._remember_native(item["id"], backup)
        with self._lock:
            self._active_native.add(item["id"])
        try:
            if not device.is_on:
                await device.turn_on()
            await effects.set_custom_effect(payload)
            await device.update()
            confirmed = await self._read_raw_effect(device)
            mismatch = {key: {"requested": payload[key], "confirmed": confirmed.get(key)}
                        for key in ("id", "name", "enable", "sequence", "transition")
                        if confirmed.get(key) != payload[key]}
            self._last_native_mismatch = mismatch
            if mismatch:
                raise ValueError("Effetto nativo non accettato dalla striscia")
            return True
        except Exception as exc:
            self._last_native_error = f"{type(exc).__name__}: {exc}"
            try:
                current = await self._read_raw_effect(device)
                if all(current.get(key) == original.get(key)
                       for key in ("id", "name", "enable", "sequence")):
                    if not backup["on"]:
                        await device.turn_off()
                    self._forget_native(item["id"])
                else:
                    await self._restore_native(item, device, backup)
            finally:
                with self._lock:
                    self._active_native.discard(item["id"])
            return False

    def stream_animation(self, device_ids: list[str], stop: threading.Event,
                         frame_at: Callable[[float, int], dict], started: float,
                         *, duration: float | None = None, interval: float = 0.15,
                         native: dict | None = None,
                         external_probe_interval: float = 5.0) -> None:
        """Keep one LAN session per light while streaming a smooth animation.

        Frames are computed from monotonic time, so a delayed LAN reply skips a
        frame instead of making the pulse run slower or queue stale colors.
        """
        if not device_ids or interval < 0.1 or external_probe_interval < 0.1:
            raise ValueError("Destinazioni o intervallo animazione non validi")

        async def animate() -> None:
            sessions: dict[str, tuple] = {}
            retry_at = dict.fromkeys(device_ids, 0.0)
            native_probe_at: dict[str, float] = {}
            external_probe_at: dict[str, float] = {}
            overridden: set[str] = set()
            next_tick = time.monotonic()

            def report_native_failure(item: dict, device, message: str) -> None:
                try:
                    state = self._snapshot(item, device) if device else {
                        **item, "type": "tapo", "online": False, "capabilities": {}}
                except Exception:
                    state = {**item, "type": "tapo", "online": False,
                             "capabilities": {}}
                with self._lock:
                    self._states[item["id"]] = {**state, "animation_error": message}
                callback = native.get("on_error") if native else None
                if callable(callback):
                    try:
                        callback(item["id"], message)
                    except Exception:
                        pass

            try:
                while not stop.is_set():
                    now = time.monotonic()
                    elapsed = max(0.0, now - started)
                    if duration is not None and elapsed >= duration:
                        break

                    for offset, device_id in enumerate(device_ids):
                        if device_id in sessions or device_id in overridden or now < retry_at[device_id]:
                            continue
                        item = self._entry(device_id)
                        strict_native = bool(native and item["model"].startswith("L900")
                                             and native.get("mode") in {"pulse", "breathe"})
                        device = None
                        try:
                            device = await asyncio.wait_for(self._connect(item), timeout=4)
                            light = device.modules.get(Module.Light)
                            if light is None or not light.has_feature("hsv"):
                                raise ValueError("Questo dispositivo non supporta i colori")
                            if strict_native:
                                self._last_native_error = None
                            await self._recover_native_if_needed(item, device)
                            is_native = False
                            if native and device_id not in self._native_recovery:
                                is_native = await self._start_native_animation(
                                    item, device, light, device.modules.get(Module.LightEffect),
                                    frame_at, offset, native["period"], native["brightness"],
                                    native.get("mode", ""), native.get("min_brightness", 0))
                            if strict_native and not is_native:
                                message = ("Effetto precedente da recuperare; controlla la striscia"
                                           if device_id in self._native_recovery else self._last_native_error or
                                           "La striscia non ha confermato l'effetto nativo fluido")
                                report_native_failure(item, device, message)
                                overridden.add(device_id)
                                await device.disconnect()
                                continue
                            if not device.is_on:
                                await asyncio.wait_for(device.turn_on(), timeout=2)
                            with self._lock:
                                self._states[device_id] = self._snapshot(item, device)
                            sessions[device_id] = (item, device, light, is_native)
                            if is_native:
                                native_probe_at[device_id] = now + 5.0
                            else:
                                external_probe_at[device_id] = now + external_probe_interval
                        except Exception as exc:
                            if strict_native:
                                report_native_failure(item, device, str(exc))
                                overridden.add(device_id)
                            else:
                                retry_at[device_id] = time.monotonic() + 2
                            if device is not None:
                                try:
                                    await device.disconnect()
                                except Exception:
                                    pass

                    if len(overridden) == len(device_ids) and not sessions:
                        break

                    if stop.is_set():
                        break

                    # A phone timer or a physical switch takes precedence over
                    # frames sent by a software animation. Reconcile power from
                    # the bulb itself while the usual background poll is paused.
                    for device_id, session in list(sessions.items()):
                        item, device, _, is_native = session
                        if is_native or now < external_probe_at.get(device_id, 0):
                            continue
                        external_probe_at[device_id] = now + external_probe_interval
                        try:
                            await asyncio.wait_for(device.update(), timeout=2)
                            if device.is_on:
                                continue
                            with self._lock:
                                self._states[device_id] = self._snapshot(item, device)
                            overridden.add(device_id)
                            sessions.pop(device_id)
                            await device.disconnect()
                        except Exception:
                            pass

                    for device_id, session in list(sessions.items()):
                        item, device, _, is_native = session
                        if not is_native or now < native_probe_at.get(device_id, 0):
                            continue
                        native_probe_at[device_id] = now + 5.0
                        try:
                            await asyncio.wait_for(device.update(), timeout=2)
                            backup = self._native_recovery.get(device_id)
                            if backup and await self._native_still_selected(device, backup):
                                continue
                            if backup:
                                try:
                                    await self._restore_native(item, device, backup)
                                except BulbRuleConflict:
                                    pass
                            await device.update()
                            with self._lock:
                                self._states[device_id] = self._snapshot(item, device)
                            overridden.add(device_id)
                            sessions.pop(device_id)
                            with self._lock:
                                self._active_native.discard(device_id)
                            await device.disconnect()
                        except Exception:
                            # A temporary query failure must not replace a
                            # running device animation with queued LAN writes.
                            pass

                    async def send(device_id: str, session: tuple, offset: int) -> None:
                        item, device, light, _ = session
                        patch = frame_at(elapsed, offset)
                        # Tapo LAN HSV commands require 1..100; native strip
                        # sequences may use zero and are handled above.
                        level = max(1, patch["brightness"])
                        await asyncio.wait_for(light.set_hsv(patch["hue"], patch["saturation"],
                                                             level), timeout=2)
                        with self._lock:
                            prior = self._states.get(device_id) or self._snapshot(item, device)
                            self._states[device_id] = {
                                **prior, "online": True, "on": True,
                                "hsv": {"hue": patch["hue"], "saturation": patch["saturation"],
                                        "value": level},
                                "brightness": level, "color_temp": 0,
                                "effect": "Off",
                            }

                    active = [(device_id, sessions[device_id], offset)
                              for offset, device_id in enumerate(device_ids)
                              if device_id in sessions and not sessions[device_id][3]]
                    results = await asyncio.gather(*(send(*entry) for entry in active),
                                                   return_exceptions=True)
                    for (device_id, (_, device, _, _), _), result in zip(active, results):
                        if isinstance(result, BaseException):
                            sessions.pop(device_id, None)
                            retry_at[device_id] = time.monotonic() + 2
                            try:
                                await device.disconnect()
                            except Exception:
                                pass

                    next_tick += interval
                    delay = next_tick - time.monotonic()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    else:
                        next_tick = time.monotonic()
            finally:
                for device_id, (item, device, _, is_native) in sessions.items():
                    try:
                        if is_native:
                            await self._restore_native(item, device,
                                                       self._native_recovery[device_id])
                        await asyncio.wait_for(device.update(), timeout=2)
                        with self._lock:
                            self._states[device_id] = self._snapshot(item, device)
                    except Exception:
                        pass
                    finally:
                        with self._lock:
                            self._active_native.discard(device_id)
                    try:
                        await device.disconnect()
                    except Exception:
                        pass

        asyncio.run(animate())

    async def _energy(self, item: dict, period: str) -> dict:
        device = await self._connect(item)
        try:
            raw = await device._query_helper("get_device_usage")
            usage = raw.get("get_device_usage", raw)
            field = {"today": "today", "7d": "past7", "30d": "past30"}[period]
            minutes = usage.get("time_usage", {}).get(field)
            power = usage.get("power_usage", {})
            mwh = power.get(field + "_mwh")
            wh = power.get(field)
            kwh = mwh / 1_000_000 if mwh is not None else (wh / 1000 if wh is not None else None)
            return {"device_id": item["id"], "period": period,
                    "duration_hours": round(minutes / 60, 2) if minutes is not None else None,
                    "energy_kwh": round(kwh, 4) if kwh is not None else None,
                    "source": "Tapo LAN get_device_usage",
                    "message": "Misure riportate dal dispositivo Tapo sulla rete locale."}
        finally:
            await device.disconnect()

    def energy(self, device_id: str, period: str) -> dict:
        if period not in {"today", "7d", "30d"}:
            raise ValueError("Periodo energia non valido")
        with self._device_locks.setdefault(device_id, threading.RLock()):
            return asyncio.run(self._energy(self._entry(device_id), period))

    def configure(self, device_id: str, patch: dict) -> dict:
        entry = self._entry(device_id)
        for field in ("name", "room", "host"):
            if field in patch:
                value = str(patch[field]).strip()
                if not value:
                    raise ValueError(f"{field} obbligatorio")
                entry[field] = value
        write_json("devices.json", self.devices)
        return entry
