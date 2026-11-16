# HA Controller — Plan 3: Sidebar Panel (Block Map Editor)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Home Assistant sidebar panel where the user edits each screen's block map. The map is laid out exactly the way navigation works on the screen ([reference screenshot](../specs/assets/editor-reference.png)).

**Architecture:** A Lit + TypeScript web component bundled by Vite into one ES module. Vite writes it to `custom_components/ha_controller/frontend/dist/ha-controller-panel.js`, which plan 2's `panel.py` serves.
- **Model:** pure functions in `src/model/` hold all editing logic (grid, validation, edits, colours, emoji). Vitest tests them against `docs/protocol/fixtures/`.
- **Components:** they only render and emit events.
- **Websocket:** the panel talks to the integration through plan 2's commands.
- **Dev harness:** `npm run dev` runs the panel against an in-memory mock `hass`.

**Tech Stack:** Node 24, TypeScript 5 (strict), Lit 3, Vite, Vitest with happy-dom. Use the current stable releases of the build and test tools, and commit `package-lock.json`.

**Spec:** `docs/superpowers/specs/2026-11-16-ha-controller-design.md` (§5.1, §5.5, §6, §9)

## Global Constraints

- **Rules and codes:** the validation rules and error codes are identical to plan 2 (spec §6). Both suites read the same fixtures.
- **Orientation:** grid `x` grows to the right and `y` grows downwards, matching the screen.
- **No Home Assistant internals:** use no HA-internal custom elements except `ha-menu-button` (optional, narrow mode). Entity pickers are built from `hass.states`.
- **Theme:** use Home Assistant theme variables with fallbacks:
  - `--primary-color` (fallback `#03a9f4`)
  - `--primary-text-color` (fallback `#212121`)
  - `--secondary-text-color` (fallback `#727272`)
  - `--card-background-color` (fallback `#fff`)
  - `--divider-color` (fallback `rgba(0,0,0,.12)`)
  - `--error-color` (fallback `#db4437`)
- **Strings:** all UI strings are in English and live in `src/messages.ts`.
- **Versioning:** `custom_components/ha_controller/frontend/package.json` `version` is `0.1.0`; plan 5's versioning script keeps it in sync.

## Review Focus

1. **Deleting a block that would strand others**, e.g. deleting "Hello World" in the reference layout strands "Bedroom". Expected: refused, with the reason shown. Owner: Task 1 `canDelete` tests, Task 4 editor test.
2. **Map with a start block away from `(0,0)`, negative coordinates, or one row/column.** The map must still render every block at the right relative place, and placeholders must stay inside ±32. Owner: Task 1 placeholder tests on `single.json`, Task 3 grid test.
3. **Websocket save rejected** (`invalid_layout`, connection lost). The working copy must be kept and the error shown, never silently dropped. Owner: Task 5 `test_save_error_keeps_changes`.
4. **Emoji typed or pasted with U+FE0F.** It must be normalised so local validation and the screen agree. Owner: Task 2 `normalizeEmoji` and Task 4 emoji picker test.
5. **`hass` updates arriving every few seconds** while the user edits. Unsaved edits must never be overwritten by a refresh. Owner: Task 5 `test_refresh_does_not_reset_working_copy`.

---

### Task 1: Tooling, types, grid model and validation

**Files:**
- Create:
  - `custom_components/ha_controller/frontend/package.json`, `custom_components/ha_controller/frontend/package-lock.json`, `custom_components/ha_controller/frontend/tsconfig.json`, `custom_components/ha_controller/frontend/vite.config.ts`
  - `custom_components/ha_controller/frontend/src/types.ts`, `custom_components/ha_controller/frontend/src/model/grid.ts`, `custom_components/ha_controller/frontend/src/model/validate.ts`, `custom_components/ha_controller/frontend/src/model/emoji.ts`
  - `custom_components/ha_controller/frontend/test/fixtures.ts`, `custom_components/ha_controller/frontend/test/grid.test.ts`, `custom_components/ha_controller/frontend/test/validate.test.ts`
