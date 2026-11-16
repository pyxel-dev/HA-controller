# HA Controller — Plan 5: Versioning, Firmware Updates, Web Installer and Releases

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the integration and the firmware as one version:
- a version check and bump script;
- a firmware update entity in Home Assistant that keeps each screen on the integration's exact version, automatically by default;
- a GitHub Pages web installer that shows the version it flashes;
- a tag-driven release workflow that publishes the HACS zip, the firmware binaries and the Pages site.

**Architecture:**
- **Versioning:** `scripts/versioning.py` owns the version rule.
- **Updates:** the integration's `update` platform asks the screen, through plan 4's `install_firmware` action, to download its OTA image for the integration version from GitHub Pages.
- **Release scripts:** three small, unit-tested scripts collect the firmware, package the integration and assemble the Pages site from GitHub release assets.
- **Workflow:** `release.yml` chains them on a `vX.Y.Z` tag. A manual run is a dry run.

**Tech Stack:** Python 3.14 (integration, scripts, tests), Python 3.13 (ESPHome CLI in CI), GitHub Actions, `gh` CLI, ESP Web Tools 10.5.2, HACS.

**Spec:** `docs/superpowers/specs/2026-11-16-ha-controller-design.md` (§10, §11)

## Global Constraints

- **Version:** one SemVer `X.Y.Z` in `custom_components/ha_controller/manifest.json`, `esphome/version.yaml`, `frontend/package.json` and `frontend/package-lock.json` (root `version` and `packages[""].version`). Change it only with `scripts/versioning.py bump`.
- **URLs:** firmware OTA `https://pyxel-dev.github.io/HA-controller/firmware/<version>/ha-controller.ota.bin` (+ `.md5`); release notes `https://github.com/pyxel-dev/HA-controller/releases/tag/v<version>`.
- **Release assets:** `ha_controller.zip`, `ha-controller-<v>.factory.bin`, `ha-controller-<v>.ota.bin`, `ha-controller-<v>.ota.bin.md5`. The `.md5` file holds exactly 32 lowercase hex characters and no newline.
- **Timings:** install timeout 300 s; auto-update at most once per screen and version every 3600 s; auto-update only when the integration version matches `^\d+\.\d+\.\d+$`.
- **Strings:** English only.

## Review Focus

1. **OTA failing repeatedly** (no internet, Pages outage). Expected: one automatic attempt per hour per version, never a storm. Owner: Task 2 `test_auto_update_installs_at_most_once_per_hour`.
2. **Screen newer than the integration** after an integration rollback. Expected: the update entity offers the integration's version and auto-update installs it. Owner: Task 2 `test_newer_firmware_is_offered_as_update`.
3. **Tag and version mismatch, or a non-SemVer tag.** Expected: the workflow fails before anything is published. Owner: Task 1 `test_check_tag_must_match`; in Task 4 the version check is the first build step.
4. **Pages rebuild dropping older OTA images.** Screens on an older integration could no longer update. Owner: Task 3 `test_build_site_keeps_every_release`.
5. **Install requested while the screen is offline or already updating.** Expected: a clear error and no second install. Owner: Task 2 `test_install_when_offline_raises`, `test_install_while_in_progress_raises`.

---

### Task 1: Version check and bump

**Files:**
- Create: `scripts/versioning.py`, `tests/scripts/__init__.py`, `tests/scripts/test_versioning.py`
- Modify: `.github/workflows/ci.yml` (job `versions`), `CLAUDE.md`

**Interfaces:**
- Produces:
  - `VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")`
  - `def read_versions(root: Path) -> dict[str, str]`, keyed by `manifest`, `esphome`, `frontend`, `frontend-lock`. The `esphome` value comes from the line `project_version: "X.Y.Z"`, and `frontend-lock` must agree in both lock positions.
  - `def check_versions(root: Path, tag: str | None = None) -> list[str]`: human-readable errors, `[]` when consistent; `tag` must equal `v` + version.
  - `def bump_version(root: Path, version: str) -> None`: raises `ValueError` on non-SemVer input. Rewrites JSON with 2-space indent and a trailing newline, and edits only the YAML line.
  - `def main(argv: list[str] | None = None) -> int`: `check [--tag vX.Y.Z]` → 0/1, `bump X.Y.Z` → 0.

- [ ] **Step 1: Write the failing tests.** A `repo(tmp_path)` fixture writes the four files at `0.1.0`.

