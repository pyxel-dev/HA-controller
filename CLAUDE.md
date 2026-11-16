# HA Controller — guidance for Claude Code

HA Controller turns the Waveshare ESP32-S3-Touch-AMOLED-1.75 round touch screen into a Home Assistant remote.
It is a custom integration with a sidebar panel, an ESPHome firmware and a GitHub Pages web installer.

## Rules

- English only: code, comments, docs and commit messages.
- One version for the whole repository. Change it only with `python scripts/versioning.py bump X.Y.Z` (added in plan 5).
- The protocol is defined in `docs/protocol.md` and pinned by `protocol/fixtures/`.
- TDD: write the failing test first, then the code.
- Never commit `esphome/secrets.yaml`.
- Specs and plans live in `docs/superpowers/`.

## Repository map

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

## Commands

| Command | Purpose |
|---|---|
| `pytest` | Run the Python tests |
| `ruff check .` | Lint the Python code |

## Skills and agents

- Skill `protocol-change` (`.claude/skills/protocol-change/`): checklist for any change that crosses the Home Assistant ↔ screen boundary.
- Agent `protocol-guardian` (`.claude/agents/protocol-guardian.md`): reviews a diff for protocol consistency across docs, fixtures, Python, TypeScript and C++.
