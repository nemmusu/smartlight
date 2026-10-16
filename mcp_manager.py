"""UI-facing MCP launcher and diagnostics; never expose the private bridge token."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from threading import RLock, Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storage import data_dir, data_dir_overrides

MCP_HTTP_PORT = 8766


class McpManager:
    def __init__(self):
        self._lock = RLock()
        self._server = None
        self._thread: Thread | None = None
        self._port: int | None = None
        self._token: str | None = None
        self._lan = False
        self._lan_ip: str | None = None
        self._last_error: str | None = None

    @staticmethod
    def _entry() -> tuple[str, list[str], str, str]:
        appimage = os.environ.get("APPIMAGE")
        if appimage and not getattr(sys, "frozen", False):
            # Dentro un AppImage sys.executable e il sorgente stanno nel mount temporaneo,
            # che sparisce alla chiusura: il client deve lanciare il file .AppImage stabile.
            return appimage, ["--mcp-stdio"], appimage, "appimage"
        if getattr(sys, "frozen", False):
            desktop = Path(sys.executable).resolve()
            name = "Smartlight-MCP.exe" if os.name == "nt" else "Smartlight-MCP"
            mcp_exe = desktop.parent.parent / "Smartlight-MCP" / name
            location = "portable"
            if os.name == "nt":
                # A setup install registers the location; a portable copy does not.
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight") as key:
                        installed = Path(winreg.QueryValueEx(key, "InstallLocation")[0]).resolve()
                        if desktop == installed / "Smartlight" / "Smartlight.exe":
                            location = "installed"
                except (ImportError, OSError, ValueError):
                    pass
            return str(mcp_exe), [], str(mcp_exe), location
        script = Path(__file__).resolve().with_name("mcp_server.py")
        # Il pacchetto .deb installa l'app in /usr/lib/smartlight con un venv stabile.
        location = "packaged" if str(script).startswith("/usr/lib/smartlight/") else "source"
        return sys.executable, [str(script)], str(script), location

    @staticmethod
    def _flags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def status(self) -> dict:
        command, args, path, location = self._entry()
        with self._lock:
            running = self._thread is not None and self._thread.is_alive() and not self._server.should_exit
            if not running:
                self._server = None
                self._thread = None
                self._port = None
                self._token = None
            url = f"http://127.0.0.1:{self._port}/mcp" if running else None
            lan_url = f"http://{self._lan_ip}:{self._port}/mcp" if running and self._lan_ip else None
            token = self._token if running else None
        stdio = {"mcpServers": {"smartlight": {"command": command, "args": args}}}
        http = {"mcpServers": {"smartlight": {"url": url,
                "headers": {"Authorization": f"Bearer {token}"}}}} if running else None
        return {"path": path, "command": command, "args": args,
                "available": Path(path).is_file(), "location": location,
                "stdio_config": stdio, "http_running": running,
                "http_url": url, "http_lan_url": lan_url,
                "http_scope": "lan" if self._lan and running else "local",
                "http_config": http, "http_error": self._last_error}

    def test_stdio(self) -> dict:
        command, args, path, _ = self._entry()
        if not Path(path).is_file():
            raise RuntimeError("Server MCP non trovato. Reinstalla o ripara Smartlight.")
        async def diagnose():
            from mcp import StdioServerParameters
            from mcp.client import Client
            params = StdioServerParameters(command=command, args=args,
                                          env=data_dir_overrides())
            async with Client(params) as client:
                tools = await client.list_tools()
                mode = await client.call_tool("get_control_mode", {})
            if mode.is_error or not tools.tools:
                raise RuntimeError("MCP risponde, ma non riesce a raggiungere Smartlight.")
            return len(tools.tools)
        try:
            count = asyncio.run(asyncio.wait_for(diagnose(), timeout=20))
        except TimeoutError as exc:
            raise RuntimeError("Il server MCP non ha risposto entro 20 secondi.") from exc
        except OSError as exc:
            raise RuntimeError("Impossibile avviare il server MCP. Reinstalla o ripara Smartlight.") from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Test MCP non riuscito. Controlla che Smartlight-MCP sia presente e riprova.") from exc
        return {"ready": True, "tool_count": count,
                "message": f"Connessione riuscita: {count} strumenti MCP e controller Smartlight raggiungibile."}

    @staticmethod
    def _check_port(lan: bool) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # SO_REUSEADDR: un riavvio subito dopo lo stop deve poter riusare la
            # porta anche se restano connessioni in TIME_WAIT (tipico su Linux).
            if os.name != "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0" if lan else "127.0.0.1", MCP_HTTP_PORT))
            except OSError as exc:
                raise RuntimeError(f"La porta MCP {MCP_HTTP_PORT} è occupata. Chiudi l'altro server o applicazione e riprova.") from exc
        return MCP_HTTP_PORT

    @staticmethod
    def _token_path():
        # DPAPI only exists on Windows; elsewhere the file is owner-only (0600).
        name = "mcp_http_token.dpapi" if os.name == "nt" else "mcp_http_token"
        return data_dir() / name

    @staticmethod
    def _store_token(token: str) -> None:
        """Persist a per-user protected token without putting it in backups."""
        path = McpManager._token_path()
        if os.name == "nt":
            import win32crypt
            payload = win32crypt.CryptProtectData(token.encode("ascii"),
                                                  "Smartlight MCP HTTP", None, None, None, 0)
        else:
            payload = token.encode("ascii")
        fd, temporary = tempfile.mkstemp(prefix="mcp-token-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def _persistent_token(cls) -> str:
        path = cls._token_path()
        try:
            if os.name == "nt":
                import win32crypt
                _, clear = win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)
                token = clear.decode("ascii")
            else:
                token = path.read_text(encoding="ascii").strip()
            if token:
                return token
        except FileNotFoundError:
            pass
        except Exception:
            # A Windows reinstall changes the DPAPI user keys. Issue a fresh
            # token in that case; an old client configuration must be recopied.
            pass
        token = secrets.token_urlsafe(48)
        try:
            cls._store_token(token)
        except Exception as exc:
            raise RuntimeError("Impossibile salvare il token MCP protetto.") from exc
        return token

    @staticmethod
    def _local_ip() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("192.0.2.1", 1))
                address = sock.getsockname()[0]
            return address if address and not address.startswith("127.") else None
        except OSError:
            try:
                return next(address for address in socket.gethostbyname_ex(socket.gethostname())[2]
                            if not address.startswith(("127.", "169.254.")))
            except (OSError, StopIteration):
                return None

    @staticmethod
    def _http_probe(url: str, token: str) -> bool:
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                              "params": {"_meta": {
                                  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                                  "io.modelcontextprotocol/clientCapabilities": {}}}}).encode()
        request = Request(url, data=payload, method="POST", headers={
            "Authorization": "Bearer " + token, "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/list"})
        with urlopen(request, timeout=2) as response:
            body = json.load(response)
        return isinstance(body, dict) and bool(body.get("result", {}).get("tools"))

    def start_http(self, *, lan: bool = False) -> dict:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self.status()
            from mcp.server.transport_security import TransportSecuritySettings
            from mcp_server import _LocalBearerAuth, mcp
            import uvicorn
            port = self._check_port(lan)
            token = self._persistent_token()
            lan_ip = self._local_ip() if lan else None
            if lan and not lan_ip:
                raise RuntimeError("Nessun indirizzo IPv4 LAN rilevato. Usa la modalità solo locale.")
            host = "0.0.0.0" if lan else "127.0.0.1"
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if lan_ip:
                allowed_hosts.add(f"{lan_ip}:{port}")
            allowed_origins = {f"http://{value}" for value in allowed_hosts}
            app = mcp.streamable_http_app(
                streamable_http_path="/mcp", json_response=True, stateless_http=True,
                host=host, transport_security=TransportSecuritySettings(
                    enable_dns_rebinding_protection=False))
            app = _LocalBearerAuth(app, token, allowed_hosts=allowed_hosts,
                                   allowed_origins=allowed_origins)
            config = uvicorn.Config(app, host=host, port=port, log_level="error",
                                    access_log=False, lifespan="on")
            server = uvicorn.Server(config)
            thread = Thread(target=server.run, daemon=True, name="smartlight-mcp-http")
            thread.start()
            url = f"http://127.0.0.1:{port}/mcp"
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if not thread.is_alive():
                    break
                try:
                    if self._http_probe(url, token):
                        self._server, self._thread = server, thread
                        self._port, self._token = port, token
                        self._lan, self._lan_ip = lan, lan_ip
                        self._last_error = None
                        return self.status()
                except (HTTPError, URLError, TimeoutError, OSError, ValueError):
                    pass
                time.sleep(0.15)
            server.should_exit = True
            thread.join(timeout=3)
            self._last_error = "Il server MCP HTTP non ha superato la verifica iniziale."
            raise RuntimeError(self._last_error)

    def stop_http(self) -> dict:
        with self._lock:
            server, thread = self._server, self._thread
            self._server = None
            self._thread = None
            self._port = None
            self._token = None
            self._lan = False
            self._lan_ip = None
        if server is not None and thread is not None and thread.is_alive():
            server.should_exit = True
            thread.join(timeout=5)
        return self.status()

    def rotate_token(self) -> dict:
        """Revoke copied client credentials while keeping the endpoint stable."""
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            lan = self._lan
            try:
                self._store_token(secrets.token_urlsafe(48))
            except Exception as exc:
                raise RuntimeError("Impossibile aggiornare il token MCP protetto da Windows.") from exc
            self.stop_http()
            if running:
                return self.start_http(lan=lan)
            return self.status()

    def close(self) -> None:
        self.stop_http()
