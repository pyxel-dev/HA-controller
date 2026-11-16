# HA Controller — Plan 1: Foundation & Protocol Contract

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the repository conventions, the documentation skeleton and the Claude Code guidance. Then write the cross-language protocol contract that plans 2–5 build on: the protocol doc, the emoji list and the shared fixtures.

**Architecture:** Documentation and data only, plus Python tests that keep the docs linked and the fixtures well formed. The fixtures are the executable contract: plan 2 (Python), plan 3 (TypeScript) and plan 4 (C++) all test against them.

**Tech Stack:** Markdown, JSON, Python 3.14, pytest, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-16-ha-controller-design.md`

## Global Constraints

- Everything is written in English: code, comments, docs, UI strings and commit messages.
- Repository `pyxel-dev/HA-controller`. Product name "HA Controller". Integration domain `ha_controller`. ESPHome project `pyxel-dev.ha-controller`.
- Python 3.14, pytest, ruff.
- Layout model and protocol v1 exactly as spec §6–§7. Golden revisions: `c4aad3fa` (empty), `90538742` (reference), `5387d4ea` (emoji-variation).
- `3D_models/` and `files/` stay untouched.

## Review Focus

1. **Invalid fixtures that break more than one rule.** Plans 2–3 would then pass for the wrong reason. Each invalid fixture is the reference layout (or `single`/`empty`) plus exactly one mutation. Plans 2 and 3 assert the full error list equals exactly the one expected error.
2. **Emoji entries the firmware cannot render.** This means multi-code-point sequences: U+FE0F, ZWJ, skin tones. `test_emoji_list_is_well_formed` asserts one code point per entry.
3. **Non-UTF-8 or BOM-prefixed fixture files** (they hold `°`, `—` and emoji). `test_all_fixtures_are_utf8_json` rejects them.
4. **A golden `rev` that drifts from the canonical hash.** `test_payload_revisions_match_canonical_hash` recomputes it.
5. **Docs linking to files that do not exist yet.** Later plans add docs. `test_relative_links_resolve` keeps every relative link valid at each commit.

---

### Task 1: Repository conventions, docs skeleton and CI

**Files:**
- Create: `.claude/CLAUDE.md`, `docs/README.md`, `docs/architecture.md`, `.github/scripts/pyproject.toml`, `.github/scripts/requirements.txt`, `.github/scripts/tests/__init__.py`, `.github/scripts/tests/test_docs_links.py`, `.github/workflows/ci.yml`
- Modify: `README.md` (rewrite in English), `.gitignore`

**Interfaces:**
- Produces:
  - `.github/scripts/pyproject.toml` with `[tool.pytest.ini_options] testpaths = ["tests"]` and `[tool.ruff] target-version = "py314"`, `line-length = 100`, lint rules `E,F,I,UP,B`.
  - `.github/scripts/requirements.txt` (`pytest`, `ruff`) for the repository checks. Plan 2 gives the integration its own test requirements under `custom_components/`.
  - `.github/workflows/ci.yml` with a single job `repo-checks`. Later plans add jobs.
  - The repository root keeps no files except `README.md`, `hacs.json` (plan 2) and `.gitignore`.
  - `docs/README.md` as the docs index. Later plans add links.
  - `.claude/CLAUDE.md` with a `## Commands` table and a `## Skills and agents` section. Later plans append rows.

- [ ] **Step 1: Write the failing tests** in `.github/scripts/tests/test_docs_links.py`.

```python
DOC_ROOTS = ["README.md", ".claude/CLAUDE.md", "docs"]  # docs/superpowers/** is excluded

def test_relative_links_resolve():
    # For every markdown link [text](target) whose target does not start with
    # http://, https://, mailto: or '#': strip the '#anchor' and assert
    # (md_file.parent / target).resolve().exists(); report every broken link.
    ...

def test_docs_index_lists_every_doc():
    # Every docs/*.md file except docs/README.md is linked from docs/README.md.
    ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest .github/scripts/tests -v`
Expected: FAIL (`docs/README.md` is missing).

