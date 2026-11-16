# HA Controller — Design Spec

| | |
|---|---|
| Date | 2026-11-16 |
| Status | Approved 2026-11-16, executed with subagent-driven development |
| Repository | https://github.com/pyxel-dev/HA-controller |
| Plans | `docs/superpowers/plans/2026-11-16-ha-controller-1-foundation.md` → `…-5-release.md` (execute in order 1, 2, 3, 4, 5) |

## 1. Goal

Turn the Waveshare ESP32-S3-Touch-AMOLED-1.75 into a Home Assistant remote. In a Home Assistant sidebar panel, the user draws a map of **blocks** on a grid. The screen shows one block at a time. To move to a neighbouring block, the user swipes in from the screen edge on that side. A block controls one entity with a knob (light brightness or thermostat temperature), or it shows custom content: text, emoji, entity states, the screen's battery level and a screen brightness control.

## 2. Requirements

| ID | Requirement (from the product owner) |
|---|---|
| R1 | Documentation lives in `/docs`. Everything in the repository is written in English. |
| R2 | `/esphome` contains everything needed to build and flash the firmware. Flashing works from an HTML page served by GitHub Pages. |
| R3 | The web page states the firmware version it installs. The firmware version always equals the integration version. |
| R4 | Home Assistant updates the screen firmware automatically. |
| R5 | Claude Code skills and agents guide future development. |
| R6 | The Home Assistant view mirrors on-screen navigation: blocks on a grid, a start block, and "+" placeholders around existing blocks ([reference screenshot](assets/editor-reference.png)). |
| R7 | Navigation: put a finger on a screen edge and slide towards the centre to move to the neighbour on that side. For example, right edge + slide left goes to the right neighbour. Transitions are smooth. |
| R8 | Entity blocks: a light with a brightness knob, a thermostat with a temperature knob. |
| R9 | Custom blocks: text, emoji, textual entity states, and screen info (battery %, screen brightness control). |
| R10 | Font size and background are configurable per block from the integration. |
| R11 | The screen sleeps after a delay set in the integration (default 20 s). A touch wakes it. |

## 3. Architecture

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

- The screen is an ordinary ESPHome device, adopted by Home Assistant's ESPHome integration. The custom integration opens no connection of its own. It calls the device's user-defined ESPHome actions, which Home Assistant exposes as services `esphome.<node>_<action>` (node name with `-` replaced by `_`). It also listens to the `esphome.ha_controller_*` events fired by the device.
- Home Assistant's ESPHome integration adds `device_id` to every device event. It requires the "Allow the device to perform Home Assistant actions" option for actions, but not for events (`homeassistant/components/esphome/manager.py`). The design uses events only, so that option can stay off.
- The integration is the single source of truth for both the layout and the version. The firmware is a generic renderer.

### Repository layout

| Path | Content |
|---|---|
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

## 4. Hardware & firmware platform

| Item | Value |
|---|---|
| Board | Waveshare ESP32-S3-Touch-AMOLED-1.75: ESP32-S3R8 (8 MB octal PSRAM), 16 MB flash, USB-C (native USB) |
| Display | 1.75" round AMOLED, 466×466, CO5300 over QSPI. CS GPIO12, SCLK GPIO38, D0–D3 GPIO4/5/6/7, RESET GPIO39. TE (GPIO13) is not used. |
| Touch | CST9217 (I²C 0x5A). INT GPIO11, RESET GPIO40. Transform: mirror_x + mirror_y. |
| I²C bus | SDA GPIO15, SCL GPIO14, 400 kHz. Shared by AXP2101 0x34, TCA9554 0x20, QMI8658 0x6B, PCF85063 0x51, ES8311 0x18 and ES7210 0x40. |
| PMU | AXP2101 at 0x34: battery %, voltage, charging (registers in §4.1) |
| ESPHome | 2026.10.2, pinned in `esphome/requirements.txt`. `min_version: 2026.10.0`, framework esp-idf. |
| Display driver | `display: platform: mipi_spi`, `model: CO5300`, `bus_mode: quad`. Brightness through `set_brightness(uint8_t)`. |
| Touch driver | External component `cst9217` from https://github.com/shelson/esphome-cst9217, pinned to a commit SHA |
| UI | ESPHome `lvgl:`, which bundles LVGL 9.5. The `ha_controller` external component drives it at runtime through the LVGL C API. |
| JSON | ArduinoJson 7, bundled by ESPHome's `json:` component |
| Native API | Max message size 32 768 bytes. Plaintext (no encryption key in a prebuilt binary). |

