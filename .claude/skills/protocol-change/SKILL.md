---
name: protocol-change
description: "Use when changing anything that crosses the Home Assistant ↔ screen boundary: layout fields, validation rules, payload keys, state update fields, events, actions, emoji list or limits."
---

# Changing the HA ↔ screen protocol

1. Classify the change. The C++ parser rejects unknown `widget`/`kind`/`font` values, so any new value is breaking: bump `PROTOCOL_VERSION` in `custom_components/ha_controller/const.py` and in the firmware's `ha_controller.h`.
2. Edit `docs/protocol/README.md` first.
3. Update `docs/protocol/fixtures/`, keeping one rule per invalid fixture and regenerating golden `rev` values with the snippet in `docs/protocol/README.md`.
4. Update the Python code in `custom_components/ha_controller/` (`layout.py`, `compiler.py`, `states.py`, `controls.py`) with its tests in `custom_components/ha_controller/tests`, the TypeScript model (`custom_components/ha_controller/frontend/src/model/`), the C++ parsers (`esphome/components/ha_controller/layout.*`, `states.*`) and the renderers (`widgets.*`, panel editor).
5. Run `pytest custom_components/ha_controller/tests`, `pytest .github/scripts/tests`, `npm --prefix custom_components/ha_controller/frontend test`, the host C++ tests and `esphome compile`.
6. Ask the `protocol-guardian` agent to review.