- [ ] **Step 3: Write the docs and config**
  - **`README.md`:**
    - Keep the title "HA Controller".
    - One paragraph pitch, then feature bullets:
      - block map editor in Home Assistant;
      - edge-swipe navigation;
      - light and thermostat knobs;
      - custom blocks;
      - automatic firmware updates.
    - Status line "Under active development".
    - Relative link `docs/README.md`.
    - Keep the 3D-models section and fix its link to `3D_models/`.
  - **`docs/README.md`:** title "HA Controller documentation", one bullet per doc (`architecture.md` for now) and a link to the design spec under `superpowers/specs/`.
  - **`docs/architecture.md`:** spec §3 rewritten for contributors. Include the diagram, the subsystems and the repository layout table, plus one paragraph each on:
    - the hello → layout/states handshake;
    - controls → service calls;
    - firmware updates.
  - **`.claude/CLAUDE.md`:**
    - Title "HA Controller — guidance for Claude Code" and a two-line purpose.
    - `## Rules`:
      - English only.
      - One version for the whole repo; change it only with `python .github/scripts/versioning.py bump X.Y.Z` (added in plan 5).
      - The protocol is defined in `docs/protocol/README.md` and pinned by `docs/protocol/fixtures/`.
      - TDD.
      - Never commit `esphome/secrets.yaml`.
      - Specs and plans live in `docs/superpowers/`.
    - `## Repository map`: the spec §3 table.
    - `## Commands`: `pytest .github/scripts/tests`, `ruff check .github/scripts`.
    - `## Skills and agents`: empty list.
  - **`.gitignore`:** keep `.DS_Store`. Add `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.venv*/`, `node_modules/`, `custom_components/ha_controller/frontend/coverage/`, `.superpowers/`, `esphome/.esphome/`, `esphome/secrets.yaml`, `build/`, `dist/`, `site/`.

- [ ] **Step 4: Run the tests and lint**

Run: `pytest .github/scripts/tests -v && ruff check .github/scripts`
Expected: PASS, no lint findings.

- [ ] **Step 5: Add CI.** In `.github/workflows/ci.yml`, workflow `CI`:
  - Triggers: `push` to `main` and `pull_request`.
  - Job `repo-checks` on `ubuntu-latest`: `actions/checkout@v4`, `actions/setup-python@v5` with `python-version: "3.14"`, `pip install -r .github/scripts/requirements.txt`, `ruff check .github/scripts`, `pytest .github/scripts/tests`.

- [ ] **Step 6: Commit**

```bash
git add README.md .claude/CLAUDE.md docs/README.md docs/architecture.md .github/scripts .gitignore .github/workflows/ci.yml
git commit -m "chore: add repository conventions, docs skeleton and CI"
```

---

### Task 2: Protocol contract — protocol doc, emoji list, fixtures and Claude guidance

**Files:**
- Create:
  - `docs/protocol/README.md`, `docs/protocol/README.md`, `custom_components/ha_controller/emoji.json`
  - `docs/protocol/fixtures/**` (see the tables below)
  - `.github/scripts/tests/__init__.py`, `.github/scripts/tests/test_protocol_fixtures.py`
  - `.claude/skills/protocol-change/SKILL.md`, `.claude/agents/protocol-guardian.md`
- Modify: `docs/README.md` (link `protocol.md`), `.claude/CLAUDE.md` (skills and agents list)

**Interfaces:**
- Produces (consumed by plans 2, 3 and 4). All fixture files are UTF-8 JSON without a BOM.
  - `custom_components/ha_controller/emoji.json`: a JSON array of the 64 strings below, in this order:
    `💡 🔥 ❄ 🌡 💧 🌬 ☀ 🌙 ⭐ ☁ ⛅ 🌧 ⚡ 🔋 🔌 🏠 🛋 🛏 🛁 🚿 🍳 🍽 ☕ 🍷 🧺 🪴 🚪 🪟 🔒 🔓 🔑 🔔 🔕 🔊 🔇 🎵 📺 🎮 💻 📱 ⏰ 📅 🚗 🚲 🐶 🐱 👶 👋 👍 ❤ 😀 😴 🎉 🎄 ✅ ❌ ⚠ ℹ ▶ ⏸ ♻ 🌀 🧊 🏡`
  - `docs/protocol/fixtures/layouts/valid/<name>.json`: a stored layout.
  - `docs/protocol/fixtures/layouts/invalid/<name>.json`: `{"expect": {"code": str, "ref": str | null}, "layout": {...}}`. The stem equals `code` or starts with `code-`.
  - `docs/protocol/fixtures/payloads/valid/<name>.json`: `{"layout": "<stem in layouts/valid>", "payload": {...}}`.
  - `docs/protocol/fixtures/payloads/invalid/<name>.json`: `{"expect": "bad_json" | "unsupported_version" | "invalid_payload", "text": "<raw string sent to set_layout>"}`.
  - `docs/protocol/fixtures/states/<name>.json`:

    ```json
    {
      "layout": "reference",
      "unit": "°C",
      "entity_ids": ["…"] | null,
      "hass_states": {"<entity_id>": {"state": "…", "attributes": {}}},
      "registry_options": {"<entity_id>": {}},
      "updates": []
    }
    ```

    `registry_options` is optional; `updates` lists the expected update objects.
  - `docs/protocol/fixtures/controls/<name>.json`: `{"layout": "reference", "hass_states": {...}, "event": {"block", "item", "op", "value"}, "expect_call": {"domain", "service", "data"} | null}`.
  - `docs/protocol/fixtures/colors.json`: `[{"bg": "#RRGGBB", "text": "#000000" | "#FFFFFF"}]`.

