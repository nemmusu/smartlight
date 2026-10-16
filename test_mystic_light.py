"""Simulated protocol/native boundary tests; these are NOT hardware certification."""
import ctypes
import io
import hashlib
import json
import os
from pathlib import Path
import queue
import struct
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import Mock, patch

from mystic_light import MAX_DOWNLOAD_BYTES, MysticBackend, MysticError, MysticLight, NativeSdk, _automation, _check_download_url, discover_sdk, download_sdk_archive, provision_sdk, validate_dll, worker_command, worker_session
from pc import PCController


ZONE = {"type": "MB", "index": 0, "name": "MSI simulated zone", "style": "Steady", "max_brightness": 10}


class WorkerTests(unittest.TestCase):
    def session(self, requests, sdk=None):
        sdk = sdk or SimpleNamespace(devices=Mock(return_value=[ZONE]), set_color=Mock(), close=Mock())
        output = io.StringIO()
        worker_session(sdk, io.StringIO("\n".join(json.dumps(item) for item in requests)), output)
        return sdk, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_discovery_never_writes_and_always_releases(self):
        sdk, result = self.session([{"op": "list"}])
        self.assertEqual(result[0]["data"], [ZONE])
        sdk.set_color.assert_not_called()
        sdk.close.assert_called_once()

    def test_static_color_on_off_and_prepare_once_per_zone(self):
        sdk, result = self.session([{"op": "list"}, {"op": "set", "zone": 0, "color": [10, 20, 30]},
                                    {"op": "set", "zone": 0, "color": [0, 0, 0]}])
        self.assertTrue(all(item["ok"] for item in result))
        self.assertEqual(sdk.set_color.call_args_list[0].kwargs, {"prepare": True})
        self.assertEqual(sdk.set_color.call_args_list[1].kwargs, {"prepare": False})
        self.assertEqual(sdk.set_color.call_args_list[1].args[1], (0, 0, 0))

    def test_bad_colors_unknown_operations_and_zones_never_write(self):
        requests = [{"op": "list"}, {"op": "set", "zone": -1, "color": [1, 2, 3]},
                    {"op": "set", "zone": True, "color": [1, 2, 3]},
                    {"op": "set", "zone": 0, "color": [256, 1, 2]},
                    {"op": "set", "zone": 0, "color": [True, 1, 2]}, {"op": "native-arbitrary"}]
        sdk, result = self.session(requests)
        self.assertTrue(all(not item["ok"] for item in result[1:]))
        sdk.set_color.assert_not_called()

    def test_sdk_error_is_reported_and_released(self):
        sdk = SimpleNamespace(devices=Mock(side_effect=MysticError("MSI SDK unavailable (-3)")), close=Mock())
        _, result = self.session([{"op": "list"}], sdk)
        self.assertFalse(result[0]["ok"])
        self.assertIn("-3", result[0]["error"])
        sdk.close.assert_called_once()

    def test_style_and_native_brightness_are_prepared_before_color(self):
        events = []
        sdk = NativeSdk.__new__(NativeSdk)
        sdk.ole = SimpleNamespace(SysAllocString=lambda value: value, SysFreeString=lambda value: None)
        sdk.dll = SimpleNamespace(
            MLAPI_SetLedStyle=lambda *args: events.append(("style", args)) or 0,
            MLAPI_SetLedBright=lambda *args: events.append(("brightness", args)) or 0,
            MLAPI_SetLedColor=lambda *args: events.append(("color", args)) or 0)
        sdk.set_color(ZONE, [12, 20, 30], prepare=True)
        self.assertEqual([item[0] for item in events], ["style", "brightness", "color"])
        self.assertEqual(events[1][1][-1], 10)
        self.assertEqual(events[2][1], ("MB", 0, 12, 20, 30))

    def test_unsupported_brightness_is_not_assumed(self):
        sdk = NativeSdk.__new__(NativeSdk)
        sdk.ole = SimpleNamespace(SysAllocString=lambda value: value, SysFreeString=lambda value: None)
        sdk.dll = SimpleNamespace(MLAPI_SetLedStyle=Mock(return_value=0), MLAPI_SetLedColor=Mock(return_value=0), MLAPI_SetLedBright=Mock())
        sdk.set_color({**ZONE, "max_brightness": None}, [12, 20, 30], prepare=True)
        sdk.dll.MLAPI_SetLedBright.assert_not_called()


