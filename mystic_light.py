"""Windows MSI Mystic Light SDK adapter (EXPERIMENTAL, no hardware validation).

No MSI DLL is distributed. Native calls run in a disposable subprocess. The
integration discovers native styles and optional controls per SDK zone;
software frames use static zones and native controls use reported ranges. It is a
fallback when OpenRGB/iCUE discover zero lights, never a simultaneous writer.
SDK reference: https://storage-asset.msi.com/files/pdf/Mystic_Light_Software_Development_Kit.pdf
"""
from __future__ import annotations

import atexit
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile

from legacy_hwlight.backends import Light

MAX_ZONES = 256
STATIC_STYLES = {"no animation", "steady", "static", "static color"}
SDK_EXPORTS = {"MLAPI_Initialize", "MLAPI_Release", "MLAPI_GetDeviceInfo", "MLAPI_GetLedInfo",
               "MLAPI_SetLedStyle", "MLAPI_SetLedColor", "MLAPI_GetLedMaxBright", "MLAPI_SetLedBright"}
SDK_URL = "https://download-2.msi.com/uti_exe/Mystic_light_SDK.zip"
SDK_ARCHIVE_SHA256 = "799f06c8cbaba8854d6b30883c3e15c2d992c0a86130427fdc7df5f5f2dc7307"
SDK_VERSION = "1.0.0.08"
SDK_FILES = {
    8: ("MysticLight_SDK_x64.dll", "ad1bd5a464c120f086839631cf9cb7a56e8e7373209158e66c628a89be06d166"),
    4: ("MysticLight_SDK.dll", "e95d541746ed036b1d5ba3e37f401e69aba498e2e1303002ad250cf19c51158f"),
}
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024


class MysticError(RuntimeError):
    pass


def validate_dll(path: str, platform: str | None = None) -> Path:
    if (platform or os.name) != "nt":
        raise MysticError("MSI Mystic Light SDK is available on Windows only")
    value = Path(path)
    if not path or not value.is_absolute() or value.suffix.lower() != ".dll":
        raise MysticError("Choose an absolute path to the official MSI SDK DLL")
    value = value.resolve(strict=True)
    if not 64 <= value.stat().st_size <= 128 * 1024 * 1024:
        raise MysticError("Invalid MSI SDK DLL file size")
    with value.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise MysticError("Invalid MSI SDK DLL: missing PE header")
        stream.seek(60)
        offset = struct.unpack("<I", stream.read(4))[0]
        if offset > 16 * 1024 * 1024:
            raise MysticError("Invalid MSI SDK DLL header")
        stream.seek(offset)
        if stream.read(4) != b"PE\0\0":
            raise MysticError("Invalid MSI SDK DLL: missing PE signature")
        machine = struct.unpack("<H", stream.read(2))[0]
    expected = 0x8664 if struct.calcsize("P") == 8 else 0x14c
    if machine != expected:
        raise MysticError("MSI SDK DLL architecture does not match Smartlight")
    _validate_exports(value)
    return value


def _validate_exports(path):
    """Read PE export names before executing a library; no heuristic byte search."""
    data = path.read_bytes()
    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise MysticError("Invalid MSI SDK DLL export table")
        return struct.unpack_from(fmt, data, offset)
    pe, = unpack("<I", 60)
    sections, = unpack("<H", pe + 6)
    optional_size, = unpack("<H", pe + 20)
    magic, = unpack("<H", pe + 24)
    if magic not in (0x10b, 0x20b) or sections > 128:
        raise MysticError("Invalid MSI SDK DLL PE format")
    export_rva, export_size = unpack("<II", pe + 24 + (112 if magic == 0x20b else 96))
    section_start = pe + 24 + optional_size
    def offset(rva):
        for index in range(sections):
            size, virtual, raw_size, raw = unpack("<IIII", section_start + index * 40 + 8)
            if virtual <= rva < virtual + min(size or raw_size, raw_size):
                value = raw + rva - virtual
                if value < len(data):
                    return value
        raise MysticError("Invalid MSI SDK DLL export address")
    if not export_rva or not export_size:
        raise MysticError("DLL does not export the MSI Mystic Light SDK API")
    directory = offset(export_rva)
    count, = unpack("<I", directory + 24)
    names_rva, = unpack("<I", directory + 32)
    if count > 8192:
        raise MysticError("Invalid MSI SDK DLL export count")
    names, table = set(), offset(names_rva)
    for index in range(count):
        name_rva, = unpack("<I", table + index * 4)
        begin = offset(name_rva)
        end = data.find(b"\0", begin, begin + 256)
        if end < 0:
            raise MysticError("Invalid MSI SDK DLL export name")
        names.add(data[begin:end].decode("ascii", "replace"))
    if SDK_EXPORTS - names:
        raise MysticError("DLL is missing required MSI SDK exports: " + ", ".join(sorted(SDK_EXPORTS - names)))


