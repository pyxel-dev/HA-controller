# HA Controller — Plan 2: Home Assistant Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `ha_controller` custom integration: config flow, layout validation and compilation, state builders, the sync engine that talks to the screen through ESPHome actions and events, control mapping, the websocket API and the sidebar panel registration.

**Architecture:**
- **Pure modules:** `layout.py`, `compiler.py`, `states.py` and `controls.py` hold the protocol logic. They are tested against `docs/protocol/fixtures/`.
- **`ScreenController`:** one per config entry. It wires those modules to Home Assistant: storage, event listeners filtered by `device_id`, entity tracking, and calls to the screen's `esphome.<node>_<action>` services.
- **`websocket.py` and `panel.py`:** expose the controller to the panel built in plan 3.

**Tech Stack:** Python 3.14, Home Assistant ≥ 2026.10, `pytest-homeassistant-custom-component==0.13.375` (pins Home Assistant 2026.10.4), ruff, Pillow (brand icon script only).

**Spec:** `docs/superpowers/specs/2026-11-16-ha-controller-design.md` (§6–§8, §15)

## Global Constraints

- Domain `ha_controller`, name "HA Controller", `MANUFACTURER = "pyxel-dev"`, `MODEL = "ha-controller"`.
- Minimum Home Assistant 2026.10.0. Python 3.14.
- **Python environment:** the integration has its own venv `custom_components/.venv`. Create it with `python3.14 -m venv custom_components/.venv`, install `custom_components/requirements_test.txt`, and run pytest and ruff from it. The repository checks keep their own venv, `.github/scripts/.venv`.
- Protocol v1 and constants exactly as spec §6, §7 and §15, defined once in `const.py`.
- Events: `esphome.ha_controller_hello` and `esphome.ha_controller_control`. Services: `esphome.<node with "-" → "_">_<action>`. The integration never registers its own services.
- No blocking I/O in the event loop. Read `emoji.json` with `hass.async_add_executor_job`.
- Time comparisons use `homeassistant.util.dt.utcnow()`, so tests can drive them with `freezer`.
- All user-facing strings are in English.

## Review Focus

1. **Screen reboot, Home Assistant restart or Wi-Fi drop.** The layout and states resync with no user action: hello `connected` → states; revision `none` → layout + states. A screen that keeps rejecting a layout gets at most one push per 300 s. Owner: Task 5 tests.
2. **An entity that is missing, unavailable or renamed.** Updates mark it unavailable, controls for it are ignored, and a failing service call never raises. Owner: Task 4 fixtures, Task 6 `test_service_error_is_swallowed`.
3. **Several screens configured.** A hello or control from one screen never affects another. Owner: Task 5 `test_hello_from_other_device_is_ignored`, Task 6 `test_control_from_other_device_is_ignored`.
4. **Saving while the screen is offline.** The save succeeds with `pushed: false` and no exception, and the next hello delivers the layout. Owner: Task 5 `test_save_layout_offline_returns_not_pushed`.
5. **A stored layout that no longer validates** (hand-edited storage, future downgrade). Setup must not fail; the controller uses an empty layout and logs a warning. Owner: Task 5 `test_invalid_stored_layout_falls_back_to_empty`.

---

### Task 1: Integration skeleton and config flow

**Files:**
- Create:
  - `custom_components/ha_controller/`: `__init__.py`, `const.py`, `config_flow.py`, `manifest.json`, `strings.json`, `translations/en.json`, `brand/icon.png`, `brand/icon@2x.png`
  - `.github/scripts/make_brand_icon.py`, `hacs.json`
  - `custom_components/ha_controller/tests/conftest.py`, `custom_components/ha_controller/tests/__init__.py`, `custom_components/ha_controller/tests/helpers.py`, `custom_components/ha_controller/tests/test_config_flow.py`
  - `.github/workflows/validate.yml`
  - `custom_components/pyproject.toml`, `custom_components/requirements_test.txt`, `custom_components/__init__.py` (empty)
- Modify: `.github/scripts/requirements.txt` (add `pillow`), `.github/workflows/ci.yml` (job `integration`), `.claude/CLAUDE.md` (commands)