class IsolationTests(unittest.TestCase):
    def test_frozen_worker_uses_console_mcp_sibling_not_windowed_gui(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "Smartlight" / "Smartlight.exe"
            worker = Path(directory) / "Smartlight-MCP" / "Smartlight-MCP.exe"
            worker.parent.mkdir()
            worker.touch()
            with patch("mystic_light.sys", SimpleNamespace(frozen=True, executable=str(app))):
                self.assertEqual(worker_command(), [str(worker)])
            worker.unlink()
            with patch("mystic_light.sys", SimpleNamespace(frozen=True, executable=str(app))):
                with self.assertRaisesRegex(MysticError, "Repair"):
                    worker_command()

    def test_explicit_path_never_searches_unrelated_directories(self):
        with patch("mystic_light.validate_dll", return_value=Path("official.dll")) as validate:
            self.assertEqual(discover_sdk("provided.dll"), Path("official.dll"))
            validate.assert_called_once_with("provided.dll")

    def test_non_windows_refuses_dll_loading(self):
        with self.assertRaisesRegex(MysticError, "Windows"):
            validate_dll("C:/MSI.dll", platform="posix")

    def test_relative_and_non_dll_paths_rejected(self):
        for path in ("MSI.dll", "", "C:/not-a-dll.txt"):
            with self.assertRaises((MysticError, FileNotFoundError)):
                validate_dll(path, platform="nt")

    def test_wrong_architecture_is_rejected_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.dll"
            content = bytearray(160)
            content[:2] = b"MZ"
            struct.pack_into("<I", content, 60, 100)
            content[100:104] = b"PE\0\0"
            struct.pack_into("<H", content, 104, 0x14c if struct.calcsize("P") == 8 else 0x8664)
            path.write_bytes(content)
            with self.assertRaisesRegex(MysticError, "architecture"):
                validate_dll(str(path), platform="nt")

    def test_timeout_disables_worker_without_retry(self):
        backend = MysticBackend("", timeout=0.01)
        process = Mock()
        process.poll.return_value = None
        backend.process = process
        with self.assertRaises(MysticError):
            backend._request({"op": "list"})
        self.assertIsNone(backend.process)
        self.assertIn("stopped", backend.status)
        with self.assertRaisesRegex(MysticError, "reconnect"):
            backend._request({"op": "list"})

    def test_worker_crash_disables_backend(self):
        backend = MysticBackend("", timeout=0.01)
        process = Mock()
        process.poll.return_value = None
        backend.process = process
        backend._responses.put(None)
        with self.assertRaisesRegex(MysticError, "unexpectedly"):
            backend._request({"op": "list"})
        self.assertIsNone(backend.process)
        self.assertTrue(backend.failed)
        self.assertFalse(backend.healthy)

    def test_zone_identity_stable_and_explicitly_experimental(self):
        one, two = MysticLight(None, 0, ZONE), MysticLight(None, 1, ZONE)
        self.assertEqual(one.key, two.key)
        self.assertEqual(one.led_count, 1)
        self.assertIn("experimental", one.source)


@unittest.skipUnless(os.name == "nt", "Windows OLE Automation boundary")
class AutomationBoundaryTests(unittest.TestCase):
    def test_real_bstr_safearray_with_nonzero_lower_bound(self):
        sdk = NativeSdk.__new__(NativeSdk)
        sdk.ole = _automation()
        sdk.ole.SafeArrayCreateVector.argtypes = [ctypes.c_ushort, ctypes.c_long, ctypes.c_uint]
        sdk.ole.SafeArrayCreateVector.restype = ctypes.c_void_p
        sdk.ole.SafeArrayPutElement.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_long), ctypes.c_void_p]
        pointer = sdk.ole.SafeArrayCreateVector(8, 2, 3)
        for index, value in enumerate(["MSI_MB", "No animation", "Test · à"], 2):
            token = sdk.ole.SysAllocString(value)
            try:
                sdk.ole.SafeArrayPutElement(pointer, ctypes.byref(ctypes.c_long(index)), token)
            finally:
                sdk.ole.SysFreeString(token)
        self.assertEqual(sdk._array(pointer), ["MSI_MB", "No animation", "Test · à"])

    def test_real_integer_safearray(self):
        sdk = NativeSdk.__new__(NativeSdk)
        sdk.ole = _automation()
        sdk.ole.SafeArrayCreateVector.argtypes = [ctypes.c_ushort, ctypes.c_long, ctypes.c_uint]
        sdk.ole.SafeArrayCreateVector.restype = ctypes.c_void_p
        sdk.ole.SafeArrayPutElement.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_long), ctypes.c_void_p]
        pointer = sdk.ole.SafeArrayCreateVector(19, 0, 2)
        for index, value in enumerate([1, 12]):
            sdk.ole.SafeArrayPutElement(pointer, ctypes.byref(ctypes.c_long(index)), ctypes.byref(ctypes.c_uint32(value)))
        self.assertEqual(sdk._array(pointer), [1, 12])