def discover_sdk(explicit=""):
    """Search bounded official MSI install locations, never PATH or working dir."""
    if explicit:
        return validate_dll(explicit)
    if os.name != "nt":
        raise MysticError("MSI Mystic Light SDK is available on Windows only")
    names = ["MysticLight_SDK_x64.dll", "MysticLight_SDK.dll"] if struct.calcsize("P") == 8 else ["MysticLight_SDK.dll"]
    relative = ("MSI/Mystic Light", "MSI/MysticLight", "MSI/Mystic Light SDK",
                "MSI/MSI Center/Mystic Light", "MSI/MSI Center/MysticLight",
                "MSI/Dragon Center/Mystic Light", "MSI/One Dragon Center/Mystic_Light")
    invalid = []
    for environment in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(environment)
        if not root or not Path(root).is_absolute():
            continue
        for location in relative:
            for name in names:
                candidate = Path(root) / location / name
                if candidate.is_file():
                    try:
                        return validate_dll(str(candidate))
                    except (MysticError, OSError, ValueError, struct.error) as exc:
                        invalid.append(str(exc))
    if invalid:
        raise MysticError("No usable official MSI SDK DLL found: " + invalid[0])
    raise MysticError("MSI SDK DLL not found. Install MSI Center with Mystic Light, download the official MSI SDK, then select its matching DLL in Settings. Installing MSI software alone does not prove compatible hardware is present.")


def _check_download_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in {"download.msi.com", "download-2.msi.com"}
            or parsed.username or parsed.password or parsed.port not in {None, 443}):
        raise MysticError("MSI SDK download redirected outside the official HTTPS download service")


class _OfficialMsiRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        _check_download_url(url)
        return super().redirect_request(request, response, code, message, headers, url)


