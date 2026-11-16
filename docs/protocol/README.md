# Device protocol v1

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

`PROTOCOL_VERSION = 1`. This page is the living copy of this section. `docs/protocol/fixtures/` pins it with examples, used by the tests of all three implementations.

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
  - Else, if `reason = connected`, push all states.
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


## Fixtures

`fixtures/` is the executable contract of this protocol. The examples pin it, and all three implementations test themselves against them. All files are UTF-8 JSON without a BOM.

| Folder | Content | Read by |
|---|---|---|
| `fixtures/layouts/valid`, `fixtures/layouts/invalid` | Stored layouts and the validation error each invalid one must produce | pytest in `custom_components/ha_controller/tests`, vitest in `custom_components/ha_controller/frontend/test` |
| `fixtures/payloads/valid` | A stored layout and the compiled payload (with golden `rev`) | pytest in `custom_components/ha_controller/tests`, vitest in `custom_components/ha_controller/frontend/test`, doctest in `esphome/tests` |
| `fixtures/payloads/invalid` | Raw strings sent to `set_layout` and the parse error expected | doctest in `esphome/tests` |
| `fixtures/states` | Home Assistant states and the expected update objects | pytest in `custom_components/ha_controller/tests` |
| `fixtures/controls` | Control events and the expected service call | pytest in `custom_components/ha_controller/tests` |
| `fixtures/colors.json` | Background colours and the expected text colour | pytest in `custom_components/ha_controller/tests`, vitest in `custom_components/ha_controller/frontend/test`, doctest in `esphome/tests` |

The consumers are:

- pytest: `custom_components/ha_controller/tests` and `.github/scripts/tests` (the latter checks the fixtures themselves);
- vitest: `custom_components/ha_controller/frontend/test`;
- doctest: `esphome/tests`.

### One broken rule per invalid fixture

Each file in `fixtures/layouts/invalid` takes a valid layout and breaks exactly one rule. Its stem is the expected error code, or the code followed by `-` and a suffix when a code has several cases.

### Canonical revision

```python
hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:8]
```

`p` is the payload without its `rev` key. Recompute the golden `rev` of `fixtures/payloads/valid/*.json` whenever a payload changes.
