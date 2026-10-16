# Changelog

## 0.4.3

- Offline help opens inside Smartlight on Windows and Linux, without launching a browser.
- Shared local asset serving fixes Linux help paths and language queries.
- Help supports English/Italian, keyboard dismissal and returning to the existing controls.
- Default documentation is English, with separate linked Italian translations.

## 0.4.2

- MSI software animations, flows, scenes, profiles and presets through the shared PC controller.
- Native Mystic Light styles discovered from SDK zones, with device-specific controls and compatible target selection in UI and MCP.
- Native state readback, supported brightness/speed ranges and direct LED addressing where the SDK provides explicit names and a direct mode.
- Capability checks before group changes, native/software ownership transitions and worker failure isolation.
- Experimental MSI support remains unverified on physical hardware; simulated tests do not certify visual smoothness or device compatibility.

## 0.4.1

- Automatic PC lighting setup, with hardware/software detection and clear missing-component guidance.
- Optional manual selection of OpenRGB, iCUE or experimental MSI on Windows; OpenRGB on Linux. Apply changes with one restart action.
- Automatic Corsair fallback to OpenRGB when iCUE finds no lights, without duplicate writers.
- Automatic verified MSI SDK preparation only with appropriate hardware and software evidence; physical MSI validation remains pending.
- English on first use, with Italian available anytime in settings and saved language preferences preserved.
- Improved setup layout, bilingual visual QA and GitHub release documentation.

## 0.4.0

- Selectable Italian/English interface, help and tray labels; preference shared through the desktop service and MCP.
- General hardware help with clear Windows/Linux differences and no personal test-PC table.
- Experimental Windows MSI Mystic Light SDK fallback, disabled by default and only attempted when OpenRGB/iCUE find no PC lights.
- MSI static colors, brightness and zone lighting power; separate worker, DLL validation, timeouts and failure reporting. No physical MSI hardware validation or vendor DLL distribution.
- Portable UI regression checks, repository documentation, bilingual README, demonstration screenshots and issue templates.

## 0.3.2

- Shared Windows/Linux source base and packaging.
- Linux uses OpenRGB for Corsair as well as other supported PC devices.
- Compact workspace, explicit command targets and selection/category controls.
