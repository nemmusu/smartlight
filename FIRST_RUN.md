# Smartlight · first launch and recovery

**English** | [Italiano](FIRST_RUN.it.md) · [README](README.md)

Smartlight shares one codebase across Windows and Linux. On Linux, all PC RGB devices, including Corsair, use OpenRGB; see the [Linux guide](LINUX.md). Both builders read the version from `version.txt`. Instructions involving iCUE apply only to Windows.

## Using the interface

The Workspace displays groups in a compact grid. Each **On/Off** pair controls only the named group. Open **Color, presets and devices** for additional controls. The panel for dragging devices into groups opens only when needed.

**Tapo lights** controls Tapo devices only. Clicking a card opens that light; checkboxes select several lights and replace individual details with one selection editor. Groups containing only PC devices are controlled from the Workspace. **PC lights** always states whether its controls affect all devices or the selection, and shows their on/off state.

Effects, scenes, automations and settings have selectable categories. PC effects show color, speed and brightness before the catalog. **Turn off all lights** controls Tapo and PC lights together. Tray commands use the same service as the interface and process clicks in order. Logitech keyboards use Direct mode to turn all keys black and restore their full lighting.

Smartlight brings local Tapo lights and PC LEDs exposed by compatible integrations into one window. The Windows installer includes the app and its Python runtime, so you do not need to install Python on the destination PC. Windows uses WebView2 for the window. **Automatic** is the recommended PC lighting mode: OpenRGB and iCUE are selected according to available hardware and software. Linux uses OpenRGB, including for Corsair.

## Preparing the components

1. Install Smartlight with `Smartlight-Setup-<version>.exe`. Setup checks WebView2 and optional components, keeping those already installed.
2. Start Smartlight and leave PC lighting set to **Automatic**. The app detects hardware and software and shows missing components with official links. You do not need to select driver folders or DLL files.
3. If vendor software is required, complete its official setup. iCUE may require software integrations to be enabled; MSI may require MSI Center with the Mystic Light module. Smartlight does not silently install drivers or software requiring vendor confirmation.
4. Scan PC lights again. Ready status requires actual controllable devices or zones: installed software alone is insufficient. Connect Tapo lights to the same network and enter their credentials when prompted.

If OpenRGB is already running without its Smartlight connection, open **SDK Server** in OpenRGB, select **Start Server** on port **6742**, then **Detect again** in Smartlight. The app displays these instructions and does not open a second OpenRGB instance.

### Automatic or manual selection

- **Automatic:** tries OpenRGB and, on Windows, iCUE. If iCUE detects no devices, OpenRGB can also control Corsair. Experimental MSI support is considered only when these integrations find no PC lights and MSI prerequisites are present. Device ownership stays stable to avoid concurrent commands. **Detect again** rechecks available components.
- **OpenRGB:** uses only OpenRGB, including for Corsair, without starting iCUE.
- **iCUE** or **MSI Mystic Light:** on Windows, uses only the selected integration. MSI retains the experimental limitations in its [dedicated guide](docs/MYSTIC_LIGHT.md).
- After changing the mode, select **Apply and restart**. Linux offers Automatic and OpenRGB.

When both MSI hardware and required MSI software are detected, Smartlight can retrieve and verify the official SDK. The SDK is not bundled with Smartlight, and you do not need to select a DLL. The required MSI application still uses its official vendor setup. The integration becomes ready only when verification finds controllable zones.

MSI supports colors, brightness, on/off, SDK-reported native effects, and Smartlight software animations, themes, scenes, presets, profiles and schedules according to detected zone capabilities. Native speed and brightness may have only a few levels; controls are mapped to those levels. Zones do not imply individual LED control. Available SDK readings describe native state, not measured light output. MSI remains experimental and unverified on physical hardware: simulations do not certify smoothness, every model's compatibility or synchronization with MSI Center.

