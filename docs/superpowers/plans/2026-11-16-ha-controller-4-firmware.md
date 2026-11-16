# HA Controller — Plan 4: ESPHome Firmware

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the screen firmware: an ESPHome config for the Waveshare ESP32-S3-Touch-AMOLED-1.75 plus a desktop simulator. It renders the layout pushed by the integration, navigates between blocks with edge swipes and smooth slides, drives the light/climate knobs and custom items, sleeps after the configured delay and wakes on touch, reports controls and hellos to Home Assistant, and installs firmware over the air on request.

**Architecture:** Two local external components.
- `ha_controller`:
  - **Pure C++17 modules** with no ESPHome or LVGL headers, unit-tested on the host against `docs/protocol/fixtures/`: `layout`, `states`, `knob`, `format`, `gesture`, `color`, `hold`.
  - **LVGL 9.5 modules:** `pager` (gestures, animation, edge hints) and `widgets` (block views).
  - **`HaController`:** the ESPHome component that glues them to the native API actions and events declared in YAML.
- `axp2101_battery`: reads the PMU.

YAML is split into `packages/board-waveshare-amoled-175.yaml` (hardware) and `packages/ui.yaml` (UI, API actions, hello). The device config and `simulator.yaml` (ESPHome `host` + SDL) both include them.

**Tech Stack:** ESPHome 2026.10.2, ESP-IDF, LVGL 9.5 (bundled by ESPHome), ArduinoJson 7, C++17, CMake ≥ 3.20, doctest 2.4.12, Python 3.13 (ESPHome CLI), SDL2 (simulator).

**Spec:** `docs/superpowers/specs/2026-11-16-ha-controller-design.md` (§4, §5, §7, §15)

## Global Constraints

- **ESPHome:** `esphome==2026.10.2` in `esphome/requirements.txt`, `min_version: 2026.10.0`, framework `esp-idf`. ESPHome project `pyxel-dev.ha-controller`, version `${project_version}` from `esphome/version.yaml`.
- **Hardware:** all pins, addresses, transforms and registers exactly as spec §4. The touch component `cst9217` comes from `https://github.com/shelson/esphome-cst9217`, pinned to the commit SHA current at implementation time.
- **LVGL 9.5 API names:**
  - screens and objects: `lv_screen_load`, `lv_layer_top`, `lv_obj_delete`, `lv_obj_remove_flag`;
  - animations: `lv_anim_set_duration`, `lv_anim_set_completed_cb`, `lv_anim_delete`, `lv_anim_path_ease_out`;
  - input and events: `lv_indev_active`, `lv_indev_get_point`, `lv_event_get_target_obj`, `lv_event_get_hit_test_info`;
  - rendering and activity: `lv_refr_now`, `lv_display_get_inactive_time`, `lv_display_trigger_activity`.

  Every LVGL call runs on the ESPHome main loop: `setup`, `loop`, API actions or LVGL event callbacks.
- **Pure modules:** `layout.*`, `states.*`, `knob.h`, `format.h`, `gesture.*`, `color.h`, `hold.h` and `axp2101_regs.h` include only the standard library and `<ArduinoJson.h>`. They compile on the host in C++17. All component sources stay flat in their component directory.
- **Protocol and constants:** protocol v1 (spec §7) and constants (spec §15). `PROTOCOL_VERSION = 1` lives in `layout.h`.
- **ESPHome callbacks:** views never register ESPHome sensor or number callbacks. `HaController` subscribes once in `setup()` and forwards to the live views, because callbacks cannot be removed when the layout is rebuilt.
- **Secrets:** no Wi-Fi credentials or secrets in any committed YAML.

## Review Focus

1. **A layout or state push arriving mid-swipe.** The pager must cancel the animation, reset the tracker and show the right page, with no dangling pointers. Owner: Task 3 `SwipeTracker reset` test, plus the Task 6 manual check "push a layout while dragging".
2. **Malformed or hostile payloads:** wrong types, huge numbers, missing `items`, deep nesting. The parser must return `invalid_payload` and leave the current UI untouched. Owner: Task 1 extra parser cases.
3. **Touches exactly on the ring boundary, on the diagonal, outside the visible circle, or arriving as several points.** Classification must stay deterministic. Owner: Task 3 boundary and tie tests.
4. **Battery absent or PMU not answering.** The sensors publish NaN, battery rows show `— %`, and nothing crashes. Owner: Task 2 `format_percent(NAN)`, Task 4 decode tests, Task 7 manual check with the battery unplugged.
5. **The touch that wakes a sleeping screen.** It must never toggle a light or move a knob, and the screen must not fall straight back asleep. Owner: Task 8 `should_sleep` tests and the Task 8 manual wake checks. The `millis()` wraparound cases remain covered by the Task 2 and Task 3 tests.

---

### Task 1: Host test harness, layout parser and colours

**Files:**
- Create:
  - `esphome/components/ha_controller/layout.h`, `layout.cpp`, `color.h`
  - `esphome/tests/CMakeLists.txt`, `esphome/tests/test_main.cpp`, `esphome/tests/fixtures.h`
  - `esphome/tests/test_layout.cpp`, `esphome/tests/test_color.cpp`

**Interfaces:**
- Produces (namespace `esphome::ha_controller`):

```cpp
constexpr int PROTOCOL_VERSION = 1;
enum class FontSize : uint8_t { S, M, L, XL };
enum class Widget : uint8_t { LIGHT, CLIMATE, CUSTOM };
enum class ItemKind : uint8_t { TEXT, EMOJI, ENTITY, BATTERY, BRIGHTNESS };
enum class ParseError : uint8_t { NONE, BAD_JSON, UNSUPPORTED_VERSION, INVALID_PAYLOAD };
struct Item { std::string id; ItemKind kind; FontSize font; std::string text; };
struct Block { std::string id; int x; int y; std::string name; uint32_t bg; FontSize font; Widget widget; std::vector<Item> items; };
struct Layout {
  std::string rev; std::string start;              // start is "" when null
  uint32_t sleep_s{20};                            // payload "sleep"; 0 = never
  std::vector<Block> blocks;
  const Block *find(const std::string &id) const;
  const Block *find_at(int x, int y) const;
};
ParseError parse_layout(const std::string &json, Layout &out);   // `out` is replaced only on NONE
const char *parse_error_code(ParseError e);                     // "none", "bad_json", "unsupported_version", "invalid_payload"
// color.h
bool parse_hex_rgb(const std::string &hex, uint32_t &out);      // "RRGGBB" or "#RRGGBB"
float relative_luminance(uint32_t rgb);
uint32_t text_color_for(uint32_t rgb);                          // 0x000000 if luminance > 0.30 else 0xFFFFFF
```

  Test helpers in `fixtures.h`: `std::string read_fixture(const std::string &relative)`, which reads from the `FIXTURES_DIR` compile definition, and `std::string json_field(const std::string &file, const char *key)`, which re-serialises one top-level field.