**4.1 AXP2101 registers** (from XPowersLib):
- Enable the ADC: set bit 0 of 0x30.
- Enable battery detection: set bit 0 of 0x68.
- Battery present: bit 3 of 0x00.
- Charging: `(reg 0x01 >> 5) == 0x01`.
- Battery %: register 0xA4 (0–100).
- Battery mV: `((reg 0x34 & 0x1F) << 8) | reg 0x35`.

The display and touch rails are powered by default, so the firmware does not touch the LDO registers.

**4.2 Fonts** compiled into the firmware (sizes in px):

| Size key | Text font (Inter 600, glyphset `GF_Latin_Core`) | Value font (Inter 600, glyphs `" 0123456789.,-+%°CFOfn—"`) | Emoji font (Noto Emoji, glyphs from `emoji.json`) |
|---|---|---|---|
| `s` | 20 | 40 | 32 |
| `m` | 28 | 56 | 48 |
| `l` | 40 | 72 | 64 |
| `xl` | 56 | 96 | 88 |

A glyph missing from a font is not drawn. v1 targets Latin scripts.

## 5. On-screen UX

**5.1 Grid.** Blocks sit on integer cells `(x, y)`. `x` grows to the right and `y` grows **downwards**, exactly as drawn in the panel.
- The screen shows the start block after a layout is applied and after a reboot.
- When a new layout arrives, the screen stays on the current block if a block with the same id still exists. Otherwise it goes to the start block.

**5.2 Edge swipe.** The touch point is classified on the round display, with `size = 466` and centre `c = (size/2, size/2)`:
- `r = distance(point, c)`. If `r < size/2 − 36`, there is no edge and the touch goes to the widgets.
- Otherwise the dominant axis of `(dx, dy) = point − c` picks the edge. If `|dx| ≥ |dy|`, it is RIGHT when `dx ≥ 0` and LEFT otherwise. If not, it is BOTTOM when `dy > 0` and TOP otherwise.
- Edge → target cell: RIGHT `(x+1, y)`, LEFT `(x−1, y)`, TOP `(x, y−1)`, BOTTOM `(x, y+1)`.
- Progress is the inward finger travel along the edge's axis, clamped to `[0, size]`:
  - RIGHT: `start_x − x`
  - LEFT: `x − start_x`
  - TOP: `y − start_y`
  - BOTTOM: `start_y − y`

  Outward and perpendicular motion is ignored.
- With a target, the current page and the target page follow the finger (offset = progress). Without a target, the current page rubber-bands: offset = `min(progress × 0.3, 48)`.
- On release, the navigation commits if a target exists and either `progress ≥ 0.25 × size`, or velocity ≥ 0.6 px/ms with `progress ≥ 24`. Velocity is measured over the last 100 ms. Otherwise both pages slide back.
- Edge touches are captured by a transparent full-screen object on LVGL's top layer. Its hit test only accepts points in the edge ring, so every other touch reaches the page widgets.

**5.3 Transition.**
- After release, the pages animate to their final position with an ease-out curve. The duration is `clamp(220 × remaining_px / size, 80, 220)` ms.
- Only the current page and the target page are visible; every other page is hidden.

**5.4 Edge hints.** A short arc (20°, 6 px, white at 60 % opacity) marks each edge of the current block that has a neighbour.

**5.5 Common page rendering.**
- Each page is a full-screen object filled with the block background.
- Text is black (`#000000`) if the background's WCAG relative luminance is `> 0.30`, otherwise white (`#FFFFFF`).
- Interactive controls stay inside the circle of radius `233 − 36 − 12 = 185` px, so they never overlap the edge ring.