Official downloads: [iCUE](https://www.corsair.com/us/en/s/downloads), [OpenRGB](https://openrgb.org/releases.html), [MSI Mystic Light](https://www.msi.com/Landing/mystic-light-rgb-gaming-pc/download), [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). Failed checks identify the component and next step. Tapo lights can keep working independently of PC RGB.

## Hardware compatibility

Smartlight has been tested on **Windows and Linux** with devices from its supported integrations. Tapo and OpenRGB are available on both systems; **iCUE is Windows only**. On Linux, Corsair devices are fully handled through OpenRGB.

Tapo devices supporting local control include L530 bulbs and L900 strips. Available features depend on model and firmware. PC lighting uses devices detected by OpenRGB and, on Windows, those exposed by the iCUE SDK.

**Help** includes a searchable offline catalog from the [official OpenRGB 1.0rc2 list](https://openrgb.org/devices_1.0rc2.html), with categories and reported features. A catalog entry does not mean Smartlight has individually tested that device or guarantees every feature. Check detection and a color change on your device. Hardware revisions, drivers and operating systems can affect support.

The initial language is **English**. Choose **Italiano / English** at any time in **Settings → General → Language**. Your choice is saved; custom light, room and preset names stay unchanged. Help also has a language selector.

Software animations for L530 and Smartlight automations require the app to remain running, including with its window minimized. They are separate from the Tapo app's cloud Smart Actions. Native L900 music synchronization appears in the protocol but is not currently implemented as a Smartlight command. When exposed by the device, Smartlight displays active minutes and kWh for today, 7 days and 30 days. [TPAP branch details](https://github.com/python-kasa/python-kasa/pull/1592) · [L530 energy data context](https://github.com/python-kasa/python-kasa/issues/1701).

The PC animation engine produces up to 30 frames per second. Pulse and breathing use transitions executed by L900 and L530 devices when accepted, avoiding stepping from continuous LAN brightness updates. Choose maximum brightness, minimum brightness including 0%, and speed; the editor immediately estimates cycle duration. Smartlight temporarily saves the previous native configuration for restoration after interruptions. Tapo app commands during an animation take priority. If an L900 rejects a native effect, Smartlight reports it rather than starting a visibly choppy pulse. On devices without native effects, Tapo HSV commands have a minimum brightness of 1%.

Flow, gradient, wave and rainbow also use native transitions when available. Otherwise, Smartlight interpolates colors over a persistent LAN connection and attempts an update roughly every 150 ms. Actual timing depends on the lights and network. During software animation, Smartlight reads bulb power roughly every 5 seconds. Turning a light off from the Tapo app or a Tapo timer stops further color updates to it and updates UI and MCP state. Sequence and cycle hold each color and use the selected transition duration, with 0 ms giving an immediate change. Flash and random retain abrupt changes. PC and Tapo share an animation clock, but perfect synchronization is not guaranteed. Smartlight must remain running, even when minimized.

## Rooms, selection and active mode

**Rooms** are Smartlight groups: choose a name and assign Tapo lights and PC RGB devices. They are independent of rooms in the Tapo app. Quick controls can target all devices, a room or a manual selection. **Select all** and **Deselect** make selection explicit. Scenes and static presets save colors and brightness; customizable themes can be static or animated. Schedules and timers can also target rooms.

**PC lights** groups devices into cooling, memory, motherboard, graphics card and peripherals. Filter or select an entire category. Smartlight receives types such as `KEYBOARD` or `MOUSE` from the backend and exposes them through MCP. If the type is missing, the interface attempts identification from the name. Obtain MCP device IDs with `list_pc_devices` or `list_targets`.

**Effects & presets** combines ready-made atmospheres, custom animations, original Tapo effects and PC RGB effects. First choose all devices, a room or one light. The catalog shows the number of compatible devices for each effect. Save and edit color, theme, animation, Tapo effect or PC effect presets; the same types are available through MCP. In Tapo device details, **Effect** shows applicable choices and opens the catalog with that light selected.

In **Automations**, choose a quick or precise time, then a single date, every day, weekdays, weekends or individual weekdays with a click. Schedule power, color, Tapo white, brightness and saved presets for one light, a room or all lights, according to device and preset capabilities. Smartlight must be running at the scheduled time. Less frequent network, backup and MCP settings are in expandable panels; all controls remain available.

The **Workspace** contains a permanent group for all lights and your custom groups. Drag a Tapo or PC device from the device panel into a group, or use **Add devices**. A device can belong to several groups. Each group has common power, color, brightness, theme and preset controls. Assignments survive reopening the app.

Smartlight always shows the **active mode**. A static command stops continuous playback. Starting animation stops PC → Tapo synchronization; starting synchronization stops animation. This prevents two modes from repeatedly overwriting the same lights. Room definitions and custom themes are included in backups.

## System tray

With **Keep running in the system tray when closed** enabled, the X hides the window while Smartlight, automations and MCP keep running. Click the Smartlight icon beside the Windows clock to reopen it. The menu offers **Turn on/off all lights**, **Turn on/off Tapo lights**, **Turn on/off PC lights** and **Exit**. Disabling the preference makes the X close the app. **Exit** always closes it. Quick commands affect currently detected lights.

The installed Windows version offers **Start with Windows** in **Settings**. With the tray preference enabled, Smartlight starts hidden once its icon is ready; otherwise it opens the window. MCP can read and change the same setting using `get_settings` and `set_settings`. Uninstalling removes the startup entry.

## MCP server

Open **Settings → MCP server**. For URL-based clients, select **Start server**. Smartlight exposes **Streamable HTTP** at `http://127.0.0.1:8766/mcp` in the app process. Choose **This PC only** or **Devices on the LAN**. LAN mode also displays the network address. Use a trusted network and allow the Windows firewall connection if prompted. The endpoint requires a Bearer token, stored on Windows in a file encrypted for the current user with DPAPI and excluded from app backups. Use **Copy token** if needed separately, or **Copy local configuration** or **Copy LAN configuration** for the correct URL and authorization. Copying uses the native Windows clipboard; if busy, the app displays text for manual copying. Port and token survive restarts. **Regenerate token** revokes old client configurations. **Start MCP with Smartlight** makes the endpoint available at startup, including in the tray.

For command-based clients, the same screen shows the exact `Smartlight-MCP.exe` path and copies its configuration. This **stdio** server is started by the MCP client. Opening it manually produces an empty console waiting for a client; **Test connection** in the UI performs a real handshake and reports available tools. The typical installed path is:

```text
%LOCALAPPDATA%\Programs\Smartlight\Smartlight-MCP\Smartlight-MCP.exe
```

Both modes forward commands to the same Smartlight instance, which must remain running, including with its window hidden in the tray. HTTP does not start a second executable or terminal.

MCP tools include `list_rooms`, `save_room`, `delete_room`, `list_targets`, `apply_target_state`, `get_control_mode`, `save_theme`, `delete_theme` and `set_settings`. Targets are `all`, `room:<id>`, a device or a list of devices.

Start with `get_lighting_overview` to obtain compact Tapo and PC IDs and current states, available effects, PC scenes and active mode without knowing internal app formats. `set_color`, `set_lights_power` and `set_lights_brightness` accept the same targets across all lights. `set_color` uses `#RRGGBB` and turns on selected devices; brightness is optional. For a blue keyboard and strip, pass their ID list as `target` and `#0066FF` as `color`. Changes use the same service as the window. Smartlight refreshes Tapo state from the network roughly every 10 seconds, including changes from Tapo timers and the official app. The visible window refreshes Smartlight state every 5 seconds. MCP reads the same updated state.

Hardware-specific controls remain separate. `set_color_temperature`, `apply_effect` and `apply_tapo_device_preset` control Tapo; kelvin values must respect model limits. `list_pc_effects`, `set_pc_effect`, `list_pc_scenes`, `apply_pc_scene` and `set_pc_global_brightness` control PC RGB. `save_custom_effect` includes PC devices with `include_pc=true`; `save_lighting_schedule` schedules Tapo and PC in one action. Smartlight must remain running for animations, synchronization, timers and schedules. Smartlight scenes and presets work across both groups; native Tapo presets are distinct.

## Back up before reinstalling your operating system

1. Use **Settings → Backup → Export** and save the file on an external drive or in private storage.
2. Also copy `%APPDATA%\Smartlight` to recover all local state. It may contain sensitive configuration; treat it as a private backup and do not publish it.
3. Export native iCUE and OpenRGB settings separately from those apps; they are not part of Smartlight backups.

## Restore after reinstalling your operating system

1. Reinstall Smartlight with Automatic component selection or restore your preferred manual mode. Connect the PC to the Tapo network and check device availability.
2. Use **Settings → Backup → Import** with the saved file. Restart if prompted.
3. Reenter Tapo credentials if unavailable on the new Windows installation. Check device names/IDs or reassign them in the UI.
4. Briefly test scenes, animations, PC profiles and Tapo presets. Check iCUE and OpenRGB status in app settings.

On first launch, Smartlight can migrate legacy HWLight state and profiles from `hwlight_state.json` and `hwlight_profili.json` in `%USERPROFILE%\Desktop\hwlight`. Migration copies data and leaves originals intact.

## Uninstalling

Uninstall Smartlight from Windows Apps. Uninstalling preserves `%APPDATA%\Smartlight` for profiles and backups. Remove it manually when no longer needed. iCUE, OpenRGB and WebView2 remain installed because other applications may use them.