- Modify: `.github/workflows/ci.yml` (job `frontend`), `.claude/CLAUDE.md` (commands)

**Interfaces:**
- Produces:
  - **`types.ts`:**
    - `FontSize = "s" | "m" | "l" | "xl"`
    - `ItemKind = "text" | "emoji" | "entity" | "battery" | "brightness"`
    - `Item {id, kind, font_size: FontSize | null, text?, emoji?, entity_id?, attribute?: string | null}`
    - `Block {id, x, y, name, background, font_size, type: "entity" | "custom", entity_id?, items?: Item[]}`
    - `Layout {version: 1, start: string | null, settings: {sleep_timeout: number}, blocks: Block[]}`
    - `LayoutError {code: string, ref: string | null}`
    - `Cell {x, y}`
    - `ScreenInfo`: the spec §8 fields
    - `HassEntity {entity_id, state, attributes}`
    - `Hass {states: Record<string, HassEntity>, callWS<T>(msg): Promise<T>}`
  - **`model/grid.ts`:**
    - `placeholders(layout: Layout): Cell[]`, sorted by `y` then `x`
    - `reachable(blocks: Block[], start: string | null): Set<string>`
    - `canDelete(layout, id): {ok: true} | {ok: false, reason: "start" | "disconnects"}`
    - `gridBounds(cells: Cell[]): {minX, maxX, minY, maxY}`
  - **`model/validate.ts`:** `validateLayout(layout: unknown, emoji: ReadonlySet<string>): LayoutError[]`. Same phases and order as plan 2 Task 2.
  - **`model/emoji.ts`:** `SUPPORTED_EMOJI: readonly string[]` imported from `../../../emoji.json` (relative to `src/model/`), `EMOJI_SET`, `normalizeEmoji(text): string`.
  - **`test/fixtures.ts`:** `validLayouts`, `invalidLayouts` and `colors`, loaded with `import.meta.glob("../../../../docs/protocol/fixtures/…", {eager: true, import: "default"})`.

- [ ] **Step 1: Scaffold the tooling.**
  - **`package.json`:** `"type": "module"`, `"private": true`, `"version": "0.1.0"`.
    - Scripts: `dev` (`vite --open dev/index.html`), `build` (`tsc --noEmit && vite build`), `test` (`vitest run`), `typecheck` (`tsc --noEmit`).
    - Dependency: `lit`. Dev dependencies: `typescript`, `vite`, `vitest`, `happy-dom`.
  - **`tsconfig.json`:** `strict`, `target` and `lib` ES2022 + DOM, `module: ESNext`, `moduleResolution: Bundler`, `experimentalDecorators: true`, `useDefineForClassFields: false`, `resolveJsonModule: true`, `noEmit: true`.
  - **`vite.config.ts`:**
    - Library mode: entry `src/ha-controller-panel.ts`, format `es`, file name `ha-controller-panel.js`.
    - `outDir: "dist"`, `emptyOutDir: true`, `target: "es2022"`, with `lit` bundled.
    - `server.fs.allow: ["../../.."]` (the repository root, for the fixtures and `emoji.json`).
    - `test.environment: "happy-dom"`.

  Run `npm install`.

- [ ] **Step 2: Write the failing tests**