**5.6 Light block.** The name sits at the top, in the text font of the block size.
- **Dimmable light:** a 270° arc knob (diameter 370 px, width 28 px, gap at the bottom) with range 0–100.
  - The centre shows `NN%` or `Off` in the value font.
  - Tapping the centre toggles the light.
  - Releasing the knob sends the new brightness; 0 turns the light off.
- **On/off-only light:** a 220 px round toggle button in the centre, showing `On`/`Off`.
- **Unavailable entity:** the centre shows `—` with a small `Unavailable` label below, and the controls are disabled.

**5.7 Climate block.**
- The name sits at the top, with an arc knob over `[min, max]` in steps of `step`.
- The centre shows the target, e.g. `21.5°`: one decimal when `step < 1`, none otherwise.
- A small label below shows `Now <current>` and the action, e.g. `Heating`.
- Releasing the knob sends the new target.
- If the entity is unavailable or has no single target temperature, the centre shows `—` and the knob is disabled.

**5.8 Custom block.** Items are stacked vertically and centred with an 8 px gap. Each item has its own font size, defaulting to the block's.
- `text`: a label.
- `emoji`: a label in the emoji font.
- `entity`: a label showing the state text pushed by Home Assistant.
- `battery`: a row `🔋 87 %` (`⚡` while charging), fed by the local battery sensor.
- `brightness`: a row with `☀` and a 220 px slider (5–100 %). It drives the local screen brightness number, applied at most every 100 ms while dragging and always on release.

A custom block with no items shows its name centred.

**5.9 Messages.** A full-screen message (title in `m`, detail in `s`) replaces the pages when:

| Condition | Title | Detail |
|---|---|---|
| No layout received since boot | `Waiting for Home Assistant` | `<node name> · v<version>` |
| Layout protocol not supported | `Firmware update required` | `Open Home Assistant to update` |
| Layout invalid | `Invalid layout` | parse error code |
| Layout has no blocks | `No blocks yet` | `Add blocks in Home Assistant › HA Controller` |
| OTA running | `Updating firmware…` | `Do not unplug the screen` |
| OTA failed (shown 5 s) | `Update failed` | `Check the screen's internet access` |

**5.10 Interaction hold.** After a local interaction with a block (knob or toggle), incoming state updates for that block are held for 1500 ms; then the latest one is applied. This stops the knob from jumping back while Home Assistant catches up.

**5.11 Sleep.**
- **Delay:** a per-screen setting (`sleep` in the payload). `0` means never; otherwise 5–3600 s. The default is 20 s, which also applies before the first layout arrives.
- **Going to sleep:** when LVGL has seen no touch activity for the delay, the display brightness goes to 0 and LVGL rendering is paused. Wi-Fi and the Home Assistant connection stay up. Incoming layouts and states are applied without waking the screen.
- **Waking:** releasing a touch wakes the screen. The waking touch never reaches a widget. Brightness returns to the `Screen brightness` value and the inactivity timer restarts.
- **Exceptions:**
  - Firmware-update messages (§5.9) wake the screen.
  - While the screen sleeps, a `Screen brightness` change is stored and applied on wake.
- **No deep sleep:** it would drop the Home Assistant connection.

## 6. Layout model (integration and panel)

The layout is stored per screen under the Home Assistant storage key `ha_controller.layout.<entry_id>` and exchanged with the panel over websocket. The reference layout `docs/protocol/fixtures/layouts/valid/reference.json` mirrors the screenshot:

```json
{ "version": 1, "start": "b1", "settings": { "sleep_timeout": 20 }, "blocks": [
  { "id": "b1", "x": 0, "y": 0, "name": "Kitchen", "background": "#5B9E4D", "font_size": "m",
    "type": "entity", "entity_id": "light.kitchen" },
  { "id": "b2", "x": 0, "y": -1, "name": "Lights", "background": "#C94F3D", "font_size": "m",
    "type": "entity", "entity_id": "light.living_room" },
  { "id": "b3", "x": -1, "y": 0, "name": "Hello World", "background": "#4F86DD", "font_size": "l",
    "type": "custom", "items": [
      { "id": "i1", "kind": "text", "text": "Hello World", "font_size": null },
      { "id": "i2", "kind": "emoji", "emoji": "👋", "font_size": "xl" },
      { "id": "i3", "kind": "entity", "entity_id": "sensor.outdoor_temperature", "attribute": null, "font_size": "s" },
      { "id": "i4", "kind": "battery", "font_size": "s" },
      { "id": "i5", "kind": "brightness", "font_size": null } ] },
  { "id": "b4", "x": -1, "y": 1, "name": "Bedroom", "background": "#7B2FA0", "font_size": "m",
    "type": "entity", "entity_id": "climate.bedroom" } ] }
```

Unknown keys are ignored, so the panel can keep `entity_id` and `items` when the user switches a block's type.

Validation returns a list of `{code, ref}`, where `ref` is the offending block or item id, or `null`. An empty list means the layout is valid. It runs in three phases:
1. **Structure.** It stops at the first error.
2. **Per-field checks.** All errors are collected.
3. **Connectivity.** Only runs if phase 2 found nothing.

| Code | Rule |
|---|---|
| `invalid_structure` | `version` must be `1`, `settings` an object, `blocks` a list, and blocks and items objects with the expected JSON types |
| `too_many_blocks` | At most 32 blocks |
| `invalid_sleep_timeout` | `settings.sleep_timeout` is an integer (not a boolean): `0` (never) or 5–3600 seconds |
| `invalid_id` | Ids match `^[a-z][a-z0-9]{0,7}$` |
| `duplicate_id` | Ids are unique across blocks **and** items |
| `coordinate_out_of_range` | `-32 ≤ x, y ≤ 32` (integers) |
| `duplicate_position` | One block per cell (ref = the later block) |
| `invalid_start` | `start` is `null` if and only if there are no blocks; otherwise it is the id of an existing block |
| `disconnected` | Every block is reachable from `start` through 4-neighbour cells (one error per unreachable block, in layout order) |
| `invalid_name` | 1–32 characters after trimming |
| `invalid_background` | `^#[0-9A-Fa-f]{6}$` |
| `invalid_font_size` | Block: `s`/`m`/`l`/`xl`. Item: the same, or `null` (inherit). |
| `invalid_type` | `entity` or `custom` |
| `invalid_entity` | Entity block: an `entity_id` of domain `light` or `climate`. Entity item: an id matching `^[a-z0-9_]+\.[a-z0-9_]+$`, and `attribute` either `null` or 1–64 characters. |
| `too_many_items` | At most 6 items per custom block |
| `invalid_item` | `kind` is one of `text`, `emoji`, `entity`, `battery`, `brightness` |
| `invalid_text` | Text item: 1–64 characters |
| `unsupported_emoji` | Emoji item: after removing U+FE0F, the value is an entry of `emoji.json` |
| `payload_too_large` | The compiled payload (§7.3) is larger than 24 576 UTF-8 bytes. Checked by the integration only. |

Lengths count Unicode code points (Python `len`, JavaScript `Array.from(text).length`), and names are trimmed of Unicode whitespace (`str.strip()`, `String.prototype.trim()`). The fixtures `astral-text` (valid) and `invalid_name-astral` pin this.

Entities that do not exist (yet) are valid; the screen shows them as unavailable.

## 7. Device protocol v1 (normative)

`PROTOCOL_VERSION = 1`. `docs/protocol/README.md` is the living copy of this section. `docs/protocol/fixtures/` pins it with examples, used by the tests of all three implementations.

**7.1 Actions (Home Assistant → screen).** Services `esphome.<node>_<action>`:

