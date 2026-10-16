"""Motore effetti di HWLight.

Un solo thread parla con i backend: per ogni dispositivo acceso calcola il frame
dell'effetto scelto e lo invia solo se e' cambiato rispetto all'ultimo inviato
(un colore statico non genera traffico). I frame restano disponibili in
`Engine.frames` per le anteprime dell'interfaccia.
"""
from __future__ import annotations

import colorsys
import math
import queue
import random
import threading
import time

from .backends import Light

RGB = tuple[int, int, int]
FPS = 30
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

DEFAULT_DEVICE = {
    "on": True,
    "effect": "statico",
    "color": [0, 120, 255],
    "color2": [255, 255, 255],
    "speed": 1.0,
    "brightness": 100,
}


# --------------------------------------------------------------------------- utilita' colore

def _clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def scale(c, f: float) -> RGB:
    return (_clamp(c[0] * f), _clamp(c[1] * f), _clamp(c[2] * f))


def smooth_pulse_level(elapsed: float, period: float, mode: str,
                       minimum: float | None = None) -> float:
    """Continuous brightness envelope shared with Tapo animations."""
    floor = (0.25 if mode == "pulse" else 0.15) if minimum is None else minimum
    return floor + (1.0 - floor) * (1.0 + math.cos(2.0 * math.pi * elapsed / period)) / 2.0


def mix(a, b, f: float) -> RGB:
    f = max(0.0, min(1.0, f))
    return (_clamp(a[0] + (b[0] - a[0]) * f), _clamp(a[1] + (b[1] - a[1]) * f), _clamp(a[2] + (b[2] - a[2]) * f))


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (_clamp(r * 255), _clamp(g * 255), _clamp(b * 255))


def _fire_palette(heat: float) -> RGB:
    heat = max(0.0, min(1.0, heat))
    if heat < 0.5:                       # rosso scuro -> arancio
        return mix((90, 0, 0), (255, 90, 0), heat * 2)
    return mix((255, 90, 0), (255, 220, 60), (heat - 0.5) * 2)   # arancio -> giallo


# --------------------------------------------------------------------------- effetti
# firma: render(n, t, p, mem) -> lista di n colori. p = {"color", "color2", "speed"}; mem = dict persistente.

def fx_statico(n, t, p, mem):
    return [p["color"]] * n


def fx_respiro(n, t, p, mem):
    f = 0.08 + 0.92 * (math.sin(t * p["speed"] * 1.5) + 1) / 2
    return [scale(p["color"], f)] * n


def fx_pulsazione(n, t, p, mem):
    f = (math.sin(t * p["speed"] * 1.5) + 1) / 2
    return [mix(p["color"], p["color2"], f)] * n


def fx_batticuore(n, t, p, mem):
    period = 1.6 / p["speed"]
    ph = (t % period) / period

    def beat(x):
        # A short rise removes the full-brightness jump at each heartbeat.
        return min(1.0, 1.85 * (1 - math.exp(-120 * x)) * math.exp(-28 * x)) if x >= 0 else 0.0
    v = max(beat(ph), beat(ph - 0.2), 0.05)
    return [scale(p["color"], v)] * n


def fx_ciclo(n, t, p, mem):
    return [hsv(t * p["speed"] * 0.08)] * n


def fx_arcobaleno(n, t, p, mem):
    base = t * p["speed"] * 0.12
    return [hsv(base + (i / n if n > 1 else 0)) for i in range(n)]


def fx_onda(n, t, p, mem):
    out = []
    for i in range(n):
        pos = (i / max(n, 1)) * 1.5 - t * p["speed"] * 0.25
        f = (math.sin(pos * 2 * math.pi) + 1) / 2
        out.append(mix(p["color"], p["color2"], f))
    return out


