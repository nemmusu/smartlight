"""Read-only evidence for automatic PC lighting setup.

Installed software is never treated as proof of compatible hardware. Detection
does not load vendor libraries, start applications, download files or write LEDs.
Actual lighting availability is determined separately by the PC controller.
"""
from __future__ import annotations

import os
import ctypes
from pathlib import Path
import re
import shutil

try:
    import winreg
except ImportError:  # Linux uses OpenRGB only.
    winreg = None

URLS = {
    "openrgb": "https://openrgb.org/releases.html",
    "icue": "https://www.corsair.com/icue",
    "msi": "https://www.msi.com/Landing/MSI-Center",
}
_UNINSTALL = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
)


def _registry_values(root: str, path: str, names: tuple[str, ...]) -> dict:
    if winreg is None:
        return {}
    try:
        hive = getattr(winreg, root)
        with winreg.OpenKey(hive, path) as key:
            result = {}
            for name in names:
                try:
                    result[name] = winreg.QueryValueEx(key, name)[0]
                except OSError:
                    pass
            return result
    except (OSError, AttributeError):
        return {}


def _registry_children(root: str, path: str, limit: int = 4096) -> list[str]:
    if winreg is None:
        return []
    try:
        with winreg.OpenKey(getattr(winreg, root), path) as key:
            result = []
            for index in range(limit):
                try:
                    result.append(winreg.EnumKey(key, index))
                except OSError:
                    break
            return result
    except (OSError, AttributeError):
        return []


def _registry_exists(root: str, path: str) -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(getattr(winreg, root), path):
            return True
    except (OSError, AttributeError):
        return False


def _is_file(path) -> bool:
    try:
        return bool(path) and Path(path).is_file()
    except (OSError, ValueError):
        return False


def _device_present(bus: str, device: str, instance: str) -> bool:
    """Read the current PnP tree without opening a driver or changing its state.

    Microsoft CM_LOCATE_DEVNODE_NORMAL (0) excludes nonpresent device nodes:
    https://learn.microsoft.com/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_locate_devnodew
    Registry Enum keys alone can survive unplugging a device.
    """
    try:
        library = ctypes.WinDLL("cfgmgr32", use_last_error=True)
        locate = library.CM_Locate_DevNodeW
        locate.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_wchar_p, ctypes.c_uint32]
        locate.restype = ctypes.c_uint32
        node = ctypes.c_uint32()
        return locate(ctypes.byref(node), bus + "\\" + device + "\\" + instance, 0) == 0
    except (AttributeError, OSError):
        return _registry_exists("HKEY_LOCAL_MACHINE", r"SYSTEM\CurrentControlSet\Enum" + "\\" + bus + "\\" + device + "\\" + instance + r"\Control")


def _program_roots() -> list[Path]:
    result = []
    for name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = os.environ.get(name)
        if value and Path(value).is_absolute() and Path(value) not in result:
            result.append(Path(value))
    return result