def download_sdk_archive():
    """Bounded first-party HTTPS download; archive content is pinned separately."""
    _check_download_url(SDK_URL)
    request = urllib.request.Request(SDK_URL, headers={"User-Agent": "Smartlight-MSI-integration/1", "Accept": "application/zip"})
    deadline = time.monotonic() + 20
    opener = urllib.request.build_opener(_OfficialMsiRedirect())
    with opener.open(request, timeout=6) as response:
        _check_download_url(response.geturl())
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise MysticError("Official MSI SDK archive exceeds the download size limit")
        chunks, size = [], 0
        while True:
            if time.monotonic() > deadline:
                raise MysticError("Official MSI SDK download timed out")
            chunk = response.read(min(65536, MAX_DOWNLOAD_BYTES - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise MysticError("Official MSI SDK archive exceeds the download size limit")
            chunks.append(chunk)
        return b"".join(chunks)


def provision_sdk(directory, evidence):
    """Install only the pinned SDK DLL for this process, never vendor services/drivers."""
    if os.name != "nt":
        raise MysticError("MSI Mystic Light SDK is available on Windows only")
    if not evidence.get("software_present"):
        raise MysticError("MSI Mystic Light software is missing. Install MSI Center with Mystic Light from MSI, then search again.")
    filename, expected = SDK_FILES[struct.calcsize("P")]
    cache = Path(directory).resolve() / "vendor" / "msi" / SDK_VERSION
    target = cache / filename
    if target.is_file():
        if target.stat().st_size <= MAX_DOWNLOAD_BYTES and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            return validate_dll(str(target))
        # A corrupt/tampered cached file is never loaded or silently trusted.
    if not evidence.get("hardware_present"):
        raise MysticError("MSI software was found, but MSI hardware was not identified. Automatic SDK download was skipped; no compatible light has been confirmed.")
    archive_bytes = download_sdk_archive()
    if (len(archive_bytes) > MAX_DOWNLOAD_BYTES
            or hashlib.sha256(archive_bytes).hexdigest() != SDK_ARCHIVE_SHA256):
        raise MysticError("Official MSI SDK archive changed or failed verification. No DLL was installed; update Smartlight before retrying.")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        # Read an exact, pinned member into memory. Never extract arbitrary ZIP paths.
        member = archive.getinfo(f"Mystic_light_SDK_{SDK_VERSION}/{filename}")
        if member.file_size > MAX_DOWNLOAD_BYTES:
            raise MysticError("Invalid MSI SDK DLL size in official archive")
        content = archive.read(member)
    if hashlib.sha256(content).hexdigest() != expected:
        raise MysticError("Official MSI SDK DLL failed integrity verification")
    cache.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix="sdk-", suffix=".dll", dir=cache)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        validate_dll(str(temporary))
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def _rgb(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(type(c) is not int or not 0 <= c <= 255 for c in value)):
        raise MysticError("RGB must contain three integers between 0 and 255")
    return tuple(value)


def _automation():
    # OleDLL treats every return value as HRESULT, corrupting BSTR/pointer
    # results on 64-bit Python. WinDLL plus explicit signatures is required.
    ole = ctypes.WinDLL("oleaut32")
    ptr = ctypes.c_void_p
    ole.SysAllocString.argtypes = [ctypes.c_wchar_p]
    ole.SysAllocString.restype = ptr
    ole.SysFreeString.argtypes = [ptr]
    ole.SysFreeString.restype = None
    ole.SafeArrayGetDim.argtypes = [ptr]
    ole.SafeArrayGetDim.restype = ctypes.c_uint
    ole.SafeArrayGetLBound.argtypes = [ptr, ctypes.c_uint, ctypes.POINTER(ctypes.c_long)]
    ole.SafeArrayGetUBound.argtypes = [ptr, ctypes.c_uint, ctypes.POINTER(ctypes.c_long)]
    ole.SafeArrayGetVartype.argtypes = [ptr, ctypes.POINTER(ctypes.c_ushort)]
    ole.SafeArrayGetElement.argtypes = [ptr, ctypes.POINTER(ctypes.c_long), ptr]
    ole.SafeArrayDestroy.argtypes = [ptr]
    return ole


class NativeSdk:
    """The only class loading the DLL; instantiate exclusively inside the worker."""

    def __init__(self, path):
        path = validate_dll(str(path))
        self._directory = os.add_dll_directory(str(path.parent))
        # The official MSI C# sample explicitly declares CallingConvention.Cdecl.
        self.dll = ctypes.CDLL(str(path), winmode=0x00000100 | 0x00001000)
        self.ole = _automation()
        ptr = ctypes.c_void_p
        self._bind("Initialize", [])
        self._bind("Release", [])
        self._bind("GetDeviceInfo", [ctypes.POINTER(ptr), ctypes.POINTER(ptr)])
        self._bind("GetLedInfo", [ptr, ctypes.c_uint32, ctypes.POINTER(ptr), ctypes.POINTER(ptr)])
        self._bind("SetLedStyle", [ptr, ctypes.c_uint32, ptr])
        self._bind("SetLedColor", [ptr, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32])
        self._bind("GetLedMaxBright", [ptr, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)])
        self._bind("SetLedBright", [ptr, ctypes.c_uint32, ctypes.c_uint32])
        for name in ("GetLedMaxSpeed", "GetLedSpeed", "GetLedBright"):
            self._bind_optional(name, [ptr, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)])
        self._bind_optional("SetLedSpeed", [ptr, ctypes.c_uint32, ctypes.c_uint32])
        self._bind_optional("GetLedStyle", [ptr, ctypes.c_uint32, ctypes.POINTER(ptr)])
        self._bind_optional("GetLedColor", [ptr, ctypes.c_uint32] + [ctypes.POINTER(ctypes.c_uint32)] * 3)
        self._bind_optional("GetLedName", [ptr, ctypes.POINTER(ptr)])
        self._bind_optional("SetLedColorEx", [ptr, ctypes.c_uint32, ptr] + [ctypes.c_uint32] * 4)
        self._check(self.dll.MLAPI_Initialize(), "Initialize")

    def _bind(self, name, args):
        fn = getattr(self.dll, "MLAPI_" + name)
        fn.argtypes, fn.restype = args, ctypes.c_int

    def _bind_optional(self, name, args):
        if hasattr(self.dll, "MLAPI_" + name):
            self._bind(name, args)

    def _level(self, token, index, name):
        fn = getattr(self.dll, "MLAPI_" + name, None)
        if fn is None:
            return None
        value = ctypes.c_uint32()
        code = fn(token, index, ctypes.byref(value))
        if code in (-103, -3):
            return None
        self._check(code, name)
        return value.value

    @staticmethod
    def _check(code, operation):
        if code:
            raise MysticError(f"MSI SDK {operation} failed ({code}); check MSI Center/Mystic Light installation")

    def _array(self, pointer):
        if not pointer:
            return []
        try:
            if self.ole.SafeArrayGetDim(pointer) != 1:
                raise MysticError("Unsupported MSI SDK array dimensions")
            lower, upper, kind = ctypes.c_long(), ctypes.c_long(), ctypes.c_ushort()
            self._check(self.ole.SafeArrayGetLBound(pointer, 1, ctypes.byref(lower)), "array lower bound")
            self._check(self.ole.SafeArrayGetUBound(pointer, 1, ctypes.byref(upper)), "array upper bound")
            self._check(self.ole.SafeArrayGetVartype(pointer, ctypes.byref(kind)), "array type")
            if not 0 <= upper.value - lower.value + 1 <= MAX_ZONES:
                raise MysticError("Invalid MSI SDK array size")
            if kind.value not in {8, 3, 19}:  # VT_BSTR, VT_I4, VT_UI4
                raise MysticError(f"Unsupported MSI SDK array type ({kind.value})")
            result = []
            for index in range(lower.value, upper.value + 1):
                slot = ctypes.c_void_p() if kind.value == 8 else ctypes.c_uint32()
                self._check(self.ole.SafeArrayGetElement(pointer, ctypes.byref(ctypes.c_long(index)), ctypes.byref(slot)), "array element")
                if kind.value == 8:
                    try:
                        result.append(ctypes.wstring_at(slot.value) if slot.value else "")
                    finally:
                        self.ole.SysFreeString(slot)
                else:
                    result.append(slot.value)
            return result
        finally:
            self.ole.SafeArrayDestroy(pointer)

    def devices(self):
        types, counts = ctypes.c_void_p(), ctypes.c_void_p()
        code = self.dll.MLAPI_GetDeviceInfo(ctypes.byref(types), ctypes.byref(counts))
        if code:
            if types: self.ole.SafeArrayDestroy(types)
            if counts: self.ole.SafeArrayDestroy(counts)
            self._check(code, "GetDeviceInfo")
        try:
            device_types = self._array(types)
        except Exception:
            if counts: self.ole.SafeArrayDestroy(counts)
            raise
        device_counts = self._array(counts)
        if len(device_types) != len(device_counts):
            raise MysticError("MSI SDK returned inconsistent device counts")
        result = []
        for device_type, count in zip(device_types, device_counts):
            count = int(count)
            if not isinstance(device_type, str) or not 0 <= count <= MAX_ZONES:
                raise MysticError("Invalid MSI SDK device metadata")
            led_names = {}
            names_fn = getattr(self.dll, "MLAPI_GetLedName", None)
            if names_fn is not None and hasattr(self.dll, "MLAPI_SetLedColorEx"):
                token, names = self.ole.SysAllocString(device_type), ctypes.c_void_p()
                try:
                    code = names_fn(token, ctypes.byref(names))
                    if code == 0:
                        for item in self._array(names):
                            if not isinstance(item, str):
                                continue
                            area, separator, name = item.partition(":")
                            if separator and area.isdecimal() and name and 0 <= int(area) < count:
                                led_names.setdefault(int(area), []).append(name)
                    elif names:
                        self.ole.SafeArrayDestroy(names)
                finally:
                    self.ole.SysFreeString(token)
            for index in range(count):
                name, styles = ctypes.c_void_p(), ctypes.c_void_p()
                token = self.ole.SysAllocString(device_type)
                try:
                    code = self.dll.MLAPI_GetLedInfo(token, index, ctypes.byref(name), ctypes.byref(styles))
                finally:
                    self.ole.SysFreeString(token)
                try:
                    label = ctypes.wstring_at(name.value) if name.value else f"{device_type} {index + 1}"
                finally:
                    self.ole.SysFreeString(name)
                if code:
                    if styles: self.ole.SafeArrayDestroy(styles)
                    continue  # An unsupported zone must not hide other zones.
                available = self._array(styles)
                steady = next((s for s in available if isinstance(s, str) and s.casefold() in STATIC_STYLES), None)
                direct = next((s for s in available if isinstance(s, str) and s.casefold() == "direct lighting control"), None)
                mapped_names = list(dict.fromkeys(led_names.get(index, []))) if direct else []
                if mapped_names:
                    steady = direct
                if available:
                    token = self.ole.SysAllocString(device_type)
                    maximum = ctypes.c_uint32()
                    try:
                        bright_code = self.dll.MLAPI_GetLedMaxBright(token, index, ctypes.byref(maximum))
                        max_speed = self._level(token, index, "GetLedMaxSpeed")
                    finally:
                        self.ole.SysFreeString(token)
                    result.append({"type": device_type, "index": index, "name": label, "style": steady,
                                   "styles": list(dict.fromkeys(s for s in available if isinstance(s, str) and s)),
                                   "max_speed": max_speed if hasattr(self.dll, "MLAPI_SetLedSpeed") else None,
                                   "max_brightness": maximum.value if bright_code == 0 else None,
                                   "led_names": mapped_names,
                                   "supports_software_effects": bool(steady)})
                if len(result) > MAX_ZONES:
                    raise MysticError("Too many MSI SDK zones")
        return result

    def set_color(self, zone, color, prepare=False):
        color = _rgb(color)
        if not zone.get("style"):
            raise MysticError("This MSI zone does not advertise a static style for software colors or animations")
        token = self.ole.SysAllocString(zone["type"])
        try:
            if prepare:
                style = self.ole.SysAllocString(zone["style"])
                try:
                    self._check(self.dll.MLAPI_SetLedStyle(token, zone["index"], style), "SetLedStyle")
                finally:
                    self.ole.SysFreeString(style)
                maximum = (self._level(token, zone["index"], "GetLedMaxBright")
                           if hasattr(self.dll, "MLAPI_GetLedMaxBright") else zone.get("max_brightness"))
                if maximum is not None and maximum > 0:
                    self._check(self.dll.MLAPI_SetLedBright(token, zone["index"], maximum), "SetLedBright")
            self._check(self.dll.MLAPI_SetLedColor(token, zone["index"], *color), "SetLedColor")
        finally:
            self.ole.SysFreeString(token)

    def set_frame(self, zone, colors, prepare=False):
        names = zone.get("led_names", [])
        if not names:
            if len(colors) != 1:
                raise MysticError("This MSI zone supports one uniform color")
            return self.set_color(zone, colors[0], prepare)
        if len(colors) != len(names):
            raise MysticError("MSI frame must match the discovered LED names")
        colors = [_rgb(color) for color in colors]
        token = self.ole.SysAllocString(zone["type"])
        try:
            if prepare:
                style = self.ole.SysAllocString(zone["style"])
                try:
                    self._check(self.dll.MLAPI_SetLedStyle(token, zone["index"], style), "SetLedStyle")
                finally:
                    self.ole.SysFreeString(style)
                maximum = self._level(token, zone["index"], "GetLedMaxBright")
                if maximum:
                    self._check(self.dll.MLAPI_SetLedBright(token, zone["index"], maximum), "SetLedBright")
            for i, (name, color) in enumerate(zip(names, colors)):
                led = self.ole.SysAllocString(name)
                try:
                    self._check(self.dll.MLAPI_SetLedColorEx(token, zone["index"], led, *color,
                                                          int(i == len(names) - 1)), "SetLedColorEx")
                finally:
                    self.ole.SysFreeString(led)
        finally:
            self.ole.SysFreeString(token)

    def set_native(self, zone, style, color=None, speed=None, brightness=None,
                   normalized_speed=None, normalized_brightness=None):
        validate_native(zone, style, color, speed, brightness, normalized_speed, normalized_brightness)
        token = self.ole.SysAllocString(zone["type"])
        style_token = self.ole.SysAllocString(style)
        try:
            self._check(self.dll.MLAPI_SetLedStyle(token, zone["index"], style_token), "SetLedStyle")
            result = {"unsupported": [], "max_speed": self._level(token, zone["index"], "GetLedMaxSpeed"),
                      "max_brightness": self._level(token, zone["index"], "GetLedMaxBright")}
            if not hasattr(self.dll, "MLAPI_SetLedSpeed"):
                result["max_speed"] = None
            if color is not None:
                code = self.dll.MLAPI_SetLedColor(token, zone["index"], *_rgb(color))
                if code == -103:
                    result["unsupported"].append("color")
                else:
                    self._check(code, "SetLedColor")
            for name, value, fraction in (("SetLedSpeed", speed, normalized_speed),
                                          ("SetLedBright", brightness, normalized_brightness)):
                if value is not None or fraction is not None:
                    field = "speed" if name == "SetLedSpeed" else "brightness"
                    maximum = result["max_" + field]
                    if maximum is None:
                        result["unsupported"].append(field)
                        continue
                    previous = zone.get("max_" + field)
                    level = (round(fraction * maximum) if fraction is not None else
                             round(value * maximum / previous) if previous else min(value, maximum))
                    code = getattr(self.dll, "MLAPI_" + name)(token, zone["index"], level)
                    if code == -103:
                        result["unsupported"].append(field)
                    else:
                        self._check(code, name)
            return result
        finally:
            self.ole.SysFreeString(style_token)
            self.ole.SysFreeString(token)

    def state(self, zone):
        """Read SDK state, which may describe configured color during animation."""
        token = self.ole.SysAllocString(zone["type"])
        result = {"source": "msi_sdk", "color": None, "style": None,
                  "brightness": None, "speed": None}
        try:
            for field, name in (("brightness", "GetLedBright"), ("speed", "GetLedSpeed")):
                result[field] = self._level(token, zone["index"], name)
            fn = getattr(self.dll, "MLAPI_GetLedStyle", None)
            if fn is not None:
                value = ctypes.c_void_p()
                try:
                    code = fn(token, zone["index"], ctypes.byref(value))
                    if code not in (-103, -3):
                        self._check(code, "GetLedStyle")
                        result["style"] = ctypes.wstring_at(value.value) if value.value else None
                finally:
                    self.ole.SysFreeString(value)
            fn = getattr(self.dll, "MLAPI_GetLedColor", None)
            if fn is not None:
                rgb = [ctypes.c_uint32() for _ in range(3)]
                code = fn(token, zone["index"], *(ctypes.byref(value) for value in rgb))
                if code not in (-103, -3):
                    self._check(code, "GetLedColor")
                    result["color"] = list(_rgb([value.value for value in rgb]))
            return result
        finally:
            self.ole.SysFreeString(token)

    def power_off(self, zone):
        if zone.get("style"):
            if zone.get("led_names"):
                return self.set_frame(zone, [(0, 0, 0)] * len(zone["led_names"]), True)
            return self.set_color(zone, (0, 0, 0), True)
        off = next((s for s in zone.get("styles", []) if s.casefold() in {"off", "disabled", "disable"}), None)
        if off:
            return self.set_native(zone, off)
        token = self.ole.SysAllocString(zone["type"])
        try:
            maximum = self._level(token, zone["index"], "GetLedMaxBright")
            if maximum is None:
                raise MysticError("This MSI zone exposes neither a static/off style nor brightness control for power off")
            self._check(self.dll.MLAPI_SetLedBright(token, zone["index"], 0), "SetLedBright")
        finally:
            self.ole.SysFreeString(token)

    def close(self):
        self.dll.MLAPI_Release()
        self._directory.close()