```ts
// grid.test.ts
expect(placeholders(validLayouts.empty)).toEqual([{x: 0, y: 0}]);
expect(placeholders(validLayouts.reference)).toEqual([
  {x: 0, y: -2}, {x: -1, y: -1}, {x: 1, y: -1}, {x: -2, y: 0},
  {x: 1, y: 0}, {x: -2, y: 1}, {x: 0, y: 1}, {x: -1, y: 2}]);           // the 8 "+" of the screenshot
expect(placeholders(rowOf32Blocks)).toEqual([]);
expect(placeholders(blockAt(32, 0))).not.toContainEqual({x: 33, y: 0});
expect(canDelete(validLayouts.reference, "b1")).toEqual({ok: false, reason: "start"});
expect(canDelete(validLayouts.reference, "b3")).toEqual({ok: false, reason: "disconnects"});
expect(canDelete(validLayouts.reference, "b2")).toEqual({ok: true});
expect(canDelete(validLayouts.single, "b1")).toEqual({ok: true});
expect(gridBounds(cellsOf(validLayouts.single))).toEqual({minX: 3, maxX: 3, minY: -2, maxY: -2});

// validate.test.ts
for (const [name, layout] of Object.entries(validLayouts)) expect(validateLayout(layout, EMOJI_SET), name).toEqual([]);
for (const [name, c] of Object.entries(invalidLayouts)) expect(validateLayout(c.layout, EMOJI_SET), name).toEqual([c.expect]);
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: FAIL (modules missing).

- [ ] **Step 4: Implement `types.ts`, `grid.ts`, `validate.ts` and `emoji.ts`.**
  - `placeholders` collects the empty 4-neighbours of every block within ±32, deduplicated. With no blocks it returns `[(0,0)]`; with 32 blocks it returns `[]`.
  - `canDelete` refuses the start block of a multi-block layout. It also refuses any block whose removal leaves another block unreachable from the start block.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm --prefix custom_components/ha_controller/frontend test && npm --prefix custom_components/ha_controller/frontend run typecheck`
Expected: PASS.

- [ ] **Step 6: Add the CI job.** Add job `frontend` to `.github/workflows/ci.yml`:
  - `actions/setup-node@v4` with `node-version: 24`, `cache: npm`, `cache-dependency-path: custom_components/ha_controller/frontend/package-lock.json`.
  - Working directory `custom_components/ha_controller/frontend`: `npm ci`, `npm test`, `npm run build`.

  Add the `npm --prefix custom_components/ha_controller/frontend …` commands to `.claude/CLAUDE.md`.

- [ ] **Step 7: Commit**

```bash
git add custom_components/ha_controller/frontend .github/workflows/ci.yml .claude/CLAUDE.md
git commit -m "feat(panel): add panel tooling, grid model and validation"
```

---

### Task 2: Edit operations, colours and emoji

**Files:**
- Create: `custom_components/ha_controller/frontend/src/model/edit.ts`, `custom_components/ha_controller/frontend/src/model/color.ts`, `custom_components/ha_controller/frontend/test/edit.test.ts`, `custom_components/ha_controller/frontend/test/color.test.ts`, `custom_components/ha_controller/frontend/test/emoji.test.ts`

**Interfaces:**
- Consumes: `canDelete` (Task 1).
- Produces. Every function is pure and returns a new `Layout` without mutating its input.
  - `PALETTE = ["#C94F3D", "#4F86DD", "#5B9E4D", "#7B2FA0", "#E08A2E", "#2E9E8F", "#D2477A", "#5C6BC0"]`
  - `nextId(layout, prefix: "b" | "i"): string`: one plus the highest numeric suffix among block and item ids with that prefix.
  - `addBlock(layout, cell): {layout, id}`. The new block gets name `Block <n>` (n = the numeric part of its id), background `PALETTE[blocks.length % 8]`, font `m`, type `custom` and `items: []`. If `start` was null, it becomes the start block.
  - `deleteBlock(layout, id)`. Throws if `canDelete` refuses. Deleting the last block sets `start` to `null`.
  - `setStart(layout, id)` and `updateBlock(layout, id, patch: Partial<Block>)`.
  - `setSleepTimeout(layout, seconds: number)`: replaces `settings.sleep_timeout`.
  - `addItem(layout, blockId, kind): {layout, id}`. Defaults: text `{text: "Text"}`, emoji `{emoji: "💡"}`, entity `{entity_id: "", attribute: null}`. Every kind gets `font_size: null`.
  - `updateItem(layout, blockId, itemId, patch)`, `removeItem(layout, blockId, itemId)` and `moveItem(layout, blockId, itemId, delta: -1 | 1)`. `moveItem` is a no-op at either end.
  - `textColorFor(bg: string): "#000000" | "#FFFFFF"`: `#000000` if WCAG relative luminance > 0.30 (spec §5.5).