def _installed_windows_software() -> dict:
    records = {key: {"installed": False, "registered": False, "executable_available": False,
                     "executable": None, "evidence": [], "url": URLS[key]}
               for key in URLS}
    patterns = {
        "openrgb": re.compile(r"\bopenrgb\b", re.I),
        "icue": re.compile(r"\bicue\b|corsair\s+icue", re.I),
        "msi": re.compile(r"(?:MSI\s*Center|Dragon\s*Center|Mystic\s*Light|One\s*Dragon\s*Center)", re.I),
    }
    filenames = {"openrgb": ("OpenRGB.exe",), "icue": ("iCUE.exe",),
                 "msi": ("MSI.CentralServer.exe", "MSI.CentralServer.WindowsService.exe",
                         "MSI Center.exe", "Dragon Center.exe", "MysticLight.exe")}
    for hive in ("HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER"):
        for base in _UNINSTALL:
            for child in _registry_children(hive, base):
                values = _registry_values(hive, base + "\\" + child,
                                          ("DisplayName", "InstallLocation", "DisplayIcon"))
                name = str(values.get("DisplayName", ""))
                for family, pattern in patterns.items():
                    if not pattern.search(name):
                        continue
                    record = records[family]
                    record["registered"] = record["installed"] = True
                    if name not in record["evidence"]:
                        record["evidence"].append(name)
                    location = str(values.get("InstallLocation") or "").strip().strip('"')
                    candidates = [Path(location) / filename for filename in filenames[family]] if location else []
                    icon = str(values.get("DisplayIcon") or "").strip()
                    # DisplayIcon can contain a quoted path and resource index.
                    match = re.match(r'^"([^\"]+\.exe)"(?:,.*)?$|^(.+\.exe)(?:,\s*-?\d+)?$', icon, re.I)
                    if match:
                        candidates.append(Path(match.group(1) or match.group(2)))
                    for candidate in candidates:
                        if candidate.is_absolute() and _is_file(candidate):
                            record["executable_available"] = True
                            record["executable"] = str(candidate)
                            break
    relative = {
        "openrgb": ("OpenRGB/OpenRGB.exe", "Programs/OpenRGB/OpenRGB.exe"),
        "icue": ("Corsair/CORSAIR iCUE5 Software/iCUE.exe", "Corsair/CORSAIR iCUE4 Software/iCUE.exe",
                 "Corsair/CORSAIR iCUE Software/iCUE.exe"),
        "msi": ("MSI/MSI Center/MSI.CentralServer.exe", "MSI/Dragon Center/Dragon Center.exe",
                "MSI/One Dragon Center/MSI.CentralServer.exe", "MSI/Mystic Light/MysticLight.exe"),
    }
    for family, paths in relative.items():
        record = records[family]
        for root in _program_roots():
            for relative_path in paths:
                candidate = root / relative_path
                if _is_file(candidate):
                    record.update(installed=True, executable_available=True, executable=str(candidate))
                    if str(candidate) not in record["evidence"]:
                        record["evidence"].append(str(candidate))
        if family == "openrgb":
            executable = shutil.which("OpenRGB.exe") or shutil.which("openrgb")
            if executable and _is_file(executable):
                record.update(installed=True, executable_available=True, executable=executable)
                record["evidence"].append(executable)
    return records


def _msi_hardware() -> list[dict]:
    evidence = []
    bios = _registry_values("HKEY_LOCAL_MACHINE", r"HARDWARE\DESCRIPTION\System\BIOS",
                            ("BaseBoardManufacturer", "SystemManufacturer"))
    # Restrict to manufacturer names, never model names, software or loose 'msi' substrings.
    for field, value in bios.items():
        manufacturer = str(value).strip()
        normalized = re.sub(r"[^a-z0-9]", "", manufacturer.casefold())
        if normalized in {"msi", "microstarinternational", "microstarinternationalcoltd", "microstarinternationalco"}:
            evidence.append({"source": "bios", "field": field, "manufacturer": manufacturer})
    base = r"SYSTEM\CurrentControlSet\Enum\PCI"
    for device in _registry_children("HKEY_LOCAL_MACHINE", base):
        # MSI PCI subsystem vendor 1462 is the final four digits of SUBSYS.
        # VEN_10DE/8086 identifies the chip designer, not the board manufacturer.
        if not re.search(r"(?:^|&)SUBSYS_[0-9A-F]{4}1462(?:&|$)", device, re.I):
            continue
        device_path = base + "\\" + device
        for instance in _registry_children("HKEY_LOCAL_MACHINE", device_path, limit=64):
            path = device_path + "\\" + instance
            values = _registry_values("HKEY_LOCAL_MACHINE", path, ("Phantom", "ConfigFlags", "FriendlyName", "DeviceDesc"))
            # Stale/disconnected registry entries alone must not authorize SDK downloads.
            # Check the current Windows PnP tree, not merely an old Enum entry.
            try:
                removed = int(values.get("ConfigFlags", 0)) & 0x1
            except (TypeError, ValueError):
                removed = True
            if values.get("Phantom") == 1 or removed:
                continue
            if not _device_present("PCI", device, instance):
                continue
            evidence.append({"source": "pci", "subsystem_vendor": "1462",
                             "device": str(values.get("FriendlyName") or values.get("DeviceDesc") or device),
                             "id": device})
            break
    return evidence