def validate_native(zone, style, color=None, speed=None, brightness=None,
                    normalized_speed=None, normalized_brightness=None):
    if not isinstance(style, str) or style not in zone.get("styles", [zone.get("style")]):
        raise MysticError("Choose an exact native style advertised by this MSI zone")
    if color is not None:
        _rgb(color)
    for name, value, raw in (("speed", normalized_speed, speed), ("brightness", normalized_brightness, brightness)):
        if value is not None and (type(value) not in (int, float) or not 0 <= value <= 1 or raw is not None):
            raise MysticError(f"Normalized MSI {name} must be between 0 and 1, without a raw value")
    for name, value in (("speed", speed), ("brightness", brightness)):
        maximum = zone.get("max_" + name)
        if value is not None and (type(value) is not int or maximum is None or not 0 <= value <= maximum):
            raise MysticError(f"MSI native {name} must be an integer from 0 to the reported maximum ({maximum})")


def worker_session(sdk, source, destination):
    """JSON boundary is independently testable without loading a vendor library."""
    zones, prepared = [], set()
    try:
        for line in source:
            try:
                request = json.loads(line)
                if request.get("op") == "list":
                    zones = sdk.devices()
                    prepared.clear()
                    result = zones
                elif request.get("op") in {"set", "frame", "native", "state", "off"}:
                    index = request.get("zone")
                    if type(index) is not int or not 0 <= index < len(zones):
                        raise MysticError("Unknown MSI SDK zone")
                    if request["op"] == "state":
                        result = sdk.state(zones[index])
                    elif request["op"] == "off":
                        prepared.discard(index)
                        sdk.power_off(zones[index])
                        result = True
                    elif request["op"] == "native":
                        validate_native(zones[index], request.get("style"), request.get("color"), request.get("speed"), request.get("brightness"), request.get("normalized_speed"), request.get("normalized_brightness"))
                        prepared.discard(index)
                        result = sdk.set_native(zones[index], request["style"], request.get("color"), request.get("speed"), request.get("brightness"),
                                                request.get("normalized_speed"), request.get("normalized_brightness"))
                    elif request["op"] == "frame":
                        colors = request.get("colors")
                        expected = len(zones[index].get("led_names", [])) or 1
                        if not isinstance(colors, list) or len(colors) != expected:
                            raise MysticError("MSI frame must match the discovered LED count")
                        colors = [_rgb(color) for color in colors]
                        sdk.set_frame(zones[index], colors, prepare=index not in prepared)
                        prepared.add(index)
                        result = True
                    else:
                        sdk.set_color(zones[index], _rgb(request.get("color")), prepare=index not in prepared)
                        prepared.add(index)
                        result = True
                elif request.get("op") == "close":
                    break
                else:
                    raise MysticError("Unsupported MSI worker operation")
                response = {"ok": True, "data": result}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            destination.write(json.dumps(response) + "\n")
            destination.flush()
    finally:
        sdk.close()


