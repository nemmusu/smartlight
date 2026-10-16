# Compatibility / Compatibilità

Smartlight uses device capabilities reported by its integrations. Support varies with model, firmware, driver and backend version.

- **Tapo:** L530 and L900 families have been exercised; native effects differ between bulbs and strips. Other python-kasa devices are not automatically guaranteed to expose every feature.
- **Windows PC RGB:** OpenRGB SDK and iCUE SDK selected by availability. Automatic selection can use OpenRGB for Corsair when iCUE finds no devices; manual selection uses only the chosen integration.
- **Linux PC RGB:** OpenRGB SDK for all supported brands, including Corsair. No iCUE backend or iCUE dependency is used.
- **MSI Mystic Light:** experimental Windows SDK backend, considered automatically only when OpenRGB and iCUE find no PC lights, or selected explicitly. Simulations validate the adapter, not physical compatibility. See [setup and limits](MYSTIC_LIGHT.md).

Automatic selection checks both lighting software and actual controllable devices; detecting an installed application alone does not establish support. Users can override the selection with a specific integration. Linux offers Automatic/OpenRGB only; Windows also offers iCUE and the experimental MSI integration.

The app help includes a searchable OpenRGB compatibility catalog. Catalog presence means upstream support is listed; it does not mean every device was tested with Smartlight.

Automated Windows/Linux tests use simulated devices. A Linux GUI needs the desktop libraries listed in [LINUX.md](../LINUX.md); the current validation environment does not establish compatibility with every Linux desktop or tray implementation.

## Italiano

Le capacità disponibili dipendono da modello, firmware e integrazione. Le prove sulle famiglie Tapo L530 e L900 e sui backend PC non equivalgono a una verifica fisica di ogni voce del catalogo OpenRGB. Su Linux il controllo PC, compreso Corsair, passa da OpenRGB. Mystic Light rimane sperimentale finché non sarà verificato con hardware reale.