```python
def test_read_versions(repo): assert set(read_versions(repo).values()) == {"0.1.0"}
def test_check_passes_when_equal(repo): assert check_versions(repo) == []
def test_check_reports_mismatch(repo): ...        # manifest 0.2.0 → one error naming "manifest", "0.2.0" and "0.1.0"
def test_check_tag_must_match(repo):
    assert check_versions(repo, "v0.1.0") == [] and check_versions(repo, "v0.1.1") and check_versions(repo, "0.1.0")
def test_check_rejects_non_semver(repo): ...       # all files "0.1" → error
def test_bump_rewrites_all(repo): ...              # bump 1.2.3 → all four "1.2.3"; other JSON keys and YAML lines preserved
@pytest.mark.parametrize("bad", ["1.2", "v1.2.3", "1.2.3-rc1"])
def test_bump_rejects_invalid(repo, bad): ...
def test_repository_versions_are_consistent(): assert check_versions(REPO_ROOT) == []
def test_main_exit_codes(repo): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/scripts/test_versioning.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `scripts/versioning.py`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/scripts -v && python scripts/versioning.py check`
Expected: PASS, exit 0.

- [ ] **Step 5: Add CI and the docs.** Add job `versions` to `ci.yml` (setup-python 3.14, `python scripts/versioning.py check`). Add the commands to `CLAUDE.md`, and replace its plan-5 placeholder rule with the real command.

- [ ] **Step 6: Commit**

```bash
git add scripts/versioning.py tests/scripts .github/workflows/ci.yml CLAUDE.md
git commit -m "build: add single-version check and bump script"
```

---

### Task 2: Firmware update entity, auto-update and options flow

**Files:**
- Create: `custom_components/ha_controller/firmware.py`, `custom_components/ha_controller/update.py`, `tests/integration/test_update.py`
- Modify:
  - `custom_components/ha_controller/controller.py`, `__init__.py` (`PLATFORMS = [Platform.UPDATE]`), `config_flow.py` (options flow)
  - `strings.json`, `translations/en.json`

**Interfaces:**
- Consumes: plan 2's `ScreenController` (`device`, `integration_version`, `async_call_device`, `async_add_listener`, hello handling); plan 4's device action `install_firmware(url, md5_url)`.
- Produces:
  - **`firmware.py`:** `def firmware_urls(version: str) -> tuple[str, str]`, returning the `.ota.bin` URL and its `.md5` URL, and `def is_release_version(version: str) -> bool`.
  - **`ScreenController` additions:**
    - `install_in_progress: bool`.
    - `async def async_install_firmware(self, version: str) -> None`. It raises `HomeAssistantError`:
      - "The screen is offline." when it is not online;
      - "A firmware update is already running." when an install is in progress;
      - when the device call fails;
      - "Firmware update to {version} did not complete." when no hello with `{version}` arrives within 300 s.

      It notifies listeners when the install starts and when it ends.
    - Auto-update inside `async_handle_hello`: when `entry.options.get(CONF_AUTO_UPDATE, True)`, the integration version is a release, the hello version differs from it, no install is running, and the last automatic attempt for that version is at least 3600 s old, then start `hass.async_create_background_task(...)` that installs and logs any failure.
  - **`update.py`:** `FirmwareUpdateEntity(UpdateEntity)`.
    - Entity setup: `has_entity_name`, `translation_key = "firmware"` ("HA Controller firmware"), `unique_id = f"{device_id}-firmware"`, `device_info = DeviceInfo(connections=<screen device>.connections)`.
    - Features: `INSTALL | PROGRESS`, `title = "HA Controller"`.
    - Versions: `installed_version = controller.device.version` and `latest_version = controller.integration_version`.
    - `release_url = RELEASE_URL.format(version=latest)` and `in_progress = controller.install_in_progress`.
    - `version_is_newer(latest, installed)` returns `latest != installed`.
    - `async_install(version, backup, **kwargs)` installs `latest_version`.
    - `async_added_to_hass` subscribes `async_write_ha_state` to the controller.
  - **Options flow:** `OptionsFlowHandler(OptionsFlow)` with step `init`: a boolean `auto_update` defaulting to the current option or `True`. `HaControllerConfigFlow.async_get_options_flow(config_entry)` returns `OptionsFlowHandler()`.
  - **Strings:**
    - `entity.update.firmware.name` = "HA Controller firmware".
    - Options step `init`: title "HA Controller options"; `auto_update` label "Update the screen firmware automatically"; description "Installs the firmware that matches this integration's version whenever the screen reports a different one."

