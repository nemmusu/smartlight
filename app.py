"""Smartlight desktop entrypoint and private loopback service for its MCP process."""

from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Vendor SDKs run in a disposable process, before the desktop service is imported.
if __name__ == "__main__" and "--mystic-worker" in sys.argv:
    from mystic_light import worker_main
    raise SystemExit(worker_main(sys.argv[sys.argv.index("--mystic-worker") + 1]))

from mcp_manager import McpManager
from service import SmartlightService
from storage import data_dir, write_json, write_secret


LOG = logging.getLogger("smartlight")


class DesktopApi:
    def __init__(self, service: SmartlightService, mcp_manager: McpManager | None = None):
        self._service = service
        self._mcp_manager = mcp_manager
        self._exit_handler = None
        self._restart_handler = None

    def _set_exit_handler(self, handler):
        self._exit_handler = handler

    def _set_restart_handler(self, handler):
        self._restart_handler = handler

    def invoke(self, command: str, params: dict | None = None) -> dict:
        if command == "app.clipboard.copy":
            try:
                from windows_clipboard import copy_text
                copy_text((params or {}).get("text"))
                return {"ok": True, "data": {"copied": True}}
            except (OSError, RuntimeError, ValueError) as exc:
                return {"ok": False, "error": {"code": "clipboard_error", "message": str(exc)}}
        if command.startswith("mcp."):
            if self._mcp_manager is None:
                return {"ok": False, "error": {"code": "unavailable", "message": "MCP non disponibile"}}
            try:
                actions = {"mcp.status": self._mcp_manager.status,
                           "mcp.test": self._mcp_manager.test_stdio,
                           "mcp.http.start": lambda: self._mcp_manager.start_http(
                               lan=(params or {}).get("scope") == "lan"),
                           "mcp.http.stop": self._mcp_manager.stop_http,
                           "mcp.http.rotate": self._mcp_manager.rotate_token}
                if command not in actions:
                    raise ValueError("Comando MCP sconosciuto")
                return {"ok": True, "data": actions[command]()}
            except (OSError, RuntimeError, ValueError) as exc:
                if command == "mcp.http.start":
                    self._mcp_manager._last_error = str(exc)
                return {"ok": False, "error": {"code": "mcp_error", "message": str(exc)}}
        if command == "app.restart":
            if self._restart_handler is None:
                return {"ok": False, "error": {"code": "unavailable", "message": "Riavvio non disponibile"}}
            threading.Timer(0.2, self._restart_handler).start()
            return {"ok": True, "data": {"restarting": True}}
        if command == "app.exit":
            if self._exit_handler is None:
                return {"ok": False, "error": {"code": "unavailable", "message": "Finestra non disponibile"}}
            # Return the bridge response before closing the webview that sent it.
            threading.Timer(0.1, self._exit_handler).start()
            return {"ok": True, "data": {"exiting": True}}
        return self._service.invoke(command, params)


def start_bridge(service: SmartlightService):
    token = secrets.token_urlsafe(48)
    write_secret("token", token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            LOG.debug(fmt, *args)

        def do_POST(self):
            if self.path != "/invoke":
                self.send_error(404)
                return
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}",
                                         f"http://localhost:{self.server.server_port}"}:
                self.send_error(403)
                return
            if self.headers.get("Authorization") != f"Bearer {token}":
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Dimensione richiesta non valida")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or not isinstance(payload.get("command"), str):
                    raise ValueError("Comando non valido")
                result = service.invoke(payload["command"], payload.get("params", {}))
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                code = 200
            except Exception as exc:
                body = json.dumps({"ok": False, "error": {"code": "bad_request", "message": str(exc)}}).encode("utf-8")
                code = 400
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    write_json("service.json", {"port": server.server_port})
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="smartlight-mcp-bridge")
    thread.start()
    return server


def _set_desktop_identity() -> None:
    """Nome applicazione per X11/Wayland.

    Senza questo la finestra si presenta come "app.py", con icona e
    raggruppamento nella barra delle applicazioni scollegati dal .desktop.
    """
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib

        GLib.set_prgname("smartlight")
        GLib.set_application_name("Smartlight")
    except (ImportError, ValueError):
        pass


