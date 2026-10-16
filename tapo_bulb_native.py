"""Temporary, recoverable device-side animations for Tapo L530 bulbs.

L530 firmware exposes two mutable dynamic-light rules, rather than arbitrary
custom effects.  This module borrows L2 only while an animation is running.
The caller must persist the returned backup *before* the first device write.
"""

from __future__ import annotations

import copy
from typing import Callable

from kasa import Module


RULE_ID = "L2"
SAMPLES = 8


class BulbRuleConflict(RuntimeError):
    """The phone or another controller changed L2 after Smartlight borrowed it."""


def _unwrap_rules(reply: dict) -> dict:
    data = reply.get("get_dynamic_light_effect_rules", reply)
    if not isinstance(data, dict) or not isinstance(data.get("rule_list"), list):
        raise ValueError("La lampadina non ha restituito le regole degli effetti")
    return data


def _find_rule(data: dict) -> dict:
    matches = [rule for rule in data["rule_list"] if rule.get("id") == RULE_ID]
    if len(matches) != 1:
        raise ValueError("La lampadina non dispone di una regola L2 univoca")
    return matches[0]


def _matches(actual: dict, expected: dict) -> bool:
    return all(actual.get(key) == expected.get(key)
               for key in ("id", "change_mode", "change_time", "color_status_list", "scene_name"))


async def _read_rules(effects) -> dict:
    # A regular device.update() can return the 24-hour module cache. A direct
    # query is essential to verify writes and to detect edits from the Tapo app.
    return _unwrap_rules(await effects.call("get_dynamic_light_effect_rules", {"start_index": 0}))


def make_bulb_rule(original: dict, frame_at: Callable[[float, int], dict],
                   offset: int, period: float) -> dict:
    """Sample one cycle; the bulb handles transitions between these points."""
    if not 2 <= period <= 20:
        raise ValueError("Periodo fuori dall'intervallo degli effetti nativi L530")
    if original.get("id") != RULE_ID or not isinstance(original.get("color_status_list"), list):
        raise ValueError("Regola L530 non valida")
    rule = copy.deepcopy(original)
    rule["change_mode"] = "bln"  # The mode used by L530's smooth Relax rule.
    rule["change_time"] = round(period * 1000 / SAMPLES)
    states = []
    for step in range(SAMPLES):
        frame = frame_at(period * step / SAMPLES, offset)
        hue, saturation, brightness = (frame[key] for key in ("hue", "saturation", "brightness"))
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in (hue, saturation, brightness)):
            raise ValueError("Fotogramma L530 non valido")
        if not (0 <= hue <= 360 and 0 <= saturation <= 100 and 0 <= brightness <= 100):
            raise ValueError("Valori del fotogramma L530 fuori intervallo")
        # A rule's fields are [brightness, hue, saturation, color temperature].
        # 0% is sent only in the native rule, never via set_hsv; support on a
        # particular firmware must still be confirmed by a read-after-write.
        states.append([brightness, hue, saturation, 0])
    rule["color_status_list"] = states
    return rule


async def start_native_bulb_effect(
    item: dict, device, frame_at: Callable[[float, int], dict], offset: int,
    period: float, remember: Callable[[str, dict], None],
    forget: Callable[[str], None],
) -> bool:
    """Borrow L2, persist its original value, then activate the temporary rule.

    Returns False only for an unsupported bulb; raises if a write or its
    confirmation fails. The caller can fall back to LAN frames *after* safe
    restoration, and must retain the backup if restoration fails.
    """
    if not item.get("model", "").startswith("L530"):
        return False
    effects = device.modules.get(Module.LightEffect)
    if effects is None or effects.has_custom_effects:
        return False

    original_data = await _read_rules(effects)
    original_rule = copy.deepcopy(_find_rule(original_data))
    temporary_rule = make_bulb_rule(original_rule, frame_at, offset, period)
    if _matches(original_rule, temporary_rule):
        return False

    light = device.modules.get(Module.Light)
    hsv = getattr(light, "hsv", None) if light else None
    backup = {
        "kind": "l530_rule", "host": item.get("host"),
        "original_rule": original_rule, "temporary_rule": temporary_rule,
        "active": bool(original_data.get("enable")),
        "active_rule_id": original_data.get("current_rule_id"),
        "on": bool(device.is_on),
        "hsv": ({"hue": hsv.hue, "saturation": hsv.saturation, "value": hsv.value}
                if hsv is not None else None),
    }
    remember(item["id"], backup)
    try:
        # set_effect() would edit L2 again from kasa's stale rule cache, so use
        # the native command directly after writing the temporary rule.
        await effects.call("edit_dynamic_light_effect_rule", temporary_rule)
        confirmed = _find_rule(await _read_rules(effects))
        if not _matches(confirmed, temporary_rule):
            raise RuntimeError("La regola temporanea L530 non è stata confermata")
        if not device.is_on:
            await device.turn_on()
        await effects.call("set_dynamic_light_effect_rule_enable", {"enable": True, "id": RULE_ID})
        active = await _read_rules(effects)
        if not active.get("enable") or active.get("current_rule_id") != RULE_ID:
            raise RuntimeError("L'effetto temporaneo L530 non è stato attivato")
        return True
    except Exception:
        await restore_native_bulb_effect(item, device, backup, forget)
        raise


async def restore_native_bulb_effect(
    item: dict, device, backup: dict, forget: Callable[[str], None],
) -> None:
    """Restore L2 only if it still contains Smartlight's temporary rule.

    On conflict the durable backup is retained for inspection; the app must
    not overwrite a subsequent edit made from the official Tapo app.
    """
    if backup.get("kind") != "l530_rule" or backup.get("host") != item.get("host"):
        raise ValueError("Backup dell'effetto L530 non corrispondente")
    effects = device.modules.get(Module.LightEffect)
    if effects is None:
        raise ValueError("Modulo effetti L530 non disponibile")
    data = await _read_rules(effects)
    current = _find_rule(data)
    original = backup["original_rule"]
    temporary = backup["temporary_rule"]
    if _matches(current, original):
        forget(item["id"])
        return
    if not _matches(current, temporary):
        raise BulbRuleConflict("La regola L2 è stata modificata nell'app Tapo; backup conservato")

    await effects.call("edit_dynamic_light_effect_rule", copy.deepcopy(original))
    confirmed_data = await _read_rules(effects)
    if not _matches(_find_rule(confirmed_data), original):
        raise RuntimeError("Ripristino della regola L530 non confermato")

    # Only change the running effect if our borrowed L2 is still selected.
    # A different selection from the phone takes precedence.
    if data.get("enable") and data.get("current_rule_id") == RULE_ID:
        if backup.get("active") and backup.get("active_rule_id"):
            await effects.call("set_dynamic_light_effect_rule_enable",
                               {"enable": True, "id": backup["active_rule_id"]})
        else:
            await effects.call("set_dynamic_light_effect_rule_enable", {"enable": False})
            hsv = backup.get("hsv")
            light = device.modules.get(Module.Light)
            # If the phone turned the bulb off meanwhile, leave it off.
            if device.is_on and hsv and light is not None and hsv["value"] >= 1:
                await light.set_hsv(hsv["hue"], hsv["saturation"], hsv["value"])
            if not backup.get("on", True):
                await device.turn_off()
    forget(item["id"])