**Interfaces:**
- Produces:
  - **`const.py`:**
    - Identity and limits: `DOMAIN`, `MANUFACTURER`, `MODEL`, `CONF_DEVICE_ID = "device_id"`, `CONF_AUTO_UPDATE = "auto_update"`, `PROTOCOL_VERSION = 1`.
    - Events and actions: `EVENT_HELLO = "esphome.ha_controller_hello"`, `EVENT_CONTROL = "esphome.ha_controller_control"`, `ACTION_SET_LAYOUT = "set_layout"`, `ACTION_SET_STATES = "set_states"`, `ACTION_INSTALL_FIRMWARE = "install_firmware"`.
    - Layout limits: `MAX_BLOCKS = 32`, `MAX_ITEMS = 6`, `MAX_NAME_LEN = 32`, `MAX_TEXT_LEN = 64`, `COORD_LIMIT = 32`, `MAX_PAYLOAD_BYTES = 24576`, `STATE_CHUNK_BYTES = 8192`.
    - Allowed values: `FONT_SIZES = ("s", "m", "l", "xl")`, `ENTITY_BLOCK_DOMAINS = ("light", "climate")`, `ITEM_KINDS = ("text", "emoji", "entity", "battery", "brightness")`.
    - Screen sleep (seconds, `0` = never): `DEFAULT_SLEEP_TIMEOUT = 20`, `MIN_SLEEP_TIMEOUT = 5`, `MAX_SLEEP_TIMEOUT = 3600`.
    - Timings: `ONLINE_TIMEOUT = timedelta(seconds=150)`, `PUSH_RETRY = timedelta(seconds=300)`, `STATE_COALESCE_SECONDS = 0.2`, `INSTALL_TIMEOUT = 300`, `AUTO_UPDATE_RETRY = timedelta(seconds=3600)`.
    - Panel: `PANEL_URL_PATH = "ha-controller"`, `PANEL_COMPONENT = "ha-controller-panel"`, `PANEL_TITLE = "HA Controller"`, `PANEL_ICON = "mdi:remote"`, `STATIC_URL = "/ha_controller_static"`.
    - Release URLs: `FIRMWARE_BASE_URL = "https://pyxel-dev.github.io/HA-controller/firmware"`, `RELEASE_URL = "https://github.com/pyxel-dev/HA-controller/releases/tag/v{version}"`.
  - **`custom_components/ha_controller/tests/helpers.py`:**
    - `async def register_screen(hass, *, name="HA Controller", manufacturer=MANUFACTURER, model=MODEL, mac="aa:bb:cc:dd:ee:ff") -> dr.DeviceEntry`. It adds an `esphome` `MockConfigEntry` and a device with `connections={(dr.CONNECTION_NETWORK_MAC, mac)}`.
    - `async def setup_screen(hass, device) -> MockConfigEntry`. It adds the `ha_controller` entry with `data={"device_id": device.id}` and `unique_id=device.id`, sets it up, and waits.
    - `NODE = "ha-controller-aabbcc"`.
    - `def hello(device, **overrides) -> dict`: a default hello for `NODE`, version `"0.1.0"`, protocol `"1"`, revision `"none"`, reason `"connected"`.
    - `def load_fixture(*parts) -> Any`: reads `docs/protocol/fixtures/...`.

- [ ] **Step 1: Write the failing tests** in `custom_components/ha_controller/tests/test_config_flow.py`, plus `custom_components/ha_controller/tests/conftest.py` with an autouse `auto_enable_custom_integrations(enable_custom_integrations)` fixture.

```python
async def test_user_step_shows_device_selector(hass): ...            # form, step_id "user", errors {}
async def test_user_step_creates_entry(hass):
    device = await register_screen(hass)
    result = await start_flow_and_submit(hass, {"device_id": device.id})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HA Controller" and result["data"] == {"device_id": device.id}
    assert result["result"].unique_id == device.id
async def test_user_step_rejects_other_device(hass):                  # model="other" → errors {"base": "not_ha_controller"}
async def test_user_step_aborts_when_already_configured(hass):        # reason "already_configured"
async def test_setup_and_unload_entry(hass):                          # LOADED, then NOT_LOADED
async def test_strings_match_english_translation():                   # strings.json == translations/en.json
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pip install -r custom_components/requirements_test.txt && pytest custom_components/ha_controller/tests/test_config_flow.py -v`
Expected: FAIL (`ModuleNotFoundError` / integration not found).

