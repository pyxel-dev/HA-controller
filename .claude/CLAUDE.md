# HA Controller — guidance for Claude Code

HA Controller turns the Waveshare ESP32-S3-Touch-AMOLED-1.75 round touch screen into a Home Assistant remote.
It is a custom integration with a sidebar panel, an ESPHome firmware and a GitHub Pages web installer.

## Rules

- English only: code, comments, docs and commit messages.
- One version for the whole repository. Change it only with `python .github/scripts/versioning.py bump X.Y.Z` (added in plan 5).
- The protocol is defined in `docs/protocol/README.md` and pinned by `docs/protocol/fixtures/`.
- The repository root holds no files except README.md, hacs.json and .gitignore. Put every new file in the folder that owns it (see the repository map).
- TDD: write the failing test first, then the code.
- Never commit `esphome/secrets.yaml`.
- Specs and plans live in `docs/superpowers/`.

## Repository map

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

## Commands

```bash
python3.14 -m venv .github/scripts/.venv
.github/scripts/.venv/bin/pip install -r .github/scripts/requirements.txt
.github/scripts/.venv/bin/pytest .github/scripts/tests
.github/scripts/.venv/bin/ruff check .github/scripts
.github/scripts/.venv/bin/python .github/scripts/make_brand_icon.py   # regenerate brand icons

# Integration (own venv, run from the repository root)
python3.14 -m venv custom_components/.venv
custom_components/.venv/bin/pip install -r custom_components/requirements_test.txt
custom_components/.venv/bin/pytest custom_components/ha_controller/tests
custom_components/.venv/bin/ruff check custom_components

# Firmware (own venv, run from the repository root)
python3.13 -m venv esphome/.venv
esphome/.venv/bin/pip install -r esphome/requirements.txt
cmake -S esphome/tests -B esphome/tests/build && cmake --build esphome/tests/build
ctest --test-dir esphome/tests/build --output-on-failure

# Firmware (needs SDL2 for the simulator: brew install sdl2 / apt install libsdl2-dev)
esphome/.venv/bin/esphome compile esphome/ha-controller.yaml
esphome/.venv/bin/esphome compile esphome/simulator.yaml
esphome/.venv/bin/esphome run esphome/simulator.yaml   # desktop simulator, API on port 6053

# Panel (Node 24, run from the repository root)
npm --prefix custom_components/ha_controller/frontend ci
npm --prefix custom_components/ha_controller/frontend test
npm --prefix custom_components/ha_controller/frontend run typecheck
npm --prefix custom_components/ha_controller/frontend run build
npm --prefix custom_components/ha_controller/frontend run dev   # panel against a mock hass
```

## Skills and agents

- Skill `protocol-change` (`.claude/skills/protocol-change/`): checklist for any change that crosses the Home Assistant ↔ screen boundary.
- Skill `firmware-dev` (`.claude/skills/firmware-dev/`): commands, simulator loop and rules for the ESPHome firmware and LVGL code.
- Skill `add-widget` (`.claude/skills/add-widget/`): end-to-end checklist for a new block widget or custom item kind.
- Agent `firmware-reviewer` (`.claude/agents/firmware-reviewer.md`): reviews changes under `esphome/` for ESPHome/LVGL correctness, memory and hardware safety.
- Agent `protocol-guardian` (`.claude/agents/protocol-guardian.md`): reviews a diff for protocol consistency across docs, fixtures, Python, TypeScript and C++.
- Agent `ha-integration-reviewer` (`.claude/agents/ha-integration-reviewer.md`): reviews integration changes against Home Assistant development rules.