- [ ] **Step 1: Write the failing tests**

```ts
const r = addBlock(validLayouts.reference, {x: 1, y: 0});
expect(r.id).toBe("b5");
expect(r.layout.blocks.at(-1)).toMatchObject({name: "Block 5", background: "#E08A2E", font_size: "m", type: "custom", items: []});
expect(r.layout.start).toBe("b1");
expect(addBlock(validLayouts.empty, {x: 0, y: 0}).layout).toMatchObject({start: "b1", blocks: [{id: "b1", background: "#C94F3D"}]});
expect(nextId(validLayouts.reference, "i")).toBe("i6");
expect(deleteBlock(validLayouts.single, "b1")).toEqual({version: 1, start: null, settings: {sleep_timeout: 0}, blocks: []});
expect(setSleepTimeout(validLayouts.reference, 45).settings).toEqual({sleep_timeout: 45});
expect(() => deleteBlock(validLayouts.reference, "b3")).toThrow();
expect(itemIds(moveItem(validLayouts.reference, "b3", "i1", 1), "b3")).toEqual(["i2", "i1", "i3", "i4", "i5"]);
expect(itemIds(moveItem(validLayouts.reference, "b3", "i1", -1), "b3")).toEqual(["i1", "i2", "i3", "i4", "i5"]);
const copy = structuredClone(validLayouts.reference); updateBlock(copy, "b2", {name: "X"}); expect(copy).toEqual(validLayouts.reference);
for (const c of colors) expect(textColorFor(c.bg)).toBe(c.text);
expect(SUPPORTED_EMOJI).toHaveLength(64); expect(normalizeEmoji("❄️")).toBe("❄");
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: FAIL.

- [ ] **Step 3: Implement `edit.ts` and `color.ts`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/frontend/src/model custom_components/ha_controller/frontend/test
git commit -m "feat(panel): add pure layout edit operations"
```

---

### Task 3: Block map component (`hc-grid`)

**Files:**
- Create: `custom_components/ha_controller/frontend/src/components/hc-grid.ts`, `custom_components/ha_controller/frontend/test/hc-grid.test.ts`

**Interfaces:**
- Consumes: `placeholders`, `gridBounds` and `textColorFor`.
- Produces: a `<hc-grid>` element.
  - **Properties:** `layout: Layout`, `selectedId: string | null`, `errorRefs: ReadonlySet<string>`.
  - **Rendering:** a CSS grid with 96 px cells, a 12 px gap and a 16 px radius. Each cell is placed with `grid-column: x - minX + 1` and `grid-row: y - minY + 1`.
    - Blocks: `button.block[data-id]`, filled with their background, showing the name in `textColorFor(background)`.
    - The start block carries a 3 px outline and a `span.start-badge` with the text `start`.
    - Placeholders: `button.placeholder[data-x][data-y]`, with a 2 px dashed `--divider-color` border and a `+`.
    - State classes: `.selected` (ring in `--primary-color`) and `.has-error` (ring in `--error-color`).
  - **Events:** `hc-add-block` `{detail: {x, y}}` and `hc-select-block` `{detail: {id}}`. Both bubble and are composed.

- [ ] **Step 1: Write the failing tests**

