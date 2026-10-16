"""Backend luci per HWLight.

Due sorgenti:
  * OpenRGB  -> scheda madre ASUS, GPU Palit, tastiera/mouse Logitech (via server SDK, porta 6742)
  * iCUE SDK -> hub iCUE LINK (pompa TITAN 360 + ventole RX) e RAM Vengeance DDR5 (iCUE deve essere aperto)

Ogni "Light" e' un blocco luminoso indipendente con N LED.
"""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

RGB = tuple[int, int, int]


class Light:
    key: str          # id stabile, usato per salvare lo stato
    name: str         # nome mostrato
    source: str       # "OpenRGB" | "iCUE"
    kind: str         # tipo (GPU, KEYBOARD, RAM, ...)
    led_count: int

    @property
    def category(self) -> str:
        k = (self.kind or "").upper()
        if k in ("COOLER", "FAN"):
            return "Raffreddamento"
        if k in ("RAM", "DRAM", "MEMORYMODULE"):
            return "Memoria"
        if k == "MOTHERBOARD":
            return "Scheda madre"
        if k == "GPU":
            return "Scheda video"
        if k in ("KEYBOARD", "MOUSE", "MOUSEMAT", "HEADSET", "HEADSET_STAND", "GAMEPAD", "KEYPAD"):
            return "Periferiche"
        return "Altro"

    def set_leds(self, colors: list[RGB]) -> None:
        raise NotImplementedError

    def set_color(self, color: RGB) -> None:
        self.set_leds([color] * self.led_count)

    def off(self) -> None:
        self.set_color((0, 0, 0))


# --------------------------------------------------------------------------- OpenRGB

OPENRGB_EXE_CANDIDATES = [
    r"C:\Program Files\OpenRGB\OpenRGB.exe",
    r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\OpenRGB\OpenRGB.exe"),
]
NET_PACKET_ID_REQUEST_RESCAN_DEVICES = 140


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


OPENRGB_SDK_HINT = 'OpenRGB è avviato senza il server SDK. Abilita SDK Server sulla porta 6742 nelle sue impostazioni.'

def _openrgb_executables() -> list[str]:
    """Percorsi plausibili dell'eseguibile OpenRGB, nell'ordine di preferenza."""
    found: list[str] = []

    def add(path: str | None) -> None:
        if path and os.path.isfile(path) and path not in found:
            found.append(path)

    if os.name == "nt":
        for exe in OPENRGB_EXE_CANDIDATES:
            add(os.path.expandvars(exe))
        return found

    import shutil

    add(shutil.which("openrgb"))
    add(shutil.which("OpenRGB"))
    for path in ("/usr/bin/openrgb", "/usr/local/bin/openrgb",
                 "/var/lib/flatpak/exports/bin/org.openrgb.OpenRGB"):
        add(path)
    home = Path.home()
    for matches in (Path("/opt").glob("OpenRGB*/OpenRGB*.AppImage"),
                    home.glob("OpenRGB*/OpenRGB*.AppImage"),
                    home.glob("Applications/OpenRGB*.AppImage")):
        for candidate in matches:
            add(str(candidate))
    for argv in _openrgb_processes():
        add(argv[0])
    return found

def _openrgb_processes() -> list[list[str]]:
    """Righe di comando dei processi OpenRGB attivi (solo Linux/macOS)."""
    if os.name == "nt":
        return []
    processes: list[list[str]] = []
    try:
        for cmdline in Path("/proc").glob("*/cmdline"):
            try:
                parts = cmdline.read_bytes().split(b"\0")
            except OSError:
                continue
            argv = [part.decode("utf-8", "replace") for part in parts if part]
            if argv and "openrgb" in Path(argv[0]).name.lower():
                processes.append(argv)
    except OSError:
        pass
    return processes

def _openrgb_process_running() -> bool:
    if os.name == "nt":
        return _process_running("OpenRGB.exe")
    return bool(_openrgb_processes())