class ControllerTests(unittest.TestCase):
    def setUp(self):
        detector = patch("pc.detect_msi_environment", return_value={"software_present": False, "hardware_present": False, "details": []})
        self.detector = detector.start()
        self.addCleanup(detector.stop)

    def controller(self, directory):
        return PCController(data_dir=directory, legacy_dir=Path(directory) / "no-legacy")

    def test_auto_default_has_no_native_or_subprocess_calls_before_discovery(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch("pc.Engine.start"), patch("pc.MysticBackend") as backend:
            controller = self.controller(directory)
            backend.assert_not_called()
            self.assertIsNone(controller._mystic)
            self.assertEqual(controller.get_status()["backend_mode"], "auto")

    def test_fallback_runs_only_after_empty_normal_backends(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch("pc.Engine.start"), patch("pc.MysticBackend") as backend, patch("pc.ICueBackend") as icue:
            Path(directory, "settings.json").write_text(json.dumps({"mystic_light_enabled": True, "mystic_light_dll": "official.dll"}))
            # Patch only pc.os; do not make pathlib instantiate a WindowsPath on Linux.
            platform = SimpleNamespace(name="nt", environ={})
            with patch("pc.os", platform):
                controller = self.controller(directory)
            zone = MysticLight(backend.return_value, 0, ZONE)
            backend.return_value.connect.return_value = [zone]
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect") as openrgb:
                openrgb.return_value = []
                controller._connect()
                openrgb.assert_called_once()
            icue.return_value.connect.assert_called_once()
            backend.return_value.connect.assert_called_once()
            self.assertTrue(controller._mystic_active)
            self.assertEqual([effect["id"] for effect in controller.get_effects()], ["statico"])
            with self.assertRaisesRegex(ValueError, "static"):
                controller.start_flow([[1, 2, 3], [4, 5, 6]], 1, [], 0)

    def test_fallback_does_not_run_when_normal_backend_has_one_light(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch("pc.Engine.start"), patch("pc.MysticBackend") as backend, patch("pc.ICueBackend") as icue:
            Path(directory, "settings.json").write_text(json.dumps({"mystic_light_enabled": True}))
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            normal_light = SimpleNamespace(key="openrgb:existing")
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[normal_light]):
                controller._connect()
            backend.return_value.connect.assert_not_called()
            self.assertFalse(controller._mystic_active)
            self.assertGreater(len(controller.get_effects()), 1)

    def test_static_guard_rejects_animations_and_profiles_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"):
            controller = self.controller(directory)
            controller._mystic_active = True
            controller._engine.set_lights({"mystic:zone": MysticLight(None, 0, ZONE)})
            with self.assertRaisesRegex(ValueError, "static"):
                controller.set_device("mystic:zone", {"effect": "respiro"})
            with self.assertRaisesRegex(ValueError, "static"):
                controller.apply_to(["mystic:zone"], {"effect": "respiro"})
            with self.assertRaisesRegex(ValueError, "static"):
                controller.import_data({"state": {"devices": {"mystic:zone": {"effect": "respiro"}}}})
            self.assertEqual(controller._engine.state["mystic:zone"]["effect"], "statico")

    def test_icue_reconnect_cannot_add_parallel_writer_during_msi(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend"):
            controller = self.controller(directory)
            controller._mystic_active = True
            with patch.object(controller, "_refresh_icue") as refresh:
                controller._on_icue_reconnect()
                refresh.assert_not_called()

    def test_crashed_worker_is_offline_and_not_advertised_active(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"):
            controller = self.controller(directory)
            backend = MysticBackend("", timeout=0.01)
            process = Mock()
            process.poll.return_value = None
            backend.process = process
            controller._mystic = backend
            controller._mystic_active = True
            light = MysticLight(backend, 0, ZONE)
            controller._engine.set_lights({light.key: light})
            self.assertTrue(controller.get_status()["mystic_light_active"])
            self.assertTrue(controller.list_devices()[0]["online"])
            backend._responses.put(None)
            with self.assertRaises(MysticError):
                light.set_color((1, 2, 3))
            status = controller.get_status()
            self.assertFalse(status["mystic_light_active"])
            self.assertTrue(status["mystic_light_failed"])
            self.assertFalse(controller.list_devices()[0]["online"])
            self.assertTrue(controller._mystic_active)  # Keep static-only restrictions until rescan.
            with self.assertRaisesRegex(ValueError, "static"):
                controller.start_flow([[1, 2, 3], [4, 5, 6]], 1, [], 0)

    def test_silent_worker_exit_also_reports_offline_before_next_write(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"):
            controller = self.controller(directory)
            backend = MysticBackend("")
            backend.process = Mock()
            backend.process.poll.return_value = 1
            controller._mystic = backend
            controller._mystic_active = True
            status = controller.get_status()
            self.assertFalse(status["mystic_light_active"])
            self.assertTrue(status["mystic_light_failed"])
            backend.close()

    def test_linux_ignores_windows_only_opt_in(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.MysticBackend") as backend:
            Path(directory, "settings.json").write_text(json.dumps({"mystic_light_enabled": True}))
            with patch("pc.os", SimpleNamespace(name="posix", environ={})):
                controller = self.controller(directory)
            backend.assert_not_called()
            self.assertIsNone(controller._mystic)

    def test_auto_non_msi_machine_never_probes_downloads_or_constructs_sdk(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.MysticBackend") as backend, patch("pc.ICueBackend") as icue:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[]):
                controller._connect()
            self.detector.assert_called_once()
            backend.assert_not_called()
            self.assertIn("skipped", controller.get_status()["mystic_light"])

    def test_auto_msi_evidence_enables_actual_sdk_probe_after_zero_normal_lights(self):
        evidence = {"software_present": True, "hardware_present": True, "details": []}
        self.detector.return_value = evidence
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.MysticBackend") as backend, patch("pc.ICueBackend") as icue:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            backend.return_value.connect.return_value = [MysticLight(backend.return_value, 0, ZONE)]
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[]):
                controller._connect()
            backend.assert_called_once_with("", directory=Path(directory), evidence=evidence)
            backend.return_value.connect.assert_called_once()
            self.assertTrue(controller._mystic_active)

    def test_manual_openrgb_includes_corsair_and_never_constructs_icue(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            Path(directory, "settings.json").write_text(json.dumps({"pc_backend_mode": "openrgb"}))
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            self.assertTrue(controller._openrgb.include_corsair)
            with patch.object(controller._openrgb, "connect", return_value=[]) as openrgb:
                controller._connect()
                openrgb.assert_called_once()
            icue.assert_not_called()
            backend.assert_not_called()
            self.detector.assert_not_called()

    def test_manual_icue_never_connects_openrgb_or_msi(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            Path(directory, "settings.json").write_text(json.dumps({"pc_backend_mode": "icue"}))
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect") as openrgb:
                controller._connect()
                openrgb.assert_not_called()
            icue.return_value.connect.assert_called_once()
            backend.assert_not_called()
            self.detector.assert_not_called()

    def test_manual_mystic_never_connects_other_backends(self):
        self.detector.return_value = {"software_present": True, "hardware_present": True}
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            Path(directory, "settings.json").write_text(json.dumps({"pc_backend_mode": "mystic"}))
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            backend.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect") as openrgb:
                controller._connect()
                openrgb.assert_not_called()
            icue.assert_not_called()
            backend.return_value.connect.assert_called_once()
            self.assertFalse(controller._mystic_active)

    def test_existing_normal_lights_skip_even_msi_detection_entirely(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[SimpleNamespace(key="openrgb:one")]):
                controller._connect()
            self.detector.assert_not_called()
            backend.assert_not_called()

    def test_legacy_explicit_optout_prevents_automatic_detection(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            Path(directory, "settings.json").write_text(json.dumps({"mystic_light_enabled": False}))
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[]):
                controller._connect()
            self.detector.assert_not_called()
            backend.assert_not_called()

    def test_msi_hardware_without_required_software_does_not_load_or_download(self):
        self.detector.return_value = {"software_present": False, "hardware_present": True}
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue, patch("pc.MysticBackend") as backend:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", return_value=[]):
                controller._connect()
            backend.assert_not_called()
            self.assertIn("Install MSI Center", controller.get_status()["mystic_light"])

    def test_auto_corsair_falls_back_to_openrgb_and_keeps_owner_on_icue_reconnect(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            corsair = SimpleNamespace(name="Corsair Vengeance", leds=[0], type=SimpleNamespace(name="DRAM"))
            def discover():
                controller._openrgb.client = SimpleNamespace(devices=[corsair])
                controller._openrgb._build()
                return controller._openrgb.lights
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", side_effect=lambda **kwargs: discover()):
                controller._connect()
            self.assertTrue(controller._openrgb.include_corsair)
            self.assertTrue(controller._openrgb_owns_corsair)
            self.assertEqual([device["source"] for device in controller.list_devices()], ["OpenRGB"])
            icue.return_value.connect.reset_mock()
            with patch.object(controller, "_refresh_icue") as refresh:
                controller._on_icue_reconnect()
                refresh.assert_not_called()
            icue.return_value.connect.assert_not_called()
            self.detector.assert_not_called()

    def test_explicit_rescan_transfers_corsair_back_to_icue_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            corsair = SimpleNamespace(name="Corsair Vengeance", leds=[0], type=SimpleNamespace(name="DRAM"))
            def discover():
                controller._openrgb.client = SimpleNamespace(devices=[corsair])
                controller._openrgb._build()
                return controller._openrgb.lights
            icue.return_value.connect.return_value = []
            with patch.object(controller._openrgb, "connect", side_effect=lambda **kwargs: discover()):
                controller._connect()
            icue_light = SimpleNamespace(key="icue:Corsair Vengeance", name="Corsair Vengeance", source="iCUE",
                                         kind="RAM", category="Memoria", led_count=1)
            icue.return_value.connect.return_value = [icue_light]
            with patch.object(controller._openrgb, "rescan", side_effect=lambda: discover()):
                controller._connect(rescan=True)
            self.assertFalse(controller._openrgb.include_corsair)
            self.assertFalse(controller._openrgb_owns_corsair)
            self.assertEqual([device["key"] for device in controller.list_devices()], [icue_light.key])
            self.assertEqual([device["source"] for device in controller.list_devices()], ["iCUE"])

    def test_live_icue_owner_filters_corsair_from_openrgb(self):
        with tempfile.TemporaryDirectory() as directory, patch("pc.Engine.start"), patch("pc.ICueBackend") as icue:
            with patch("pc.os", SimpleNamespace(name="nt", environ={})):
                controller = self.controller(directory)
            icue_light = SimpleNamespace(key="icue:Corsair Vengeance", name="Corsair Vengeance", source="iCUE",
                                         kind="RAM", category="Memoria", led_count=1)
            icue.return_value.connect.return_value = [icue_light]
            def discover():
                controller._openrgb.client = SimpleNamespace(devices=[SimpleNamespace(name="Corsair Vengeance", leds=[0])])
                controller._openrgb._build()
                return controller._openrgb.lights
            with patch.object(controller._openrgb, "connect", side_effect=lambda **kwargs: discover()):
                controller._connect()
            self.assertFalse(controller._openrgb.include_corsair)
            self.assertEqual([device["source"] for device in controller.list_devices()], ["iCUE"])


class ProvisionTests(unittest.TestCase):
    def evidence(self):
        return {"software_present": True, "hardware_present": True}

    def archive(self):
        output = io.BytesIO()
        filename = "MysticLight_SDK_x64.dll" if struct.calcsize("P") == 8 else "MysticLight_SDK.dll"
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(f"Mystic_light_SDK_1.0.0.08/{filename}", b"simulated DLL content")
            archive.writestr("../../never-extracted.exe", b"unwanted")
        return output.getvalue(), filename

    def windows(self):
        return patch("mystic_light.os", SimpleNamespace(name="nt", fdopen=os.fdopen, replace=os.replace))

    def test_software_and_hardware_required_before_download(self):
        with tempfile.TemporaryDirectory() as directory, self.windows(), patch("mystic_light.download_sdk_archive") as download:
            for evidence in ({}, {"software_present": True}, {"hardware_present": True}):
                with self.assertRaises(MysticError):
                    provision_sdk(directory, evidence)
            download.assert_not_called()

    def test_non_windows_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory, patch("mystic_light.os", SimpleNamespace(name="posix")), patch("mystic_light.download_sdk_archive") as download:
            with self.assertRaisesRegex(MysticError, "Windows"):
                provision_sdk(directory, self.evidence())
            download.assert_not_called()

    def test_hash_change_rejected_without_writing_any_dll(self):
        with tempfile.TemporaryDirectory() as directory, self.windows(), patch("mystic_light.download_sdk_archive", return_value=b"unexpected archive"):
            with self.assertRaisesRegex(MysticError, "changed"):
                provision_sdk(directory, self.evidence())
            self.assertFalse(list(Path(directory).rglob("*.dll")))

    def test_native_preflight_failure_never_leaves_downloaded_dll_installed(self):
        data, filename = self.archive()
        expected = hashlib.sha256(b"simulated DLL content").hexdigest()
        with tempfile.TemporaryDirectory() as directory, self.windows(), patch("mystic_light.SDK_ARCHIVE_SHA256", hashlib.sha256(data).hexdigest()), patch("mystic_light.SDK_FILES", {struct.calcsize("P"): (filename, expected)}), patch("mystic_light.download_sdk_archive", return_value=data), patch("mystic_light.validate_dll", side_effect=MysticError("missing exports")):
            with self.assertRaisesRegex(MysticError, "missing exports"):
                provision_sdk(directory, self.evidence())
            self.assertFalse(list(Path(directory).rglob("*.dll")))

    def test_only_exact_verified_sdk_member_installed_atomically_and_cache_reused(self):
        data, filename = self.archive()
        expected = hashlib.sha256(b"simulated DLL content").hexdigest()
        with tempfile.TemporaryDirectory() as directory, self.windows(), patch("mystic_light.SDK_ARCHIVE_SHA256", hashlib.sha256(data).hexdigest()), patch("mystic_light.SDK_FILES", {struct.calcsize("P"): (filename, expected)}), patch("mystic_light.download_sdk_archive", return_value=data) as download, patch("mystic_light.validate_dll", side_effect=lambda name: Path(name)) as validate:
            result = provision_sdk(directory, self.evidence())
            self.assertEqual(result.read_bytes(), b"simulated DLL content")
            self.assertEqual([p.name for p in Path(directory).rglob("*.dll")], [filename])
            self.assertFalse(Path(directory).parent.joinpath("never-extracted.exe").exists())
            self.assertEqual(provision_sdk(directory, {"software_present": True}), result)
            download.assert_called_once()
            self.assertGreaterEqual(validate.call_count, 2)

    def test_unofficial_or_http_redirects_are_rejected(self):
        for url in ("http://download.msi.com/sdk.zip", "https://evil.example/sdk.zip", "https://download.msi.com:444/sdk.zip", "https://user@download.msi.com/sdk.zip"):
            with self.assertRaises(MysticError):
                _check_download_url(url)
        _check_download_url("https://download-2.msi.com/uti_exe/Mystic_light_SDK.zip")

    def test_download_header_size_limit_prevents_body_read(self):
        response = Mock()
        response.geturl.return_value = "https://download-2.msi.com/uti_exe/Mystic_light_SDK.zip"
        response.headers = {"Content-Length": str(MAX_DOWNLOAD_BYTES + 1)}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("mystic_light.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(MysticError, "size limit"):
                download_sdk_archive()
            response.read.assert_not_called()

    def test_download_total_deadline_prevents_slow_unbounded_read(self):
        response = Mock()
        response.geturl.return_value = "https://download-2.msi.com/uti_exe/Mystic_light_SDK.zip"
        response.headers = {}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("mystic_light.urllib.request.build_opener") as opener, patch("mystic_light.time.monotonic", side_effect=[0, 21]):
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(MysticError, "timed out"):
                download_sdk_archive()
            response.read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
