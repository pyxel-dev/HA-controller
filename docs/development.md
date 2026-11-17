# Development

## Prerequisites

- Python 3.14 (integration tests and repository checks).
- Node 24 (panel build, filled in by plan 3).
- ESPHome (firmware build, filled in by plan 4).

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

Filled in by plan 4.