```ts
const el = await mount(html`<hc-grid .layout=${validLayouts.reference} .selectedId=${null} .errorRefs=${new Set(["b4"])}></hc-grid>`);
expect(all(el, ".block")).toHaveLength(4);
expect(all(el, ".placeholder")).toHaveLength(8);
expect(one(el, '.block[data-id="b1"] .start-badge')?.textContent).toBe("start");
expect(one(el, '.block[data-id="b4"]')!.classList.contains("has-error")).toBe(true);
const added = nextEvent(el, "hc-add-block"); one(el, '.placeholder[data-x="1"][data-y="0"]')!.click();
expect((await added).detail).toEqual({x: 1, y: 0});
// grid placement: b3 (-1, 0) → column 2, row 3 with bounds minX -2, minY -2
expect(one(el, '.block[data-id="b3"]')!.style.gridColumn).toBe("2"); expect(one(el, '.block[data-id="b3"]')!.style.gridRow).toBe("3");
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: FAIL.

- [ ] **Step 3: Implement `hc-grid.ts`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/frontend/src/components/hc-grid.ts custom_components/ha_controller/frontend/test/hc-grid.test.ts
git commit -m "feat(panel): render the block map"
```

---

### Task 4: Block editor components

**Files:**
- Create:
  - `custom_components/ha_controller/frontend/src/messages.ts`
  - `custom_components/ha_controller/frontend/src/components/`: `hc-block-editor.ts`, `hc-item-editor.ts`, `hc-entity-input.ts`, `hc-emoji-picker.ts`, `hc-preview.ts`
  - `custom_components/ha_controller/frontend/test/hc-block-editor.test.ts`, `custom_components/ha_controller/frontend/test/hc-item-editor.test.ts`

**Interfaces:**
- Consumes: the Task 2 edit operations and `canDelete`.
- Produces:
  - **`messages.ts`:**
    - `errorMessage(code: string): string`, keyed by error code:

      | code | Message |
      |---|---|
      | `invalid_structure` | "The layout is malformed." |
      | `too_many_blocks` | "A screen holds at most 32 blocks." |
      | `invalid_id` | "Invalid identifier." |
      | `duplicate_id` | "Duplicate identifier." |
      | `coordinate_out_of_range` | "This block is too far from the centre of the map." |
      | `duplicate_position` | "Two blocks share the same cell." |
      | `invalid_start` | "Choose a start block." |
      | `disconnected` | "This block can't be reached from the start block." |
      | `invalid_name` | "Names need 1 to 32 characters." |
      | `invalid_background` | "Pick a background colour." |
      | `invalid_font_size` | "Pick a font size." |
      | `invalid_type` | "Pick a block type." |
      | `invalid_entity` | "Pick a valid entity." |
      | `too_many_items` | "A custom block holds at most 6 items." |
      | `invalid_item` | "Unknown item type." |
      | `invalid_text` | "Text needs 1 to 64 characters." |
      | `unsupported_emoji` | "This emoji is not available on the screen." |
      | `payload_too_large` | "The layout is too large for the screen. Remove blocks or shorten texts." |
      | `invalid_sleep_timeout` | "The sleep delay must be 0 (never) or between 5 and 3600 seconds." |
      | any other code | "Invalid layout." |

    - `deleteReason`: `start` → "Choose another start block first."; `disconnects` → "Other blocks would become unreachable."
  - **`<hc-block-editor>`:** properties `hass`, `layout` and `blockId`. It emits `hc-layout-change` `{detail: {layout}}` and contains:
    - a name input and a background colour input with 8 palette swatches;
    - font size buttons `S M L XL`;
    - a type select (`Entity` / `Custom`) that switches with `updateBlock` and keeps the other type's fields;
    - for entity blocks, `<hc-entity-input .domains=${["light", "climate"]}>`;
    - for custom blocks, the item list with an "Add item" select (Text, Emoji, Entity state, Battery, Screen brightness);
    - a `Set as start block` button, disabled for the start block;
    - a `Delete block` button, disabled with `deleteReason` text when `canDelete` refuses;
    - `<hc-preview>`.
  - **`<hc-item-editor>`:**
    - Properties: `hass`, `item`, `index` and `count`.
    - Kind-specific fields:
      - text: an input;
      - emoji: `<hc-emoji-picker>`;
      - entity: `<hc-entity-input>` (all domains) plus an optional attribute input.
    - A font size select (Inherit/S/M/L/XL) and up/down/remove buttons.
    - Events: `hc-item-change {patch}`, `hc-item-move {delta}` and `hc-item-remove`.
  - **`<hc-entity-input>`:** properties `hass`, `value` and `domains?: string[]`. It renders an `<input list>` with a `<datalist>` of matching entity ids, sorted, labelled by `friendly_name`, and emits `hc-value-change {value}`.
  - **`<hc-emoji-picker>`:** property `value`. It renders 64 `button.emoji` elements and emits `hc-value-change {value: normalizeEmoji(...)}`.
  - **`<hc-preview>`:** properties `block` and `hass`. It renders a 220 px circle in the block background with contrast text, showing the name and a content summary:
    - entity blocks: the entity's state;
    - custom blocks: one line per item.