def _graceful_signals(on_stop):
    """SIGTERM/SIGINT devono seguire lo stesso percorso di chiusura dell'app.

    systemd (unità utente del pacchetto .deb) ferma il processo con SIGTERM:
    senza handler il blocco `finally` non gira e restano token e service.json
    pendenti, oltre all'ultimo stato non salvato.
    """
    import signal

    def handler(_signum, _frame):
        on_stop()

    for name in ("SIGTERM", "SIGINT"):
        number = getattr(signal, name, None)
        if number is None:
            continue
        try:
            signal.signal(number, handler)
        except (OSError, ValueError):
            pass


def _single_instance():
    path = data_dir() / "instance.lock"
    handle = path.open("a+b")
    handle.seek(0)
    if not handle.read(1):
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError("Smartlight è già in esecuzione") from exc
    return handle


def _launch_again():
    """Called after the bridge and single-instance lock have been released."""
    image = os.environ.get("APPIMAGE", "")
    if os.name != "nt" and image and Path(image).is_absolute() and Path(image).is_file():
        command = [image]
    elif getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, str(Path(__file__).resolve())]
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
               "close_fds": True}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        options["start_new_session"] = True
    return subprocess.Popen(command, **options)


def main() -> int:
    # PyInstaller's --windowed bootloader sets these streams to None. Uvicorn
    # and MCP use standard logging streams even when no console is shown.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="avvia solo il servizio locale, senza finestra")
    parser.add_argument("--self-test", action="store_true", help="controlla che il servizio si avvii")
    parser.add_argument("--self-test-mcp", action="store_true",
                        help="verifica l'endpoint MCP HTTP senza modificare le luci")
    parser.add_argument("--minimized-to-tray", action="store_true",
                        help="avvia nell'area di notifica quando l'icona è pronta")
    parser.add_argument("--mcp-stdio", action="store_true",
                        help="avvia il server MCP via stdio (usato dai client, senza finestra)")
    args = parser.parse_args()
    if args.mcp_stdio:
        # Il client avvia questo processo: non deve prendere il lock dell'app grafica.
        from mcp_server import mcp
        mcp.run(transport="stdio")
        return 0
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    lock = _single_instance()
    service = SmartlightService()
    mcp_manager = McpManager()
    bridge = start_bridge(service)
    restart_requested = threading.Event()
    try:
        if args.self_test:
            print(json.dumps({"ok": True, "port": bridge.server_port,
                              "pc": service.pc.get_status(), "tapo_configured": service._has_credentials()}))
            return 0
        if args.self_test_mcp:
            details = mcp_manager.start_http(lan=False)
            print(json.dumps({"ok": True, "url": details["http_url"],
                              "transport": "streamable-http"}))
            mcp_manager.stop_http()
            return 0
        if service.settings.get("mcp_auto_start"):
            try:
                mcp_manager.start_http(lan=service.settings.get("mcp_scope") == "lan")
            except (OSError, RuntimeError, ValueError) as exc:
                mcp_manager._last_error = str(exc)
                LOG.warning("MCP HTTP auto-start failed: %s", exc)
        stop = threading.Event()
        if args.headless:
            _graceful_signals(stop.set)
            stop.wait()
            return 0
        import webview
        from tray import TrayController
        _set_desktop_identity()
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        # GTK (Linux) non legge le icone .ico: usa il PNG, che PIL e GtkIcon accettano.
        icon = root / "ui" / ("smartlight.ico" if os.name == "nt" else "smartlight.png")
        api = DesktopApi(service, mcp_manager)
        window = webview.create_window("Smartlight", (root / "ui" / "index.html").as_uri(),
                                       js_api=api, width=1440, height=900,
                                       min_size=(1040, 650), background_color="#09121c")
        tray = TrayController(service, window, icon, launch_hidden=args.minimized_to_tray)
        api._set_exit_handler(tray.request_exit)
        def restart():
            restart_requested.set()
            tray.request_exit()
        api._set_restart_handler(restart)
        _graceful_signals(lambda: (stop.set(), tray.request_exit()))
        try:
            webview.start(func=tray.start, debug=False, private_mode=False,
                          icon=str(icon) if icon.exists() else None)
        finally:
            tray.stop()
        return 0
    finally:
        mcp_manager.close()
        bridge.shutdown()
        service.close()
        (data_dir() / "service.json").unlink(missing_ok=True)
        (data_dir() / "token").unlink(missing_ok=True)
        lock.close()
        if restart_requested.is_set():
            _launch_again()


if __name__ == "__main__":
    raise SystemExit(main())