- [ ] **Step 3: Implement the skeleton.**
  - **`custom_components/requirements_test.txt`:** `pytest-homeassistant-custom-component==0.13.375`, `ruff`.
  - **`custom_components/pyproject.toml`:**
    - `[tool.pytest.ini_options]`: `testpaths = ["ha_controller/tests"]`, `pythonpath = [".."]`, `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`.
    - `[tool.ruff]`: `target-version = "py314"`, `line-length = 100`, lint rules `E,F,I,UP,B`.
  - **`custom_components/__init__.py`:** empty. pytest then imports the tests as `custom_components.ha_controller.tests.*`, so the integration is never imported a second time under the name `ha_controller`. Tests import the integration only as `custom_components.ha_controller`.
  - **`.github/scripts/requirements.txt`:** add `pillow`, for the brand icon script.
  - **`manifest.json`**, keys in hassfest order:

    ```json
    {
      "domain": "ha_controller",
      "name": "HA Controller",
      "after_dependencies": ["esphome"],
      "codeowners": ["@pyxel-dev"],
      "config_flow": true,
      "dependencies": ["frontend", "http", "panel_custom", "websocket_api"],
      "documentation": "https://github.com/pyxel-dev/HA-controller/tree/main/docs",
      "integration_type": "device",
      "iot_class": "local_push",
      "issue_tracker": "https://github.com/pyxel-dev/HA-controller/issues",
      "requirements": [],
      "version": "0.1.0"
    }
    ```

  - **`__init__.py`:**
    - `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`.
    - `async_setup` returns `True`.
    - `async_setup_entry` and `async_unload_entry` return `True`; they are filled in Task 5.
  - **`config_flow.py`:** `HaControllerConfigFlow(ConfigFlow, domain=DOMAIN)`, `VERSION = 1`, with step `user`:
    - The schema has one field, `vol.Required(CONF_DEVICE_ID)`:

      ```python
      selector.DeviceSelector(selector.DeviceSelectorConfig(filter=[
          selector.DeviceFilterSelectorConfig(integration="esphome", manufacturer=MANUFACTURER, model=MODEL)
      ]))
      ```

    - On submit, accept the device only if it exists, belongs to a config entry of domain `esphome`, and has `manufacturer == MANUFACTURER` and `model == MODEL`. Otherwise set error `not_ha_controller`.
    - Then `async_set_unique_id(device.id)`, `_abort_if_unique_id_configured()`, and create the entry with title `device.name_by_user or device.name`.
  - **`strings.json` = `translations/en.json`:**
    - User step: title "Add an HA Controller screen"; description "Pick the screen. It must already be added to Home Assistant with the ESPHome integration."; field `device_id` "Screen".
    - Error: `not_ha_controller` "This device is not an HA Controller screen."
    - Abort: `already_configured` "This screen is already set up."
  - **`hacs.json`:** `{"name": "HA Controller", "homeassistant": "2026.10.0"}`.
  - **`.github/scripts/make_brand_icon.py`:** a Pillow script that writes `brand/icon.png` (256×256) and `brand/icon@2x.png` (512×512), scaled from a 512 design:
    - transparent background;
    - a filled circle `#111827` with radius 240;
    - a ring `#374151`, width 36, radius 170;
    - an arc `#F59E0B`, width 36, radius 170, from 135° to 315°;
    - a centre dot `#F9FAFB` with radius 40.

    Run it once and commit both PNGs.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests/test_config_flow.py -v && ruff check custom_components`
Expected: PASS.

- [ ] **Step 5: Add CI.**
  - Add job `integration` to `.github/workflows/ci.yml`: setup-python 3.14, `pip install -r custom_components/requirements_test.txt`, `ruff check custom_components`, `pytest custom_components/ha_controller/tests`.
  - Create `.github/workflows/validate.yml`:
  - Triggers: `push`, `pull_request`, `schedule` (`cron: "0 0 * * *"`) and `workflow_dispatch`.
  - Job `hassfest`: checkout, then `home-assistant/actions/hassfest@master`.
  - Job `hacs`: `hacs/action@main` with `category: integration`.
  - If HACS reports the repository description or topics checks, the owner sets them once on GitHub. Description: "Home Assistant remote on the Waveshare ESP32-S3 1.75\" round AMOLED". Topics: `home-assistant`, `hacs`, `esphome`, `integration`.
  - Add to the `.claude/CLAUDE.md` commands: `pytest custom_components/ha_controller/tests` and `python .github/scripts/make_brand_icon.py`.

- [ ] **Step 6: Commit**

```bash
git add custom_components/ha_controller .github/scripts/make_brand_icon.py hacs.json custom_components/requirements_test.txt custom_components/pyproject.toml custom_components/__init__.py .github/scripts/requirements.txt .github/workflows/ci.yml .github/workflows/validate.yml .claude/CLAUDE.md
git commit -m "feat(integration): add integration skeleton and config flow"
```

---

### Task 2: Layout validation

**Files:**
- Create: `custom_components/ha_controller/layout.py`, `custom_components/ha_controller/tests/test_layout.py`

**Interfaces:**
- Produces:
  - `class LayoutError(NamedTuple): code: str; ref: str | None`
  - `def validate_layout(layout: Any, emoji: frozenset[str]) -> list[LayoutError]`
  - `def empty_layout() -> dict[str, Any]`, which returns `{"version": 1, "start": None, "settings": {"sleep_timeout": DEFAULT_SLEEP_TIMEOUT}, "blocks": []}`
  - `def normalize_emoji(text: str) -> str`, which removes U+FE0F
  - `def bound_entities(layout: dict) -> dict[str, list[str]]`: entity_id → binding ids (block ids for entity blocks, item ids for entity items), in layout order
  - `def load_emoji_file(path: Path) -> frozenset[str]` (sync) and `async def async_load_emoji(hass) -> frozenset[str]`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("path", sorted(VALID_LAYOUTS), ids=stem)
def test_valid_fixtures(path): assert validate_layout(load(path), EMOJI) == []

@pytest.mark.parametrize("path", sorted(INVALID_LAYOUTS), ids=stem)
def test_invalid_fixtures(path):
    case = load(path)
    assert validate_layout(case["layout"], EMOJI) == [LayoutError(case["expect"]["code"], case["expect"]["ref"])]

def test_connectivity_is_skipped_when_fields_are_invalid(): ...  # disconnected block + bad name → only invalid_name
def test_normalize_emoji_strips_variation_selector(): assert normalize_emoji("❄️") == "❄"
def test_bound_entities_reference():
    assert bound_entities(load_layout("reference")) == {
        "light.kitchen": ["b1"], "light.living_room": ["b2"],
        "sensor.outdoor_temperature": ["i3"], "climate.bedroom": ["b4"]}
def test_bool_is_not_a_coordinate(): ...  # x = True → coordinate_out_of_range
@pytest.mark.parametrize("value,ok", [(0, True), (5, True), (3600, True), (4, False), (3601, False), (True, False), ("20", False)])
def test_sleep_timeout_bounds(value, ok): ...  # reference with settings.sleep_timeout = value → [] or [LayoutError("invalid_sleep_timeout", None)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_layout.py -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement `validate_layout`.** It runs in three phases, following spec §6.
  - **Phase 1 — containers only.** Stop at the first error. The checks:
    - the layout is a dict;
    - `version == 1`;
    - `settings` is a dict;
    - `blocks` is a list of dicts;
    - every block with `type == "custom"` has `items` as a list of dicts.

    Each failure produces `invalid_structure` with ref `None`.
  - **Phase 2 — per field, all errors collected.** The checks run in this order:
    1. `too_many_blocks`, then `invalid_sleep_timeout`. `settings.sleep_timeout` must be an `int` that is not a `bool`, either `0` or within 5–3600.
    2. For each block: `invalid_id`, `duplicate_id`, `coordinate_out_of_range` (an `int` that is not a `bool`, within ±32), `duplicate_position`, `invalid_name`, `invalid_background`, `invalid_font_size`, `invalid_type`, then the type-specific checks. The type-specific checks are skipped when the type is invalid:
       - entity blocks: `invalid_entity`;
       - custom blocks: `too_many_items`, then for each item `invalid_id`, `duplicate_id`, `invalid_item`, `invalid_font_size`, and the kind-specific check (`invalid_text`, `unsupported_emoji` or `invalid_entity`).
    3. `invalid_start`, last.

    A field of the wrong JSON type yields that field's code.
  - **Phase 3 — connectivity.** Runs only when phases 1–2 found nothing: a BFS from `start` over 4-neighbour cells. Each unreachable block yields `disconnected`, in layout order.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests/test_layout.py -v`