def fx_cometa(n, t, p, mem):
    tail = max(3, n // 4)
    # Let the highlight leave the strip fully before it re-enters. The old
    # modulo restarted directly on LED 0 and produced a visible jump.
    span = n + tail + 1
    head = (t * p["speed"] * max(6.0, n * 0.35)) % span - 1
    out = []
    for i in range(n):
        d = head - i
        width = 1.0 if d < 0 else tail
        v = (1.0 + math.cos(math.pi * d / width)) / 2.0 if -1.0 < d < tail else 0.0
        out.append(scale(p["color"], 0.03 + 0.97 * v))
    return out


def fx_scintille(n, t, p, mem):
    v = mem.setdefault("v", [0.0] * n)
    if len(v) != n:
        v[:] = [0.0] * n
    spawn = 0.02 * p["speed"] * n
    while spawn > 0:
        if random.random() < spawn:
            v[random.randrange(n)] = 1.0
        spawn -= 1
    out = []
    for i in range(n):
        v[i] *= 0.86
        c = mix(p["color"], WHITE, v[i] * 0.5)
        out.append(scale(c, 0.18 + 0.82 * v[i]))
    return out


def fx_pioggia(n, t, p, mem):
    drops = mem.setdefault("drops", [])
    last = mem.get("t", t)
    dt = min(0.2, max(0.0, t - last))
    mem["t"] = t
    if random.random() < 0.06 * p["speed"] * max(1, n / 8):
        drops.append(-1.0)
    vel = 8.0 * p["speed"]
    for k in range(len(drops)):
        drops[k] += vel * dt
    drops[:] = [d for d in drops if d < n + 3]
    bg = scale(p["color"], 0.15)
    out = [bg] * n
    for d in drops:
        for k in range(3):
            pos = d - k
            first = math.floor(pos)
            for i in (first, first + 1):
                if 0 <= i < n:
                    coverage = max(0.0, 1.0 - abs(i - pos))
                    out[i] = mix(out[i], p["color2"], (1 - k / 3) ** 2 * coverage)
    return out


def fx_fuoco(n, t, p, mem):
    heat = mem.setdefault("heat", [random.random() for _ in range(n)])
    if len(heat) != n:
        heat[:] = [random.random() for _ in range(n)]
    k = min(1.0, 0.25 * p["speed"])
    for i in range(n):
        target = random.random() ** 0.7
        heat[i] += (target - heat[i]) * k
    return [_fire_palette(h) for h in heat]


def fx_aurora(n, t, p, mem):
    out = []
    for i in range(n):
        x = i / max(n, 1)
        a = (math.sin(x * 3.0 + t * p["speed"] * 0.5) + 1) / 2
        b = (math.sin(x * 5.0 - t * p["speed"] * 0.33 + 1.7) + 1) / 2
        c = mix(p["color"], p["color2"], a)
        c = mix(c, (40, 255, 150), 0.3 * b)
        out.append(scale(c, 0.45 + 0.55 * a))
    return out


def fx_lampi(n, t, p, mem):
    flash = mem.get("flash", 0.0) * 0.72
    nxt = mem.setdefault("next", t + random.uniform(0.5, 2.5) / p["speed"])
    if t >= nxt:
        flash = 1.0
        if random.random() < 0.5:
            mem["next"] = t + 0.12          # eco ravvicinata
        else:
            mem["next"] = t + random.uniform(0.6, 3.0) / p["speed"]
    mem["flash"] = flash
    bg = scale(p["color"], 0.06)
    return [mix(bg, WHITE, flash)] * n


def fx_neon(n, t, p, mem):
    level = mem.get("level", 1.0)
    if random.random() < 0.04 * p["speed"]:
        level = random.uniform(0.15, 0.6)
    else:
        level += (1.0 - level) * 0.35
    mem["level"] = level
    hum = 0.94 + 0.06 * math.sin(t * 40)
    return [scale(p["color"], level * hum)] * n


def fx_inseguimento(n, t, p, mem):
    step = t * p["speed"] * 6.0
    out = []
    for i in range(n):
        phase = (i - step) % 6
        # A periodic lobe crosses each LED continuously instead of switching
        # between three fixed intensities at the phase boundaries.
        v = 0.05 + 0.95 * ((1 + math.cos(2 * math.pi * (phase - 1) / 6)) / 2) ** 5
        out.append(scale(p["color"], v))
    return out


def fx_scanner(n, t, p, mem):
    if n == 1:
        return [scale(p["color"], 0.12 + 0.88 * (math.sin(t * p["speed"] * 3) * 0.5 + 0.5))]
    span = (n - 1) * 2
    pos = (t * p["speed"] * max(6.0, n * 0.5)) % span
    if pos > n - 1:
        pos = span - pos                      # rimbalza al bordo
    width = max(1.5, n / 8)
    out = []
    for i in range(n):
        v = max(0.0, 1 - (abs(i - pos) / width) ** 2)
        out.append(scale(p["color"], 0.04 + 0.96 * v))
    return out


def fx_strobo(n, t, p, mem):
    period = max(0.09, 0.5 / p["speed"])
    return [p["color"] if (t % period) < period * 0.18 else BLACK] * n


def fx_coriandoli(n, t, p, mem):
    cells = mem.setdefault("cells", [])
    if len(cells) != n:
        cells[:] = [[0.0, BLACK] for _ in range(n)]
    spawn = 0.05 * p["speed"] * n
    while spawn > 0:
        if random.random() < spawn:
            cell = cells[random.randrange(n)]
            cell[0] = 1.0
            cell[1] = hsv(random.random())
        spawn -= 1
    out = []
    for cell in cells:
        cell[0] *= 0.90
        out.append(scale(cell[1], cell[0]))
    return out


def fx_plasma(n, t, p, mem):
    out = []
    for i in range(n):
        x = i / max(n - 1, 1)
        v = (math.sin(x * 4 + t * p["speed"] * 0.7)
             + math.sin(x * 7 - t * p["speed"] * 0.5)
             + math.sin(t * p["speed"] * 0.3)) / 3
        out.append(hsv(0.5 + v * 0.5, 0.9, 1.0))
    return out


def fx_vortice(n, t, p, mem):
    base = t * p["speed"] * 0.25
    out = []
    for i in range(n):
        x = i / max(n, 1)
        v = 0.3 + 0.7 * ((math.sin((x * 2 - base) * 2 * math.pi) + 1) / 2)
        out.append(hsv(base + x * 2, 1.0, v))
    return out


def fx_fuochi(n, t, p, mem):
    bursts = mem.setdefault("bursts", [])
    last = mem.get("t", t)
    dt = min(0.2, max(0.0, t - last))
    mem["t"] = t
    if random.random() < 0.035 * p["speed"] * max(1.0, n / 10):
        bursts.append({"c": random.uniform(0, n - 1), "r": 0.0, "col": hsv(random.random())})
    for b in bursts:
        b["r"] += dt * p["speed"] * max(3.0, n * 0.35)
    limit = n * 0.6 + 2
    bursts[:] = [b for b in bursts if b["r"] < limit + 2]
    out = [BLACK] * n
    for b in bursts:
        fade = max(0.0, 1 - b["r"] / limit)
        for i in range(n):
            edge = abs(abs(i - b["c"]) - b["r"])
            if edge < 1.6:
                out[i] = mix(out[i], b["col"], (1 - edge / 1.6) * fade)
    return out


def fx_caramella(n, t, p, mem):
    step = t * p["speed"] * 4.0
    width = max(2.0, n / 6)
    return [mix(p["color"], p["color2"],
                (1.0 - math.cos(math.pi * (i + step) / width)) / 2.0)
            for i in range(n)]


def fx_polizia(n, t, p, mem):
    period = max(0.25, 1.2 / p["speed"])
    ph = (t % period) / period
    rosso = ph < 0.18 or 0.24 <= ph < 0.42
    blu = 0.5 <= ph < 0.68 or 0.74 <= ph < 0.92
    half = max(1, n // 2)
    return [((255, 0, 0) if rosso else BLACK) if i < half else ((0, 40, 255) if blu else BLACK)
            for i in range(n)]


EFFECTS = {
    "statico":     {"label": "Statico",      "colors": 1, "render": fx_statico},
    "respiro":     {"label": "Respiro",      "colors": 1, "render": fx_respiro},
    "pulsazione":  {"label": "Pulsazione",   "colors": 2, "render": fx_pulsazione},
    "batticuore":  {"label": "Batticuore",   "colors": 1, "render": fx_batticuore},
    "ciclo":       {"label": "Ciclo colori", "colors": 0, "render": fx_ciclo},
    "arcobaleno":  {"label": "Arcobaleno",   "colors": 0, "render": fx_arcobaleno},
    "onda":        {"label": "Onda colore",  "colors": 2, "render": fx_onda},
    "cometa":      {"label": "Cometa",       "colors": 1, "render": fx_cometa},
    "scintille":   {"label": "Scintille",    "colors": 1, "render": fx_scintille},
    "pioggia":     {"label": "Pioggia",      "colors": 2, "render": fx_pioggia},
    "fuoco":       {"label": "Fuoco",        "colors": 0, "render": fx_fuoco},
    "aurora":      {"label": "Aurora",       "colors": 2, "render": fx_aurora},
    "lampi":       {"label": "Tempesta",     "colors": 1, "render": fx_lampi},
    "neon":        {"label": "Neon",         "colors": 1, "render": fx_neon},
    # aggiunti dopo
    "inseguimento": {"label": "Inseguimento",       "colors": 1, "render": fx_inseguimento},
    "scanner":      {"label": "Scanner",            "colors": 1, "render": fx_scanner},
    "strobo":       {"label": "Stroboscopio",       "colors": 1, "render": fx_strobo},
    "caramella":    {"label": "Caramella",          "colors": 2, "render": fx_caramella},
    "coriandoli":   {"label": "Coriandoli",         "colors": 0, "render": fx_coriandoli},
    "plasma":       {"label": "Plasma",             "colors": 0, "render": fx_plasma},
    "vortice":      {"label": "Vortice",            "colors": 0, "render": fx_vortice},
    "fuochi":       {"label": "Fuochi d'artificio", "colors": 0, "render": fx_fuochi},
    "polizia":      {"label": "Polizia",            "colors": 0, "render": fx_polizia},
}


def effects_info() -> list[dict]:
    return [{"id": k, "label": v["label"], "colors": v["colors"]} for k, v in EFFECTS.items()]


def normalize_device_state(st: dict | None) -> dict:
    """Completa uno stato (anche nel vecchio formato {color,on}) con i valori di default."""
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_DEVICE.items()}
    if st:
        for k in out:
            if k in st and st[k] is not None:
                out[k] = list(st[k]) if isinstance(out[k], list) else st[k]
    if out["effect"] not in EFFECTS and not (isinstance(out["effect"], str) and out["effect"].startswith("msi:")):
        out["effect"] = "statico"
    out["speed"] = float(max(0.2, min(4.0, out["speed"])))
    out["brightness"] = int(max(0, min(100, out["brightness"])))
    out["color"] = [_clamp(v) for v in out["color"][:3]]
    out["color2"] = [_clamp(v) for v in out["color2"][:3]]
    out["on"] = bool(out["on"])
    controls = (st or {}).get("native_controls", [])
    out["native_controls"] = [key for key in controls if key in {"color", "speed", "brightness"}] if isinstance(controls, list) else []
    return out


# --------------------------------------------------------------------------- motore

class Engine(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="hwlight-engine")
        self.lock = threading.RLock()
        self.lights: dict[str, Light] = {}
        self.state: dict[str, dict] = {}
        self.global_brightness = 100
        self.jobs: queue.Queue = queue.Queue()
        self.errors: queue.Queue = queue.Queue()
        self.frames: dict[str, list[RGB]] = {}
        self.writes = 0
        self._last_sent: dict[str, list[RGB]] = {}
        self._native_sent: dict[str, tuple] = {}
        self._native_read_at: dict[str, float] = {}
        self._native_brightness_managed: set[str] = set()
        self._mem: dict[str, dict] = {}
        self._off_done: set[str] = set()
        self._last_err: dict[str, tuple[str, float]] = {}
        self.flow: dict | None = None

    def start_flow(self, palette: list[RGB], period: float, keys: list[str],
                   started: float, direction: str = "forward", *,
                   mode: str = "flow", brightness: int = 100,
                   transition_ms: float | None = None,
                   min_brightness: int | None = None) -> None:
        """Render one shared color wave at 30 FPS across selected PC blocks."""
        with self.lock:
            self.flow = {"palette": palette, "period": period, "keys": tuple(keys),
                         "started": started, "direction": direction,
                         "mode": mode, "brightness": brightness,
                         "transition_ms": transition_ms,
                         "min_brightness": min_brightness}
            self._last_sent.clear()
            self._native_sent.clear()

    def stop_flow(self) -> None:
        with self.lock:
            self.flow = None
            self._last_sent.clear()
            self._native_sent.clear()

    # -- stato ---------------------------------------------------------------
    def device_state(self, key: str) -> dict:
        with self.lock:
            st = self.state.get(key)
            if st is None:
                st = normalize_device_state(None)
                self.state[key] = st
            return st

    def update_device(self, key: str, patch: dict) -> dict:
        with self.lock:
            cur = self.state.get(key) or normalize_device_state(None)
            merged = dict(cur)
            merged.update({k: v for k, v in patch.items() if k in DEFAULT_DEVICE})
            if merged.get("effect", "").startswith("msi:"):
                controls = set(cur.get("native_controls", [])) if merged["effect"] == cur.get("effect") else set()
                controls.update(set(patch).intersection({"color", "speed", "brightness"}))
                merged["native_controls"] = sorted(controls)
            st = normalize_device_state(merged)
            if st["effect"] != cur.get("effect"):
                self._mem.pop(key, None)
                self._native_brightness_managed.discard(key)
            self.state[key] = st
            self._native_sent.pop(key, None)
            self._native_read_at.pop(key, None)
            self._last_sent.pop(key, None)      # forza la riscrittura al prossimo frame
            self._off_done.discard(key)        # anche OFF ripetuto deve arrivare all'hardware
            return st

    def set_lights(self, lights: dict[str, Light]):
        with self.lock:
            self.lights = dict(lights)
            self._native_brightness_managed.clear()
            self._native_read_at.clear()
            self._last_sent.clear()
            self._native_sent.clear()
            self._off_done.clear()
            for key in self.lights:
                if key not in self.state:
                    self.state[key] = normalize_device_state(None)

    def invalidate(self):
        with self.lock:
            self._last_sent.clear()
            self._native_sent.clear()
            self._off_done.clear()

    def submit(self, fn):
        self.jobs.put(fn)

    # -- loop ---------------------------------------------------------------
    def run(self):
        t_start = time.time()
        period = 1.0 / FPS
        next_tick = time.time()
        while True:
            try:
                while True:
                    fn = self.jobs.get_nowait()
                    try:
                        fn()
                    except Exception as e:  # noqa: BLE001
                        self.errors.put(str(e))
            except queue.Empty:
                pass
            with self.lock:
                items = list(self.lights.items())
            t = time.time() - t_start
            for key, light in items:
                # Non perdere un comando arrivato mentre un frame precedente era in invio.
                with self.lock:
                    st = self.state.get(key)
                    if st is None or self.lights.get(key) is not light:
                        continue
                    try:
                        self._render(key, light, st, t, self.global_brightness / 100.0)
                    except Exception as e:  # noqa: BLE001
                        self._report(key, str(e))
            next_tick += period
            delay = next_tick - time.time()
            if delay > 0:
                time.sleep(delay)
            else:
                next_tick = time.time()

    def _read_native(self, key, light, *, force=False):
        now = time.monotonic()
        if not force and now - self._native_read_at.get(key, -10) < 3:
            return
        observed = dict(light.get_native_state())
        style = observed.get("style")
        brightness = observed.get("brightness")
        observed["power"] = (False if (isinstance(style, str) and style.strip().casefold() == "off") or brightness == 0
                             else True if isinstance(brightness, (int, float)) and brightness > 0 and style
                             else None)
        observed["observed_at"] = time.time()
        light.cached_native_state = observed
        self._native_read_at[key] = now

    def _render(self, key: str, light: Light, st: dict, t: float, gbri: float):
        n = light.led_count
        flow = self.flow
        native_mode = st["effect"].startswith("msi:") and not (flow and key in flow["keys"])
        if native_mode:
            self._read_native(key, light)
        native_zero = st["effect"].startswith("msi:") and not (flow and key in flow["keys"]) and (st["brightness"] == 0 or gbri == 0)
        if not st["on"] or native_zero:
            if key not in self._off_done:
                light.off()
                self._off_done.add(key)
                self._last_sent.pop(key, None)
                self._native_sent.pop(key, None)
                self.writes += 1
                if native_mode:
                    self._read_native(key, light, force=True)
            self.frames[key] = [BLACK] * n
            return
        restoring_native = key in self._off_done
        self._off_done.discard(key)
        flow = self.flow
        if st["effect"].startswith("msi:") and not (flow and key in flow["keys"]):
            style = st["effect"][4:]
            controls = set(st.get("native_controls", []))
            speed = (st["speed"] - 0.2) / 3.8 if "speed" in controls else None
            if gbri != 1 or restoring_native:
                self._native_brightness_managed.add(key)
            brightness = st["brightness"] / 100 * gbri if ("brightness" in controls or key in self._native_brightness_managed) else None
            color = tuple(st["color"]) if "color" in controls else None
            signature = (style, color, speed, brightness)
            if signature != self._native_sent.get(key):
                light.native_apply_result = light.set_native_effect(style,
                    color=list(color) if color is not None else None,
                    normalized_speed=speed, normalized_brightness=brightness)
                self._native_sent[key] = signature
                self._last_sent.pop(key, None)
                self.writes += 1
                self._read_native(key, light, force=True)
            # Readback runs on the writer thread, never on the UI/status path.
            # Native hardware animations cannot be accurately previewed from a
            # configured SDK color. Do not feed invented frames to PC-to-Tapo sync.
            self.frames.pop(key, None)
            return
        self._native_sent.pop(key, None)
        if flow and key in flow["keys"]:
            palette = flow["palette"]
            order = flow["keys"].index(key)
            sign = -1 if flow["direction"] == "reverse" else 1
            elapsed = time.monotonic() - flow["started"]
            alternate_steps = (flow["direction"] == "alternate"
                               and flow["mode"] in {"sequence", "cycle"})
            # Stepped reverse starts on the first color, then visits the
            # remaining colors backwards. Negating the phase would jump to
            # the last held color immediately after animation start.
            reverse_steps = sign < 0 and flow["mode"] in {"sequence", "cycle"}
            if reverse_steps:
                palette = [palette[0], *reversed(palette[1:])]
            render_period = flow["period"]
            if alternate_steps:
                indices = [*range(len(palette)), *range(len(palette) - 2, 0, -1)]
                palette = [palette[index] for index in indices]
            if flow["direction"] == "alternate" and not alternate_steps:
                phase = (elapsed / render_period) % 2.0
                base = phase if phase <= 1.0 else 2.0 - phase
            else:
                base = (1 if reverse_steps or alternate_steps else sign) * elapsed / render_period
            base += sign * order / max(1, len(flow["keys"]))
            frame = []
            for led in range(n):
                point = (base + sign * led / max(1, n * len(flow["keys"]))) % 1.0
                position = point * len(palette)
                i = int(position)
                blend = position - i
                if flow["mode"] in {"sequence", "cycle"} and flow["transition_ms"] is not None:
                    step_ms = render_period * 1000.0 / len(palette)
                    fade = min(1.0, flow["transition_ms"] / step_ms)
                    blend = max(0.0, (blend - (1.0 - fade)) / fade) if fade else 0.0
                frame.append(mix(palette[i % len(palette)], palette[(i + 1) % len(palette)], blend))
        else:
            fx = EFFECTS.get(st["effect"], EFFECTS["statico"])
            p = {"color": tuple(st["color"]), "color2": tuple(st["color2"]), "speed": float(st["speed"])}
            frame = fx["render"](n, t, p, self._mem.setdefault(key, {}))
        bri = (st["brightness"] / 100.0) * gbri
        if flow and key in flow["keys"]:
            bri *= flow["brightness"] / 100.0
            if flow["mode"] in {"pulse", "breathe"}:
                minimum = flow["min_brightness"]
                floor = None if minimum is None else (minimum / flow["brightness"]
                                                      if flow["brightness"] else 0.0)
                bri *= smooth_pulse_level(elapsed, flow["period"], flow["mode"], floor)
        if bri < 0.999:
            frame = [scale(c, bri) for c in frame]
        self.frames[key] = frame
        if frame != self._last_sent.get(key):
            light.set_leds(frame)
            self._last_sent[key] = frame
            self.writes += 1

    def _report(self, key: str, msg: str):
        last = self._last_err.get(key)
        now = time.time()
        if last and last[0] == msg and now - last[1] < 10:
            return
        self._last_err[key] = (msg, now)
        self.errors.put(f"{key.split(':', 1)[-1]}: {msg}")