class OpenRGBLight(Light):
    def __init__(self, dev, name: str | None = None):
        self.dev = dev
        self.name = name or dev.name
        self.key = f"openrgb:{self.name}"
        self.source = "OpenRGB"
        self.kind = dev.type.name
        self.led_count = len(dev.leds)
        self._mode_ready = False
        # G512/G815-family controllers keep a per-key color cache in OpenRGB.
        # Their native Off/Static mode does not reliably reach the keyboard;
        # entering Direct also resets keys without invalidating that cache.
        # Keep keyboard power in Direct and refresh every key on entry.
        self._direct_keyboard = self.kind == "KEYBOARD" and "logitech" in self.name.lower()
        self._full_frame_pending = False

    def _mode_names(self) -> list[str]:
        return [m.name.lower() for m in self.dev.modes]

    def _ensure_direct(self) -> None:
        """Mette il dispositivo in una modalita' che accetta colori dal software."""
        if self._mode_ready:
            return
        names = self._mode_names()
        for want in ("direct", "static", "custom"):
            if want in names:
                # Il valore locale puo' essere vecchio dopo standby o interventi esterni.
                self.dev.set_mode(self._sanitized_mode(names.index(want)))
                self._full_frame_pending = self._direct_keyboard and want == "direct"
                break
        self._mode_ready = True

    def _sanitized_mode(self, index: int):
        """Alcuni controller (es. GPU Palit) riportano valori fuori scala: li riporto nei limiti."""
        mode = self.dev.modes[index]
        if mode.brightness_max is not None and mode.brightness is not None:
            lo, hi = sorted((mode.brightness_min or 0, mode.brightness_max))
            if not lo <= mode.brightness <= hi:
                mode.brightness = hi
        if mode.speed_max is not None and mode.speed is not None:
            lo, hi = sorted((mode.speed_min or 0, mode.speed_max))
            if not lo <= mode.speed <= hi:
                mode.speed = (lo + hi) // 2
        return mode

    def set_leds(self, colors: list[RGB]) -> None:
        from openrgb.utils import RGBColor
        self._ensure_direct()
        colors = list(colors[: self.led_count])
        if len(colors) < self.led_count:
            colors += [colors[-1] if colors else (0, 0, 0)] * (self.led_count - len(colors))
        if not colors:
            return
        if self._full_frame_pending:
            # Repeating the target frame cannot bypass OpenRGB's own cache.
            # A one-level difference makes the following frame update ALL keys
            # without a visible color flash, including a previously black key.
            priming = [(r + 1 if r < 255 else r - 1, g, b) for r, g, b in colors]
            self.dev.set_colors([RGBColor(*c) for c in priming], fast=True)
        if len(set(colors)) == 1:
            self.dev.set_color(RGBColor(*colors[0]), fast=True)
        else:
            self.dev.set_colors([RGBColor(*c) for c in colors], fast=True)
        self._full_frame_pending = False

    def off(self) -> None:
        if self._direct_keyboard:
            # Native Off leaves the G512's cached per-key frame untouched and
            # can be a no-op. Black in Direct is reversible with the same path
            # used by UI/MCP colors; it never re-enters a native mode on power on.
            self.set_color((0, 0, 0))
            return
        names = self._mode_names()
        if "off" in names:
            # Preferire lo spegnimento globale del controller: il nero in Direct
            # sulla G512 richiede piu' pacchetti di aggiornamento dei singoli tasti.
            self.dev.set_mode(self._sanitized_mode(names.index("off")))
            self._mode_ready = False
        else:
            self._mode_ready = False
            self.set_color((0, 0, 0))


class OpenRGBBackend:
    def __init__(self, host: str = "127.0.0.1", port: int = 6742, *, include_corsair: bool | None = None):
        self.host = host
        self.port = port
        self.include_corsair = os.name != "nt" if include_corsair is None else include_corsair
        self.client = None
        self.status = "non connesso"
        self.lights: list[OpenRGBLight] = []

    def _launch(self) -> bool:
        executables = _openrgb_executables()
        if not executables:
            return False
        exe = executables[0]
        command = [exe, "--server", "--startminimized"]
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["cwd"] = os.path.dirname(exe)
            kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(command, **kwargs)
        return True

    def connect(self, autostart: bool = True, timeout: float = 60,
                log: Callable[[str], None] = lambda s: None) -> list[OpenRGBLight]:
        from openrgb import OpenRGBClient

        if not _port_open(self.host, self.port):
            if _openrgb_process_running():
                # Due istanze di OpenRGB comanderebbero gli stessi dispositivi:
                # spiego come abilitare il server invece di avviarne una copia.
                self.status = OPENRGB_SDK_HINT
                return []
            if not autostart or not self._launch():
                self.status = f"OpenRGB non raggiungibile su {self.host}:{self.port} (avvialo con --server)"
                return []
            log("Avvio OpenRGB con server SDK, attendo la rilevazione...")
            t0 = time.time()
            while not _port_open(self.host, self.port):
                if time.time() - t0 > timeout:
                    self.status = "OpenRGB non ha avviato il server SDK"
                    return []
                time.sleep(1)
        self.client = OpenRGBClient(self.host, self.port, "Smartlight")
        self._build()
        return self.lights

    def _build(self) -> None:
        """Un blocco per ogni dispositivo OpenRGB; i nomi ripetuti prendono un indice."""
        devices = [device for device in self.client.devices if len(device.leds) > 0
                   and (self.include_corsair or not device.name.lower().startswith("corsair"))]
        totali: dict[str, int] = {}
        for device in devices:
            totali[device.name] = totali.get(device.name, 0) + 1
        visti: dict[str, int] = {}
        self.lights = []
        for device in devices:
            visti[device.name] = visti.get(device.name, 0) + 1
            index = visti[device.name]
            label = device.name if totali[device.name] == 1 else f"{device.name} #{index}"
            self.lights.append(OpenRGBLight(device, label))
        self.status = f"connesso ({len(self.lights)} dispositivi)"

    def rescan(self, wait: float = 30) -> list[OpenRGBLight]:
        """Chiede a OpenRGB di rilevare di nuovo i dispositivi (es. mouse wireless riacceso)."""
        if not self.client:
            return self.connect()
        self.client.comms.send_header(0, NET_PACKET_ID_REQUEST_RESCAN_DEVICES, 0)
        time.sleep(wait)
        self.client.update()
        self._build()
        return self.lights


