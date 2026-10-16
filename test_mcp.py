"""Contract tests for the MCP-to-desktop-service boundary."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mcp import StdioServerParameters
from mcp.client import Client

import bridge_client
import mcp_server
from service import SmartlightService
from test_ui_contract import MockPC, MockTapo


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class BridgeTests(unittest.TestCase):
    def test_invoke_uses_loopback_token_and_contract(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            config = Path(root) / "Smartlight"
            config.mkdir()
            (config / "service.json").write_text('{"port":8765}', encoding="utf-8")
            (config / "token").write_text("secret-token\n", encoding="utf-8")
            captured = {}

            def fake_urlopen(request, timeout):
                captured["url"] = request.full_url
                captured["authorization"] = request.get_header("Authorization")
                captured["body"] = json.loads(request.data)
                captured["timeout"] = timeout
                return _Response(b'{"ok":true,"data":{"state":"on"}}')

            with patch.dict("os.environ", {"APPDATA": root, "XDG_DATA_HOME": root}), \
                    patch.object(bridge_client, "urlopen", fake_urlopen):
                result = bridge_client.invoke("lights.set", {"device": "lampadina1", "power": True})
            self.assertEqual(result, {"state": "on"})
            self.assertEqual(captured["url"], "http://127.0.0.1:8765/invoke")
            self.assertEqual(captured["authorization"], "Bearer secret-token")
            self.assertEqual(captured["body"], {"command": "lights.set", "params": {"device": "lampadina1", "power": True}})

    def test_missing_service_does_not_expose_paths_or_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as root, \
                patch.dict("os.environ", {"APPDATA": root, "XDG_DATA_HOME": root}):
            with self.assertRaisesRegex(bridge_client.BridgeError, "Servizio Smartlight non disponibile"):
                bridge_client.invoke("devices.list", {})


class ToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_effect_exposes_and_forwards_pulse_minimum(self) -> None:
        transport = AsyncMock(return_value={"saved": True})
        with patch.object(mcp_server, "invoke_async", transport):
            await mcp_server.save_custom_effect("Respiro", ["#FF0000"], mode="breathe",
                                                brightness=80, min_brightness=0,
                                                speed=60, include_pc=True)
            with self.assertRaisesRegex(ValueError, "min_brightness"):
                await mcp_server.save_custom_effect("Errato", ["#FF0000"],
                                                    brightness=50, min_brightness=51)
        definition = transport.await_args.args[1]["definition"]
        self.assertEqual(definition["min_brightness"], 0)
        self.assertEqual(definition["brightness"], 80)
        self.assertEqual(definition["speed"], 60)
        self.assertTrue(definition["include_pc"])
        tools = await mcp_server.mcp.list_tools()
        schema = next(tool.input_schema for tool in tools if tool.name == "save_custom_effect")
        self.assertEqual(schema["properties"]["min_brightness"]["minimum"], 0)
        self.assertEqual(schema["properties"]["min_brightness"]["maximum"], 100)

    async def test_forwarding_and_none_omission(self) -> None:
        transport = AsyncMock(return_value={"saved": True})
        with patch.object(mcp_server, "invoke_async", transport):
            self.assertEqual(await mcp_server.set_color_hsv("striscia", 250, 90), {"saved": True})
            await mcp_server.save_animation("sera", {"colors": ["#0088FF"], "mode": "breathe"})
            await mcp_server.set_pc_device("keyboard", {"effect": "rainbow"})
            await mcp_server.save_animation_preset("Sera animata", "animation-1")
            await mcp_server.apply_theme("aurora")
            await mcp_server.save_room("Studio", ["striscia"], ["keyboard"])
            await mcp_server.apply_target_state("room:studio", color="#ff3300", brightness=40)
            await mcp_server.save_theme("Caldo", ["#ff8800", "#ff3300"], mode="static")
            await mcp_server.set_settings(auto_start=True, minimize_to_tray=True)
        self.assertEqual(transport.await_args_list[0].args, ("lights.set", {"device": "striscia", "hue": 250, "saturation": 90}))
        self.assertEqual(transport.await_args_list[1].args, ("animations.save", {"name": "sera", "definition": {"colors": ["#0088FF"], "mode": "breathe"}}))
        self.assertEqual(transport.await_args_list[2].args, ("pc.set_device", {"device": "keyboard", "state": {"effect": "rainbow"}}))
        self.assertEqual(transport.await_args_list[3].args, ("presets.save", {"name": "Sera animata", "state": {"kind": "animation", "animation_id": "animation-1"}}))
        self.assertEqual(transport.await_args_list[4].args, ("theme_apply", {"id": "aurora"}))
        self.assertEqual(transport.await_args_list[5].args, ("rooms.save", {"name": "Studio", "device_ids": ["striscia"], "pc_keys": ["keyboard"]}))
        self.assertEqual(transport.await_args_list[6].args, ("target.apply", {"target": "room:studio", "color": "#ff3300", "brightness": 40}))
        self.assertEqual(transport.await_args_list[7].args, ("themes.save", {"name": "Caldo", "colors": ["#ff8800", "#ff3300"], "mode": "static", "brightness": 100, "step_ms": 1000, "speed": 50}))
        self.assertEqual(transport.await_args_list[8].args, ("settings_set", {"auto_start": True, "minimize_to_tray": True}))

    async def test_tools_have_specific_schemas(self) -> None:
        tools = await mcp_server.mcp.list_tools()
        by_name = {tool.name: tool for tool in tools}
        self.assertIn("set_color_hsv", by_name)
        self.assertIn("save_schedule", by_name)
        self.assertIn("set_pc_device", by_name)
        self.assertIn("import_backup", by_name)
        self.assertIn("list_themes", by_name)
        self.assertIn("save_theme_preset", by_name)
        self.assertIn("list_rooms", by_name)
        self.assertIn("apply_target_state", by_name)
        self.assertIn("save_theme", by_name)
        self.assertIn("set_settings", by_name)
        for name in ("get_lighting_overview", "set_color", "set_lights_power",
                     "set_lights_brightness", "set_pc_effect", "list_pc_scenes",
                     "apply_pc_scene", "apply_tapo_device_preset", "save_lighting_schedule"):
            self.assertIn(name, by_name)
        self.assertIn("pattern", by_name["set_color"].input_schema["properties"]["color"])
        self.assertIn("device", by_name["set_color_hsv"].input_schema["properties"])
        self.assertTrue(by_name["import_backup"].annotations.destructive_hint)
        self.assertTrue(by_name["list_devices"].annotations.read_only_hint)

    async def test_agent_tool_descriptions_include_working_examples(self) -> None:
        tools = {tool.name: tool for tool in await mcp_server.mcp.list_tools()}
        for name in ("set_color", "save_room", "save_custom_effect", "start_animation",
                     "save_lighting_schedule", "save_schedule", "save_scene", "set_pc_effect",
                     "set_pc_device", "configure_sync"):
            self.assertIn("Esempio", tools[name].description, name)
        self.assertIn("colors", tools["save_animation"].input_schema["properties"]["definition"]["description"])
        self.assertIn("HH:MM", tools["save_lighting_schedule"].input_schema["properties"]["time"]["description"])
        self.assertIn("list_targets", tools["set_color"].input_schema["properties"]["target"]["description"])

    async def test_typed_controls_forward_supported_service_commands(self) -> None:
        transport = AsyncMock(return_value={"ok": True})
        with patch.object(mcp_server, "invoke_async", transport):
            await mcp_server.set_color(["striscia", "keyboard"], "#FF8800", 55)
            await mcp_server.set_lights_power("all", False)
            await mcp_server.set_pc_effect(["keyboard"], "respiro", "#112233", "#445566", 0.7, 40)
            await mcp_server.apply_pc_scene("keyboard_only")
            await mcp_server.apply_tapo_device_preset("striscia", "Light preset 1")
            await mcp_server.save_lighting_schedule("Sera", "20:30", "all", "color",
                                                     repeat="weekdays", color="#ff8800", brightness=45)
        self.assertEqual(transport.await_args_list[0].args,
                         ("target.apply", {"target": ["striscia", "keyboard"], "color": "#FF8800", "brightness": 55, "power": True}))
        self.assertEqual(transport.await_args_list[1].args, ("target.apply", {"target": "all", "power": False}))
        self.assertEqual(transport.await_args_list[2].args,
                         ("pc.apply_to", {"devices": ["keyboard"], "state": {
                             "effect": "respiro", "on": True, "color": [17, 34, 51],
                             "color2": [68, 85, 102], "speed": 0.7, "brightness": 40}}))
        self.assertEqual(transport.await_args_list[3].args, ("pc.scene.apply", {"id": "keyboard_only"}))
        self.assertEqual(transport.await_args_list[4].args,
                         ("lights.set", {"device": "striscia", "device_preset": "Light preset 1"}))
        self.assertEqual(transport.await_args_list[5].args,
                         ("schedules.save", {"name": "Sera", "definition": {
                             "target": "all", "time": "20:30", "days": [1, 2, 3, 4, 5],
                             "enabled": True, "action": {"power": True, "color": "#ff8800", "brightness": 45}}}))

    async def test_one_time_schedule_can_choose_calendar_date(self) -> None:
        transport = AsyncMock(return_value={"ok": True})
        with patch.object(mcp_server, "invoke_async", transport):
            await mcp_server.save_lighting_schedule("Ospiti", "19:30", "all", "on",
                                                     repeat="once", once_date="2026-10-15")
        self.assertEqual(transport.await_args.args,
                         ("schedules.save", {"name": "Ospiti", "definition": {
                             "target": "all", "time": "19:30", "days": [], "enabled": True,
                             "action": {"power": True}, "once_date": "2026-10-15"}}))

    async def test_real_stdio_transport_lists_tools(self) -> None:
        server = Path(__file__).with_name("mcp_server.py")
        async with Client(StdioServerParameters(command=sys.executable, args=[str(server)])) as client:
            result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        self.assertIn("set_power", names)
        self.assertIn("save_animation", names)
        self.assertIn("set_pc_device", names)

    async def test_real_stdio_tool_call_reaches_loopback_service(self) -> None:
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["path"] = self.path
                received["authorization"] = self.headers.get("Authorization")
                received["payload"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = b'{"ok":true,"data":{"devices":[{"id":"lampadina1"}]}}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=service.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as root:
                directory = Path(root) / "Smartlight"
                directory.mkdir()
                (directory / "service.json").write_text(json.dumps({"port": service.server_port}), encoding="utf-8")
                (directory / "token").write_text("test-token", encoding="utf-8")
                server = Path(__file__).with_name("mcp_server.py")
                async with Client(StdioServerParameters(command=sys.executable, args=[str(server)],
                                                        env={"APPDATA": root, "XDG_DATA_HOME": root})) as client:
                    result = await client.call_tool("list_devices", {})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content, {"devices": [{"id": "lampadina1"}]})
                self.assertEqual(received, {
                    "path": "/invoke",
                    "authorization": "Bearer test-token",
                    "payload": {"command": "devices.list", "params": {}},
                })
        finally:
            service.shutdown()
            service.server_close()
            worker.join(timeout=2)

    async def test_mcp_and_desktop_ui_read_the_same_lighting_state(self) -> None:
        with tempfile.TemporaryDirectory() as root, \
                patch.dict(os.environ, {"APPDATA": root, "XDG_DATA_HOME": root}):
            lighting = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)

            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    result = lighting.invoke(request["command"], request["params"])
                    body = json.dumps(result).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *_args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                config = Path(root) / "Smartlight"
                config.mkdir(exist_ok=True)
                (config / "service.json").write_text(json.dumps({"port": server.server_port}), encoding="utf-8")
                (config / "token").write_text("test-token", encoding="utf-8")
                script = Path(__file__).with_name("mcp_server.py")
                async with Client(StdioServerParameters(
                        command=sys.executable, args=[str(script)],
                        env={"APPDATA": root, "XDG_DATA_HOME": root})) as client:
                    result = await client.call_tool("set_color", {
                        "target": ["strip", "keyboard"], "color": "#00FF88", "brightness": 63})
                    self.assertFalse(result.is_error)
                    ui_state = lighting.invoke("status", {})["data"]
                    self.assertEqual(ui_state["devices"][0]["brightness"], 63)
                    self.assertEqual(ui_state["pc"]["state"]["keyboard"]["color"], [0, 255, 136])
                    self.assertEqual(ui_state["pc"]["state"]["mouse"]["color"], [102, 186, 255])

                    lighting.invoke("target.apply", {"target": "keyboard", "power": False})
                    overview = await client.call_tool("get_lighting_overview", {})
                    self.assertFalse(overview.is_error)
                    self.assertFalse(next(item for item in overview.structured_content["pc"]
                                          if item["key"] == "keyboard")["state"]["on"])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=2)
                lighting.close()


if __name__ == "__main__":
    unittest.main()
