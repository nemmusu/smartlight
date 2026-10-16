"""Private loopback client for the Smartlight desktop service.

The MCP process reads connection details only when a tool is called, so it can
survive service restarts and port changes without retaining a credential.
"""

from __future__ import annotations

import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storage import data_dir


class BridgeError(RuntimeError):
    """A safe, user-facing service connection or command error."""


def config_dir():
    # Same directory the desktop service writes service.json and token to.
    return data_dir()


def _connection() -> tuple[int, str]:
    directory = config_dir()
    try:
        details = json.loads((directory / "service.json").read_text(encoding="utf-8"))
        port = details["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("port non valida")
        token = (directory / "token").read_text(encoding="utf-8").strip()
        if not token or "\r" in token or "\n" in token:
            raise ValueError("token non valido")
        return port, token
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BridgeError("Servizio Smartlight non disponibile. Avvia Smartlight e riprova.") from exc


def invoke(command: str, params: dict) -> dict:
    """Invoke one command. The service is the authority for validation and state."""
    port, token = _connection()
    payload = json.dumps({"command": command, "params": params}, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"http://127.0.0.1:{port}/invoke",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            result = json.load(response)
    except HTTPError as exc:
        # Do not echo the response: it may contain service diagnostics or secrets.
        raise BridgeError(f"Smartlight ha rifiutato il comando (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise BridgeError("Impossibile contattare il servizio Smartlight locale.") from exc
    except (ValueError, UnicodeError) as exc:
        raise BridgeError("Risposta non valida dal servizio Smartlight.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise BridgeError("Risposta non valida dal servizio Smartlight.")
    if not result["ok"]:
        error = result.get("error") or {}
        code = str(error.get("code", "ERROR")) if isinstance(error, dict) else "ERROR"
        message = str(error.get("message", "Comando non riuscito")) if isinstance(error, dict) else "Comando non riuscito"
        raise BridgeError(f"{code}: {message}")
    data = result.get("data", {})
    return data if isinstance(data, dict) else {"result": data}


async def invoke_async(command: str, params: dict) -> dict:
    return await asyncio.to_thread(invoke, command, params)
