---
name: release
description: "Use when cutting a release or changing the release pipeline: versions, release workflow, GitHub Pages installer, HACS packaging, firmware OTA URLs."
---

# Releasing HA Controller

- Never edit versions by hand. Use `.github/scripts/.venv/bin/python .github/scripts/versioning.py bump X.Y.Z`.

## Steps (from `docs/releasing.md`)

1. `.github/scripts/.venv/bin/python .github/scripts/versioning.py bump X.Y.Z`
2. Commit `chore: release X.Y.Z`.
3. `git tag vX.Y.Z && git push origin main vX.Y.Z`
4. Watch the "Release" workflow.
5. Check that the Pages page shows X.Y.Z and that HACS offers X.Y.Z.

Dry runs use `workflow_dispatch` (only the `build` job runs).

## What each job produces

- `build`: `dist/ha_controller.zip` (integration with the built panel, for HACS) and `dist/ha-controller-X.Y.Z.*` (factory image, OTA image and OTA md5), uploaded as the `dist` artifact.
- `release`: the GitHub release with every file of `dist`. Tag runs only.
- `pages`: the installer site, built from `esphome/web` and the firmware of every release. Tag runs only.

## Rules

- OTA URLs must stay stable (`firmware/<v>/ha-controller.ota.bin`), because integrations already installed depend on them.
- After any script change, run `.github/scripts/.venv/bin/pytest .github/scripts/tests`.
