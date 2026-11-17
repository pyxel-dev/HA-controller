"""Single-version check and bump across manifest, ESPHome, panel and panel lock."""

import json
from pathlib import Path

import pytest

import versioning
from versioning import bump_version, check_versions, main, read_versions

REPO_ROOT = Path(__file__).resolve().parents[3]

MANIFEST = "custom_components/ha_controller/manifest.json"
ESPHOME = "esphome/version.yaml"
FRONTEND = "custom_components/ha_controller/frontend/package.json"
FRONTEND_LOCK = "custom_components/ha_controller/frontend/package-lock.json"


def _json(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def _manifest(version: str) -> str:
    # Same shape as the real manifest: inline arrays that json.dumps would reflow.
    return (
        "{\n"
        '  "domain": "ha_controller",\n'
        '  "name": "HA Controller",\n'
        '  "after_dependencies": ["esphome"],\n'
        '  "codeowners": ["@pyxel-dev"],\n'
        '  "config_flow": true,\n'
        '  "dependencies": ["frontend", "http", "panel_custom", "websocket_api"],\n'
        '  "requirements": [],\n'
        f'  "version": "{version}"\n'
        "}\n"
    )


def _yaml(version: str) -> str:
    return (
        "substitutions:\n"
        '  device_name: "ha-controller"\n'
        f'  project_version: "{version}"\n'
        "esphome:\n"
        "  name: ha-controller\n"
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    files = {
        MANIFEST: _manifest("0.1.0"),
        ESPHOME: _yaml("0.1.0"),
        FRONTEND: _json({"name": "ha-controller-panel", "version": "0.1.0", "private": True}),
        FRONTEND_LOCK: _json(
            {
                "name": "ha-controller-panel",
                "version": "0.1.0",
                "lockfileVersion": 3,
                "packages": {"": {"name": "ha-controller-panel", "version": "0.1.0"}},
            }
        ),
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_read_versions(repo):
    assert set(read_versions(repo).values()) == {"0.1.0"}


def test_check_passes_when_equal(repo):
    assert check_versions(repo) == []


def test_check_reports_mismatch(repo):
    path = repo / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = "0.2.0"
    path.write_text(_json(data), encoding="utf-8")

    errors = check_versions(repo)

    assert len(errors) == 1
    assert "manifest" in errors[0]
    assert MANIFEST in errors[0]
    assert "0.2.0" in errors[0]
    assert "0.1.0" in errors[0]


def test_check_errors_name_file_path_for_unreadable_source(repo):
    (repo / ESPHOME).unlink()

    errors = check_versions(repo)

    assert any("esphome" in error and ESPHOME in error for error in errors)


def test_check_tag_must_match(repo):
    assert check_versions(repo, "v0.1.0") == []
    assert check_versions(repo, "v0.1.1")
    assert check_versions(repo, "0.1.0")


def test_check_rejects_non_semver(repo):
    (repo / ESPHOME).write_text(_yaml("0.1"), encoding="utf-8")
    for relative in (MANIFEST, FRONTEND, FRONTEND_LOCK):
        path = repo / relative
        text = path.read_text(encoding="utf-8").replace('"0.1.0"', '"0.1"')
        path.write_text(text, encoding="utf-8")

    assert check_versions(repo)


def test_bump_rewrites_all(repo):
    before_yaml = (repo / ESPHOME).read_text(encoding="utf-8")

    bump_version(repo, "1.2.3")

    assert set(read_versions(repo).values()) == {"1.2.3"}
    assert check_versions(repo) == []

    manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.3"
    assert manifest["dependencies"] == ["frontend", "http", "panel_custom", "websocket_api"]

    frontend = json.loads((repo / FRONTEND).read_text(encoding="utf-8"))
    assert frontend == {"name": "ha-controller-panel", "version": "1.2.3", "private": True}

    lock = json.loads((repo / FRONTEND_LOCK).read_text(encoding="utf-8"))
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["name"] == "ha-controller-panel"

    yaml_after = (repo / ESPHOME).read_text(encoding="utf-8")
    assert yaml_after == before_yaml.replace('project_version: "0.1.0"', 'project_version: "1.2.3"')
    assert '  device_name: "ha-controller"' in yaml_after

    for relative in (FRONTEND, FRONTEND_LOCK):
        assert (repo / relative).read_text(encoding="utf-8").endswith("}\n")


def test_bump_changes_only_manifest_version_text(repo):
    before = (repo / MANIFEST).read_text(encoding="utf-8")

    bump_version(repo, "1.2.3")

    after = (repo / MANIFEST).read_text(encoding="utf-8")
    assert after == before.replace('"version": "0.1.0"', '"version": "1.2.3"')


@pytest.mark.parametrize("bad", ["1.2", "v1.2.3", "1.2.3-rc1"])
def test_bump_rejects_invalid(repo, bad):
    with pytest.raises(ValueError):
        bump_version(repo, bad)
    assert set(read_versions(repo).values()) == {"0.1.0"}


def test_repository_versions_are_consistent():
    assert check_versions(REPO_ROOT) == []


def test_main_exit_codes(repo, monkeypatch):
    monkeypatch.setattr(versioning, "REPO_ROOT", repo)

    assert main(["check"]) == 0
    assert main(["check", "--tag", "v0.1.0"]) == 0
    assert main(["check", "--tag", "v0.1.1"]) == 1
    assert main(["bump", "0.3.0"]) == 0
    assert set(read_versions(repo).values()) == {"0.3.0"}
    assert main(["check"]) == 0
    assert main(["bump", "0.3"]) == 1


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        (MANIFEST, "{ not json"),
        (MANIFEST, "[]"),
        (MANIFEST, '{"domain": "ha_controller"}'),
        (FRONTEND_LOCK, "[]"),
        (FRONTEND_LOCK, '{"version": "0.1.0"}'),
        (ESPHOME, "substitutions: {}\n"),
    ],
)
@pytest.mark.parametrize("argv", [["check"], ["bump", "1.2.3"]])
def test_main_reports_malformed_files_without_traceback(
    repo, monkeypatch, capsys, relative, content, argv
):
    monkeypatch.setattr(versioning, "REPO_ROOT", repo)
    (repo / relative).write_text(content, encoding="utf-8")

    assert main(argv) == 1

    assert capsys.readouterr().err.strip()


def test_main_reports_missing_file_without_traceback(repo, monkeypatch, capsys):
    monkeypatch.setattr(versioning, "REPO_ROOT", repo)
    (repo / FRONTEND).unlink()

    assert main(["check"]) == 1
    assert main(["bump", "1.2.3"]) == 1
    assert FRONTEND in capsys.readouterr().err
