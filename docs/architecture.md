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
- **Panel** (`frontend/`): the block map editor, built with Lit and Vite and served from the integration.
- **Firmware** (`esphome/`): a generic renderer. It parses the layout and states it receives, draws the blocks and reports touches as events.
- **Distribution** (`scripts/`, `.github/workflows/`): HACS release zip, firmware builds and the web installer on GitHub Pages.

## Handshake: hello, layout and states

When the screen connects (or reboots) it fires a `hello` event carrying its firmware version and the protocol version. The integration answers with `set_layout` (the compiled layout payload with its revision) and then `set_states` (the current Home Assistant states of the entities the layout uses). Afterwards it sends `set_states` again whenever a watched entity changes, and `set_layout` whenever the stored layout changes. The exact messages are defined in `docs/protocol.md` and pinned by `protocol/fixtures/`.

## Controls become service calls

A touch on a block (a knob turn, a tap on a custom item) is sent by the firmware as a `control` event. The integration maps the event to a Home Assistant service call using the stored layout, never trusting the device for entity ids or service names, and runs it. The resulting state change flows back to the screen through `set_states`.

## Firmware updates

The integration version is the single version of the repository. The integration creates an `update` entity per screen: the installed version comes from the last hello and the latest version is the integration version. Installing calls the device's `install_firmware` action with the OTA URL on GitHub Pages (`firmware/<version>/`). With the `auto_update` option on, a hello reporting a different version triggers one automatic install attempt per screen and version, only for release versions. OTA needs internet access from the screen. Without it, re-flash over USB from the web installer.

## Repository layout

| Path | Content |
|---|---|
| `docs/` | User and developer documentation. `docs/superpowers/` holds this spec and the plans. |
| `protocol/fixtures/` | Shared test fixtures: the cross-language contract |
| `custom_components/ha_controller/` | Home Assistant integration (Python) |
| `custom_components/ha_controller/emoji.json` | Canonical list of supported emoji, read by the firmware build, the panel and the integration |
| `custom_components/ha_controller/frontend/` | Built panel bundle (generated, git-ignored) |
| `frontend/` | Panel source (TypeScript, Lit, Vite) |
| `esphome/` | Firmware: device config, packages, simulator config, external components, host tests, web installer page |
| `scripts/` | Versioning, packaging, GitHub Pages site builder |
| `tests/` | Python tests (protocol fixtures, docs, integration, scripts) |
| `.claude/` | Claude Code skills and agents |
| `.github/workflows/` | CI, firmware CI, release |
| `3D_models/`, `files/` | Existing enclosure models (unchanged) |