- [ ] **Step 1: Write the failing tests.** Mock the `esphome.ha_controller_aabbcc_install_firmware` service and drive time with `freezer`.

```python
async def test_unknown_before_first_hello(hass): ...                      # state "unknown"
async def test_update_entity_reports_versions(hass): ...                  # hello 0.0.9 → state "on", installed 0.0.9, latest 0.1.0, release_url …/tag/v0.1.0
async def test_update_entity_off_when_versions_match(hass): ...
async def test_newer_firmware_is_offered_as_update(hass): ...             # hello 0.2.0 → "on"
async def test_install_calls_device_and_completes_on_hello(hass): ...
    # auto_update off; update.install → call data {"url": ".../firmware/0.1.0/ha-controller.ota.bin", "md5_url": "....ota.bin.md5"}
    # in_progress True until hello version 0.1.0 → state "off", in_progress False
async def test_install_times_out(hass, freezer): ...                       # +301 s → HomeAssistantError, in_progress False
async def test_install_when_offline_raises(hass): ...
async def test_install_while_in_progress_raises(hass): ...
async def test_auto_update_installs_at_most_once_per_hour(hass, freezer): ...  # hello 0.0.9 ×2 → 1 call; +3601 s → 2 calls
async def test_auto_update_disabled_by_option(hass): ...
async def test_auto_update_skipped_for_dev_versions(hass): ...             # controller integration version "0.2.0.dev0" → no call
async def test_options_flow_toggles_auto_update(hass): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/integration/test_update.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `firmware.py`, the controller additions, `update.py` and the options flow.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest -v && ruff check .`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/ha_controller tests/integration/test_update.py
git commit -m "feat(integration): keep screen firmware on the integration version"
```

---

### Task 3: Release scripts and the web installer page

**Files:**
- Create:
  - `scripts/collect_firmware.py`, `scripts/package_integration.py`, `scripts/build_pages.py`
  - `esphome/web/index.html`
  - `tests/scripts/test_release_scripts.py`

**Interfaces:**
- Consumes: the plan 3 bundle `custom_components/ha_controller/frontend/ha-controller-panel.js`; the ESPHome build tree (`esphome/.esphome/build/**/firmware.factory.bin`, `firmware.ota.bin`).
- Produces (each has an `argparse` CLI with the same parameters):
  - **`collect(build_dir: Path, version: str, out_dir: Path) -> list[Path]`.** Requires exactly one `*.factory.bin` and one `*.ota.bin` under `build_dir`, otherwise it raises `ValueError`. It writes `ha-controller-<v>.factory.bin`, `ha-controller-<v>.ota.bin` and `ha-controller-<v>.ota.bin.md5`.
  - **`package(root: Path, out_file: Path) -> Path`.** Zips the contents of `custom_components/ha_controller/` at the zip root, excluding `__pycache__/`, `*.pyc` and `.gitkeep`. Raises `FileNotFoundError("Build the panel first: npm --prefix frontend run build")` when the bundle is missing.
  - **`build_site(web_dir: Path, releases_dir: Path, latest: str, out_dir: Path) -> None`.** `releases_dir/<v>/` holds each release's assets. It writes:
    - `index.html`, with every `{{VERSION}}` replaced by `latest`;
    - `.nojekyll`;
    - `firmware/ha-controller.factory.bin`, copied from `latest`;
    - `firmware/<v>/ha-controller.ota.bin` and `.md5` for **every** version;
    - `firmware/manifest.json`:

```json
{"name": "HA Controller", "version": "<latest>", "home_assistant_domain": "esphome", "new_install_prompt_erase": true,
 "builds": [{"chipFamily": "ESP32-S3",
             "parts": [{"path": "ha-controller.factory.bin", "offset": 0}],
             "ota": {"path": "<latest>/ha-controller.ota.bin", "md5": "<md5 of latest>",
                     "release_url": "https://github.com/pyxel-dev/HA-controller/releases/tag/v<latest>"}}]}