- [ ] **Step 1: Write the failing tests**

```ts
// hc-block-editor
const changed = nextEvent(el, "hc-layout-change"); type(one(el, "input[name=name]")!, "Kitchen 2");
expect((await changed).detail.layout.blocks[0].name).toBe("Kitchen 2");
expect(options(el, "hc-entity-input datalist option")).toEqual(["climate.bedroom", "light.kitchen", "light.living_room"]); // hass has sensor.* too
expect(one(el, "button.delete")!.hasAttribute("disabled")).toBe(true);                // start block of the reference layout
expect(el.shadowRoot!.textContent).toContain("Choose another start block first.");
// switching b1 to Custom keeps entity_id, adds items []
// hc-item-editor / emoji picker
expect(all(picker, "button.emoji")).toHaveLength(64);
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: FAIL.

- [ ] **Step 3: Implement the five components and `messages.ts`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm --prefix custom_components/ha_controller/frontend test && npm --prefix custom_components/ha_controller/frontend run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller/frontend/src custom_components/ha_controller/frontend/test
git commit -m "feat(panel): add block and item editors"
```

---

### Task 5: Panel root, websocket API, dev harness, build and docs

**Files:**
- Create:
  - `custom_components/ha_controller/frontend/src/ha-controller-panel.ts`, `custom_components/ha_controller/frontend/src/api.ts`
  - `custom_components/ha_controller/frontend/dev/index.html`, `custom_components/ha_controller/frontend/dev/mock-hass.ts`
  - `custom_components/ha_controller/frontend/test/panel.test.ts`
  - `docs/configuration.md`
- Modify: `docs/README.md`, `docs/development.md` ("Panel" section), `.claude/CLAUDE.md`

**Interfaces:**
- Consumes: plan 2's websocket commands `ha_controller/screens`, `ha_controller/layout/get` and `ha_controller/layout/save`; Tasks 1–4.
- Produces:
  - **`api.ts`:** `listScreens(hass): Promise<ScreenInfo[]>`, `getLayout(hass, entryId): Promise<Layout>` and `saveLayout(hass, entryId, layout): Promise<{revision: string, pushed: boolean}>`.
  - **`<ha-controller-panel>`:**
    - Properties: `hass`, `narrow`, `panel`, `route`.
    - Internal state: `screens`, `entryId`, `saved`, `layout` (working copy), `selectedId`, `notice`, `saving`.
    - Lifecycle:
      - On the first `hass` assignment, load the screens and select the first one. A user selection is kept.
      - Refresh only `screens` every 10 s (an interval started in `connectedCallback` and cleared in `disconnectedCallback`).
      - Later `hass` changes never reload the layout.
    - Header:
      - `ha-menu-button` when `narrow`;
      - the title "HA Controller";
      - a screen select, shown when there is more than one screen;
      - the status line, one of:
        - `Offline`
        - `Online · firmware <v> — update available`, when the firmware differs from the integration version
        - `Online · firmware <v> · in sync`, when `revision == device_revision`
        - `Online · firmware <v> · syncing…`
      - `Revert` and `Save` buttons, disabled when `layout` deep-equals `saved` or when local validation returns errors.
    - Body: `<hc-grid>` plus `<hc-block-editor>` side by side, stacked when narrow. Local errors are listed under the map as `errorMessage(code)` plus the block name, and `errorRefs` is passed to the grid.
    - Screen settings: a "Screen" section under the map, with a number input "Sleep after (seconds)" wired through `setSleepTimeout` and the helper text "0 keeps the screen on."
    - Save:
      - Success: `Saved — sent to the screen.` when `pushed`, else `Saved — the screen is offline and will update when it reconnects.`
      - On rejection, keep the working copy. If `code == "invalid_layout"`, show the parsed error messages; otherwise show `err.message`.
  - **`dev/mock-hass.ts`:** `createMockHass()` returns a `Hass` with:
    - states for `light.kitchen`, `light.living_room`, `climate.bedroom` and `sensor.outdoor_temperature`;
    - `callWS` that serves one screen and keeps the layout in memory, starting from the reference fixture.

    Tests and `dev/index.html` both use it.

