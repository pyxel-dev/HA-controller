# Updates

## One version

The whole repository has a single version. The integration, the panel and the firmware always share it, and the integration expects the firmware of the same version on the screen.

## Integration

Integration updates come through HACS. To install them automatically, create an automation that calls `update.install` on the HACS update entity of HA Controller.

## Firmware

The firmware follows the integration automatically (the `auto_update` option, on by default). You can also update it by hand from the "HA Controller firmware" update entity.

Rolling back the integration to an older version makes the firmware follow it.

## Screen without internet access

The firmware is downloaded from GitHub. A screen without internet access must be re-flashed over USB from the [installer](https://pyxel-dev.github.io/HA-controller/).
