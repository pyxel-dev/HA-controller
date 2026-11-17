---
name: firmware-dev
description: Use when building, flashing, simulating or changing the ESPHome firmware (esphome/), including LVGL UI code.
---

# Firmware development

The firmware is ESPHome with LVGL in `esphome/`. Hardware facts are in `docs/hardware.md`; the manual hardware checklist is in `docs/development.md`.

## Commands

Run from the repository root:

```bash
# Host tests (pure C++ logic)
cmake -S esphome/tests -B esphome/tests/build && cmake --build esphome/tests/build
ctest --test-dir esphome/tests/build --output-on-failure

# Compile both configs (long; run in the background)
esphome/.venv/bin/esphome compile esphome/ha-controller.yaml
esphome/.venv/bin/esphome compile esphome/simulator.yaml

# Flash over USB-C, or run the SDL simulator
esphome/.venv/bin/esphome run esphome/ha-controller.yaml
esphome/.venv/bin/esphome run esphome/simulator.yaml
```

The venv is Python 3.13 with `esphome/requirements.txt`. Never commit `esphome/secrets.yaml`.

## Simulator loop

1. Change the code and run the host tests.
2. `esphome run esphome/simulator.yaml` (an SDL window; mouse drags act as finger swipes).
3. Connect it to a development Home Assistant (see `docs/development.md`) and edit the layout in the panel.
4. Before finishing, compile both configs. `install_firmware` exists only in `ha-controller.yaml` (the simulator has no HTTP OTA).

## Rules

- Pure logic goes in host-tested headers or modules under `esphome/components/ha_controller/` with a test in `esphome/tests/`.
- LVGL is called on the main loop only.
- Views never register ESPHome callbacks; the component registers them once.
- Call `lv_refr_now` before blocking work (such as OTA), so the message is on the panel.
- LVGL is paused while the screen sleeps. Call `wake()` before showing anything the user must see (`show_message` already does).
- Fonts are declared in `esphome/packages/ui.yaml` and mapped in the `ha_controller:` block.
- A new LVGL widget type needs a hidden instance on `boot_page`, so ESPHome compiles it in.
- Controls stay inside radius 185 of the 466 px circle.
- Keep the `cst9217` external component pinned to its commit SHA.