# --------------------------------------------------------------------------- iCUE

class ICueLight(Light):
    def __init__(self, backend: "ICueBackend", device_id: str, name: str, led_ids: list[int], kind: str):
        self.backend = backend
        self.device_id = device_id
        self.led_ids = led_ids
        self.key = f"icue:{name}"
        self.name = name
        self.source = "iCUE"
        self.kind = kind
        self.led_count = len(led_ids)

    def set_leds(self, colors: list[RGB]) -> None:
        colors = list(colors[: self.led_count])
        if len(colors) < self.led_count:
            colors += [colors[-1] if colors else (0, 0, 0)] * (self.led_count - len(colors))
        self.backend.write(self.device_id, self.led_ids, colors)


ICUE_DIR = r"C:\Program Files\Corsair\Corsair iCUE5 Software"
ICUE_LAUNCH_CANDIDATES = [
    ([os.path.join(ICUE_DIR, "iCUE Launcher.exe"), "--autorun"]),   # stesso comando dell'avvio automatico: parte in tray
    ([os.path.join(ICUE_DIR, "iCUE.exe")]),
]


def _ok(err) -> bool:
    """True se una chiamata dell'SDK iCUE e' andata a buon fine."""
    return str(err) == "CorsairError.CE_Success"


def _process_running(image_name: str) -> bool:
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/NH"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return image_name.lower() in out.lower()
    except Exception:  # noqa: BLE001
        return False