```

  - **`esphome/web/index.html`:** a self-contained English page with inline CSS following `prefers-color-scheme`, titled "HA Controller — Web installer". It contains:
    - the subtitle "Firmware {{VERSION}}" and a release-notes link `…/releases/tag/v{{VERSION}}`;
    - `<script type="module" src="https://unpkg.com/esp-web-tools@10.5.2/dist/web/install-button.js?module"></script>`;
    - `<esp-web-install-button manifest="firmware/manifest.json">` with slots `unsupported` ("Use Chrome or Edge on a desktop computer.") and `not-allowed` ("Open this page over HTTPS.");
    - five steps:
      1. connect the screen with USB-C;
      2. click Install;
      3. set up Wi-Fi when asked, or join the "HA Controller" access point;
      4. add the screen in Home Assistant (ESPHome);
      5. install the HA Controller integration **{{VERSION}}** from HACS;
    - the tip "If the board is not detected, hold BOOT while plugging it in."

- [ ] **Step 1: Write the failing tests**

```python
def test_collect_writes_versioned_files_and_md5(tmp_path): ...          # .md5 == hashlib.md5(ota).hexdigest(), 32 chars, no newline
def test_collect_requires_exactly_one_of_each(tmp_path): ...            # none → ValueError; two factory bins → ValueError
def test_package_zips_integration_with_panel(tmp_path): ...             # names include "manifest.json", "frontend/ha-controller-panel.js"; no __pycache__
def test_package_requires_built_panel(tmp_path): ...
def test_build_site_manifest(tmp_path): ...                             # exact dict above for latest 0.2.0
def test_build_site_keeps_every_release(tmp_path): ...                  # releases 0.1.0 + 0.2.0 → both firmware/<v>/ha-controller.ota.bin(.md5)
def test_build_site_renders_version(tmp_path): ...                      # index.html contains "Firmware 0.2.0", no "{{VERSION}}"; .nojekyll exists
def test_build_site_requires_latest_assets(tmp_path): ...
def test_web_page_template(): ...                                       # real esphome/web/index.html: ≥ 2 "{{VERSION}}" and "esp-web-tools@10.5.2"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/scripts/test_release_scripts.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the three scripts and `index.html`.**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/scripts -v`
Expected: PASS.

- [ ] **Step 5: Preview locally.**
  1. Build a fake site from the scripts' test data: `python scripts/build_pages.py --web esphome/web --releases <tmp> --latest 0.1.0 --out site`.
  2. Serve it with `python3 -m http.server -d site`.
  3. Open it in Chrome and confirm the page shows "Firmware 0.1.0" and an Install button.

- [ ] **Step 6: Commit**

```bash
git add scripts esphome/web tests/scripts
git commit -m "build: add release packaging scripts and web installer page"
```

---

### Task 4: Release workflow, HACS packaging, user docs and release skill

**Files:**
- Create:
  - `.github/workflows/release.yml`
  - `docs/getting-started.md`, `docs/updates.md`, `docs/releasing.md`
  - `.claude/skills/release/SKILL.md`
