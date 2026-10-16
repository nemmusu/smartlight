# MSI Mystic Light · experimental

[English](MYSTIC_LIGHT.md) · [Italiano](MYSTIC_LIGHT.it.md)

Smartlight can use the official MSI Mystic Light SDK on **Windows**. This integration remains **experimental and has not been validated with physical MSI hardware**. Simulations test the adapter; they do not certify device models or visual results.

### Simple setup

**Automatic** is recommended. Smartlight checks available hardware and lighting software, then tries OpenRGB and iCUE first. It considers MSI only when these find **zero PC lights**. If required software is missing, the interface shows the component and its official link; complete the MSI Center/Mystic Light setup, or install the MSI application required by the device.

When **both MSI hardware and the required MSI software** are detected, Smartlight can retrieve and verify the official SDK and keep it in its local cache. You do not need to find, extract or select a DLL. The MSI application may require guided installation or confirmation prompts; Smartlight does not silently install privileged software or drivers.

You can explicitly select **MSI Mystic Light** instead of Automatic and use **Apply and restart**. Manual mode uses only the chosen integration while retaining prerequisite and actual-zone checks. Linux offers Automatic and OpenRGB; neither iCUE nor the MSI SDK is used there.

### When it is ready

Installed MSI software, a hardware brand, or an SDK file alone is insufficient. SDK initialization and enumeration of **actual zones with supported styles reported by the SDK** must succeed. Failed checks display a problem and never create inferred devices.

In Automatic mode, MSI stays idle if either OpenRGB or iCUE detects even one light. This initial integration does not fill gaps in a partially detected setup. Avoid concurrent writers to the same LEDs while keeping the MSI software required by the SDK installed.

### Controls and limits

- Colors, brightness and lighting on/off, within each zone’s reported capabilities.
- Smartlight animations, themes, scenes, presets, profiles and schedules through the shared PC controls.
- Native MSI styles enumerated by the SDK, with speed and brightness mapped to supported levels.
- Selections and groups: effects are offered for compatible zones; incompatible targets are reported.
- Native state readback when the relevant SDK methods are supported.

Software animations require a static or direct style. Spatial effects address individual LEDs only when the SDK supplies names mapped to the zone and compatible direct control; otherwise the color is uniform per zone. Native controls can vary by style: a parameter supported on one device is not assumed to work on another.

Native speed and brightness may have only a few levels, so Smartlight maps its controls to the device range. Available SDK readback describes native state, not measured light output. Smoothness, MSI Center synchronization and every device model’s behavior cannot be certified without physical hardware.

### Component verification

Downloads use the official MSI archive over HTTPS with bounded size and a pinned SHA-256. The DLL must match Smartlight’s architecture and pass PE format and required-export checks. The SDK remains in the local cache and **is not bundled in Smartlight packages or the repository**.

Native calls run in a separate worker with a five-second timeout. A failed, blocked or crashed worker is stopped without repeated failed frame writes. These measures limit application disruption; they cannot guarantee that vendor drivers have no hardware issues.

Simulations cover detection, prerequisite gating, verified acquisition, zone enumeration, invalid data, style/brightness/color ordering, on/off, errors, timeouts, worker failures and isolation from other integrations. Physical validation remains necessary.

## Official references

- [MSI Mystic Light SDK download and requirements](https://www.msi.com/Landing/mystic-light-rgb-gaming-pc/download)
- [MSI SDK API reference, version 1.0.0.08](https://storage-asset.msi.com/files/pdf/Mystic_Light_Software_Development_Kit.pdf)

Vendor components remain subject to MSI’s terms. Developer-only overrides are implementation details and are not required for normal setup.
