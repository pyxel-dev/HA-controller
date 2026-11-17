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
        MANIFEST: _json(
            {"domain": "ha_controller", "name": "HA Controller", "version": "0.1.0"}
        ),
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
    assert "0.2.0" in errors[0]
    assert "0.1.0" in errors[0]


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
    assert manifest == {"domain": "ha_controller", "name": "HA Controller", "version": "1.2.3"}

    frontend = json.loads((repo / FRONTEND).read_text(encoding="utf-8"))
    assert frontend == {"name": "ha-controller-panel", "version": "1.2.3", "private": True}

    lock = json.loads((repo / FRONTEND_LOCK).read_text(encoding="utf-8"))
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["name"] == "ha-controller-panel"

    yaml_after = (repo / ESPHOME).read_text(encoding="utf-8")
    assert yaml_after == before_yaml.replace('project_version: "0.1.0"', 'project_version: "1.2.3"')
    assert '  device_name: "ha-controller"' in yaml_after

    for relative in (MANIFEST, FRONTEND, FRONTEND_LOCK):
        assert (repo / relative).read_text(encoding="utf-8").endswith("}\n")


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