- Modify: `hacs.json`, `README.md`, `docs/README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: Tasks 1–3, `esphome/requirements.txt` and the `npm` scripts.
- Produces:
  - **`hacs.json`:** `{"name": "HA Controller", "homeassistant": "2026.10.0", "zip_release": true, "filename": "ha_controller.zip"}`.
  - **`release.yml`.** Triggers: `push` on tags `v*` and `workflow_dispatch` (dry run). Permissions: `contents: write`, `pages: write`, `id-token: write`. Concurrency group `release`.
    - **Job `build`** (`ubuntu-latest`). Steps, in order:
      1. Checkout, then setup-python 3.13 and setup-node 24 with the npm cache.
      2. Read the version from `manifest.json` into an output.
      3. `python scripts/versioning.py check`, plus `--tag "$GITHUB_REF_NAME"` on tag runs.
      4. `npm --prefix frontend ci` and `npm --prefix frontend run build`.
      5. `python scripts/package_integration.py --out dist/ha_controller.zip`.
      6. `pip install -r esphome/requirements.txt` and `esphome compile esphome/ha-controller.yaml`.
      7. `python scripts/collect_firmware.py --build-dir esphome/.esphome/build --version <v> --out dist`.
      8. `actions/upload-artifact@v4` (`dist`).
    - **Job `release`** (needs `build`, tag runs only): download the artifact, then `gh release create "$GITHUB_REF_NAME" dist/* --title "$GITHUB_REF_NAME" --generate-notes --verify-tag` with `GH_TOKEN`.
    - **Job `pages`** (needs `build` and `release`, tag runs only, environment `github-pages`):
      1. Checkout.
      2. For every tag from `gh release list --limit 200 --json tagName -q '.[].tagName'`, run `gh release download "$tag" -p 'ha-controller-*' -D "releases/${tag#v}"`.
      3. `python scripts/build_pages.py --web esphome/web --releases releases --latest <v> --out site`.
      4. `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` (`site`) and `actions/deploy-pages@v4`.

- [ ] **Step 1: Write the workflow and update `hacs.json`.**

- [ ] **Step 2: Dry run.** Push the branch, run "Release" with `workflow_dispatch`, and download the `dist` artifact. Expected:
  - the `build` job is green and `release`/`pages` are skipped;
  - the artifact holds `ha_controller.zip` (with `frontend/ha-controller-panel.js` inside) plus the three `ha-controller-0.1.0.*` files.

- [ ] **Step 3: Write the user docs.**
  - **`docs/getting-started.md`:**
    1. Hardware and enclosure: link `../3D_models/`.
    2. Flash from `https://pyxel-dev.github.io/HA-controller/` with Chrome or Edge.
    3. Wi-Fi via Improv or the `HA Controller` access point and captive portal.
    4. Adopt the discovered ESPHome device in Home Assistant.
    5. In HACS, add the custom repository `https://github.com/pyxel-dev/HA-controller` (type Integration), install the **same version** as shown on the installer page, and restart.
    6. Settings › Devices & services › Add integration › HA Controller, then pick the screen.
    7. Open the HA Controller panel.

    Troubleshooting:
    - **The screen stays on "Waiting for Home Assistant":** check that the ESPHome device and the HA Controller entry exist. If the hello events never show up under Developer tools › Events, enable "Allow the device to perform Home Assistant actions" in the ESPHome device options.
    - **"Firmware update required":** see `updates.md`.
  - **`docs/updates.md`:**
    - The one-version rule.
    - Integration updates come through HACS. To install them automatically, create an automation that calls `update.install` on the HACS update entity.
    - Firmware follows the integration automatically (the `auto_update` option, default on), or by hand from the "HA Controller firmware" update entity.
    - Rolling back the integration makes the firmware follow.
    - A screen without internet access must be re-flashed over USB from the installer.
  - **`docs/releasing.md`:**
    - One-time setup: Settings › Pages › Source "GitHub Actions"; repository description and topics for HACS.
    - Steps:
      1. `python scripts/versioning.py bump X.Y.Z`
      2. commit `chore: release X.Y.Z`
      3. `git tag vX.Y.Z && git push origin main vX.Y.Z`
      4. watch the "Release" workflow
      5. check the Pages page shows X.Y.Z, and that HACS offers X.Y.Z
    - Dry runs use `workflow_dispatch`.
  - **`README.md`:** an "Install" section with the installer URL and the HACS custom repository, and links to `docs/getting-started.md` and `docs/README.md`.
  - **`docs/README.md`:** link the three new docs.

- [ ] **Step 4: Write `.claude/skills/release/SKILL.md`** and list it in `CLAUDE.md`.
  - Frontmatter `name: release`.
  - `description:` "Use when cutting a release or changing the release pipeline: versions, release workflow, GitHub Pages installer, HACS packaging, firmware OTA URLs."
  - Body:
    - Never edit versions by hand.
    - The release steps from `docs/releasing.md`.
    - What each job produces.
    - OTA URLs must stay stable (`firmware/<v>/ha-controller.ota.bin`), because integrations already installed depend on them.
    - Check `pytest tests/scripts` after any script change.

- [ ] **Step 5: Run every suite**

Run: `pytest && ruff check . && python scripts/versioning.py check && npm --prefix frontend test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/release.yml hacs.json README.md docs .claude CLAUDE.md
git commit -m "ci: release integration, firmware and web installer from tags"
```

- [ ] **Step 7: First release (owner).** Follow `docs/releasing.md` for `0.1.0`. Expected:
  - the GitHub release has 4 assets;
  - `https://pyxel-dev.github.io/HA-controller/` shows "Firmware 0.1.0" and flashes a blank board;
  - HACS installs 0.1.0;
  - the "HA Controller firmware" entity reports `0.1.0` / `0.1.0`.