def worker_main(path):
    try:
        worker_session(NativeSdk(path), sys.stdin, sys.stdout)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 1


class MysticBackend:
    def __init__(self, dll_path="", timeout=5.0, *, directory=None, evidence=None):
        self.dll_path, self.timeout = dll_path, timeout
        self.directory = directory
        self.evidence = evidence or {}
        self.status = "Experimental: not validated on physical MSI hardware"
        self.process = None
        self.failed = False
        self._lock = threading.RLock()
        self._responses = queue.Queue()
        atexit.register(self.close)

    @property
    def healthy(self):
        return self.process is not None and self.process.poll() is None and not self.failed

    def _request(self, request):
        with self._lock:
            if self.process is None or self.process.poll() is not None:
                self.failed = True
                self.status = "Experimental MSI backend stopped: worker is not running; reconnect to retry"
                self.close()
                raise MysticError("MSI SDK worker is not running; reconnect to retry")
            try:
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                line = self._responses.get(timeout=self.timeout)
                if not line:
                    raise MysticError("MSI SDK worker stopped unexpectedly")
                response = json.loads(line)
                if not response.get("ok"):
                    raise MysticError(response.get("error", "MSI SDK error"))
                return response["data"]
            except Exception as exc:
                self.failed = True
                self.status = f"Experimental MSI backend stopped: {exc}"
                self.close()  # Circuit breaker: never retry a failing frame continuously.
                raise MysticError(str(exc) or "MSI SDK worker timed out") from exc

    def connect(self, log=None):
        self.close()
        self.failed = False
        if self.dll_path:
            path = discover_sdk(self.dll_path)
        else:
            if not self.evidence.get("software_present"):
                raise MysticError("MSI Mystic Light software is missing. Install MSI Center with Mystic Light from MSI, then search again.")
            try:
                path = discover_sdk()
            except (MysticError, OSError, ValueError):
                if self.directory is None:
                    raise
                self.status = "Preparing verified official MSI SDK"
                if log:
                    log(self.status)
                path = provision_sdk(self.directory, self.evidence)
        args = worker_command()
        args += ["--mystic-worker", str(path)]
        self._responses = queue.Queue()
        responses = self._responses
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        process = self.process
        def read():
            try:
                for line in process.stdout:
                    responses.put(line)
            finally:
                responses.put(None)
        threading.Thread(target=read, daemon=True, name="mystic-sdk-reader").start()
        zones = self._request({"op": "list"})
        if not isinstance(zones, list) or len(zones) > MAX_ZONES:
            self.close()
            raise MysticError("Invalid MSI SDK zone list")
        self.status = f"Experimental: {len(zones)} SDK zones; physical hardware not validated"
        return [MysticLight(self, index, zone) for index, zone in enumerate(zones)]

    def close(self):
        with self._lock:
            process, self.process = self.process, None
            if process is not None:
                try:
                    if process.poll() is None:
                        try:
                            process.stdin.write('{"op":"close"}\n')
                            process.stdin.flush()
                            process.wait(timeout=0.3)
                        except Exception:
                            process.kill()
                            process.wait(timeout=1)
                finally:
                    for stream in (process.stdin, process.stdout):
                        if stream:
                            stream.close()


