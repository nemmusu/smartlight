"""Browser QA bridge using the real command router and simulated hardware.

Run with ``python test_ui_contract.py --serve`` and open the printed local URL.
No Tapo, OpenRGB or iCUE connection is made. APPDATA is moved into a disposable
workspace directory before SmartlightService is constructed.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
DATA_DIR_ENV = ("APPDATA", "XDG_DATA_HOME")

def data_dir_env(path) -> dict[str, str]:
    """Overrides that point Smartlight's data dir at ``path`` on every OS."""
    return {"APPDATA": str(path), "XDG_DATA_HOME": str(path)}

def use_data_dir(path) -> dict[str, str | None]:
    previous = {name: os.environ.get(name) for name in DATA_DIR_ENV}
    os.environ.update(data_dir_env(path))
    return previous

def restore_data_dir(previous: dict[str, str | None]) -> None:
    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

os.environ.update(data_dir_env(ROOT / ".testdata" / "ui_contract"))

from service import SmartlightService  # noqa: E402
from pc import _valid_patch  # noqa: E402
from legacy_hwlight.engine import effects_info  # noqa: E402


class MockTapo:
    def __init__(self):
        self.devices = [
            {"id": "strip", "name": "LED scrivania", "host": "127.0.0.10", "model": "L900-10", "room": "Camera da letto"},
            {"id": "bulb1", "name": "Lampadina 1", "host": "127.0.0.11", "model": "L530", "room": "Camera da letto"},
            {"id": "bulb2", "name": "Lampadina 2", "host": "127.0.0.12", "model": "L530", "room": "Camera da letto"},
        ]
        self._states = {}
        for i, item in enumerate(self.devices):
            self._states[item["id"]] = {
                **item, "type": "tapo", "online": True, "on": True,
                "brightness": (100, 91, 87)[i],
                "hsv": {"hue": (240, 42, 42)[i], "saturation": (100, 24, 22)[i], "value": (100, 91, 87)[i]},
                "color_temp": 4000 if i == 0 else 5426,
                "effect": "Off", "effects": (["Off", "Aurora", "Rainbow", "Sunset"] if i == 0 else ["Off", "Party", "Relax"]),
                "device_presets": ["Not set", *[f"Light preset {n}" for n in range(1, 8)]],
                "capabilities": {"power": True, "brightness": True, "color": True, "temperature": True,
                                 "effects": True, "custom_effects_native": i == 0, "device_presets": True},
            }

    def credentials(self):
        raise ValueError("Nessuna credenziale nel test")

    def _entry(self, device_id):
        for item in self.devices:
            if item["id"] == device_id:
                return item
        raise ValueError("Dispositivo inesistente")

    def list_devices(self):
        return list(self._states.values())

    def refresh(self):
        return self.list_devices()

    def stream_animation(self, device_ids, stop, frame_at, started, *, duration=None, interval=0.15,
                         native=None):
        while not stop.is_set():
            elapsed = time.monotonic() - started
            if duration is not None and elapsed >= duration:
                break
            for offset, device_id in enumerate(device_ids):
                patch = frame_at(elapsed, offset)
                self.set_group([device_id], {**patch, "power": True})
            stop.wait(min(interval, 0.05))

    def energy(self, device_id, period):
        self._entry(device_id)
        return {"device_id": device_id, "period": period,
                "duration_hours": {"today": 1.5, "7d": 8.2, "30d": 32.4}[period],
                "energy_kwh": {"today": 0.015, "7d": 0.085, "30d": 0.342}[period],
                "source": "mock", "message": "Misura simulata per QA."}

    def set_group(self, ids, patch):
        out = {}
        for device_id in ids:
            try:
                state = self._states[device_id]
                if "power" in patch:
                    state["on"] = bool(patch["power"])
                if "brightness" in patch:
                    state["brightness"] = int(patch["brightness"])
                    state["hsv"]["value"] = int(patch["brightness"])
                if "hue" in patch:
                    state["hsv"]["hue"] = int(patch["hue"])
                if "saturation" in patch:
                    state["hsv"]["saturation"] = int(patch["saturation"])
                if "temperature" in patch:
                    state["color_temp"] = int(patch["temperature"])
                if "effect" in patch:
                    effect = patch["effect"]
                    if effect not in state["effects"]:
                        raise ValueError("Effetto non supportato dal dispositivo")
                    state["effect"] = effect
                if "device_preset" in patch:
                    preset = patch["device_preset"]
                    if preset not in state["device_presets"]:
                        raise ValueError("Preset nativo non supportato dal dispositivo")
                    state["device_preset"] = preset
                out[device_id] = {"ok": True, "state": dict(state)}
            except Exception as exc:
                out[device_id] = {"ok": False, "error": str(exc)}
        return out


