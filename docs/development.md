# Development

## Prerequisites

- Python 3.14 (integration tests and repository checks).
- Node 24 (panel build).
- Firmware: a Python 3.13 venv with ESPHome, CMake and SDL2 (see [Firmware](#firmware)).

Each part of the repository has its own virtual environment: the integration uses `custom_components/.venv`, the repository checks use `.github/scripts/.venv`.

## Home Assistant integration

Create the environment and install the test requirements from the repository root:

```bash
python3.14 -m venv custom_components/.venv
custom_components/.venv/bin/pip install -r custom_components/requirements_test.txt
```

Run the tests and the linter:

```bash
custom_components/.venv/bin/pytest custom_components/ha_controller/tests
custom_components/.venv/bin/ruff check custom_components
```

### Running a development Home Assistant

Symlink the integration into the configuration directory of a development Home Assistant, then restart it:

```bash
ln -s "$PWD/custom_components/ha_controller" <config>/custom_components/ha_controller
```

Add the integration from Settings › Devices & services. The sidebar panel only shows up once the panel bundle has been built; until then Home Assistant logs a warning that the bundle is missing.

### Watching the traffic

The screen reports itself with ESPHome events. Open Developer tools › Events, listen to `esphome.ha_controller_hello` and reconnect the screen: every hello shows up there, followed by the layout the integration sends back with `set_layout`.

## Panel

The panel is TypeScript with Lit and Vite, in `custom_components/ha_controller/frontend/` (Node 24). Run these from the repository root:

```bash
npm --prefix custom_components/ha_controller/frontend ci              # install
npm --prefix custom_components/ha_controller/frontend test            # unit and component tests
npm --prefix custom_components/ha_controller/frontend run dev         # mock harness (dev/index.html) in the browser
npm --prefix custom_components/ha_controller/frontend run build -- --watch   # rebuild dist/ while testing in Home Assistant
```

`npm run dev` serves the panel against `dev/mock-hass.ts`, an in-memory fake of the websocket API seeded with the reference layout. The production bundle is `frontend/dist/ha-controller-panel.js` (git-ignored); the integration serves it to the sidebar panel.

## Firmware

The firmware is ESPHome with LVGL, in `esphome/`. The hardware is described in [hardware.md](hardware.md).

### Prerequisites

- Python 3.13 (CI uses 3.13; ESPHome is pinned in `esphome/requirements.txt`).
- CMake and a C++ compiler for the host tests.
- SDL2 (`brew install sdl2` or `sudo apt-get install libsdl2-dev`) for the simulator.

```bash
python3.13 -m venv esphome/.venv
esphome/.venv/bin/pip install -r esphome/requirements.txt
```

### Commands

Run these from the repository root:

```bash
# Host tests for the pure C++ logic
cmake -S esphome/tests -B esphome/tests/build
cmake --build esphome/tests/build
ctest --test-dir esphome/tests/build --output-on-failure

# Compile the device and the simulator configs
esphome/.venv/bin/esphome compile esphome/ha-controller.yaml
esphome/.venv/bin/esphome compile esphome/simulator.yaml

# Flash the screen over USB-C (first flash, or when OTA is not possible)
esphome/.venv/bin/esphome run esphome/ha-controller.yaml

# Run the simulator (an SDL window on the development machine)
esphome/.venv/bin/esphome run esphome/simulator.yaml
```

`esphome/secrets.yaml` must never be committed. ESPHome recreates `esphome/.gitignore` on every compile; it is git-ignored.

### Connecting Home Assistant to the simulator

1. Run `esphome/.venv/bin/esphome run esphome/simulator.yaml`. The window shows "Waiting for Home Assistant".
2. In Home Assistant, add an ESPHome device on `<development machine IP>:6053`.
3. Add the HA Controller integration and pick "HA Controller Simulator".
4. Within 5 s the simulator shows "No blocks yet". Developer tools › Events shows `esphome.ha_controller_hello` with the reasons `connected` and then `applied`.

Edit the layout in the panel and the simulator follows. Mouse drags stand in for finger swipes. The simulator has no HTTP OTA, so `install_firmware` exists only in the device config.

### Manual hardware checklist

Plan 4 could not test these on the board. Run them in one go with the firmware flashed over USB-C and, where marked, the simulator connected to Home Assistant.

**Display, touch and power** (device)

- The round display shows "HA Controller", the version and 💡, centred.
- Tapping near the top, right, bottom and left edges logs about `(233,5)`, `(460,233)`, `(233,460)` and `(5,233)`. Otherwise fix `transform` (`mirror_x`, `mirror_y`, `swap_xy`) and repeat.
- With a battery: `Battery` reads 0–100 %, `Battery voltage` 3.3–4.3 V, and `Charging` turns on when USB is plugged in.
- Without a battery: level and voltage are unknown (NaN) and there are no errors.
- The `Screen brightness` number dims the panel.
- Wi-Fi provisioning works through the `HA Controller` access point and its captive portal.

**End to end with Home Assistant** (simulator)

- The simulator shows "No blocks yet" within 5 s of the connection; the hello events show `connected` then `applied`.
- In the panel, add three blocks and save. The simulator shows the start block's name on its background.
- Heartbeat hellos arrive every 60 s with a revision equal to the panel's.

**Navigation** (simulator, then device with a finger)

Build the reference map in the panel: Kitchen start, Lights above, Hello World left, Bedroom below Hello World.

- From Kitchen, a drag from the left edge to the right slides to Hello World.
- From the top edge downwards slides to Lights.
- From the right edge leftwards rubber-bands by at most 48 px and returns.
- From Hello World, the bottom edge upwards slides to Bedroom.
- A drag starting in the centre does nothing.
- A short slow drag snaps back; a quick flick commits.
- The edge hints match the neighbours.
- Saving a layout from the panel while holding a drag shows the new layout cleanly, with no stuck half-page.
- On the device, the slides look smooth (about 30 fps or better). If not, follow the tuning order in [hardware.md](hardware.md#performance-settings) and record the result there.

**Controls** (simulator with Home Assistant, then device)

- Light: the knob shows Home Assistant's brightness; dragging to about 30 % and releasing sets the light to 30 %; a centre tap toggles it; a brightness change in Home Assistant moves the knob within 1 s; incoming updates do not move the knob while dragging.
- On/off-only light: a toggle button.
- Climate: steps of 0.5 °C; release updates the target; `Now …` and the action are shown.
- Custom block: text, emoji and the outdoor temperature are shown and follow sensor changes; the battery row shows `🔋 76 %`; the brightness slider changes `number.*_screen_brightness`.
- Renamed entity: renaming a bound entity in Home Assistant shows `—` and `Unavailable` and disables its control.
- Taps give immediate visual feedback.
- On the device: repeat the light, climate and custom checks, the battery row shows the real level, the brightness slider dims the panel smoothly, and with the battery unplugged the row shows `🔋 — %` and nothing crashes.

**Sleep** (simulator, then device)

- Simulator: after 20 s without input the log shows `screen_off` and the window stops updating; clicking the light knob position wakes the screen without toggling or moving anything; a delay of 5 s in the panel sleeps after 5 s and `0` keeps the screen awake; a Home Assistant state change made while asleep is visible right after waking.
- Device: the panel goes black after the delay; a tap on the knob area only wakes the screen, which then stays awake for the full delay; changing `Screen brightness` from Home Assistant while asleep keeps the panel dark and the new level shows on wake.
- Watch for a one-frame flash of stale content on wake.

**Over-the-air update** (device)

1. Bump `esphome/version.yaml` locally to `0.1.1` (do not commit) and compile.
2. Find the build output with `find esphome/.esphome/build -name firmware.ota.bin`. In that directory, create the checksum with `md5 -q firmware.ota.bin > firmware.ota.bin.md5` (Linux: `md5sum firmware.ota.bin | cut -d' ' -f1 > firmware.ota.bin.md5`), then serve it with `python3 -m http.server 8000 -d <that directory>`.
3. In Developer tools › Actions, call `esphome.ha_controller_<suffix>_install_firmware` with the LAN URLs of the `.bin` and the `.md5`. The screen shows "Updating firmware…", reboots, and the next hello carries `0.1.1`.
4. Run it once while the screen sleeps: the screen must wake first.
5. Repeat with a wrong `.md5`. The screen shows "Update failed" for 5 s, then the pages return.
6. Revert `version.yaml`.

Plain `http://` URLs are fine for the LAN test: `verify_ssl` only affects HTTPS.
