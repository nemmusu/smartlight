# Smartlight — Tapo & PC RGB control for Windows and Linux

**Your room, your PC, one place to control the lights.**

[Italiano](README.it.md) · [Download](https://github.com/nemmusu/smartlight/releases/latest) · [Getting started](FIRST_RUN.md) · [Linux setup](LINUX.md) · [Compatibility](docs/COMPATIBILITY.md)

Smartlight brings TP-Link Tapo smart lights and PC RGB lighting into one desktop app, with rooms, effects, schedules and an MCP server for AI assistants. The interface starts in **English**. Switch between **English and Italiano** anytime in **Settings → General → Language**; your choice is saved.

![Smartlight workspace with demonstration devices](docs/screenshots/workspace-en.png)

## What you can do

- Control a single light, a selection, a room or all lights, with clear targets.
- Set colors, white temperature and brightness where supported.
- Save presets and scenes; adjust animation speed and brightness range.
- Use native Tapo effects on supported models and shared PC/Tapo animations.
- Schedule actions with a calendar, weekdays and time controls; use timers or presence simulation.
- Keep UI and MCP on the same controller, with periodic refresh of Tapo changes made outside Smartlight.
- Control lights from the tray, including PC lights and Tapo separately.
- Connect AI assistants through local stdio or authenticated Streamable HTTP MCP.
- Export and import configurations without Tapo credentials.

## Compatibility at a glance

| Integration | Windows | Linux | Status |
| --- | --- | --- | --- |
| Tapo over the local network | Yes | Yes | Tested with L530 and L900 family devices; capabilities vary by model/firmware |
| OpenRGB SDK | Yes | Yes | Supported devices depend on OpenRGB and the installed hardware |
| Corsair iCUE SDK | Yes | No | Automatic selection can use OpenRGB if iCUE finds no devices; Linux uses OpenRGB |
| MSI Mystic Light SDK | Experimental | No | Automatic fallback when the usual integrations find no PC lights; no physical MSI validation yet |

An OpenRGB catalog entry is **not** a claim that the model was individually tested with Smartlight. See [compatibility and experimental support](docs/COMPATIBILITY.md) for details.

## Get started

1. Install the package for your system, or follow [source setup](FIRST_RUN.md).
2. Keep **Automatic** selected for PC lights. Smartlight detects available hardware and lighting software and shows any missing prerequisite with its official installation link.
3. Enter your Tapo account in Settings, discover lights on your local network and create rooms.
4. Pick a room or device, then choose a color, preset or effect.

Get the latest version from [GitHub Releases](https://github.com/nemmusu/smartlight/releases/latest): **Windows** `Smartlight-Setup-0.4.1.exe` or **Linux** `Smartlight_0.4.1_amd64.deb`. The Debian package targets a Python 3.12 system; see [Linux requirements](LINUX.md).

## PC lighting setup

Keep **Automatic** selected: Smartlight detects available hardware and lighting software and shows any missing component with its official setup link. You can also choose **OpenRGB**, **iCUE** or **MSI Mystic Light** on Windows, or **OpenRGB** on Linux. Use **Apply and restart** after changing the selection.

“Ready” means actual controllable lights were detected. The experimental MSI integration can acquire its verified official SDK automatically when the required hardware and software are present; no DLL selection is needed. Vendor software may still require its own guided installation. [Setup details and MSI limits](docs/MYSTIC_LIGHT.md).

## A closer look

| Effects & presets | Schedules |
| --- | --- |
| ![Effects and presets](docs/screenshots/effects-en.png) | ![Schedule controls](docs/screenshots/schedules-en.png) |

Screenshots use simulated devices and demonstration configurations.

## AI assistant control (MCP)

Open Settings → MCP assistants to copy the configuration for your client. Keep Smartlight running, including in the tray. Tools expose device identity and type, rooms, supported capabilities, colors, effects, presets and schedules.

Useful requests include “Make the desk lights blue”, “Turn off PC lights except the keyboard”, and “Create a weekday evening schedule”. Ask the assistant to discover devices and capabilities first. User-defined room and device names are preserved when switching language.

## For contributors

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and simulated tests, and [SECURITY.md](SECURITY.md) for sensitive data and network access. The MSI backend has a separate [experimental guide](docs/MYSTIC_LIGHT.md).