class MockPC:
    def __init__(self):
        self.devices = [
            {"key": "keyboard", "name": "Tastiera", "backend": "OpenRGB", "kind": "RGB", "online": True},
            {"key": "mouse", "name": "Mouse", "backend": "iCUE" if os.name == "nt" else "OpenRGB", "kind": "RGB", "online": True},
        ]
        self.state = {d["key"]: {"on": True, "effect": "statico", "color": [102, 186, 255], "brightness": 100} for d in self.devices}

    def list_devices(self): return self.devices
    def get_status(self): return {"openrgb": "mock", "icue": "mock"}
    def get_state(self): return self.state
    def get_effects(self): return effects_info()
    def list_profiles(self): return []
    def list_scenes(self): return []
    def get_frames(self): return {key: [item["color"]] for key, item in self.state.items()}
    def rescan_async(self): return self.get_status()
    def connect_async(self): return None
    def save_now(self): return None
    def stop_flow(self): return {"running": False}
    def start_flow(self, palette, period, keys=None, started=None, direction="forward", *, mode="flow", brightness=100, transition_ms=500, min_brightness=None):
        self.flow = {"palette": palette, "period": period, "keys": keys,
                     "direction": direction, "mode": mode, "brightness": brightness,
                     "transition_ms": transition_ms, "min_brightness": min_brightness}
        return {"running": True, **self.flow}
    def apply_scene(self, scene_id):
        self.scene = scene_id
        return {"scene": scene_id, "devices": list(self.state)}
    def export_data(self): return {"state": self.state, "profiles": []}
    def import_data(self, data): self.state = data.get("state", self.state); return self.state
    def apply_to(self, keys, patch):
        clean = _valid_patch(patch)
        for key in keys or self.state:
            if key not in self.state: raise ValueError(f"Dispositivo PC sconosciuto: {key}")
            self.state[key].update(clean)
        return {"keys": keys, "patch": clean}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--rich", action="store_true", help="15 devices and six groups for UI layout QA")
    args = parser.parse_args()
    if args.rich:
        os.environ.update(data_dir_env(tempfile.mkdtemp(prefix="ui-rich-",dir=ROOT / ".testdata")))
    service = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)
    if args.rich:
        extras = [("fan1","Ventola iCUE LINK RX RGB 1","FAN"),("fan2","Ventola iCUE LINK RX RGB 2","FAN"),
                  ("fan3","Ventola iCUE LINK RX RGB 3","FAN"),("pump","iCUE LINK TITAN 360 (pompa)","COOLER"),
                  *[(f"ram{i}",f"VENGEANCE RGB DDR5 - Modulo {i}","RAM") for i in range(1,5)],
                  ("board","ASUS PRIME Z890-P WIFI","MOTHERBOARD"),("gpu","Palit GeForce RTX 5090 Gamerock","GPU")]
        service.pc.devices[0]["kind"]="KEYBOARD";service.pc.devices[1]["kind"]="MOUSE"
        for key,name,kind in extras:
            service.pc.devices.append({"key":key,"name":name,"kind":kind,"source":"iCUE" if os.name == "nt" and kind in {"RAM","FAN","COOLER"} else "OpenRGB","online":True})
            service.pc.state[key]={"on":True,"effect":"statico","color":[102,186,255],"brightness":100}
        for name,tapo,pc in [("Camera",["strip","bulb1","bulb2"],[]),("Lampadine camera",["bulb1","bulb2"],[]),
                             ("PC senza tastiera",[],[d["key"] for d in service.pc.devices if d["key"]!="keyboard"]),
                             ("LED",["strip"],[]),("Tastiera",[],["keyboard"]),("Scrivania",["strip"],["keyboard","mouse"])]:
            service.invoke("rooms.save",{"name":name,"device_ids":tapo,"pc_keys":pc})
    calls: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def _json(self, data, code=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/invoke": return self._json({"error": "not found"}, 404)
            try:
                n = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(n))
                if payload["command"] == "mcp.status":
                    result={"ok":True,"data":{"available":True,"path":"Smartlight-MCP.exe","location":"installed","http_running":False}}
                elif payload["command"] == "app.restart":
                    result={"ok":True,"data":{"restarting":True}}
                else:
                    result = service.invoke(payload["command"], payload.get("params") or {})
                calls.append({"command": payload["command"], "params": payload.get("params") or {}, "result": result})
                self._json(result)
            except Exception as exc:
                self._json({"ok": False, "error": {"code": "harness", "message": str(exc)}}, 500)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/calls": return self._json(calls)
            if parsed.path in ("/", "/index.html"):
                html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
                bridge = """<script>window.pywebview={api:{invoke:async(command,params)=>{
                    const r=await fetch('/invoke',{method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({command,params})});return await r.json();}}};</script>"""
                page = parse_qs(parsed.query).get("page", [""])[0]
                qa_nav = (f'<script>addEventListener("load",()=>document.querySelector("[data-page={page}]")?.click())</script>'
                          if page in {"home", "lights", "effects", "automation", "pc", "scenes", "settings"} else "")
                body = html.replace('<script src="app.js"></script>', bridge + '<script src="app.js"></script>' + qa_nav).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            else:
                path = (ROOT / "ui" / parsed.path.lstrip("/")).resolve()
                if ROOT / "ui" not in path.parents or not path.is_file():
                    return self._json({"error": "not found"}, 404)
                body = path.read_bytes()
                suffix = path.suffix.lower()
                self.send_response(200)
                self.send_header("Content-Type", {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}.get(suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    if args.serve:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        print(f"http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            service.close()
    else:
        # Router smoke checks; browser workflow can be run with --serve.
        assert service.invoke("status")["ok"]
        assert service.invoke("device_set", {"id": "strip", "power": False})["ok"]
        assert not service.status()["devices"][0]["on"]
        service.close()
        print("Router QA mock: OK")


if __name__ == "__main__":
    main()
