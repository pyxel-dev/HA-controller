# Releasing

## One-time setup

- Settings > Pages > Source: "GitHub Actions".
- Settings > Environments > `github-pages` > Deployment branches and tags: add a tag rule `v*`. By default the environment only accepts the default branch, so the `pages` job of a tag run would be rejected.
- Set the repository description and topics, which HACS requires.

## Steps

1. Set the version everywhere: `.github/scripts/.venv/bin/python .github/scripts/versioning.py bump X.Y.Z`.
2. Commit it: `git commit -am "chore: release X.Y.Z"`.
3. Tag and push: `git tag vX.Y.Z && git push origin main vX.Y.Z`.
4. Watch the "Release" workflow.
5. Check that the Pages installer shows X.Y.Z and that HACS offers X.Y.Z.

The workflow builds the panel, packages `ha_controller.zip`, compiles the firmware, rebuilds and deploys the GitHub Pages site with the new firmware and every earlier released firmware, and only then creates the GitHub release with the zip and the firmware files. Pages is deployed before the release so that the `firmware/<version>/ha-controller.ota.bin` URLs already exist when HACS offers the new version; otherwise the first automatic update would get a 404.

## Dry runs

Run the "Release" workflow with `workflow_dispatch`. Only the `build` job runs, and it uploads a `dist` artifact without creating a release.

## Stable OTA URLs

Installed integrations download `firmware/<version>/ha-controller.ota.bin` from the Pages site. Never change this layout.