class MysticLight(Light):
    def __init__(self, backend, index, zone):
        self.backend, self.index = backend, index
        self.zone = dict(zone)
        self.supports_software_effects = bool(zone.get("style"))
        identity = f"{zone['type']}:{zone['index']}"
        self.key = "mystic:" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        self.name = f"{zone['name']} · MSI experimental"
        self.source = "Mystic Light (experimental)"
        token = zone["type"].upper().removeprefix("MSI_")
        self.kind = next((kind for prefix, kind in (("MB", "MOTHERBOARD"), ("VGA", "GPU"),
                                                  ("DRAM", "RAM"), ("KEYBOARD", "KEYBOARD"),
                                                  ("MOUSE", "MOUSE"), ("HEADSET", "HEADSET"))
                          if token.startswith(prefix)), "UNKNOWN")
        self.led_count = len(zone.get("led_names", [])) or 1

    def set_leds(self, colors):
        if len(colors) != self.led_count:
            raise MysticError("MSI colors must match the discovered LED count")
        if self.zone.get("led_names"):
            self.backend._request({"op": "frame", "zone": self.index, "colors": [list(_rgb(c)) for c in colors]})
        else:
            self.backend._request({"op": "set", "zone": self.index, "color": list(_rgb(colors[0]))})

    def native_effects(self):
        return [{"style": style, "max_speed": self.zone.get("max_speed"),
                 "max_brightness": self.zone.get("max_brightness"), "color": None}
                for style in self.zone.get("styles", [self.zone.get("style")]) if style]

    def set_native_effect(self, style, color=None, speed=None, brightness=None,
                          normalized_speed=None, normalized_brightness=None):
        validate_native(self.zone, style, color, speed, brightness, normalized_speed, normalized_brightness)
        return self.backend._request({"op": "native", "zone": self.index, "style": style,
                                      "color": color, "speed": speed, "brightness": brightness,
                                      "normalized_speed": normalized_speed,
                                      "normalized_brightness": normalized_brightness})

    def get_native_state(self):
        return self.backend._request({"op": "state", "zone": self.index})

    def off(self):
        return self.backend._request({"op": "off", "zone": self.index})


def worker_command():
    if not getattr(sys, "frozen", False):
        return [sys.executable, str(Path(__file__).with_name("app.py"))]
    # The desktop executable is built --windowed and cannot provide Python
    # stdin/stdout. Use our bundled console executable, with dedicated early
    # worker dispatch, rather than recovering opaque CRT handles in the GUI.
    current = Path(sys.executable)
    worker = (current if current.name.casefold() == "smartlight-mcp.exe"
              else current.parent.parent / "Smartlight-MCP" / "Smartlight-MCP.exe")
    if not worker.is_file():
        raise MysticError("MSI SDK worker executable is missing. Repair or reinstall Smartlight to restore Smartlight-MCP.exe")
    return [str(worker)]