def _corsair_hardware() -> list[dict]:
    """A currently enumerated Corsair USB device is useful iCUE evidence."""
    result = []
    base = r"SYSTEM\CurrentControlSet\Enum\USB"
    for device in _registry_children("HKEY_LOCAL_MACHINE", base):
        if not re.search(r"(?:^|&)VID_1B1C(?:&|$)", device, re.I):
            continue
        path = base + "\\" + device
        for instance in _registry_children("HKEY_LOCAL_MACHINE", path, limit=64):
            instance_path = path + "\\" + instance
            values = _registry_values("HKEY_LOCAL_MACHINE", instance_path, ("Phantom", "FriendlyName", "DeviceDesc"))
            if values.get("Phantom") == 1 or not _device_present("USB", device, instance):
                continue
            result.append({"source": "usb", "vendor": "1B1C", "id": device,
                           "device": str(values.get("FriendlyName") or values.get("DeviceDesc") or "Corsair USB")})
            break
    return result


def detect_msi_environment() -> dict:
    """Return independent software and hardware evidence; never assert SDK readiness."""
    if os.name != "nt":
        return {"software_present": False, "hardware_present": False, "software": [], "hardware": [],
                "details": ["Linux uses OpenRGB only"]}
    software = _installed_windows_software()["msi"]
    hardware = _msi_hardware()
    return {"software_present": software["installed"], "hardware_present": bool(hardware),
            "software": software["evidence"], "hardware": hardware,
            "details": [*software["evidence"], *[item.get("manufacturer") or item.get("device", "") for item in hardware]]}


def discover_pc_setup() -> dict:
    """Software prerequisites; the service adds live backend/device availability."""
    if os.name != "nt":
        executable = shutil.which("openrgb") or shutil.which("OpenRGB")
        if not executable:
            # Match the portable Linux locations supported by the OpenRGB backend.
            candidates = [Path("/usr/bin/openrgb"), Path("/usr/local/bin/openrgb"),
                          Path("/var/lib/flatpak/exports/bin/org.openrgb.OpenRGB")]
            for root, pattern in ((Path("/opt"), "OpenRGB*/OpenRGB*.AppImage"),
                                  (Path.home(), "OpenRGB*/OpenRGB*.AppImage"),
                                  (Path.home() / "Applications", "OpenRGB*.AppImage")):
                try:
                    candidates.extend(root.glob(pattern))
                except OSError:
                    pass
            executable = next((str(candidate) for candidate in candidates if _is_file(candidate)), None)
        installed = bool(executable and _is_file(executable))
        software = {"openrgb": {"installed": installed, "registered": False,
                               "executable_available": installed, "executable": executable,
                               "evidence": [executable] if installed else [], "url": URLS["openrgb"]}}
        recommendations = [{"id": "openrgb", "status": "detected" if installed else "missing",
                            "url": URLS["openrgb"]}]
        return {"platform": "linux", "automatic": True, "software": software,
                "hardware": {"msi": []}, "recommendations": recommendations,
                "notes": ["Linux uses OpenRGB only, including Corsair devices"]}
    software = _installed_windows_software()
    hardware = _msi_hardware()
    corsair = _corsair_hardware()
    recommendations = []
    for family, record in software.items():
        status = "detected" if record["installed"] else "missing" if family == "openrgb" else "not_needed"
        if family == "msi" and hardware and not record["installed"]:
            status = "missing"
        if family == "icue" and corsair and not record["installed"]:
            status = "missing"
        recommendations.append({"id": family, "status": status, "url": URLS[family]})
    return {"platform": "windows", "automatic": True, "software": software,
            "hardware": {"msi": hardware, "corsair": corsair}, "recommendations": recommendations,
            "notes": ["Installed software does not prove compatible RGB hardware",
                      "Lighting readiness is confirmed only by backend discovery"]}
