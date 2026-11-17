# Hardware

The firmware targets the Waveshare ESP32-S3-Touch-AMOLED-1.75: an ESP32-S3R8 (8 MB octal PSRAM, 16 MB flash) with a 1.75" round AMOLED (466×466) and a capacitive touch panel, powered over USB-C or a LiPo battery.

## Pins and buses

| Item | Value |
|---|---|
| Display | CO5300 over QSPI. CS GPIO12, SCLK GPIO38, D0–D3 GPIO4/5/6/7, RESET GPIO39. TE (GPIO13) is not used. |
| Touch | CST9217 at I²C 0x5A. INT GPIO11, RESET GPIO40. Transform: `mirror_x` + `mirror_y`. |
| I²C bus | SDA GPIO15, SCL GPIO14, 400 kHz. |

The I²C bus is shared by these devices:

| Device | Address | Used by the firmware |
|---|---|---|
| AXP2101 (PMU) | 0x34 | yes (battery) |
| TCA9554 (IO expander) | 0x20 | no |
| QMI8658 (IMU) | 0x6B | no |
| PCF85063 (RTC) | 0x51 | no |
| ES8311 (audio codec) | 0x18 | no |
| ES7210 (audio ADC) | 0x40 | no |

The touch driver is the external component `cst9217` from `shelson/esphome-cst9217`, pinned to a commit SHA in `esphome/packages/board-waveshare-amoled-175.yaml`. Keep it pinned.

## Power and battery

The AXP2101 reports the battery state through the `axp2101_battery` component (`esphome/components/axp2101_battery/`). The display and touch rails are powered by default, so the firmware does not touch the LDO registers.

Registers used (from XPowersLib):

- Enable the ADC: set bit 0 of 0x30.
- Enable battery detection: set bit 0 of 0x68.
- Battery present: bit 3 of 0x00.
- Charging: `(reg 0x01 >> 5) == 0x01`.
- Battery percentage: register 0xA4 (0–100).
- Battery voltage in mV: `((reg 0x34 & 0x1F) << 8) | reg 0x35`.

Without a battery the level and voltage are unknown (NaN) and nothing logs an error. While the screen sleeps the panel brightness is 0 and LVGL is paused; the Wi-Fi and API connections stay up.

## Performance settings

- LVGL draws with `lvgl: buffer_size: 25%` (in `esphome/packages/ui.yaml`). This is the current setting.
- It has not been tuned on hardware yet. If the page slides stutter (below about 30 fps), try these in order and keep the best:
  1. `lvgl: buffer_size: 100%`;
  2. `esp32: framework: sdkconfig_options: {CONFIG_ESP32S3_DATA_CACHE_64KB: "y", CONFIG_ESP32S3_DATA_CACHE_LINE_64B: "y"}`;
  3. `lvgl: buffer_size: 12%`.
- Record the result here once measured.
- Image size: about 2.0 MB, in an app partition of about 8.1 MB (ESPHome sizes the partitions for 16 MB flash).

## Fonts

Fonts are declared in `esphome/packages/ui.yaml` and reach LVGL through `font::Font::get_lv_font()`. The text font uses `glyphsets: [GF_Latin_Core]` and the Google Fonts source (`gfonts`); both were accepted by ESPHome 2026.10.2, so no explicit-glyph fallback was needed. The emoji fonts take their glyphs from `custom_components/ha_controller/emoji.json`.

## Sleep

Sleep uses `touchscreen::TouchListener::release()` to wake on touch (the touch that wakes the screen is swallowed) and the `lvgl.pause`, `lvgl.resume` and `lvgl.widget.redraw` actions to stop and restart drawing.

## Enclosures

Printable enclosures are in [`3D_models/`](../3D_models/), in two variants: [with a PWR button](../3D_models/with_pwr_button) and [without one](../3D_models/without_pwr_button).