- [ ] **Step 1: Set up the host harness** in `esphome/tests/CMakeLists.txt`:
  - CMake ≥ 3.20, C++17.
  - `FetchContent` doctest `v2.4.12` (GIT_TAG) and ArduinoJson `v7.4.2` (GIT_TAG; same major as ESPHome's bundled 7.x).
  - Target `unit_tests`: every `test_*.cpp` plus the pure `.cpp` files from `../components/ha_controller/`.
  - Include path `../components`.
  - `FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../../docs/protocol/fixtures"`.
  - `add_test(unit_tests …)`.

- [ ] **Step 2: Write the failing tests**

```cpp
TEST_CASE("parses the reference payload") {
  Layout l; REQUIRE(parse_layout(json_field("payloads/valid/reference.json", "payload"), l) == ParseError::NONE);
  CHECK(l.rev == "90538742"); CHECK(l.start == "b1"); CHECK(l.sleep_s == 20); CHECK(l.blocks.size() == 4);
  CHECK(l.find("b3")->widget == Widget::CUSTOM); CHECK(l.find("b3")->items.size() == 5);
  CHECK(l.find("b3")->items[1].kind == ItemKind::EMOJI); CHECK(l.find("b3")->items[1].text == "👋");
  CHECK(l.find("b3")->items[1].font == FontSize::XL); CHECK(l.find("b3")->items[2].font == FontSize::S);
  CHECK(l.find("b4")->widget == Widget::CLIMATE); CHECK(l.find("b1")->bg == 0x5B9E4D);
  CHECK(l.find_at(0, -1)->id == "b2"); CHECK(l.find_at(5, 5) == nullptr);
}
TEST_CASE("parses the empty payload") { /* start == "" and blocks empty */ }
TEST_CASE("strips U+FE0F from emoji text") { /* {"…","kind":"emoji","text":"❄️",…} → "❄" */ }
TEST_CASE("rejects every invalid payload fixture") {
  // for each payloads/invalid/*.json: parse_layout(text, l) returns the expected code; a pre-filled `l` is unchanged
}
TEST_CASE("rejects hostile payloads") {
  // "x": 1e40 · "x": "1" · "name": 5 · custom block without "items" · "font": "xxl" · "bg": "GGGGGG" · "sleep": -1 · "sleep": 4000 · no "sleep" · nested 64-deep arrays → INVALID_PAYLOAD or BAD_JSON
}
TEST_CASE("text colour follows colors.json") { /* every entry: text_color_for(bg) == text */ }
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cmake -S esphome/tests -B build/tests && cmake --build build/tests`
Expected: FAIL (`layout.h` not found).

- [ ] **Step 4: Implement `layout.cpp` and `color.h`.**
  - Use `JsonDocument doc; deserializeJson(doc, json)`. An error or non-object gives `BAD_JSON`.
  - `v` must be the integer 1; otherwise `UNSUPPORTED_VERSION`.
  - Every required field from spec §7.3 must be present with its JSON type, `x`/`y` must fit `int`, and `sleep` must be an integer from 0 to 3600. Otherwise `INVALID_PAYLOAD`.
  - Remove the UTF-8 bytes `EF B8 8F` from `text`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cmake --build build/tests && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add esphome/components/ha_controller esphome/tests
git commit -m "feat(firmware): parse layout payloads on the screen"
```

---

### Task 2: State parser, knob scale, formatting and interaction hold

**Files:**
- Create:
  - `esphome/components/ha_controller/states.h`, `states.cpp`, `knob.h`, `format.h`, `hold.h`
  - `esphome/tests/test_states.cpp`, `test_knob.cpp`, `test_format.cpp`, `test_hold.cpp`

**Interfaces:**
- Produces:

```cpp
struct StateUpdate {
  std::string id; bool available{true};
  std::optional<bool> on; std::optional<int> brightness;          // light (nullopt brightness = on/off only)
  std::optional<float> target; float min{7}, max{35}, step{0.5f};   // climate
  std::string unit, current, action;                                // climate
  std::optional<std::string> text;                                  // entity item
};
bool parse_states(const std::string &json, std::vector<StateUpdate> &out);  // false on bad JSON / not an array; elements without a string id are skipped
struct KnobScale {
  float min, max, step;
  int steps() const;                 // round((max-min)/step); step <= 0 counts as 1; 0 when max <= min
  int index_of(float value) const;   // clamped to [0, steps()]
  float value_at(int index) const;   // min + index*step, clamped to [min, max]
};
std::string format_value(float value, float step);   // 1 decimal if step < 1, else none
std::string format_percent(float pct);               // "87 %", NaN → "— %"
class InteractionHold { public: explicit InteractionHold(uint32_t window_ms = 1500);
  void touch(uint32_t now_ms); bool active(uint32_t now_ms) const; };   // active iff touched and (now - last) < window, unsigned
```

- [ ] **Step 1: Write the failing tests**

```cpp
// states: parse json_field("states/<name>.json", "updates") for each fixture
CHECK(u.on == true); CHECK(u.brightness == 50);                                   // light-dimmable-on
CHECK(!u.brightness.has_value());                                                 // light-onoff
CHECK(u.available == false);                                                      // light-unavailable
CHECK(*u.target == doctest::Approx(20.5)); CHECK(u.step == doctest::Approx(0.5));
CHECK(u.unit == "°C"); CHECK(u.current == "19.8 °C"); CHECK(u.action == "Heating"); // climate-heating
CHECK(!u.target.has_value()); CHECK(u.current == "—");                            // climate-defaults
CHECK(*u.text == "12.3 °C");                                                      // entity-precision
CHECK_FALSE(parse_states("{\"id\":1}", out));
// knob
CHECK(KnobScale{0, 100, 1}.steps() == 100); CHECK(KnobScale{7, 35, 0.5f}.steps() == 56);
CHECK(KnobScale{7, 35, 0.5f}.index_of(20.5f) == 27); CHECK(KnobScale{7, 35, 0.5f}.value_at(27) == doctest::Approx(20.5));
CHECK(KnobScale{7, 35, 0.5f}.index_of(100) == 56); CHECK(KnobScale{7, 35, 0.5f}.index_of(-5) == 0);
CHECK(KnobScale{10, 10, 0.5f}.steps() == 0); CHECK(KnobScale{7, 35, 0}.steps() == 28);
// format
CHECK(format_value(20.5f, 0.5f) == "20.5"); CHECK(format_value(21, 1) == "21"); CHECK(format_value(21, 0.5f) == "21.0");
CHECK(format_percent(87.4f) == "87 %"); CHECK(format_percent(NAN) == "— %");
// hold
InteractionHold h; CHECK_FALSE(h.active(0)); h.touch(1000); CHECK(h.active(2499)); CHECK_FALSE(h.active(2500));
h.touch(0xFFFFFF00u); CHECK(h.active(0x00000100u));                               // wraparound
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cmake --build build/tests`
Expected: FAIL.

- [ ] **Step 3: Implement the five headers and `states.cpp`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cmake --build build/tests && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add esphome/components/ha_controller esphome/tests
git commit -m "feat(firmware): parse state updates and add knob helpers"
```

---

### Task 3: Edge-swipe gesture model

**Files:**
- Create: `esphome/components/ha_controller/gesture.h`, `gesture.cpp`, `esphome/tests/test_gesture.cpp`

**Interfaces:**
- Produces (spec §5.2–§5.3):

```cpp
enum class Edge : uint8_t { NONE, LEFT, RIGHT, TOP, BOTTOM };
struct GridStep { int dx; int dy; };
Edge classify_edge(int x, int y, int size, int edge_width);     // centre = size/2.0f; ring iff r >= size/2.0f - edge_width (inclusive); |dx| >= |dy| → horizontal
GridStep step_for(Edge edge);                                    // RIGHT {1,0} · LEFT {-1,0} · TOP {0,-1} · BOTTOM {0,1} · NONE {0,0}
struct SwipeConfig { int size = 466; float commit_ratio = 0.25f; float flick_velocity = 0.6f;
                     int flick_min_px = 24; float rubber_factor = 0.3f; int rubber_max_px = 48; uint32_t velocity_window_ms = 100; };
class SwipeTracker {
 public:
  explicit SwipeTracker(SwipeConfig cfg = {});
  void begin(Edge edge, bool has_target, int x, int y, uint32_t t_ms);
  int update(int x, int y, uint32_t t_ms);   // visual offset (px) along the navigation axis
  bool release(uint32_t t_ms);              // true = commit; tracker becomes inactive
  void reset();                             // abort without decision
  bool active() const; Edge edge() const; int progress() const;
};
uint32_t settle_duration_ms(int remaining_px, int size);   // clamp(220 * remaining / size, 80, 220)
```

- [ ] **Step 1: Write the failing tests**

```cpp
CHECK(classify_edge(233, 233, 466, 36) == Edge::NONE);   CHECK(classify_edge(460, 233, 466, 36) == Edge::RIGHT);
CHECK(classify_edge(5, 233, 466, 36) == Edge::LEFT);     CHECK(classify_edge(233, 4, 466, 36) == Edge::TOP);
CHECK(classify_edge(233, 462, 466, 36) == Edge::BOTTOM); CHECK(classify_edge(430, 233, 466, 36) == Edge::RIGHT);  // r = 197, boundary
CHECK(classify_edge(429, 233, 466, 36) == Edge::NONE);   CHECK(classify_edge(10, 10, 466, 36) == Edge::LEFT);     // diagonal tie → horizontal
CHECK(classify_edge(456, 10, 466, 36) == Edge::RIGHT);   // outside the visible circle still classifies
SwipeTracker t;
t.begin(Edge::RIGHT, true, 460, 233, 0); CHECK(t.update(400, 233, 50) == 60); CHECK(t.update(300, 240, 300) == 160); CHECK(t.release(400));
t.begin(Edge::RIGHT, true, 460, 233, 0); CHECK(t.update(420, 233, 500) == 40); CHECK_FALSE(t.release(600));       // slow and short
t.begin(Edge::LEFT, true, 5, 233, 0); t.update(25, 233, 10); CHECK(t.update(65, 233, 40) == 60); CHECK(t.release(45));  // flick
t.begin(Edge::RIGHT, true, 460, 233, 0); CHECK(t.update(470, 233, 50) == 0);                                       // outward ignored
t.begin(Edge::TOP, false, 233, 4, 0); CHECK(t.update(233, 204, 100) == 48); CHECK_FALSE(t.release(150));            // rubber band
t.begin(Edge::BOTTOM, true, 233, 462, 0); CHECK(t.update(233, -600, 50) == 466);                                   // clamp to size
t.begin(Edge::LEFT, true, 5, 233, 0xFFFFFFF0u); t.update(65, 233, 0x00000020u); CHECK(t.release(0x00000020u));      // wraparound flick
t.begin(Edge::LEFT, true, 5, 233, 0); t.update(300, 233, 10); t.reset(); CHECK_FALSE(t.active()); CHECK_FALSE(t.release(20));
CHECK(settle_duration_ms(466, 466) == 220); CHECK(settle_duration_ms(0, 466) == 80); CHECK(settle_duration_ms(233, 466) == 110);
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cmake --build build/tests`
Expected: FAIL.

- [ ] **Step 3: Implement `gesture.cpp`.** Keep a small ring buffer of `(t, progress)` samples, including the `begin` sample. On release, velocity = `(progress_now − progress_old) / (t_now − t_old)`, where `old` is the oldest sample inside `velocity_window_ms`. Use unsigned time differences.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cmake --build build/tests && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add esphome/components/ha_controller esphome/tests
git commit -m "feat(firmware): model edge swipes"
```

---

### Task 4: Hardware bring-up — board package, AXP2101 battery, boot page, firmware CI

**Files:**
- Create:
  - `esphome/requirements.txt`, `esphome/version.yaml`, `esphome/ha-controller.yaml`
  - `esphome/packages/board-waveshare-amoled-175.yaml`, `esphome/packages/ui.yaml`
  - `esphome/components/axp2101_battery/__init__.py`, `axp2101_battery.h`, `axp2101_battery.cpp`, `axp2101_regs.h`
  - `esphome/tests/test_axp2101.cpp`
  - `.github/workflows/firmware.yml`
- Modify: `esphome/tests/CMakeLists.txt` (include path for `axp2101_battery`), `.claude/CLAUDE.md` (commands)

**Interfaces:**
- Produces:
  - **`axp2101_regs.h`** (namespace `esphome::axp2101_battery`):
    - register constants `REG_STATUS1 = 0x00`, `REG_STATUS2 = 0x01`, `REG_ADC_CTRL = 0x30`, `REG_VBAT_H = 0x34`, `REG_VBAT_L = 0x35`, `REG_BAT_DET = 0x68`, `REG_BAT_PERCENT = 0xA4`;
    - `bool battery_present(uint8_t status1)` (bit 3);
    - `bool is_charging(uint8_t status2)`: `(status2 >> 5) == 0x01`;
    - `uint16_t battery_millivolts(uint8_t hi, uint8_t lo)`: `((hi & 0x1F) << 8) | lo`;
    - `float battery_percent(uint8_t raw)`: capped at 100.
  - **The `axp2101_battery:` YAML component:** `PollingComponent` + `i2c::I2CDevice`, default address `0x34`, `update_interval` default 30 s. It has optional sub-entities:
    - `battery_level`: sensor, %, device_class `battery`, accuracy 0;
    - `battery_voltage`: sensor, V, device_class `voltage`, accuracy 2;
    - `charging`: binary sensor, device_class `battery_charging`.

    `setup()` sets bit 0 of `0x30` and bit 0 of `0x68` (read-modify-write) and calls `mark_failed()` on an I²C error. `update()` publishes NaN for level and voltage when no battery is present.
  - **YAML ids used by later tasks:** `amoled` (display), `touch`, `bus_a`, `battery_level`, `battery_charging`, `screen_brightness`. The fonts are `font_s|m|l|xl`, `value_s|m|l|xl` and `emoji_s|m|l|xl`.

- [ ] **Step 1: Write the failing tests** in `test_axp2101.cpp`.

```cpp
CHECK(battery_present(0x08)); CHECK_FALSE(battery_present(0xF7));
CHECK(is_charging(0x20)); CHECK(is_charging(0x3F)); CHECK_FALSE(is_charging(0x40)); CHECK_FALSE(is_charging(0x00)); CHECK_FALSE(is_charging(0xA0));
CHECK(battery_millivolts(0x0F, 0xA0) == 4000); CHECK(battery_millivolts(0xFF, 0xFF) == 0x1FFF);
CHECK(battery_percent(87) == 87.0f); CHECK(battery_percent(150) == 100.0f);
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cmake --build build/tests`
Expected: FAIL (`axp2101_regs.h` not found).

- [ ] **Step 3: Implement `axp2101_regs.h`, the `axp2101_battery` component (`__init__.py`, `.h`, `.cpp`) and the CMake include path**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cmake --build build/tests && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 5: Write the YAML.**
  - **`esphome/requirements.txt`:** `esphome==2026.10.2`.
  - **`esphome/version.yaml`:** `substitutions: {project_version: "0.1.0"}`.
  - **`esphome/packages/board-waveshare-amoled-175.yaml`**, verbatim apart from the SHA:

```yaml
esphome:
  platformio_options:
    board_build.flash_mode: dio
    board_build.f_flash: 80000000L
    board_build.f_cpu: 240000000L
esp32:
  variant: esp32s3
  flash_size: 16MB
  framework:
    type: esp-idf
psram:
  mode: octal
  speed: 80MHz
external_components:
  - source:
      type: git
      url: https://github.com/shelson/esphome-cst9217
      ref: <commit SHA pinned at implementation time>
    components: [cst9217]
i2c:
  - id: bus_a
    sda: GPIO15
    scl: GPIO14
    frequency: 400kHz
spi:
  - id: display_qspi
    type: quad
    clk_pin: GPIO38
    data_pins: [GPIO4, GPIO5, GPIO6, GPIO7]
display:
  - platform: mipi_spi
    id: amoled
    model: CO5300
    bus_mode: quad
    reset_pin: GPIO39
    cs_pin: GPIO12
    dimensions: {width: 466, height: 466}
    auto_clear_enabled: false
    update_interval: never
touchscreen:
  - platform: cst9217
    id: touch
    display: amoled
    interrupt_pin: GPIO11
    reset_pin: GPIO40
    transform: {mirror_x: true, mirror_y: true}
    on_touch:
      - logger.log: {level: DEBUG, format: "touch x=%d y=%d", args: [touch.x, touch.y]}
axp2101_battery:
  i2c_id: bus_a
  battery_level: {id: battery_level, name: Battery}
  battery_voltage: {name: Battery voltage}
  charging: {id: battery_charging, name: Charging}
number:
  - platform: template
    id: screen_brightness
    name: Screen brightness
    icon: mdi:brightness-6
    entity_category: config
    unit_of_measurement: "%"
    min_value: 5
    max_value: 100
    step: 1
    initial_value: 80
    restore_value: true
    optimistic: true
    on_value:
      - lambda: id(amoled).set_brightness((uint8_t) lroundf(x * 2.55f));
```

  - **`esphome/packages/ui.yaml`:**
    - The 12 fonts of spec §4.2:
      - text: `file: {type: gfonts, family: Inter, weight: 600}`, `bpp: 4`, `glyphsets: [GF_Latin_Core]`;
      - value: same file, `glyphs: " 0123456789.,-+%°CFOfn—"`;
      - emoji: `file: {type: gfonts, family: Noto Emoji}`, `bpp: 4`, `glyphs: !include ../../custom_components/ha_controller/emoji.json`.
    - `lvgl:` with `displays: [amoled]`, `touchscreens: [touch]`, `buffer_size: 25%`, `bg_color: 0x000000` and page `boot_page` holding:
      - label `HA Controller` (`font_m`, white, centre, y −40);
      - label `v${project_version}` (`font_s`, `0x9CA3AF`, y 10);
      - label `💡` (`emoji_m`, y 70);
      - a hidden `arc` (`keep_arc`) and a hidden `slider` (`keep_slider`), so that ESPHome compiles those LVGL widgets for the runtime code.
  - **`esphome/ha-controller.yaml`:**
    - Substitutions `name: ha-controller` and `friendly_name: HA Controller`.
    - `packages`: `version`, `board`, `ui`.
    - `esphome:` with name, friendly_name, `name_add_mac_suffix: true`, `min_version: 2026.10.0` and `project: {name: pyxel-dev.ha-controller, version: ${project_version}}`.
    - `logger:`, `api:`, `ota: [{platform: esphome}]`.
    - `wifi: {ap: {ssid: HA Controller}}`, `captive_portal:`, `improv_serial:`.
    - `external_components: [{source: {type: local, path: components}}]`.

- [ ] **Step 6: Compile**

Run: `python3.13 -m venv esphome/.venv && esphome/.venv/bin/pip install -r esphome/requirements.txt && esphome/.venv/bin/esphome compile esphome/ha-controller.yaml`
Expected: `SUCCESS`, and the image fits the app partition (ESPHome sizes it for 16 MB). If a font option is rejected (e.g. `glyphsets`), replace it with an explicit `glyphs:` string covering U+0020–U+007E, U+00A0–U+017F and `°—…’“”€`. Record the change in `docs/hardware.md` in Task 9.

- [ ] **Step 7: Hardware check.** Flash over USB-C with `esphome/.venv/bin/esphome run esphome/ha-controller.yaml`. Expected:
  - the round display shows "HA Controller", the version and 💡, centred;
  - tapping near the top/right/bottom/left edges logs about `(233,5)` / `(460,233)` / `(233,460)` / `(5,233)`. If not, fix `transform` (`mirror_x`, `mirror_y`, `swap_xy`) and repeat;
  - with a battery: `Battery` reads 0–100 %, `Battery voltage` 3.3–4.3 V, and `Charging` turns on when USB is plugged in;
  - without a battery: level and voltage are unknown (NaN) and there are no errors;
  - the `Screen brightness` number dims the panel;
  - Wi-Fi provisioning works through the `HA Controller` access point and its captive portal.

- [ ] **Step 8: Add the firmware CI.** In `.github/workflows/firmware.yml`, workflow `Firmware`:
  - Triggers: `push` to `main` and `pull_request`, on paths `esphome/**`, `docs/protocol/**`, `custom_components/ha_controller/emoji.json` and `.github/workflows/firmware.yml`.
  - Job `host-tests`: `cmake -S esphome/tests -B build/tests`, `cmake --build build/tests`, `ctest --test-dir build/tests --output-on-failure`.
  - Job `compile`:
    - `actions/setup-python@v5` with Python 3.13;
    - `actions/cache@v4` on `~/.platformio` and `esphome/.esphome`, keyed on `hashFiles('esphome/requirements.txt', 'esphome/**/*.yaml')`;
    - `pip install -r esphome/requirements.txt`;
    - `esphome compile esphome/ha-controller.yaml`.

  Add the host-test and compile commands to `.claude/CLAUDE.md`.

- [ ] **Step 9: Commit**

```bash
git add esphome .github/workflows/firmware.yml .claude/CLAUDE.md
git commit -m "feat(firmware): bring up the Waveshare AMOLED 1.75 board"
```

---

### Task 5: `ha_controller` component, API actions, hello and simulator

**Files:**
- Create:
  - `esphome/components/ha_controller/__init__.py`, `ha_controller.h`, `ha_controller.cpp`
  - `esphome/components/ha_controller/widgets.h`, `widgets.cpp` (placeholder views in this task)
  - `esphome/simulator.yaml`
- Modify: `esphome/packages/ui.yaml`, `.github/workflows/firmware.yml` (simulator compile), `.claude/CLAUDE.md`

**Interfaces:**
- Consumes: Tasks 1–2 (parsers), plan 2 (hello handling, `set_layout`/`set_states` callers).
- Produces:
  - **The `ha_controller:` YAML component** (`DEPENDENCIES = ["lvgl"]`, `AUTO_LOAD = ["json"]`):
    - Keys: `id`, `size` (default 466), `edge_width` (default 36).
    - Fonts: `text_fonts`, `value_fonts`, `emoji_fonts`, each a mapping `{s, m, l, xl}` → `font` id.
    - Optional local sources: `battery_level` (sensor id), `battery_charging` (binary_sensor id), `screen_brightness` (number id).
    - Trigger `on_control`, with variables `block`, `item`, `op` (`std::string`) and `value` (`float`).
  - **The component class:**

```cpp
enum class FontRole : uint8_t { TEXT, VALUE, EMOJI };
class ControlSink { public: virtual void on_control(const std::string &block, const std::string &item, const char *op, float value) = 0; };
class HaController : public Component, public ControlSink {
 public:
  void setup() override; void loop() override; float get_setup_priority() const override;  // setup_priority::LATE
  void set_geometry(int size, int edge_width);
  void set_font(FontRole role, FontSize size, font::Font *font);   // wraps with lvgl::FontEngine → const lv_font_t*
  void set_battery_sensor(sensor::Sensor *s); void set_charging_sensor(binary_sensor::BinarySensor *s);
  void set_brightness_number(number::Number *n);
  void add_on_control_callback(std::function<void(std::string, std::string, std::string, float)> &&cb);
  void set_layout(const std::string &json);     // parse; on NONE rebuild views (keep current block id if still present, else start)
  void set_states(const std::string &json);     // dispatch each update to the view that owns its id
  void show_message(const std::string &title, const std::string &detail);   // full-screen overlay + lv_refr_now(nullptr)
  void hide_message();                          // back to what the current mode requires
  std::string get_revision() const;             // "none" until a layout is applied
  void on_control(const std::string &block, const std::string &item, const char *op, float value) override;
};
class ControlTrigger : public Trigger<std::string, std::string, std::string, float> { public: explicit ControlTrigger(HaController *parent); };
// widgets.h (completed in Task 7)
struct Theme { const lv_font_t *text[4]; const lv_font_t *value[4]; const lv_font_t *emoji[4]; int size; int edge_width; };
struct LocalSources { sensor::Sensor *battery{}; binary_sensor::BinarySensor *charging{}; number::Number *brightness{}; };
class BlockView { public: virtual ~BlockView();
  lv_obj_t *root() const; const std::string &id() const;
  virtual bool owns(const std::string &id) const;
  virtual void apply(const StateUpdate &u, uint32_t now_ms);
  virtual void on_local_update();                // battery / charging / brightness changed
  virtual void loop(uint32_t now_ms); };
std::unique_ptr<BlockView> make_block_view(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink, const LocalSources &local);
```

  - **Messages** (spec §5.9): the "no layout" detail is `App.get_name() + " · v" + ESPHOME_PROJECT_VERSION`.
  - **`ui.yaml` additions:**
    - the `ha_controller:` block wired to the Task 4 ids;
    - `on_control` → `homeassistant.event` `esphome.ha_controller_control`, with data `block`, `item`, `op` and `value: !lambda 'return str_sprintf("%.2f", value);'`;
    - `api: on_client_connected: [delay: 5s, script.execute: {id: send_hello, reason: connected}]`;
    - API actions `set_layout` (`layout: string`), which calls `id(ui).set_layout(layout)` then `script.execute {id: send_hello, reason: applied}`, and `set_states` (`states: string`);
    - script `send_hello` (`parameters: {reason: string}`, `mode: queued`) firing `esphome.ha_controller_hello` with data `node` (`App.get_name()`), `version: ${project_version}`, `protocol: "1"`, `revision` (`id(ui).get_revision()`) and `reason`;
    - `interval: 60s`, which runs the script with reason `heartbeat` when `api.connected`.
  - **Fallback for event data:** if ESPHome rejects lambdas in `homeassistant.event` `data:`, use `variables:` + `data_template:` with the same keys.

- [ ] **Step 1: Implement the codegen and the C++ component.**
  - In this task, `make_block_view` returns a basic view: a full-screen object with the block background and its name centred in `text_fonts[block.font]` and `text_color_for(bg)`.
  - The component builds its own screen (`lv_obj_create(nullptr)` + `lv_screen_load`) in `setup()`. It shows "Waiting for Home Assistant" until a layout arrives, and in this task it shows only the current block.
  - `setup()` registers the battery/charging/brightness state callbacks once, and they forward to `view->on_local_update()`.

- [ ] **Step 2: Write `esphome/simulator.yaml`**:
  - `packages`: `version` and `ui`.
  - `esphome:`: name `ha-controller-sim`, friendly name `HA Controller Simulator`, the same `project`.
  - `host:`, `logger:`, `api:`.
  - `display: [{platform: sdl, id: amoled, dimensions: {width: 466, height: 466}, auto_clear_enabled: false, update_interval: never}]` and `touchscreen: [{platform: sdl, id: touch, display: amoled}]`.
  - Template stand-ins: `sensor` `battery_level` (constant 76, unit %), `binary_sensor` `battery_charging` (false), and `number` `screen_brightness` (5–100, optimistic, no `on_value`).
  - `external_components` (local).

- [ ] **Step 3: Compile both configs**

Run: `esphome/.venv/bin/esphome compile esphome/ha-controller.yaml && esphome/.venv/bin/esphome compile esphome/simulator.yaml`
Expected: both `SUCCESS`. The simulator needs SDL2: `brew install sdl2` or `apt install libsdl2-dev`.

- [ ] **Step 4: End-to-end check with Home Assistant**, using plan 2's integration and plan 3's built panel.
  1. Run `esphome/.venv/bin/esphome run esphome/simulator.yaml`. The window shows "Waiting for Home Assistant".
  2. In Home Assistant, add an ESPHome device on `<dev machine IP>:6053`, then add the HA Controller integration and pick "HA Controller Simulator".
  3. Within 5 s of the connection, the simulator shows "No blocks yet". Developer tools › Events shows `esphome.ha_controller_hello` with reasons `connected` and then `applied`.
  4. In the panel, add three blocks and save. The simulator shows the start block's name on its background.
  5. Heartbeat hellos arrive every 60 s with a revision equal to the panel's.

- [ ] **Step 5: Extend CI and the docs.** In `firmware.yml` `compile`, add `sudo apt-get install -y libsdl2-dev` and `esphome compile esphome/simulator.yaml`. Add the simulator commands to `.claude/CLAUDE.md`.

- [ ] **Step 6: Commit**

```bash
git add esphome .github/workflows/firmware.yml .claude/CLAUDE.md
git commit -m "feat(firmware): receive layouts and talk to Home Assistant"
```

---

### Task 6: Pager — edge swipes, slide animation, edge hints

**Files:**
- Create: `esphome/components/ha_controller/pager.h`, `pager.cpp`
- Modify: `esphome/components/ha_controller/ha_controller.h`, `ha_controller.cpp`

**Interfaces:**
- Consumes: `classify_edge`, `step_for`, `SwipeTracker` and `settle_duration_ms` (Task 3); `Layout::find_at` (Task 1).
- Produces:

```cpp
struct PageRef { std::string id; int x; int y; lv_obj_t *obj; };
class Pager {
 public:
  void attach(lv_obj_t *screen, int size, int edge_width);   // creates viewport, edge overlay on lv_layer_top(), 4 hint arcs
  lv_obj_t *viewport() const;                                 // parent for page objects
  void set_pages(std::vector<PageRef> pages, const std::string &show_id);   // cancels animations, resets tracker, shows one page
  void set_enabled(bool enabled);                             // false while a message is shown
  const std::string &current_id() const;
};
```

- **Edge overlay:** a transparent full-screen object with `LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_ADV_HITTEST`. On `LV_EVENT_HIT_TEST` it sets `res` to `classify_edge(point) != NONE`.
  - `PRESSED` begins the tracker. The target is `find_at(current + step_for(edge))`. A present target page is unhidden at its offset.
  - `PRESSING` updates the tracker and positions the pages: current at `(-dx·offset, -dy·offset)`, target at `(dx·(size−offset), dy·(size−offset))`.
  - `RELEASED` and `PRESS_LOST` release the tracker and animate with `lv_anim_path_ease_out` over `settle_duration_ms(remaining, size)`. On completion, commit (the target becomes current, the old page is hidden, the hints are refreshed) or cancel (the target is hidden).
  - Presses during an animation are ignored.
- **Hints:** four non-clickable arcs on the top layer:
  - RIGHT 350°→10°, BOTTOM 80°→100°, LEFT 170°→190°, TOP 260°→280°;
  - size 458 px, width 6, white at `LV_OPA_60`, indicator and knob hidden;
  - visible only where `find_at` has a neighbour.

- [ ] **Step 1: Implement `Pager` and use it from `HaController`.** `set_layout` builds the views under `pager.viewport()`, then calls `set_pages`.

- [ ] **Step 2: Compile both configs**

Run: `esphome/.venv/bin/esphome compile esphome/ha-controller.yaml && esphome/.venv/bin/esphome compile esphome/simulator.yaml`
Expected: `SUCCESS`.

- [ ] **Step 3: Simulator check.** Build the reference map in the panel: Kitchen start, Lights above, Hello World left, Bedroom below Hello World. Expected:
  - From Kitchen, a mouse-drag from the left edge to the right slides to Hello World.
  - From the top edge downwards, it slides to Lights.
  - From the right edge leftwards, it rubber-bands by at most 48 px and returns.
  - From Hello World, the bottom edge upwards slides to Bedroom.
  - A drag starting in the centre does nothing.
  - A short slow drag snaps back; a quick flick commits.
  - The hints match the neighbours.
  - Saving a layout from the panel while holding a drag shows the new layout cleanly, with no stuck half-page.

- [ ] **Step 4: Device check.** Flash and repeat Step 3 with a finger. The slides look smooth (no visible stutter at ~30 fps or better). If they don't, try in order and keep the best:
  1. `lvgl: buffer_size: 100%`;
  2. `esp32: framework: sdkconfig_options: {CONFIG_ESP32S3_DATA_CACHE_64KB: "y", CONFIG_ESP32S3_DATA_CACHE_LINE_64B: "y"}`;
  3. `lvgl: buffer_size: 12%`.

  Note the result for `docs/hardware.md`.

- [ ] **Step 5: Commit**

```bash
git add esphome/components/ha_controller esphome/packages
git commit -m "feat(firmware): navigate between blocks with edge swipes"
```

---

### Task 7: Block views — light knob, climate knob, custom items

**Files:**
- Modify: `esphome/components/ha_controller/widgets.h`, `widgets.cpp`, `ha_controller.cpp`

**Interfaces:**
- Consumes: `KnobScale`, `format_value`, `format_percent`, `InteractionHold`, `StateUpdate`, `text_color_for` and `ControlSink` (Tasks 2, 5).
- Produces: `LightView`, `ClimateView` and `CustomView` behind `make_block_view`, following spec §5.5–§5.8 and §5.10.
  - **Geometry:** knob arc 370 px, width 28, background angles 135°→45°, `LV_OBJ_FLAG_ADV_HITTEST` so only the ring takes touches. The name sits 96 px from the top.
  - **Controls:**
    - Arc `LV_EVENT_VALUE_CHANGED` updates the centre label only.
    - Arc `LV_EVENT_RELEASED` → `sink.on_control(block, "", "set", value)`.
    - A centre tap on a dimmable light → `"toggle"`. The toggle button on an on/off-only light → `"toggle"`.
    - Every interaction calls `hold.touch(millis())`.
  - **`apply()`:** while the hold is active, store the update as pending. `loop()` applies the pending update once the hold has expired.
  - **Unavailable entity:** the centre shows `—` with a small `Unavailable` label, and the arc or button gets `LV_STATE_DISABLED`.
  - **Custom items:**
    - `text`, `emoji`, `entity` → labels, with `entity` text from `StateUpdate::text`.
    - `battery` → a row with `🔋` (or `⚡` while charging) and `format_percent(level)`.
    - `brightness` → a row with `☀` and a 220 px slider (5–100). It calls `brightness->make_call().set_value(v).perform()` at most every 100 ms while dragging and always on release, and follows the number's state in `on_local_update()`.
    - A custom block without items shows its name centred.

- [ ] **Step 1: Implement the three views.**

- [ ] **Step 2: Compile both configs**

Run: `esphome/.venv/bin/esphome compile esphome/ha-controller.yaml && esphome/.venv/bin/esphome compile esphome/simulator.yaml`
Expected: `SUCCESS`.

- [ ] **Step 3: Simulator + Home Assistant check.** Use the reference map with real or template entities. Expected:
  1. **Light:**
     - The knob shows Home Assistant's brightness.
     - Dragging to about 30 % and releasing sets the light to 30 % (logbook).
     - A centre tap toggles it.
     - A brightness change in Home Assistant moves the knob within 1 s.
     - While dragging, incoming updates do not move the knob.
  2. **On/off-only light:** a toggle button.
  3. **Climate:** steps of 0.5 °C; release updates the target; `Now …` and the action are shown.
  4. **Custom block:**
     - text, emoji and the outdoor temperature are shown, and the temperature follows sensor changes;
     - the battery row shows `🔋 76 %`;
     - the brightness slider changes `number.*_screen_brightness`.
  5. **Renamed entity:** renaming one bound entity in Home Assistant shows `—` + `Unavailable` and disables its control.

- [ ] **Step 4: Device check.**
  - Repeat checks 1, 3 and 4 on hardware.
  - The battery row shows the real level.
  - The brightness slider dims the panel smoothly.
  - With the battery unplugged, the row shows `🔋 — %` and nothing crashes.

- [ ] **Step 5: Commit**

```bash
git add esphome/components/ha_controller
git commit -m "feat(firmware): render light, climate and custom blocks"
```

---

### Task 8: Screen sleep and wake

**Files:**
- Create: `esphome/components/ha_controller/sleep.h`, `esphome/tests/test_sleep.cpp`
- Modify:
  - `esphome/components/ha_controller/__init__.py`, `ha_controller.h`, `ha_controller.cpp`
  - `esphome/packages/ui.yaml`, `esphome/packages/board-waveshare-amoled-175.yaml`
  - `esphome/simulator.yaml`

**Interfaces:**
- Consumes: `Layout::sleep_s` (Task 1); spec §5.11.
- Produces:

```cpp
// sleep.h (pure)
constexpr uint32_t DEFAULT_SLEEP_S = 20;
bool should_sleep(uint32_t inactive_ms, uint32_t timeout_s);   // false when timeout_s == 0; true iff inactive_ms >= timeout_s * 1000
// HaController additions
void set_sleep_timeout(uint32_t seconds);   // set_layout passes layout.sleep_s; DEFAULT_SLEEP_S until the first layout
bool is_sleeping() const;
void wake();                                // no-op when awake; otherwise fire on_wake, then lv_display_trigger_activity(nullptr)
```

  - **`ha_controller:` additions:**
    - Required `touchscreen` (id). The component registers a `touchscreen::TouchListener` whose `release()` calls `wake()` while sleeping.
    - Triggers `on_sleep` and `on_wake` (no variables).
  - **`loop()`:** while awake, when `should_sleep(lv_display_get_inactive_time(nullptr), timeout)` holds, mark the screen as sleeping and fire `on_sleep`.
  - **`show_message()`:** calls `wake()` first.
  - **YAML wiring:**
    - **Board package:** script `screen_on` runs `id(amoled).set_brightness((uint8_t) lroundf(id(screen_brightness).state * 2.55f));`, and script `screen_off` runs `id(amoled).set_brightness(0);`. The `screen_brightness` `on_value` becomes "if `!id(ui).is_sleeping()` then `script.execute: screen_on`".
    - **Simulator:** scripts `screen_on` and `screen_off` that only log.
    - **`ui.yaml`:**
      - `ha_controller:` gets `touchscreen: touch`;
      - `on_sleep: [script.execute: screen_off, lvgl.pause]`;
      - `on_wake: [lvgl.resume, lvgl.widget.redraw, script.execute: screen_on]`.

- [ ] **Step 1: Write the failing tests** in `test_sleep.cpp`.

```cpp
CHECK(DEFAULT_SLEEP_S == 20);
CHECK_FALSE(should_sleep(10'000'000, 0));                               // 0 = never
CHECK_FALSE(should_sleep(19'999, 20)); CHECK(should_sleep(20'000, 20));
CHECK_FALSE(should_sleep(3'599'999, 3600)); CHECK(should_sleep(3'600'000, 3600));
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cmake --build build/tests`
Expected: FAIL (`sleep.h` not found).

- [ ] **Step 3: Implement `sleep.h`**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cmake --build build/tests && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 5: Implement the component additions and the YAML wiring, then compile both configs**

Run: `esphome/.venv/bin/esphome compile esphome/ha-controller.yaml && esphome/.venv/bin/esphome compile esphome/simulator.yaml`
Expected: `SUCCESS`.

- [ ] **Step 6: Simulator check.** Expected:
  - After 20 s without input, the log shows `screen_off` and the window stops updating.
  - Clicking the light knob position wakes the screen without toggling or moving anything.
  - Setting the delay to 5 s in the panel makes the screen sleep after 5 s; `0` keeps it awake.
  - A Home Assistant state change made while asleep is visible right after waking.

- [ ] **Step 7: Device check.** Expected:
  - The panel goes black after the delay.
  - A tap on the knob area only wakes the screen, and the screen stays awake for the full delay afterwards.
  - Changing `Screen brightness` from Home Assistant while asleep keeps the panel dark, and the new level shows on wake.

- [ ] **Step 8: Commit**

```bash
git add esphome
git commit -m "feat(firmware): sleep after the configured delay and wake on touch"
```

---

### Task 9: OTA install action, firmware docs, skills and reviewer agent

**Files:**
- Create:
  - `docs/hardware.md`
  - `.claude/skills/firmware-dev/SKILL.md`, `.claude/skills/add-widget/SKILL.md`
  - `.claude/agents/firmware-reviewer.md`
- Modify: `esphome/ha-controller.yaml`, `docs/development.md` ("Firmware" section), `docs/README.md`, `.claude/CLAUDE.md`

**Interfaces:**
- Produces (used by plan 5): the device API action `install_firmware` (`url: string`, `md5_url: string`):

```yaml
ota:
  - platform: esphome
  - platform: http_request
http_request:
  verify_ssl: true
api:
  actions:
    - action: install_firmware
      variables: {url: string, md5_url: string}
      then:
        - lambda: |-
            id(ui).show_message("Updating firmware…", "Do not unplug the screen");
        - ota.http_request.flash:
            url: !lambda return url;
            md5_url: !lambda return md5_url;
        - lambda: |-
            id(ui).show_message("Update failed", "Check the screen's internet access");
        - delay: 5s
        - lambda: id(ui).hide_message();
```

  The action lives in the device config only, because the simulator has no HTTP OTA.

- [ ] **Step 1: Add the action, then compile**

Run: `esphome/.venv/bin/esphome compile esphome/ha-controller.yaml`
Expected: `SUCCESS`.

- [ ] **Step 2: OTA check on hardware.**
  1. Bump `esphome/version.yaml` locally to `0.1.1` (do not commit) and compile.
  2. Find the build output with `find esphome/.esphome/build -name firmware.ota.bin`. In that directory, create `firmware.ota.bin.md5` with `md5 -q firmware.ota.bin > firmware.ota.bin.md5` (Linux: `md5sum firmware.ota.bin | cut -d' ' -f1 > firmware.ota.bin.md5`), then serve it with `python3 -m http.server 8000 -d <that directory>`.
  3. Call `esphome.ha_controller_<suffix>_install_firmware` from Developer tools with the LAN URLs. The screen shows "Updating firmware…", reboots, and the next hello carries `0.1.1`. Run it once while the screen sleeps: it must wake first.
  4. Repeat with a wrong `.md5`. The screen shows "Update failed" for 5 s, then the pages return.
  5. Revert `version.yaml`.

- [ ] **Step 3: Write the docs.**
  - **`docs/hardware.md`:**
    - the board summary and pin table (spec §4);
    - power and battery notes;
    - the AXP2101 registers;
    - the performance settings chosen in Task 6;
    - any font fallback chosen in Task 4;
    - enclosures: link `../3D_models/` (with or without a PWR button).
  - **`docs/development.md`, "Firmware" section:**
    - prerequisites: Python 3.13 venv with `esphome/requirements.txt`, CMake, SDL2;
    - commands: host tests, compile, flash over USB, simulator;
    - connecting Home Assistant to the simulator;
    - the manual hardware checklist (Task 4 Step 7, Task 6 Steps 3–4, Task 7 Steps 3–4, Task 8 Steps 6–7, Task 9 Step 2).
  - **`docs/README.md`:** link `hardware.md`.

- [ ] **Step 4: Write the Claude guidance.**
  - **`.claude/skills/firmware-dev/SKILL.md`:**
    - `name: firmware-dev`.
    - `description:` "Use when building, flashing, simulating or changing the ESPHome firmware (esphome/), including LVGL UI code."
    - Body:
      - commands;
      - simulator loop;
      - rules:
        - pure logic goes in host-tested modules;
        - LVGL is called on the main loop only;
        - views never register ESPHome callbacks;
        - call `lv_refr_now` before blocking work;
        - LVGL is paused while the screen sleeps, so call `wake()` before showing anything the user must see;
        - fonts are declared in `ui.yaml` and mapped in `ha_controller:`;
        - new LVGL widget types need a hidden instance on `boot_page`;
        - controls stay inside radius 185;
        - keep the `cst9217` SHA pinned.
  - **`.claude/skills/add-widget/SKILL.md`:**
    - `name: add-widget`.
    - `description:` "Use when adding a new block widget or custom item kind (e.g. switch, cover, fan, media volume) end-to-end."
    - Body, a checklist that starts with the `protocol-change` skill:
      1. protocol doc and fixtures;
      2. `ENTITY_BLOCK_DOMAINS` / `ITEM_KINDS` in `const.py` and the panel model;
      3. state builder and control mapping;
      4. panel editor options and preview;
      5. C++ parser enum and view;
      6. `docs/configuration.md`;
      7. run all suites and both compiles.
  - **`.claude/agents/firmware-reviewer.md`:**
    - `name: firmware-reviewer`, `tools: Read, Grep, Glob, Bash`.
    - `description:` "Reviews changes under esphome/ for ESPHome/LVGL correctness, memory and hardware safety. Use before merging firmware changes."
    - Checklist:
      - no blocking calls in `loop` except the OTA action;
      - LVGL objects deleted with their views, with animations cancelled first;
      - no ESPHome callbacks registered per view;
      - JSON parsed defensively;
      - pins and addresses match `docs/hardware.md`;
      - host tests for new pure logic;
      - both configs compile.
    - Output: `file:line — issue — fix`.
  - **`.claude/CLAUDE.md`:** list the skills and the agent.

- [ ] **Step 5: Run every suite**

Run: `pytest custom_components/ha_controller/tests && pytest .github/scripts/tests && npm --prefix custom_components/ha_controller/frontend test && ctest --test-dir build/tests --output-on-failure`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add esphome/ha-controller.yaml docs .claude .claude/CLAUDE.md
git commit -m "feat(firmware): install firmware over the air on request"
```
