# Architecture

HA Controller has three parts: a Home Assistant custom integration with a sidebar panel, an ESPHome firmware for the screen, and a GitHub Pages web installer. This page is the contributor overview.

## Overview

```text
            Home Assistant                                       Screen (ESPHome firmware)
┌──────────────────────────────────────────┐            ┌──────────────────────────────────────┐
│ custom integration `ha_controller`       │  ESPHome   │ external component `ha_controller`   │
│  config entry per screen                 │  actions   │  layout + state parsers (pure C++)   │
│  layout store + validation               │ ─────────▶ │  pager: edge swipes, slide animation │
│  compiler → device payload (+ revision)  │ set_layout │  block views: knobs, custom items    │
│  sync engine (hello, states, controls)   │ set_states │  message screen                      │
│  firmware update entity + auto-update    │ install_fw │                                      │
│  websocket API + sidebar panel (Lit)     │ ◀───────── │ board package: CO5300 display,       │
└──────────────────────────────────────────┘   events   │ CST9217 touch, AXP2101 battery,      │
        ▲ HACS (release zip)                  hello /    │ screen brightness number             │
        │                                     control    └──────────────────────────────────────┘
  GitHub Releases ──────▶ GitHub Pages: web installer + firmware/<version>/   ▲ OTA download / USB flash
```

## Subsystems

- The screen is an ordinary ESPHome device, adopted by Home Assistant's ESPHome integration. The custom integration opens no connection of its own. It calls the device's user-defined ESPHome actions, which Home Assistant exposes as services `esphome.<node>_<action>` (node name with `-` replaced by `_`). It also listens to the `esphome.ha_controller_*` events fired by the device.
- Home Assistant's ESPHome integration adds `device_id` to every device event. It requires the "Allow the device to perform Home Assistant actions" option for actions, but not for events (`homeassistant/components/esphome/manager.py`). The design uses events only, so that option can stay off.
- The integration is the single source of truth for both the layout and the version. The firmware is a generic renderer.

- **Integration** (`custom_components/ha_controller/`): stores and validates layouts, compiles them into the device payload, runs the sync engine and exposes the websocket API used by the panel.
- **Panel** (`custom_components/ha_controller/frontend/`): the block map editor, built with Lit and Vite and served from the integration.
- **Firmware** (`esphome/`): a generic renderer. It parses the layout and states it receives, draws the blocks and reports touches as events.
- **Distribution** (`.github/scripts/`, `.github/workflows/`): HACS release zip, firmware builds and the web installer on GitHub Pages.

## Handshake: hello, layout and states

When the screen connects (or reboots) it fires a `hello` event carrying its firmware version and the protocol version. When the revision differs, the integration answers with `set_layout` (the compiled layout payload with its revision) and then `set_states` (the current Home Assistant states of the entities the layout uses). The integration pushes the layout only when the hello's revision differs from its own, and after a `connected` hello with the same revision it pushes all states. Afterwards it sends `set_states` again whenever a watched entity changes, and `set_layout` whenever the stored layout changes. The exact messages are defined in `docs/protocol/README.md` and pinned by `docs/protocol/fixtures/`.

## Controls become service calls

A touch on a block (a knob turn, a tap on a custom item) is sent by the firmware as a `control` event. The integration maps the event to a Home Assistant service call using the stored layout, never trusting the device for entity ids or service names, and runs it. The resulting state change flows back to the screen through `set_states`.

## Firmware updates

The integration version is the single version of the repository. The integration creates an `update` entity per screen: the installed version comes from the last hello and the latest version is the integration version. Installing calls the device's `install_firmware` action with the OTA URL on GitHub Pages (`firmware/<version>/`). With the `auto_update` option on, a hello reporting a different version triggers one automatic install attempt per screen and version, only for release versions. OTA needs internet access from the screen. Without it, re-flash over USB from the web installer.

## Repository layout

The repository root holds no files except `README.md` (GitHub and HACS landing page), `hacs.json` (HACS reads it only at the root) and `.gitignore`. Everything else lives in a folder:

| Path | Content |
|---|---|
| `docs/` | User and developer documentation. `docs/protocol/` holds the protocol doc (`README.md`) and its shared fixtures (`fixtures/`), the cross-language contract. `docs/superpowers/` holds this spec and the plans. |
| `custom_components/` | Everything for the Home Assistant integration. HACS allows a single directory here, so development files live inside it, or next to it as plain files. |
| `custom_components/ha_controller/` | The integration (Python). Also holds `emoji.json` (canonical emoji list, also read by the firmware build and the panel), `brand/`, `tests/` (pytest), and `frontend/` (panel source in TypeScript, Lit and Vite, built to `frontend/dist/`, which is git-ignored). |
| `custom_components/pyproject.toml`, `requirements_test.txt`, `__init__.py` | Python test and lint configuration for the integration. The empty `__init__.py` keeps test imports under `custom_components.ha_controller`. |
| `esphome/` | Everything for the firmware: device config, packages, simulator config, external components, C++ host tests, web installer page, `requirements.txt` (ESPHome version) and its venv (`esphome/.venv`, git-ignored) |
| `.github/workflows/` | CI, firmware CI, release |
| `.github/scripts/` | Release and repository-check tooling (versioning, packaging, GitHub Pages site builder, docs and fixture checks), with its own `pyproject.toml`, `requirements.txt` and `tests/` |
| `.claude/` | `CLAUDE.md`, Claude Code skills and agents |
| `3D_models/`, `files/` | Existing enclosure models (unchanged) |
