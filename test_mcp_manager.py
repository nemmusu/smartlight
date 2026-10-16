"""MCP settings diagnostics and in-process HTTP transport."""

from __future__ import annotations

import json
import os
import socket
import tempfile
import unittest
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from app import DesktopApi, start_bridge
from mcp_manager import McpManager
from service import SmartlightService
from test_ui_contract import MockPC, MockTapo, data_dir_env


class McpManagerTests(unittest.TestCase):
    def test_stdio_diagnostic_and_http_session(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            test_port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, data_dir_env(root)), \
                patch("mcp_manager.MCP_HTTP_PORT", test_port):
            service = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)
            bridge = start_bridge(service)
            manager = McpManager()
            try:
                api = DesktopApi(service, manager)
                status = api.invoke("mcp.status")["data"]
                self.assertTrue(status["available"])
                self.assertEqual(status["location"], "source")
                self.assertIn("smartlight", status["stdio_config"]["mcpServers"])

                diagnostic = api.invoke("mcp.test")
                self.assertTrue(diagnostic["ok"], diagnostic)
                self.assertGreaterEqual(diagnostic["data"]["tool_count"], 60)

                started = api.invoke("mcp.http.start", {"scope": "local"})
                self.assertTrue(started["ok"], started)
                status = started["data"]
                self.assertTrue(status["http_running"])
                self.assertTrue(status["http_url"].startswith("http://127.0.0.1:"))
                self.assertIsNone(status["http_lan_url"])

                config = status["http_config"]["mcpServers"]["smartlight"]
                url, auth = config["url"], config["headers"]["Authorization"]
                token_name = "mcp_http_token.dpapi" if os.name == "nt" else "mcp_http_token"
                token_file = Path(root) / "Smartlight" / token_name
                stored = token_file.read_bytes()
                if os.name == "nt":
                    # DPAPI ciphertext must not contain the clear token.
                    self.assertNotIn(auth.encode(), stored)
                else:
                    # Outside Windows the file is owner-only and holds the token as-is.
                    self.assertEqual(auth, "Bearer " + stored.decode("ascii"))
                    self.assertEqual(token_file.stat().st_mode & 0o777, 0o600)
                payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

                def post(message, *, token=auth, origin=None):
                    message["params"]["_meta"] = {
                        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientCapabilities": {}}
                    headers = {"Authorization": token, "Content-Type": "application/json",
                               "Accept": "application/json, text/event-stream",
                               "MCP-Protocol-Version": "2026-07-28",
                               "Mcp-Method": message["method"]}
                    if message["method"] == "tools/call":
                        headers["Mcp-Name"] = message["params"]["name"]
                    if origin:
                        headers["Origin"] = origin
                    with urlopen(Request(url, data=json.dumps(message).encode(),
                                         method="POST", headers=headers), timeout=5) as response:
                        return json.load(response)

                self.assertGreaterEqual(len(post(payload)["result"]["tools"]), 60)
                tools = post({"jsonrpc": "2.0", "id": 2,
                              "method": "tools/list", "params": {}})["result"]["tools"]
                self.assertGreaterEqual(len(tools), 60)
                mode = post({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "get_control_mode", "arguments": {}}})
                self.assertFalse(mode["result"].get("isError"), mode)
                with self.assertRaises(HTTPError) as denied:
                    post(payload, token="Bearer wrong")
                self.assertEqual(denied.exception.code, 401)
                with self.assertRaises(HTTPError) as denied_origin:
                    post(payload, origin="https://untrusted.example")
                self.assertEqual(denied_origin.exception.code, 403)

                stopped = api.invoke("mcp.http.stop")
                self.assertTrue(stopped["ok"], stopped)
                self.assertFalse(stopped["data"]["http_running"])

                restarted = api.invoke("mcp.http.start", {"scope": "local"})
                self.assertTrue(restarted["ok"], restarted)
                self.assertEqual(restarted["data"]["http_url"], url)
                self.assertEqual(restarted["data"]["http_config"]["mcpServers"]["smartlight"]["headers"]["Authorization"], auth)
                manager.stop_http()

                lan = api.invoke("mcp.http.start", {"scope": "lan"})
                if manager._local_ip():
                    self.assertTrue(lan["ok"], lan)
                    self.assertEqual(lan["data"]["http_scope"], "lan")
                    self.assertTrue(manager._http_probe(lan["data"]["http_lan_url"], manager._token))
                    old_token = manager._token
                    rotated = api.invoke("mcp.http.rotate")
                    self.assertTrue(rotated["ok"], rotated)
                    self.assertEqual(rotated["data"]["http_lan_url"], lan["data"]["http_lan_url"])
                    self.assertNotEqual(manager._token, old_token)
                    with self.assertRaises(HTTPError) as revoked:
                        manager._http_probe(lan["data"]["http_url"], old_token)
                    self.assertEqual(revoked.exception.code, 401)
                manager.stop_http()
            finally:
                manager.close()
                bridge.shutdown()
                bridge.server_close()
                service.close()

    def test_packaged_path_is_resolved_beside_desktop_bundle(self):
        with tempfile.TemporaryDirectory() as root:
            exe = ".exe" if os.name == "nt" else ""
            desktop = Path(root) / "Smartlight" / f"Smartlight{exe}"
            mcp = Path(root) / "Smartlight-MCP" / f"Smartlight-MCP{exe}"
            desktop.parent.mkdir(); desktop.touch()
            mcp.parent.mkdir(); mcp.touch()
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(desktop)):
                info = McpManager().status()
            self.assertEqual(info["path"], str(mcp))
            self.assertTrue(info["available"])
            self.assertEqual(info["location"], "portable")

    def test_appimage_entry_points_to_stable_file_not_temporary_mount(self):
        appimage = "/home/me/Applicazioni/Smartlight-0.2.16-x86_64.AppImage"
        with patch.dict(os.environ, {"APPIMAGE": appimage}):
            command, args, path, location = McpManager._entry()
        self.assertEqual(command, appimage)
        self.assertEqual(args, ["--mcp-stdio"])
        self.assertEqual(path, appimage)
        self.assertEqual(location, "appimage")

    @unittest.skipIf(os.name == "nt", "Percorsi del pacchetto verificati su Linux")
    def test_deb_install_is_reported_as_packaged(self):
        import mcp_manager
        packaged = "/usr/lib/smartlight/mcp_server.py"
        with patch.object(mcp_manager, "__file__", "/usr/lib/smartlight/mcp_manager.py"), \
                patch.dict(os.environ, {}, clear=False):
            os.environ.pop("APPIMAGE", None)
            command, args, path, location = McpManager._entry()
        self.assertEqual(path, packaged)
        self.assertEqual(args, [packaged])
        self.assertEqual(location, "packaged")


if __name__ == "__main__":
    unittest.main()
