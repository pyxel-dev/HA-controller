# Getting started

1. **Hardware and enclosure.** You need a Waveshare ESP32-S3-Touch-AMOLED-1.75. Print an enclosure from the [3D models](../3D_models/) (see [Hardware](hardware.md)).
2. **Flash the firmware.** Open <https://pyxel-dev.github.io/HA-controller/> in Chrome or Edge, connect the board over USB and click Install. Note the firmware version shown on the page.
3. **Connect to Wi-Fi.** Use Improv in the installer, or join the `HA Controller` access point and use its captive portal.
4. **Adopt the device.** In Home Assistant, the ESPHome device is discovered. Adopt it under Settings > Devices & services.
5. **Install the integration.** In HACS, add the custom repository `https://github.com/pyxel-dev/HA-controller` (type Integration). Install the **same version** as shown on the installer page, then restart Home Assistant.
6. **Add the integration.** Go to Settings > Devices & services > Add integration > HA Controller, then pick the screen.
7. **Open the panel.** Open HA Controller in the sidebar and design your screens (see [Configuration](configuration.md)).

## Troubleshooting

- **The screen stays on "Waiting for Home Assistant".** Check that the ESPHome device and the HA Controller entry both exist. If the hello events never show up under Developer tools > Events, enable "Allow the device to perform Home Assistant actions" in the ESPHome device options.
- **"Firmware update required".** See [Updates](updates.md).