- [ ] **Step 1: Write the failing tests** in `panel.test.ts`, using `createMockHass` with `callWS` wrapped in `vi.fn`.

```ts
test("loads the first screen and renders its map", ...)                  // 4 .block inside hc-grid
test("save is disabled until something changes", ...)
test("adding a block and saving sends the new layout", ...)               // callWS called with {type: "ha_controller/layout/save", entry_id, layout: 5 blocks}; notice "Saved — sent to the screen."
test("save error keeps changes", ...)                                     // callWS rejects {code: "invalid_layout", message: "invalid_name@b2"} → "Names need 1 to 32 characters." shown, 5 blocks still rendered
test("refresh does not reset working copy", ...)                          // edit, advance fake timers 10 s, assign a new hass → edit still present
test("changing the sleep delay enables Save and sends it", ...)           // 20 → 45; saved layout.settings.sleep_timeout === 45
test("status line reports update available", ...)                         // firmware_version 0.0.9 vs integration 0.1.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix custom_components/ha_controller/frontend test`
Expected: FAIL.

- [ ] **Step 3: Implement `api.ts`, `ha-controller-panel.ts` (with `customElements.define` guarded against double definition), `dev/mock-hass.ts` and `dev/index.html`.**

- [ ] **Step 4: Run the tests and the build**

Run: `npm --prefix custom_components/ha_controller/frontend test && npm --prefix custom_components/ha_controller/frontend run build && test -f custom_components/ha_controller/frontend/dist/ha-controller-panel.js`
Expected: PASS, and the bundle exists.

- [ ] **Step 5: Manual check.** Run `npm --prefix custom_components/ha_controller/frontend run dev`. Expected:
  - the reference map looks like the screenshot, with 4 blocks and 8 "+";
  - clicking "+" right of Kitchen adds "Block 5";
  - deleting Hello World is refused with "Other blocks would become unreachable.";
  - Save shows the notice.

  The end-to-end check inside Home Assistant happens in plan 4, Task 5.

- [ ] **Step 6: Write the docs.**
  - **`docs/configuration.md`** (user guide):
    - opening the panel (sidebar › HA Controller, admin only);
    - the map: start block, adding a block with "+";
    - how swiping on the screen follows the map: put a finger on the right edge and slide left to open the block on the right, and the same for every edge;
    - block types (Light, Thermostat, Custom) and custom items;
    - font sizes S/M/L/XL and backgrounds (text colour is automatic);
    - screen settings: the sleep delay (default 20 s; `0` keeps the screen on);
    - saving and the status line;
    - limits (32 blocks, 6 items, 32-char names, 64-char texts, 64 emoji).
  - **`docs/development.md`**, "Panel" section: `npm ci`, `npm test`, `npm run dev` (mock harness), and `npm run build -- --watch` while testing in Home Assistant.
  - **`docs/README.md`:** link `configuration.md`.

- [ ] **Step 7: Commit**

```bash
git add custom_components/ha_controller/frontend docs .claude/CLAUDE.md
git commit -m "feat(panel): add panel root with save, status and dev harness"
```