- [ ] **Step 1: Write the failing tests** in `.github/scripts/tests/test_protocol_fixtures.py`. Local helpers: `canonical_rev(payload) -> str` and `luminance(hex) -> float` (spec §5.5/§7.3).

```python
def test_emoji_list_is_well_formed():
    emoji = json.loads(EMOJI.read_text("utf-8"))
    assert len(emoji) == 64 and len(set(emoji)) == 64
    assert all(len(e) == 1 for e in emoji)          # one code point each
    assert "️" not in "".join(emoji)
    assert {"💡", "🔋", "⚡", "☀", "👋"} <= set(emoji) and "🦄" not in emoji

def test_all_fixtures_are_utf8_json(): ...        # every docs/protocol/fixtures/**/*.json: no BOM, json.loads ok

def test_invalid_layout_fixtures_declare_known_codes():
    # expect.code in the 18 codes of spec §6 except payload_too_large
    # expect.ref is str or None; stem == code or stem.startswith(code + "-")

def test_payload_revisions_match_canonical_hash():
    revs = {p.stem: json.loads(p.read_text("utf-8"))["payload"]["rev"] for p in VALID_PAYLOADS}
    assert revs == {"empty": "c4aad3fa", "reference": "90538742", "emoji-variation": "5387d4ea"}
    # and canonical_rev(payload) == payload["rev"] for each file

def test_fixtures_reference_existing_layouts(): ...  # "layout" fields of payloads/states/controls exist in layouts/valid

def test_color_fixture_matches_luminance_rule():
    for case in COLORS:
        assert case["text"] == ("#000000" if luminance(case["bg"]) > 0.30 else "#FFFFFF")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest .github/scripts/tests -v`
Expected: FAIL (the files are missing).

- [ ] **Step 3: Write `emoji.json` and the fixtures.**

**Valid layouts:**
- **`empty.json`:** `{"version": 1, "start": null, "settings": {"sleep_timeout": 20}, "blocks": []}`.
- **`reference.json`:** the JSON of spec §6, verbatim (it includes `"settings": {"sleep_timeout": 20}`).
- **`single.json`:** `{"version": 1, "start": "b1", "settings": {"sleep_timeout": 0}, "blocks": [{"id": "b1", "x": 3, "y": -2, "name": "Solo", "background": "#000000", "font_size": "s", "type": "custom", "items": []}]}`.
- **`emoji-variation.json`:** `{"version": 1, "start": "b1", "settings": {"sleep_timeout": 3600}, "blocks": [{"id": "b1", "x": 0, "y": 0, "name": "Snow", "background": "#FFFFFF", "font_size": "xl", "type": "custom", "items": [{"id": "i1", "kind": "emoji", "emoji": "❄️", "font_size": null}]}]}`. The emoji is U+2744 followed by U+FE0F.

**Invalid layouts.** Each is a single mutation of the base layout:

| File | Base | Mutation | expect |
|---|---|---|---|
| `invalid_structure.json` | reference | `"blocks": {}` | `invalid_structure`, `null` |
| `invalid_structure-version.json` | reference | `"version": 2` | `invalid_structure`, `null` |
| `invalid_structure-settings.json` | reference | `"settings": 20` | `invalid_structure`, `null` |
| `too_many_blocks.json` | — | 33 blocks: block N is `{"id": "bN", "x": N-1, "y": 0, "name": "Block N", "background": "#000000", "font_size": "m", "type": "custom", "items": []}` for N = 1…33, start `b1`, `"settings": {"sleep_timeout": 20}` | `too_many_blocks`, `null` |
| `invalid_sleep_timeout.json` | reference | `"settings": {"sleep_timeout": 3}` | `invalid_sleep_timeout`, `null` |
| `invalid_id.json` | reference | b4 id → `"B4"` | `invalid_id`, `"B4"` |
| `duplicate_id.json` | reference | item i5 id → `"b1"` | `duplicate_id`, `"b1"` |
| `coordinate_out_of_range.json` | single | b1 `x: 33` | `coordinate_out_of_range`, `"b1"` |
| `duplicate_position.json` | reference | b4 → `x: 0, y: 0` | `duplicate_position`, `"b4"` |
| `invalid_start.json` | reference | `"start": "zz"` | `invalid_start`, `null` |
| `invalid_start-empty.json` | empty | `"start": "b1"` | `invalid_start`, `null` |
| `disconnected.json` | reference | b4 → `y: 2` | `disconnected`, `"b4"` |
| `invalid_name.json` | reference | b2 name → `"   "` | `invalid_name`, `"b2"` |
| `invalid_background.json` | reference | b2 background → `"red"` | `invalid_background`, `"b2"` |
| `invalid_font_size.json` | reference | b2 font_size → `"xxl"` | `invalid_font_size`, `"b2"` |
| `invalid_font_size-item.json` | reference | i1 font_size → `"huge"` | `invalid_font_size`, `"i1"` |
| `invalid_type.json` | reference | b2 type → `"gauge"` | `invalid_type`, `"b2"` |
| `invalid_entity.json` | reference | b1 entity_id → `"switch.kettle"` | `invalid_entity`, `"b1"` |
| `invalid_entity-item.json` | reference | i3 entity_id → `"not an entity"` | `invalid_entity`, `"i3"` |
| `too_many_items.json` | reference | b3 items + `{"id": "i6", "kind": "text", "text": "A", "font_size": null}`, `{"id": "i7", …"B"…}` | `too_many_items`, `"b3"` |
| `invalid_item.json` | reference | i4 kind → `"image"` | `invalid_item`, `"i4"` |
| `invalid_text.json` | reference | i1 text → 65 × `"a"` | `invalid_text`, `"i1"` |
| `unsupported_emoji.json` | reference | i2 emoji → `"🦄"` | `unsupported_emoji`, `"i2"` |

**Valid payloads.** Write each `payload` by hand from spec §7.3:
- **`empty.json`:** layout `empty`, payload `{"v": 1, "rev": "c4aad3fa", "start": null, "sleep": 20, "blocks": []}`.
- **`reference.json`:** layout `reference`, payload:

```json
{"v": 1, "rev": "90538742", "start": "b1", "sleep": 20, "blocks": [
 {"id": "b1", "x": 0, "y": 0, "name": "Kitchen", "bg": "5B9E4D", "font": "m", "widget": "light"},
 {"id": "b2", "x": 0, "y": -1, "name": "Lights", "bg": "C94F3D", "font": "m", "widget": "light"},
 {"id": "b3", "x": -1, "y": 0, "name": "Hello World", "bg": "4F86DD", "font": "l", "widget": "custom", "items": [
   {"id": "i1", "kind": "text", "text": "Hello World", "font": "l"},
   {"id": "i2", "kind": "emoji", "text": "👋", "font": "xl"},
   {"id": "i3", "kind": "entity", "font": "s"},
   {"id": "i4", "kind": "battery", "font": "s"},
   {"id": "i5", "kind": "brightness", "font": "l"}]},
 {"id": "b4", "x": -1, "y": 1, "name": "Bedroom", "bg": "7B2FA0", "font": "m", "widget": "climate"}]}
```

- **`emoji-variation.json`:** layout `emoji-variation`, payload `{"v": 1, "rev": "5387d4ea", "start": "b1", "sleep": 3600, "blocks": [{"id": "b1", "x": 0, "y": 0, "name": "Snow", "bg": "FFFFFF", "font": "xl", "widget": "custom", "items": [{"id": "i1", "kind": "emoji", "text": "❄", "font": "xl"}]}]}`.