Expected: PASS (all 4 valid and 23 invalid fixtures, plus the unit tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/layout.py custom_components/ha_controller/tests/test_layout.py
git commit -m "feat(integration): validate layouts against protocol rules"
```

---

### Task 3: Layout compiler

**Files:**
- Create: `custom_components/ha_controller/compiler.py`, `custom_components/ha_controller/tests/test_compiler.py`

**Interfaces:**
- Consumes: `normalize_emoji` (Task 2).
- Produces:
  - `def compile_layout(layout: dict) -> dict`. It expects a valid layout and returns the payload with `rev` (spec §7.3). Names are trimmed.
  - `def payload_revision(payload: dict) -> str`. It ignores any `rev` key.
  - `def encode_payload(payload: dict) -> str`. Compact output, with `ensure_ascii=False`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("path", sorted(VALID_PAYLOADS), ids=stem)
def test_golden_payloads(path):
    case = load(path)
    assert compile_layout(load_layout(case["layout"])) == case["payload"]

def test_revision_ignores_rev_key():
    assert payload_revision({"v": 1, "rev": "zzz", "start": None, "sleep": 20, "blocks": []}) == "c4aad3fa"
def test_encode_payload_is_compact_utf8():
    text = encode_payload(compile_layout(load_layout("reference")))
    assert ", " not in text and ": " not in text and "👋" in text
def test_huge_layout_exceeds_payload_limit():
    # 32 custom blocks in a row, each with 6 text items of 64 × "é"
    assert len(encode_payload(compile_layout(huge)).encode()) > MAX_PAYLOAD_BYTES
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_compiler.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the three functions in `compiler.py`, following spec §7.3.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests/test_compiler.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/compiler.py custom_components/ha_controller/tests/test_compiler.py
git commit -m "feat(integration): compile layouts into device payloads"
```

---

### Task 4: State builders

**Files:**
- Create: `custom_components/ha_controller/states.py`, `custom_components/ha_controller/tests/test_states.py`

**Interfaces:**
- Produces:
  - `def build_updates(hass, layout: dict, entity_ids: Collection[str] | None = None) -> list[dict]`. Returns updates in layout order (spec §7.4, §7.7); `None` means all bound entities.
  - `def format_entity_text(hass, entity_id: str, attribute: str | None) -> str`
  - `def chunk_updates(updates: list[dict], max_bytes: int = STATE_CHUNK_BYTES) -> list[str]`. Each chunk is an encoded JSON array of at most `max_bytes` bytes, unless a single update is larger; in that case it is sent alone.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("path", sorted(STATE_FIXTURES), ids=stem)
async def test_state_fixtures(hass, path):
    case = load(path)
    hass.config.units = METRIC_SYSTEM
    for entity_id, s in case["hass_states"].items():
        hass.states.async_set(entity_id, s["state"], s["attributes"])
    registry = er.async_get(hass)
    for entity_id, options in case.get("registry_options", {}).items():
        domain, object_id = entity_id.split(".", 1)
        entry = registry.async_get_or_create(domain, "test", object_id, suggested_object_id=object_id)
        assert entry.entity_id == entity_id
        for option_domain, value in options.items():
            registry.async_update_entity_options(entity_id, option_domain, value)
    assert build_updates(hass, load_layout(case["layout"]), case["entity_ids"]) == case["updates"]

async def test_entity_text_truncated_to_64(hass): ...       # 100-char state → len == 64
async def test_entity_text_uses_attribute(hass): ...        # attribute "battery" = 80 → "80"
def test_chunk_updates_splits_by_size(): ...                # 300 updates, max 8192 → every chunk ≤ 8192 and the union equals the input
def test_chunk_updates_keeps_oversize_update_alone(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_states.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the builders in `states.py`, following spec §7.7.** `—` is U+2014. The climate unit is `hass.config.units.temperature_unit`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests/test_states.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/states.py custom_components/ha_controller/tests/test_states.py
git commit -m "feat(integration): build screen state updates"
```

---

### Task 5: Layout store and ScreenController sync engine

**Files:**
- Create: `custom_components/ha_controller/store.py`, `custom_components/ha_controller/controller.py`, `custom_components/ha_controller/tests/test_controller.py`
- Modify: `custom_components/ha_controller/__init__.py`

**Interfaces:**
- Consumes: Tasks 2–4.
- Produces:
  - **`class LayoutStore`:** `__init__(hass, entry_id)` with Home Assistant `Store` version 1 and key `f"{DOMAIN}.layout.{entry_id}"`, plus `async_load() -> dict | None`, `async_save(layout) -> None` and `async_remove() -> None`.
  - **`@dataclass class DeviceStatus`:** fields `node`, `version`, `revision` (`str | None`), `protocol: int | None`, `last_seen: datetime | None`, and `def online(self) -> bool`, which compares `last_seen` with `utcnow()` and `ONLINE_TIMEOUT`.
  - **`class InvalidLayout(HomeAssistantError)`:** attribute `errors: list[LayoutError]`.
  - **`class ScreenController`:**
    - `__init__(hass, entry, store, emoji: frozenset[str], integration_version: str)`
    - properties: `device_id`, `layout`, `revision`, `device: DeviceStatus`, `integration_version`
    - lifecycle: `async_start()` (load the layout, subscribe to the hello event, the control event and entity tracking) and `async_stop()`
    - layout: `async_save_layout(layout) -> tuple[str, bool]`, returning `(revision, pushed)`
    - sync: `async_handle_hello(data) -> None`, `async_push_layout() -> bool`, `async_push_states(entity_ids: Collection[str] | None = None) -> bool`
    - `async_call_device(action: str, data: dict) -> bool`
    - `status() -> dict`, shaped like one `ha_controller/screens` item (spec §8)
    - `@callback async_add_listener(cb) -> CALLBACK_TYPE`, which notifies on every device status change
  - **`__init__.py`:** `type HaControllerConfigEntry = ConfigEntry[ScreenController]`. `async_setup_entry` builds and starts the controller and stores it in `entry.runtime_data`. `async_unload_entry` stops it. `async_remove_entry` calls `LayoutStore.async_remove()`.

- [ ] **Step 1: Write the failing tests.** Mock the screen's services with `async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_layout")` and `async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_states")`. Drive time with `freezer`, `async_fire_time_changed` and `async_block_till_done`.

```python
async def test_hello_with_unknown_revision_pushes_layout_and_states(hass): ...
    # saved reference layout, hello(revision="none", reason="heartbeat")
    # → one set_layout call (json.loads(layout)["rev"] == "90538742"), then ≥1 set_states call
async def test_hello_connected_with_current_revision_pushes_states_only(hass): ...
async def test_heartbeat_with_current_revision_pushes_nothing(hass): ...
async def test_stale_revision_is_retried_at_most_every_300s(hass, freezer): ...
    # heartbeat ×2 within 299 s → 1 push; after +301 s → 2 pushes; reason "connected" always pushes
async def test_hello_with_other_protocol_pushes_nothing(hass): ...           # protocol "2"
async def test_hello_from_other_device_is_ignored(hass): ...                  # second screen registered; its hello leaves screen 1 untouched
async def test_state_changes_are_coalesced(hass): ...                         # 2 changes < 200 ms → one set_states with b1 and b2
async def test_state_change_not_pushed_when_offline(hass, freezer): ...       # last hello 151 s ago → no call
async def test_save_layout_pushes_when_online(hass): ...                      # returns ("90538742", True)
async def test_save_layout_offline_returns_not_pushed(hass): ...              # no hello yet → ("90538742", False); still persisted
async def test_save_invalid_layout_raises(hass): ...                          # InvalidLayout, errors == [LayoutError("invalid_name", "b2")]
async def test_save_too_large_layout_raises_payload_too_large(hass): ...      # errors == [LayoutError("payload_too_large", None)]
async def test_push_failure_is_logged_not_raised(hass, caplog): ...           # set_layout service raises HomeAssistantError → False
async def test_invalid_stored_layout_falls_back_to_empty(hass, hass_storage): ...
async def test_layout_survives_reload(hass): ...
async def test_status_reports_device(hass): ...                               # status() fields after a hello
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_controller.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the controller, following spec §7.5.**
  - **Hello and control events:** `hass.bus.async_listen(EVENT_…, handler, event_filter=…)`. The filter is a `@callback` that compares `event_data.get("device_id")` with the configured device id.
  - **Entity tracking:** `async_track_state_change_event` over `bound_entities(layout)`. It is re-subscribed when the layout changes.
  - **State coalescing:** a pending entity-id set, flushed by `async_call_later(hass, STATE_COALESCE_SECONDS, …)`.
  - **Device calls:** `hass.services.async_call("esphome", f"{node.replace('-', '_')}_{action}", data, blocking=True)`. On `HomeAssistantError`, log a warning and return `False`. Return `False` when the node is unknown.
  - **Push retry:** remember `(revision, utcnow())` of the last layout push. Skip a non-`connected` push of the same revision within `PUSH_RETRY`.
  - **Saving a layout:**
    1. Validate, then compile and encode. If the encoded size exceeds `MAX_PAYLOAD_BYTES`, raise `InvalidLayout([LayoutError("payload_too_large", None)])`.
    2. Store the layout and re-track entities.
    3. Push if the screen is online with protocol 1, bypassing the retry limit.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller custom_components/ha_controller/tests/test_controller.py
git commit -m "feat(integration): sync layouts and states with the screen"
```

---

### Task 6: Control events

**Files:**
- Create: `custom_components/ha_controller/controls.py`, `custom_components/ha_controller/tests/test_controls.py`
- Modify: `custom_components/ha_controller/controller.py`

**Interfaces:**
- Produces:
  - `class ControlCall(NamedTuple): domain: str; service: str; data: dict`
  - `def resolve_control(layout: dict, hass, data: Mapping[str, Any]) -> ControlCall | None` (spec §7.6). A non-finite or unparsable value returns `None`.
  - `ScreenController.async_handle_control(data) -> None`, subscribed to `EVENT_CONTROL` in `async_start`. It calls the service with `blocking=True` and logs a `HomeAssistantError` instead of raising it.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("path", sorted(CONTROL_FIXTURES), ids=stem)
async def test_control_fixtures(hass, path):
    case = load(path)   # set hass_states, then:
    call = resolve_control(load_layout(case["layout"]), hass, case["event"])
    assert (call and call._asdict()) == case["expect_call"]   # None ↔ null

async def test_control_event_calls_service(hass): ...         # fire EVENT_CONTROL with device_id → light.toggle mock receives entity_id light.kitchen
async def test_control_from_other_device_is_ignored(hass): ...
async def test_service_error_is_swallowed(hass, caplog): ...  # registered light.turn_on raises HomeAssistantError → no exception, warning logged
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_controls.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `resolve_control` and the controller handler.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller custom_components/ha_controller/tests/test_controls.py
git commit -m "feat(integration): map screen controls to service calls"
```

---

### Task 7: Websocket API

**Files:**
- Create: `custom_components/ha_controller/websocket.py`, `custom_components/ha_controller/tests/test_websocket.py`
- Modify: `custom_components/ha_controller/__init__.py` (call `async_register_websocket(hass)` in `async_setup`)

**Interfaces:**
- Consumes: `ScreenController.status`, `.layout` and `.async_save_layout` (Task 5).
- Produces (used by plan 3):
  - `ha_controller/screens` → `{"screens": [status, …]}`, covering loaded entries in title order.
  - `ha_controller/layout/get` `{entry_id}` → `{"layout": layout}`.
  - `ha_controller/layout/save` `{entry_id, layout}` → `{"revision": str, "pushed": bool}`.
  - Errors: `not_found`, which happens when the entry is missing or not loaded; and `invalid_layout`, whose message is the `", "`-joined `f"{code}@{ref or ''}"` list.
  - All three commands are admin-only: `@websocket_api.websocket_command`, then `@websocket_api.require_admin`, then `@websocket_api.async_response` for the save command or `@callback` for the others.

- [ ] **Step 1: Write the failing tests** with `hass_ws_client` and `hass_admin_user`.

```python
async def test_screens_lists_entries(hass, hass_ws_client): ...
async def test_layout_get_returns_stored_layout(hass, hass_ws_client): ...
async def test_layout_get_unknown_entry_returns_not_found(hass, hass_ws_client): ...
async def test_layout_save_valid(hass, hass_ws_client): ...           # result {"revision": "90538742", "pushed": False}
async def test_layout_save_invalid(hass, hass_ws_client): ...         # error code "invalid_layout", message "invalid_name@b2"
async def test_commands_require_admin(hass, hass_ws_client, hass_admin_user): ...   # remove the admin group → error code "unauthorized"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_websocket.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `websocket.py`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller custom_components/ha_controller/tests/test_websocket.py
git commit -m "feat(integration): add websocket API for the panel"
```

---

### Task 8: Sidebar panel registration, developer docs and reviewer agent

**Files:**
- Create:
  - `custom_components/ha_controller/panel.py`
  - `custom_components/ha_controller/tests/test_panel.py`
  - `docs/development.md`, `.claude/agents/ha-integration-reviewer.md`
- Modify: `custom_components/ha_controller/__init__.py`, `docs/README.md`, `.claude/CLAUDE.md`

**Interfaces:**
- Consumes: the plan 3 bundle path `custom_components/ha_controller/frontend/dist/ha-controller-panel.js`.
- Produces:
  - `async def async_register_panel(hass, version: str) -> None`. It registers `StaticPathConfig(f"{STATIC_URL}/ha-controller-panel.js", <integration dir>/frontend/dist/ha-controller-panel.js, True)` once per Home Assistant run, guarded by a `hass.data` flag. This is a file route, so a missing bundle never breaks setup. If `PANEL_URL_PATH` is not already in `hass.data[frontend.DATA_PANELS]`, it registers the panel with:

    ```python
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/ha-controller-panel.js?v={version}",
        require_admin=True,
        config={},
    )
    ```

    It logs a warning when the bundle file is missing.
  - `@callback def async_unregister_panel(hass) -> None`, which calls `frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)`. `async_unload_entry` calls it only when no other `ha_controller` entry is still loaded.

- [ ] **Step 1: Write the failing tests**

```python
async def test_panel_registered_on_setup(hass): ...                 # "ha-controller" in hass.data[frontend.DATA_PANELS], require_admin True
async def test_panel_kept_while_another_entry_is_loaded(hass): ...
async def test_panel_removed_when_last_entry_unloaded(hass): ...
async def test_static_path_registered_once(hass): ...               # patch hass.http.async_register_static_paths → awaited once for two entries
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest custom_components/ha_controller/tests/test_panel.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `panel.py` and wire it into `async_setup_entry` / `async_unload_entry`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest custom_components/ha_controller/tests -v && ruff check custom_components`
Expected: PASS.

- [ ] **Step 5: Write the docs and the reviewer agent.**
  - **`docs/development.md`:** create it with sections "Prerequisites" (Python 3.14, Node 24, ESPHome; the later plans fill these in) and "Home Assistant integration". The integration section covers:
    - venv setup and `pip install -r custom_components/requirements_test.txt`;
    - `pytest custom_components/ha_controller/tests`;
    - running a development Home Assistant, by symlinking `custom_components/ha_controller` into `<config>/custom_components/`;
    - how hello / set_layout traffic shows up under Developer tools › Events (`esphome.ha_controller_hello`).
  - **`docs/README.md`:** link the new doc.
  - **`.claude/agents/ha-integration-reviewer.md`:**
    - Frontmatter `name: ha-integration-reviewer`, `tools: Read, Grep, Glob, Bash`.
    - `description:` "Reviews changes under custom_components/ha_controller and custom_components/ha_controller/tests against Home Assistant development rules. Use before merging integration changes."
    - Checklist:
      - async only, with no blocking I/O in the loop;
      - `entry.runtime_data`, with no new `hass.data` globals beyond the panel flags;
      - listeners and timers removed on unload;
      - event filters by `device_id`;
      - service errors caught;
      - constants come from `const.py`;
      - English strings in `strings.json` and `translations/en.json`;
      - every branch tested;
      - protocol changes routed to the `protocol-change` skill.
    - Output: findings as `file:line — issue — fix`.
  - **`.claude/CLAUDE.md`:** list the agent.

- [ ] **Step 6: Commit**

```bash
git add custom_components/ha_controller custom_components/ha_controller/tests/test_panel.py docs .claude .claude/CLAUDE.md
git commit -m "feat(integration): register the sidebar panel"
```
