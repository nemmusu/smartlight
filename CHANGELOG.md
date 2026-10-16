# Changelog

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