**Invalid payloads** (`text` values):

| File | text | expect |
|---|---|---|
| `bad_json.json` | `{"v":1,` | `bad_json` |
| `bad_json-array.json` | `[1,2]` | `bad_json` |
| `unsupported_version.json` | `{"v":2,"rev":"x","start":null,"blocks":[]}` | `unsupported_version` |
| `invalid_payload.json` | `{"v":1,"rev":"x","start":"b1","blocks":[{"id":"b1"}]}` | `invalid_payload` |
| `invalid_payload-widget.json` | `{"v":1,"rev":"x","start":"b1","sleep":20,"blocks":[{"id":"b1","x":0,"y":0,"name":"A","bg":"000000","font":"m","widget":"gauge"}]}` | `invalid_payload` |
| `invalid_payload-sleep.json` | `{"v":1,"rev":"x","start":null,"sleep":-1,"blocks":[]}` | `invalid_payload` |

**States.** All use layout `reference` and unit `°C`:

| File | entity_ids | hass_states | updates |
|---|---|---|---|
| `light-dimmable-on.json` | `["light.kitchen"]` | `light.kitchen`: `on`, `{"brightness": 128, "supported_color_modes": ["brightness"]}` | `[{"id": "b1", "available": true, "on": true, "brightness": 50}]` |
| `light-dimmable-off.json` | `["light.living_room"]` | `light.living_room`: `off`, `{"supported_color_modes": ["color_temp"]}` | `[{"id": "b2", "available": true, "on": false, "brightness": 0}]` |
| `light-onoff.json` | `["light.kitchen"]` | `on`, `{"supported_color_modes": ["onoff"]}` | `[{"id": "b1", "available": true, "on": true, "brightness": null}]` |
| `light-unavailable.json` | `["light.kitchen"]` | `unavailable`, `{}` | `[{"id": "b1", "available": false}]` |
| `climate-heating.json` | `["climate.bedroom"]` | `heat`, `{"temperature": 20.5, "current_temperature": 19.8, "min_temp": 7, "max_temp": 35, "target_temp_step": 0.5, "hvac_action": "heating"}` | `[{"id": "b4", "available": true, "target": 20.5, "min": 7, "max": 35, "step": 0.5, "unit": "°C", "current": "19.8 °C", "action": "Heating"}]` |
| `climate-defaults.json` | `["climate.bedroom"]` | `off`, `{"temperature": null, "current_temperature": null}` | `[{"id": "b4", "available": true, "target": null, "min": 7, "max": 35, "step": 0.5, "unit": "°C", "current": "—", "action": "Off"}]` |
| `entity-precision.json` | `["sensor.outdoor_temperature"]` | `"12.345"`, `{"unit_of_measurement": "°C"}`; registry_options `{"sensor.outdoor_temperature": {"sensor": {"display_precision": 1}}}` | `[{"id": "i3", "text": "12.3 °C"}]` |
| `entity-missing.json` | `["sensor.outdoor_temperature"]` | `{}` | `[{"id": "i3", "text": "—"}]` |
| `all-missing.json` | `null` | `{}` | `[{"id": "b1", "available": false}, {"id": "b2", "available": false}, {"id": "i3", "text": "—"}, {"id": "b4", "available": false}]` |

**Controls.** All use layout `reference`. `item` is `""` everywhere:

| File | hass_states | event (block, op, value) | expect_call |
|---|---|---|---|
| `light-toggle.json` | `{}` | `b1`, `toggle`, `"0.00"` | `light.toggle` `{"entity_id": "light.kitchen"}` |
| `light-set.json` | `{}` | `b1`, `set`, `"42.40"` | `light.turn_on` `{"entity_id": "light.kitchen", "brightness_pct": 42}` |
| `light-set-zero.json` | `{}` | `b1`, `set`, `"0.00"` | `light.turn_off` `{"entity_id": "light.kitchen"}` |
| `light-set-over.json` | `{}` | `b2`, `set`, `"150"` | `light.turn_on` `{"entity_id": "light.living_room", "brightness_pct": 100}` |
| `climate-set.json` | `climate.bedroom`: `heat`, `{"min_temp": 7, "max_temp": 35}` | `b4`, `set`, `"21.50"` | `climate.set_temperature` `{"entity_id": "climate.bedroom", "temperature": 21.5}` |
| `climate-clamp.json` | same as above | `b4`, `set`, `"50.00"` | `climate.set_temperature` `{"entity_id": "climate.bedroom", "temperature": 35}` |
| `ignored-unknown-block.json` | `{}` | `zz`, `set`, `"1"` | `null` |
| `ignored-custom-block.json` | `{}` | `b3`, `set`, `"1"` | `null` |
| `ignored-bad-value.json` | `{}` | `b1`, `set`, `"abc"` | `null` |
| `ignored-climate-toggle.json` | `{}` | `b4`, `toggle`, `"0.00"` | `null` |

