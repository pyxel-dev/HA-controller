---
name: add-widget
description: Use when adding a new block widget or custom item kind (e.g. switch, cover, fan, media volume) end-to-end.
---

# Add a widget

A widget crosses the Home Assistant ↔ screen boundary, so start with the `protocol-change` skill and keep its checklist open. Then:

1. Protocol doc and fixtures: `docs/protocol/README.md` and `docs/protocol/fixtures/` (recompute golden `rev` values).
2. `ENTITY_BLOCK_DOMAINS` / `ITEM_KINDS` in `custom_components/ha_controller/const.py`, and the panel model in `custom_components/ha_controller/frontend/`.
3. The state builder and the control mapping in the integration.
4. The panel editor options and the preview.
5. The C++ parser enum and the view under `esphome/components/ha_controller/` (with host tests; see the `firmware-dev` skill).
6. `docs/configuration.md`.
7. Run all suites and both firmware compiles:
   - `custom_components/.venv/bin/pytest custom_components/ha_controller/tests`
   - `.github/scripts/.venv/bin/pytest .github/scripts/tests`
   - `npm --prefix custom_components/ha_controller/frontend test`
   - `ctest --test-dir esphome/tests/build --output-on-failure`
   - `esphome compile` for `esphome/ha-controller.yaml` and `esphome/simulator.yaml`

Finish with the `protocol-guardian` and `firmware-reviewer` agents.
