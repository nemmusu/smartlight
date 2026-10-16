"""Official SDK ABI behavior simulated without claims of physical certification."""
import ctypes
import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from mystic_light import MysticError, MysticLight, NativeSdk, _automation, worker_session


ZONE = {"type": "MSI_MB", "index": 0, "name": "Demo", "style": "Steady",
        "styles": ["Steady", "Breathing", "Rainbow"], "max_speed": 4, "max_brightness": 10}


class NativeTests(unittest.TestCase):
    def sdk(self):
        sdk = NativeSdk.__new__(NativeSdk)
        sdk.ole = SimpleNamespace(SysAllocString=lambda x: x, SysFreeString=Mock())
        sdk.dll = SimpleNamespace(MLAPI_SetLedStyle=Mock(return_value=0),
                                  MLAPI_SetLedColor=Mock(return_value=0),
                                  MLAPI_SetLedSpeed=Mock(return_value=0),
                                  MLAPI_SetLedBright=Mock(return_value=0))
        def level(value):
            def read(token, index, pointer):
                ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))[0] = value
                return 0
            return read
        sdk.dll.MLAPI_GetLedMaxSpeed = level(8)
        sdk.dll.MLAPI_GetLedMaxBright = level(100)
        return sdk

    def test_native_uses_style_specific_ranges(self):
        sdk = self.sdk()
        result = sdk.set_native(ZONE, "Breathing", [1, 2, 3], 2, 5)
        sdk.dll.MLAPI_SetLedSpeed.assert_called_once_with("MSI_MB", 0, 4)
        sdk.dll.MLAPI_SetLedBright.assert_called_once_with("MSI_MB", 0, 50)
        self.assertEqual(result, {"unsupported": [], "max_speed": 8, "max_brightness": 100})

    def test_unsupported_color_does_not_cancel_native_animation(self):
        sdk = self.sdk()
        sdk.dll.MLAPI_SetLedColor.return_value = -103
        result = sdk.set_native(ZONE, "Rainbow", [20, 40, 60], 2, 10)
        self.assertEqual(result["unsupported"], ["color"])
        sdk.dll.MLAPI_SetLedSpeed.assert_called_once()

    def test_normalized_controls_work_when_initial_style_has_no_range(self):
        sdk = self.sdk()
        zone = {**ZONE, "max_speed": None, "max_brightness": None}
        sdk.set_native(zone, "Breathing", normalized_speed=0.5, normalized_brightness=0.25)
        sdk.dll.MLAPI_SetLedSpeed.assert_called_once_with("MSI_MB", 0, 4)
        sdk.dll.MLAPI_SetLedBright.assert_called_once_with("MSI_MB", 0, 25)

    def test_static_restore_requeries_brightness_after_style_change(self):
        sdk = self.sdk()
        sdk.set_color(ZONE, [20, 30, 40], prepare=True)
        sdk.dll.MLAPI_SetLedBright.assert_called_once_with("MSI_MB", 0, 100)

    def test_missing_optional_speed_setter_is_reported_unsupported(self):
        sdk = self.sdk()
        del sdk.dll.MLAPI_SetLedSpeed
        result = sdk.set_native(ZONE, "Breathing", normalized_speed=0.5)
        self.assertEqual(result["max_speed"], None)
        self.assertEqual(result["unsupported"], ["speed"])

    def test_invalid_normalized_control_never_changes_style(self):
        sdk = self.sdk()
        for value in (True, float("nan"), float("inf"), -0.1, 1.1):
            with self.assertRaises(MysticError):
                sdk.set_native(ZONE, "Breathing", normalized_speed=value)
        with self.assertRaises(MysticError):
            sdk.set_native(ZONE, "Breathing", speed=2, normalized_speed=0.5)
        sdk.dll.MLAPI_SetLedStyle.assert_not_called()

    def test_bad_style_or_parameters_cause_no_mutation(self):
        sdk = self.sdk()
        for args in [("Invented", None, None, None), ("Steady", None, True, None),
                     ("Steady", [256, 0, 0], None, None), ("Steady", None, 5, None)]:
            with self.assertRaises(MysticError):
                sdk.set_native(ZONE, *args)
        sdk.dll.MLAPI_SetLedStyle.assert_not_called()

    def test_named_direct_frame_flushes_last_pixel_only(self):
        sdk = self.sdk()
        sdk.dll.MLAPI_SetLedColorEx = Mock(return_value=0)
        zone = {**ZONE, "style": "Direct Lighting Control", "led_names": ["A", "B"]}
        sdk.set_frame(zone, [[1, 2, 3], [4, 5, 6]], True)
        self.assertEqual(sdk.dll.MLAPI_SetLedColorEx.call_args_list[0].args, ("MSI_MB", 0, "A", 1, 2, 3, 0))
        self.assertEqual(sdk.dll.MLAPI_SetLedColorEx.call_args_list[1].args, ("MSI_MB", 0, "B", 4, 5, 6, 1))
        sdk.dll.MLAPI_SetLedColor.assert_not_called()

    def test_malformed_frame_does_not_write_partial_pixels(self):
        sdk = self.sdk()
        sdk.dll.MLAPI_SetLedColorEx = Mock(return_value=0)
        zone = {**ZONE, "led_names": ["A", "B"]}
        with self.assertRaises(MysticError):
            sdk.set_frame(zone, [[1, 2, 3], [0, -1, 0]], True)
        sdk.dll.MLAPI_SetLedStyle.assert_not_called()
        sdk.dll.MLAPI_SetLedColorEx.assert_not_called()

    def test_native_only_off_uses_brightness(self):
        sdk = self.sdk()
        sdk.power_off({**ZONE, "style": None})
        sdk.dll.MLAPI_SetLedBright.assert_called_once_with("MSI_MB", 0, 0)
        sdk.dll.MLAPI_SetLedColor.assert_not_called()

    def test_readback_returns_null_for_unsupported_not_invented_state(self):
        sdk = self.sdk()
        sdk.dll.MLAPI_GetLedBright = Mock(return_value=-103)
        sdk.dll.MLAPI_GetLedSpeed = Mock(return_value=-103)
        self.assertEqual(sdk.state(ZONE), {"source": "msi_sdk", "brightness": None,
                                          "speed": None, "style": None, "color": None})
        sdk.dll.MLAPI_SetLedStyle.assert_not_called()

    def test_worker_native_to_software_reprepares_style(self):
        sdk = SimpleNamespace(devices=Mock(return_value=[ZONE]), set_color=Mock(),
                              set_native=Mock(return_value={"unsupported": []}), close=Mock())
        requests = [{"op": "list"}, {"op": "set", "zone": 0, "color": [1, 2, 3]},
                    {"op": "native", "zone": 0, "style": "Rainbow"},
                    {"op": "set", "zone": 0, "color": [4, 5, 6]}]
        out = io.StringIO()
        worker_session(sdk, io.StringIO("\n".join(map(json.dumps, requests))), out)
        self.assertTrue(all(json.loads(line)["ok"] for line in out.getvalue().splitlines()))
        self.assertTrue(all(call.kwargs["prepare"] for call in sdk.set_color.call_args_list))

    def test_light_metadata_and_protocol_use_actual_discovered_pixels(self):
        backend = SimpleNamespace(_request=Mock())
        light = MysticLight(backend, 0, {**ZONE, "led_names": ["A", "B"]})
        self.assertEqual(light.led_count, 2)
        light.set_leds([(10, 20, 30), (40, 50, 60)])
        self.assertEqual(backend._request.call_args.args[0]["op"], "frame")
        light.off()
        self.assertEqual(backend._request.call_args.args[0]["op"], "off")

    @unittest.skipUnless(os.name == "nt", "Windows OLE BSTR boundary")
    def test_real_bstr_discovery_maps_names_only_to_matching_area(self):
        sdk = self.sdk()
        sdk.ole = _automation()
        sdk._array = Mock(side_effect=[["MSI_MB"], [2], ["0:A", "0:B", "1:C", "9:wrong", "invalid"],
                                      ["Steady", "Direct Lighting Control"], ["Rainbow"]])
        sdk.dll.MLAPI_GetDeviceInfo = Mock(return_value=0)
        sdk.dll.MLAPI_GetLedName = Mock(return_value=0)
        sdk.dll.MLAPI_SetLedColorEx = Mock(return_value=0)
        def info(token, index, label, styles):
            self.assertEqual(ctypes.wstring_at(token), "MSI_MB")
            ctypes.cast(label, ctypes.POINTER(ctypes.c_void_p))[0] = sdk.ole.SysAllocString("Zone " + str(index))
            return 0
        sdk.dll.MLAPI_GetLedInfo = info
        zones = sdk.devices()
        self.assertEqual(zones[0]["led_names"], ["A", "B"])
        self.assertEqual(zones[0]["style"], "Direct Lighting Control")
        self.assertTrue(zones[0]["supports_software_effects"])
        self.assertEqual(zones[1]["led_names"], [])
        self.assertEqual(zones[1]["styles"], ["Rainbow"])
        self.assertFalse(zones[1]["supports_software_effects"])

    @unittest.skipUnless(os.name == "nt", "Windows OLE BSTR boundary")
    def test_real_bstr_state_reads_vendor_style_and_rgb(self):
        sdk = self.sdk()
        sdk.ole = _automation()
        def style(token, index, out):
            ctypes.cast(out, ctypes.POINTER(ctypes.c_void_p))[0] = sdk.ole.SysAllocString("Breathing")
            return 0
        def color(token, index, *out):
            for pointer, value in zip(out, [12, 34, 56]):
                ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))[0] = value
            return 0
        sdk.dll.MLAPI_GetLedStyle = style
        sdk.dll.MLAPI_GetLedColor = color
        state = sdk.state(ZONE)
        self.assertEqual(state["style"], "Breathing")
        self.assertEqual(state["color"], [12, 34, 56])


if __name__ == "__main__":
    unittest.main()