class ICueBackend:
    def __init__(self):
        self.sdk = None
        self.status = "non connesso"
        self.lights: list[ICueLight] = []
        self._controlled: set[str] = set()
        self._state = None
        self._cb = None  # tenuto vivo: il callback nativo non deve essere raccolto dal GC
        self._launched = False
        self._ever_connected = False
        self._dropped = False
        self.on_reconnect: Callable[[], None] | None = None  # chiamata quando iCUE torna disponibile

    @staticmethod
    def _launch() -> bool:
        for cmd in ICUE_LAUNCH_CANDIDATES:
            if os.path.isfile(cmd[0]):
                subprocess.Popen(cmd, cwd=ICUE_DIR,
                                 creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
                return True
        return False

    def _wait_connected(self, timeout: float) -> bool:
        from cuesdk import CorsairSessionState
        t0 = time.time()
        while self._state != CorsairSessionState.CSS_Connected:
            if time.time() - t0 > timeout:
                return False
            time.sleep(0.1)
        return True

    def connect(self, timeout: float = 6, autostart: bool = True, launch_timeout: float = 90,
                devices_timeout: float = 45, log: Callable[[str], None] = lambda s: None) -> list[ICueLight]:
        from cuesdk import CueSdk
        try:
            if self.sdk is None:
                self.sdk = CueSdk()

                def on_state(evt):
                    from cuesdk import CorsairSessionState
                    self._state = evt.state
                    if evt.state == CorsairSessionState.CSS_Connected:
                        self._ever_connected = True
                        if self._dropped:
                            # iCUE e' tornato: il controllo esclusivo va richiesto di nuovo
                            self._dropped = False
                            if self.on_reconnect:
                                threading.Thread(target=self.on_reconnect, daemon=True).start()
                    else:
                        # sessione persa (iCUE chiuso, riavviato o aggiornato): il controllo decade
                        self._controlled.clear()
                        if self._ever_connected:
                            self._dropped = True
                self._cb = on_state
                err = self.sdk.connect(on_state)
                if not _ok(err):
                    self.status = f"errore SDK: {err}"
                    return []
            connected = self._wait_connected(timeout)
            if not connected and autostart and not self._launched and not _process_running("iCUE.exe"):
                # iCUE e' chiuso: lo avvio io (ridotto in tray) e aspetto che l'SDK si colleghi
                self._launched = True
                if self._launch():
                    log("iCUE non era avviato: lo avvio in tray e attendo la connessione...")
                    self.status = "avvio di iCUE in corso..."
                    connected = self._wait_connected(launch_timeout)
            if not connected:
                self.status = ("iCUE non in esecuzione (o integrazioni software disattivate)"
                               if not _process_running("iCUE.exe") else
                               "iCUE avviato ma SDK non raggiungibile (controlla 'integrazioni software' in iCUE)")
                return []
            self._build()
            if not self.lights and devices_timeout > 0:
                # appena avviato, iCUE impiega qualche secondo a enumerare i dispositivi
                log("iCUE collegato, attendo che rilevi i dispositivi...")
                t0 = time.time()
                while not self.lights and time.time() - t0 < devices_timeout:
                    time.sleep(2)
                    self._build()
        except Exception as e:  # noqa: BLE001
            self.status = f"errore iCUE: {e}"
            return []
        return self.lights

    def _build(self) -> None:
        from cuesdk import CorsairDeviceFilter, CorsairDeviceType
        devs, err = self.sdk.get_devices(CorsairDeviceFilter(device_type_mask=CorsairDeviceType.CDT_All))
        if not _ok(err):
            raise RuntimeError(f'Lettura dispositivi iCUE fallita: {err}')
        found = []
        for d in devs or []:
            leds, err = self.sdk.get_led_positions(d.device_id)
            if not _ok(err):
                raise RuntimeError(f'Lettura LED {d.model} fallita: {err}')
            if not leds:
                continue
            for name, ids, kind in self._split(d, leds):
                found.append(ICueLight(self, d.device_id, name, ids, kind))
        self.lights = found
        self.status = f"connesso ({len(self.lights)} blocchi)"

    @staticmethod
    def _split(dev, leds):
        """Divide un dispositivo iCUE nei suoi blocchi fisici usando le posizioni dei LED."""
        from cuesdk import CorsairDeviceType
        if dev.type == CorsairDeviceType.CDT_MemoryModule:
            # ogni modulo RAM ha la sua colonna (cx)
            cols: dict[float, list] = {}
            for l in leds:
                cols.setdefault(round(l.cx), []).append(l)
            out = []
            for n, cx in enumerate(sorted(cols), start=1):
                ids = [l.id for l in sorted(cols[cx], key=lambda l: (l.cy, l.id))]
                out.append((f"{dev.model} - Modulo {n}", ids, "RAM"))
            return out
        if dev.type == CorsairDeviceType.CDT_LedController and dev.led_count > 12:
            # hub iCUE LINK: i LED sono in fila, con un vuoto tra un dispositivo e l'altro
            srt = sorted(leds, key=lambda l: (l.cx, l.id))
            groups, cur = [], [srt[0]]
            for prev, l in zip(srt, srt[1:]):
                if l.cx - prev.cx > 40:
                    groups.append(cur)
                    cur = []
                cur.append(l)
            groups.append(cur)
            out, nfan, nother = [], 0, 0
            for g in groups:
                ids = [l.id for l in g]
                if len(ids) >= 16:
                    out.append(("iCUE LINK TITAN 360 (pompa)", ids, "COOLER"))
                elif len(ids) == 8:
                    nfan += 1
                    out.append((f"Ventola iCUE LINK RX RGB {nfan}", ids, "FAN"))
                else:
                    nother += 1
                    out.append((f"{dev.model} - blocco {nother}", ids, "LED"))
            return out
        return [(dev.model, [l.id for l in leds], dev.type.name.replace("CDT_", ""))]

    def write(self, device_id: str, led_ids: list[int], colors: list[RGB]) -> None:
        from cuesdk import CorsairLedColor, CorsairAccessLevel, CorsairSessionState
        if self._state != CorsairSessionState.CSS_Connected:
            # senza sessione le chiamate native fallirebbero una per frame: mi fermo subito
            raise RuntimeError("iCUE non e' collegato")
        payload = [CorsairLedColor(i, r, g, b, 255) for i, (r, g, b) in zip(led_ids, colors)]
        if device_id not in self._controlled:
            err = self.sdk.request_control(device_id, CorsairAccessLevel.CAL_ExclusiveLightingControl)
            if not _ok(err):
                raise RuntimeError(f"iCUE ha negato il controllo delle luci ({err})")
            self._controlled.add(device_id)
        err = self.sdk.set_led_colors(device_id, payload)
        if not _ok(err):
            # es. il controllo e' decaduto: lo richiedo al prossimo frame
            self._controlled.discard(device_id)
            raise RuntimeError(f"iCUE ha rifiutato i colori ({err})")

    def release_all(self) -> None:
        """Restituisce il controllo a iCUE (torna il profilo iCUE)."""
        if self.sdk and self._controlled:
            for device_id in list(self._controlled):
                try:
                    self.sdk.release_control(device_id)
                except Exception:  # noqa: BLE001
                    pass
            self._controlled.clear()