**`colors.json`:**

| bg | text |
|---|---|
| `#FFFFFF` | `#000000` |
| `#000000` | `#FFFFFF` |
| `#5B9E4D` | `#FFFFFF` |
| `#4F86DD` | `#FFFFFF` |
| `#C94F3D` | `#FFFFFF` |
| `#7B2FA0` | `#FFFFFF` |
| `#F1C40F` | `#000000` |
| `#9E9E9E` | `#000000` |
| `#8C8C8C` | `#FFFFFF` |

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest .github/scripts/tests -v`
Expected: PASS.

- [ ] **Step 5: Write the protocol doc and guidance**
  - **`docs/protocol/README.md`:** spec §6 and §7, verbatim, under the heading "Device protocol v1". Add a closing "Fixtures" section with the relative link `../protocol/README.md`.
  - **`docs/protocol/README.md`:**
    - Who reads each fixture folder: pytest in `custom_components/ha_controller/tests`, vitest in `custom_components/ha_controller/frontend/test`, doctest in `esphome/tests`.
    - The rule "one broken rule per invalid fixture".
    - The canonical-revision snippet:

      ```python
      hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:8]
      ```
  - **`.claude/skills/protocol-change/SKILL.md`:**
    - Frontmatter `name: protocol-change`.
    - `description:` "Use when changing anything that crosses the Home Assistant ↔ screen boundary: layout fields, validation rules, payload keys, state update fields, events, actions, emoji list or limits."
    - Body, a numbered checklist:
      1. Classify the change. The C++ parser rejects unknown `widget`/`kind`/`font` values, so any new value is breaking: bump `PROTOCOL_VERSION` in `custom_components/ha_controller/const.py` and in the firmware's `ha_controller.h`.
      2. Edit `docs/protocol/README.md` first.
      3. Update `docs/protocol/fixtures/`, keeping one rule per invalid fixture and regenerating golden `rev` values with the snippet.
      4. Update the Python code (`layout.py`, `compiler.py`, `states.py`, `controls.py`), the TypeScript model (`custom_components/ha_controller/frontend/src/model/`), the C++ parsers (`esphome/components/ha_controller/layout.*`, `states.*`) and the renderers (`widgets.*`, panel editor).
      5. Run `pytest custom_components/ha_controller/tests`, `pytest .github/scripts/tests`, `npm --prefix custom_components/ha_controller/frontend test`, the host C++ tests and `esphome compile`.
      6. Ask the `protocol-guardian` agent to review.
  - **`.claude/agents/protocol-guardian.md`:**
    - Frontmatter `name: protocol-guardian`, `tools: Read, Grep, Glob, Bash`.
    - `description:` "Reviews a diff for consistency of the HA ↔ screen protocol across docs/protocol/README.md, docs/protocol/fixtures, the integration (Python), the panel model (TypeScript) and the firmware parsers (C++). Use after any protocol-related change and before merging."
    - Body:
      - A checklist: field names, error codes, limits and constants identical in all places; fixtures updated; golden revs recomputed; `PROTOCOL_VERSION` bumped on breaking changes; docs updated.
      - Output: a list of `file:line — inconsistency — fix`, or "Protocol consistent".
  - **`docs/README.md`:** add a `protocol.md` bullet.
  - **`.claude/CLAUDE.md`:** list the skill and the agent under `## Skills and agents`.

- [ ] **Step 6: Run the whole suite**

Run: `pytest .github/scripts/tests -v && ruff check .github/scripts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/protocol docs/README.md custom_components/ha_controller/emoji.json .github/scripts/tests .claude .claude/CLAUDE.md
git commit -m "feat(protocol): add protocol v1 contract, shared fixtures and guidance"
```