| Action | Variables | Effect |
|---|---|---|
| `set_layout` | `layout: string` (payload JSON, §7.3) | Parse it. On success, rebuild the pages and adopt `rev`. Then fire a hello with reason `applied`; this also happens after a failure, with the revision unchanged. |
| `set_states` | `states: string` (JSON array, §7.4) | Apply each update to the block or item with that id. Unknown ids are ignored. |
| `install_firmware` | `url: string`, `md5_url: string` | Show `Updating firmware…`, render it immediately, then run `ota.http_request.flash`. On failure, show `Update failed` for 5 s. |

**7.2 Events (screen → Home Assistant).** Data values are strings, and Home Assistant adds `device_id`.

| Event | Data | When |
|---|---|---|
| `esphome.ha_controller_hello` | `node` (ESPHome node name), `version` (firmware version), `protocol` (`"1"`), `revision` (applied `rev` or `none`), `reason` (`connected` / `heartbeat` / `applied`) | 5 s after an API client connects, every 60 s while connected, and after each `set_layout` |
| `esphome.ha_controller_control` | `block` (block id), `item` (item id or empty), `op` (`toggle` / `set`), `value` (decimal, `%.2f`) | Centre tap on a light (`toggle`), knob release (`set`) |

**7.3 Layout payload.** The integration compiles it from the stored layout:
- **Top level:** `v` (1), `rev`, `start` (id or `null`), `sleep` (integer seconds, `0` = never), `blocks`.
- **Block:** `id`, `x`, `y`, `name`, `bg` (6 uppercase hex digits, no `#`), `font`, `widget`.
  - `widget` is `light` or `climate` (taken from the entity domain), or `custom`.
  - Custom blocks also carry `items` (possibly empty). Entity blocks carry no `items`.
