"""Setup detection uses independent, read-only evidence, never vendor drivers."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pc_discovery as discovery


class DiscoveryTests(TestCase):
    def windows(self):
        return patch.object(discovery, "os", SimpleNamespace(name="nt", environ={}))

    def software(self, name):
        base = discovery._UNINSTALL[0]
        def children(hive, path, **kwargs):
            return ["app"] if hive == "HKEY_LOCAL_MACHINE" and path == base else []
        def values(hive, path, names):
            return {"DisplayName": name, "InstallLocation": ""} if path == base + r"\app" else {}
        return patch.object(discovery, "_registry_children", side_effect=children), patch.object(discovery, "_registry_values", side_effect=values)

    def test_msi_software_does_not_claim_msi_hardware_or_sdk_readiness(self):
        children, values = self.software("MSI Center SDK")
        with self.windows(), children, values, patch.object(discovery.shutil, "which", return_value=None):
            result = discovery.detect_msi_environment()
        self.assertTrue(result["software_present"])
        self.assertFalse(result["hardware_present"])
        self.assertNotIn("ready", result)

    def test_afterburner_does_not_count_as_mystic_light_software(self):
        children, values = self.software("MSI Afterburner 4.6")
        with self.windows(), children, values, patch.object(discovery.shutil, "which", return_value=None):
            self.assertFalse(discovery.detect_msi_environment()["software_present"])

    def test_bios_manufacturer_is_independent_hardware_evidence(self):
        def values(hive, path, names):
            return {"BaseBoardManufacturer": "Micro-Star International Co., Ltd."} if path.endswith("BIOS") else {}
        with self.windows(), patch.object(discovery, "_registry_children", return_value=[]), patch.object(discovery, "_registry_values", side_effect=values), patch.object(discovery.shutil, "which", return_value=None):
            result = discovery.detect_msi_environment()
        self.assertFalse(result["software_present"])
        self.assertTrue(result["hardware_present"])
        self.assertEqual(result["hardware"][0]["source"], "bios")

    def test_bios_loose_substring_does_not_claim_msi_hardware(self):
        with self.windows(), patch.object(discovery, "_registry_children", return_value=[]), patch.object(discovery, "_registry_values", return_value={"SystemManufacturer": "NotMSIOtherVendor"}), patch.object(discovery.shutil, "which", return_value=None):
            self.assertFalse(discovery.detect_msi_environment()["hardware_present"])

    def test_current_pci_subsystem_vendor_detects_msi_board_not_chip_vendor(self):
        base = r"SYSTEM\CurrentControlSet\Enum\PCI"
        msi = r"VEN_10DE&DEV_1234&SUBSYS_89771462&REV_A1"
        other = r"VEN_1462&DEV_1234&SUBSYS_89771043&REV_A1"
        def children(hive, path, **kwargs):
            return [msi, other] if path == base else ["instance"] if path == base + "\\" + msi else []
        with self.windows(), patch.object(discovery, "_registry_children", side_effect=children), patch.object(discovery, "_registry_values", return_value={"FriendlyName": "MSI GPU"}), patch.object(discovery, "_device_present", return_value=True):
            result = discovery._msi_hardware()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["subsystem_vendor"], "1462")

    def test_stale_and_phantom_pci_devices_do_not_authorize_download(self):
        base = r"SYSTEM\CurrentControlSet\Enum\PCI"
        msi = r"VEN_10DE&DEV_1234&SUBSYS_89771462"
        def children(hive, path, **kwargs):
            return [msi] if path == base else ["instance"]
        for control, metadata in [(False, {}), (True, {"Phantom": 1}), (True, {"ConfigFlags": 1})]:
            with self.subTest(control=control,metadata=metadata), self.windows(), patch.object(discovery, "_registry_children", side_effect=children), patch.object(discovery, "_registry_values", return_value=metadata), patch.object(discovery, "_device_present", return_value=control):
                self.assertEqual(discovery._msi_hardware(), [])

    def test_linux_is_openrgb_only_without_registry_reads(self):
        platform = SimpleNamespace(name="posix")
        with patch.object(discovery,"os",platform), patch.object(discovery,"_registry_values") as registry, patch.object(discovery.shutil,"which",return_value="/usr/bin/openrgb"), patch.object(discovery,"_is_file",return_value=True):
            result = discovery.discover_pc_setup()
            environment = discovery.detect_msi_environment()
        registry.assert_not_called()
        self.assertEqual(set(result["software"]), {"openrgb"})
        self.assertEqual(result["recommendations"][0]["status"], "detected")
        self.assertFalse(environment["hardware_present"])

    def test_known_executable_detected_without_registry_entry(self):
        root = Path("C:/Program Files")
        with self.windows(), patch.object(discovery,"_registry_children",return_value=[]), patch.object(discovery,"_program_roots",return_value=[root]), patch.object(discovery,"_is_file",side_effect=lambda p:str(p).replace('\\','/').endswith('/OpenRGB/OpenRGB.exe')), patch.object(discovery.shutil,"which",return_value=None):
            result = discovery._installed_windows_software()["openrgb"]
        self.assertTrue(result["installed"])
        self.assertTrue(result["executable_available"])
        self.assertFalse(result["registered"])

    def test_only_relevant_missing_software_is_recommended(self):
        with self.windows(), patch.object(discovery,"_registry_children",return_value=[]), patch.object(discovery,"_registry_values",return_value={}), patch.object(discovery.shutil,"which",return_value=None):
            result = discovery.discover_pc_setup()
        recommendations = {item["id"]:item["status"] for item in result["recommendations"]}
        self.assertEqual(recommendations, {"openrgb":"missing","icue":"not_needed","msi":"not_needed"})