- **Item:** `id`, `kind`, `font` (the item's size, or the block's when the item's is `null`).
  - `text` items carry `text` (the text).
  - `emoji` items carry `text` (the emoji without U+FE0F).
  - Other kinds carry no `text`.
- No entity ids are sent to the screen.
- `rev` is the first 8 hex chars of SHA-256 over the UTF-8 bytes of `json.dumps(payload_without_rev, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
  - Golden values: empty payload (`sleep` 20) → `c4aad3fa`; `payloads/valid/reference.json` → `90538742`; `payloads/valid/emoji-variation.json` → `5387d4ea`.
- **Transport encoding:** compact JSON (`separators=(",", ":")`, `ensure_ascii=False`), at most 24 576 bytes.

Device parse errors:
- `bad_json`: not JSON, or not an object.
- `unsupported_version`: `v != 1`.
- `invalid_payload`: a missing or mistyped field, an unknown `widget`, `kind` or `font`, or a `sleep` outside 0–3600.

**7.4 State updates.** A JSON array. Each element has `id` (block or item id) and `available` (bool, default `true`):

| Target | Fields |
|---|---|
| Light block | `on` (bool), `brightness` (0–100 integer; `null` for on/off-only lights; `0` when a dimmable light is off) |
| Climate block | `target` (number or `null`), `min`, `max`, `step` (numbers), `unit` (`°C`/`°F`), `current` (display string), `action` (display string, e.g. `Heating`) |
| Entity item | `text` (display string) |

An unavailable or missing entity sends `{"id": …, "available": false}`. Entity items send `{"id": …, "text": "—"}` instead. Updates are sent in layout order, in chunks of at most 8 192 bytes.

**7.5 Handshake and resync** (integration side):
- **On a hello from the screen's `device_id`:** record the node, version, protocol, revision and time. Then:
  - If `protocol ≠ 1`, push nothing (auto-update may run, §11).
  - Else, if `revision ≠` the current revision, push the layout and then all states. Push immediately when `reason = connected`. Otherwise push at most once per 300 s for the same revision.
  - Else, if `reason = connected`, or this is the first hello since the integration (re)started, push all states. After an integration reload the ESPHome connection stays up, so no `connected` hello arrives.
- **Entity state changes:** coalesced for 200 ms, then pushed for the changed entities. This only happens while the screen is online (a hello within the last 150 s) and on protocol 1.
- **Saving a layout:** pushes it immediately if the screen is online.

**7.6 Control mapping** (integration side). The entity always comes from the layout, never from the event.

| Block | op | Service call |
|---|---|---|
| Light | `toggle` | `light.toggle` `{entity_id}` |
| Light | `set`, value ≤ 0 | `light.turn_off` `{entity_id}` |
| Light | `set`, value > 0 | `light.turn_on` `{entity_id, brightness_pct: round(clamp(value, 1, 100))}` |
| Climate | `set` | `climate.set_temperature` `{entity_id, temperature: clamp(value, min_temp, max_temp)}` (bounds from the current state, defaults 7/35) |

Anything else is ignored: an unknown block, a custom block, an unparsable value. Service errors are logged, never raised.

**7.7 State builders** (integration side):
- **Light:**
  - Unavailable if the entity is missing, `unavailable` or `unknown`.
  - Dimmable if `supported_color_modes` contains a mode other than `onoff`.
  - Brightness: `round((attribute brightness or 255) × 100 / 255)` when on, `0` when off, `null` when not dimmable.
- **Climate:**
  - `unit` is Home Assistant's temperature unit.
  - `step` is `target_temp_step`, or else `0.5` for °C and `1` for °F.
  - `min`/`max` come from `min_temp`/`max_temp` (defaults 7/35).
  - `current` is `"<current_temperature> <unit>"`, or `—`.
  - `action` is `hvac_action`, or else the state, with `_` replaced by a space and the first letter capitalised.
- **Entity item:**
  - `—` if the entity is missing, `unavailable` or `unknown`, or if the attribute is missing.
  - A numeric value is rounded to the entity registry's `sensor.display_precision`, or else `suggested_display_precision`, or else left unchanged.
  - The result is `"<value> <unit>"` when a unit exists, truncated to 64 characters.

## 8. Home Assistant integration

- **Config flow:** one entry per screen.
  - Step `user` shows a device selector filtered to `integration: esphome, manufacturer: pyxel-dev, model: ha-controller`. Home Assistant derives the manufacturer and model from the firmware's `project.name: pyxel-dev.ha-controller`.
  - The manufacturer and model are checked server-side (error `not_ha_controller`).
  - `unique_id` = device id. Title = device name. Data: `{"device_id": …}`.
- **Options flow** (plan 5): `auto_update` (bool, default `true`).
- **Runtime:** `entry.runtime_data` is a `ScreenController`. It owns the layout store, the compiled payload and revision, the device status, the event listeners (filtered by `device_id`), entity tracking, and firmware installs.
- **Websocket API** (admin only):
  - `ha_controller/screens` → `{"screens": [{entry_id, title, device_id, online, firmware_version, integration_version, protocol_ok, revision, device_revision}]}`
  - `ha_controller/layout/get` `{entry_id}` → `{"layout": …}`
  - `ha_controller/layout/save` `{entry_id, layout}` → `{"revision": …, "pushed": bool}`. Errors: `not_found`, and `invalid_layout` with message `code@ref, …`.
- **Panel:**
  - Sidebar entry "HA Controller", icon `mdi:remote`, URL `/ha-controller`, admins only.
  - The module is served from `/ha_controller_static/ha-controller-panel.js?v=<version>`.
  - Registered with the first loaded entry and removed with the last.
- **Manifest:** `dependencies: ["frontend", "http", "panel_custom", "websocket_api"]`, `after_dependencies: ["esphome"]`, `integration_type: device`, `iot_class: local_push`. Brand images live in `custom_components/ha_controller/brand/`.
- **Minimum Home Assistant:** 2026.10.0 (Python 3.14).

## 9. Panel UX

- **Header:**
  - A screen selector, when there are several screens.
  - A status line: `Online · firmware 0.1.0 · in sync`, `Offline`, or `Firmware 0.0.9 — update available`.
  - `Revert` and `Save` buttons, disabled when nothing changed or the layout has errors.
- **Map** (see the [reference screenshot](assets/editor-reference.png)):
  - A CSS grid of 96 px square cells with 12 px gaps and a 16 px radius, covering blocks and placeholders. Columns follow `x` ascending, rows follow `y` ascending.
  - Blocks are filled with their background and show their name in the contrast text colour.
  - The start block has a 3 px outline and a `start` badge.
  - Placeholders (2 px dashed border, `+`) appear on every empty 4-neighbour of a block. If there is no block, there is only one, at `(0, 0)`. There are none at 32 blocks, and none for cells out of range.
  - The selected block has a ring in the theme's primary colour.
- **Adding a block:** clicking a placeholder adds a block there and selects it. The first block becomes the start block. Defaults:
  - id `b<n>`, name `Block <n>`;
  - background from the palette `#C94F3D #4F86DD #5B9E4D #7B2FA0 #E08A2E #2E9E8F #D2477A #5C6BC0`, picked by block count;
  - font `m`, type `custom`, no items.
- **Editor** for the selected block:
  - Name, background (colour input + palette swatches), font size (S/M/L/XL), type (Entity/Custom).
  - An entity picker limited to `light.*`/`climate.*`.
  - For custom blocks, an items list: add Text, Emoji, Entity state, Battery or Screen brightness; edit, move up/down, remove; per-item font size with "Inherit". The emoji picker shows only `emoji.json`.
  - `Set as start block`.
  - `Delete block`, disabled with the reason when it is the start block of a multi-block layout or when deleting it would disconnect other blocks.
  - A 220 px round preview showing the background, the contrast text and the content.
- **Validation** runs locally with the same rules and codes as the integration. Errors are listed with human messages and highlighted on the map.
- **Screen settings:** a "Screen" section under the map with a "Sleep after (seconds)" input. Default 20; `0` keeps the screen on. Validated with `invalid_sleep_timeout`.
- **Refresh and save:** the screen list refreshes every 10 s. Saving reports `Saved — sent to the screen.` or `Saved — the screen is offline and will update when it reconnects.`

## 10. Versioning & distribution

- **One version:** a single SemVer version `X.Y.Z` for the whole repository, stored in three places:
  - `custom_components/ha_controller/manifest.json` (`version`)
  - `esphome/version.yaml` (`substitutions.project_version`)
  - `custom_components/ha_controller/frontend/package.json` (`version`)

  `.github/scripts/versioning.py check [--tag vX.Y.Z]` fails CI on any mismatch, and `.github/scripts/versioning.py bump X.Y.Z` rewrites all three. The initial version is `0.1.0`.
- **Release:** pushing tag `vX.Y.Z` cuts a release. The release workflow:
  1. verifies the versions;
  2. builds the panel;
  3. packages `ha_controller.zip`: the contents of `custom_components/ha_controller/` without `tests/` and the panel sources, plus the built panel `frontend/dist/ha-controller-panel.js`;
  4. compiles the firmware;
  5. publishes a GitHub release with `ha_controller.zip`, `ha-controller-X.Y.Z.factory.bin`, `ha-controller-X.Y.Z.ota.bin` and `ha-controller-X.Y.Z.ota.bin.md5`.
- **GitHub Pages:** the release workflow then rebuilds `https://pyxel-dev.github.io/HA-controller/` from the release assets:
  - `index.html` (web installer);
  - `firmware/manifest.json` (ESP Web Tools manifest for the latest version);
  - `firmware/ha-controller.factory.bin` (latest);
  - `firmware/<version>/ha-controller.ota.bin` + `.md5` for every release.
- **Web installer:** an ESP Web Tools 10.5.2 install button. The page prints "Firmware X.Y.Z" (substituted at build time) and links to the release notes. It explains:
  - USB-C with Chrome or Edge;
  - Wi-Fi setup, through Improv serial or the `HA Controller` access point + captive portal;
  - adding the screen in Home Assistant;
  - installing the integration with the **same version** through HACS.
- **HACS:** a custom repository. `hacs.json` sets `zip_release: true`, `filename: ha_controller.zip` and `homeassistant: 2026.10.0`.

## 11. Firmware updates

- **Update entity:** the integration creates one `update` entity per screen ("HA Controller firmware"), attached to the screen's device.
  - `installed_version` is the version from the last hello.
  - `latest_version` is the integration version.
  - `release_url` is the release page.
  - `version_is_newer` returns `latest != installed`. A firmware newer than the integration (after an integration rollback) therefore also shows as an update.
- **Install:** calls `install_firmware` with `https://pyxel-dev.github.io/HA-controller/firmware/<latest>/ha-controller.ota.bin` and its `.md5`, and sets `in_progress`. It then waits up to 300 s for a hello carrying `<latest>`, and raises an error otherwise.
- **Auto-update** (option `auto_update`, default on): the integration installs automatically when all of these hold:
  - a hello reports a version different from the integration version;
  - the integration version is a release (`^\d+\.\d+\.\d+$`);
  - no install is running.

  It makes at most one automatic attempt per screen and version every 3600 s.
- **Network requirement:** OTA requires internet access from the screen to GitHub Pages. Without it, re-flash over USB from the web installer.
- **No ESPHome `update:` entity:** the firmware does not define one of its own.

## 12. Testing strategy

- **Shared fixtures** in `docs/protocol/fixtures/`, read by the Python, TypeScript and C++ tests:
  - `layouts/valid`
  - `layouts/invalid` (expected code + ref)
  - `payloads/valid` (stored layout + golden payload)
  - `payloads/invalid` (raw text + expected device parse error)
  - `states` (Home Assistant states + expected updates)
  - `controls` (event + expected service call)
  - `colors.json` (background → text colour)
- **Integration:** pytest + `pytest-homeassistant-custom-component`, ruff. hassfest and HACS validation run in CI.
- **Panel:** vitest (model, and components with happy-dom), `tsc --noEmit`, production build.
- **Firmware:**
  - Host C++ tests (CMake, doctest, ArduinoJson 7) for the pure modules: layout and state parsing, knob scale, gestures, colours, AXP2101 decoding.
  - `esphome compile` of the device and simulator configs.
  - A manual hardware checklist in `docs/development.md`.
- **Simulator:** `esphome/simulator.yaml` runs the same UI on a desktop (ESPHome `host` platform + SDL, 466×466) and accepts Home Assistant API connections.

## 13. Developer guidance (Claude Code)

- `.claude/CLAUDE.md`: purpose; rules (English only, one version, protocol changes go through the protocol skill, TDD); repository map; commands.
- Skills (`.claude/skills/`): `protocol-change`, `add-widget`, `firmware-dev`, `release`.
- Agents (`.claude/agents/`): `protocol-guardian`, `ha-integration-reviewer`, `firmware-reviewer`.

## 14. Out of scope for v1

- PWR button handling.
- Deep sleep.
- IMU, RTC, audio and SD card features.
- Colour emoji.
- Non-Latin scripts.
- Entity widgets other than light and climate, such as switch, cover, fan or media player. Add them with the `add-widget` skill.
- Drag-and-drop to move blocks.
- Several layouts per screen.
- Panel translations.
- OTA without internet access.
- Automatic discovery of new screens.
- API encryption in the prebuilt firmware.

## 15. Constants

| Name | Value |
|---|---|
| Screen size | 466 px |
| Edge ring width | 36 px |
| Commit distance / flick | 0.25 × size / 0.6 px/ms with ≥ 24 px |
| Rubber band | × 0.3, max 48 px |
| Settle animation | clamp(220 × remaining / size, 80, 220) ms, ease-out |
| Interaction hold | 1500 ms |
| Max blocks / items / name / text | 32 / 6 / 32 / 64 |
| Coordinate range | −32…32 |
| Max payload / state chunk | 24 576 / 8 192 bytes |
| Hello delay / heartbeat | 5 s / 60 s |
| Online timeout | 150 s |
| Push retry (same revision) | 300 s |
| State coalescing | 200 ms |
| Install timeout | 300 s |
| Auto-update retry | 3600 s |
| Panel status refresh | 10 s |
| Sleep delay | default 20 s; `0` = never; otherwise 5–3600 s |
