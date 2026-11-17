"""Release tooling: firmware collection, integration zip and GitHub Pages site."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from build_pages import build_site
from collect_firmware import collect
from package_integration import package

REPO_ROOT = Path(__file__).resolve().parents[3]
INTEGRATION = "custom_components/ha_controller"
PANEL = f"{INTEGRATION}/frontend/dist/ha-controller-panel.js"


def _write(path: Path, content: bytes | str = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return path


def test_collect_writes_versioned_files_and_md5(tmp_path):
    build = tmp_path / "build" / "ha-controller" / "build"
    _write(build / "firmware.factory.bin", b"factory")
    _write(build / "firmware.ota.bin", b"ota-image")
    _write(build / "ha-controller.bin", b"other")
    _write(build / "bootloader" / "bootloader.bin", b"boot")
    out = tmp_path / "out"

    written = collect(tmp_path / "build", "0.2.0", out)

    assert sorted(p.name for p in written) == [
        "ha-controller-0.2.0.factory.bin",
        "ha-controller-0.2.0.ota.bin",
        "ha-controller-0.2.0.ota.bin.md5",
    ]
    assert (out / "ha-controller-0.2.0.factory.bin").read_bytes() == b"factory"
    md5 = (out / "ha-controller-0.2.0.ota.bin.md5").read_bytes()
    assert md5 == hashlib.md5(b"ota-image").hexdigest().encode()
    assert len(md5) == 32


def test_collect_requires_exactly_one_of_each(tmp_path):
    build = tmp_path / "build"
    build.mkdir()
    with pytest.raises(ValueError):
        collect(build, "0.2.0", tmp_path / "out")

    _write(build / "a" / "firmware.factory.bin")
    _write(build / "b" / "firmware.factory.bin")
    _write(build / "a" / "firmware.ota.bin")
    with pytest.raises(ValueError):
        collect(build, "0.2.0", tmp_path / "out")


def _fake_repo(root: Path, with_panel: bool = True) -> None:
    _write(root / INTEGRATION / "manifest.json", "{}")
    _write(root / INTEGRATION / "__init__.py", "")
    _write(root / INTEGRATION / "emoji.json", "[]")
    _write(root / INTEGRATION / "brand" / "icon.png")
    _write(root / INTEGRATION / "__pycache__" / "x.cpython-314.pyc")
    _write(root / INTEGRATION / "tests" / "test_x.py", "")
    _write(root / INTEGRATION / "frontend" / "src" / "a.ts", "")
    _write(root / INTEGRATION / "frontend" / "package.json", "{}")
    _write(root / INTEGRATION / "frontend" / "node_modules" / "m" / "i.js", "")
    _write(root / INTEGRATION / "frontend" / "dist" / "other.js", "")
    _write(root / INTEGRATION / "frontend" / "dist" / ".gitkeep", "")
    if with_panel:
        _write(root / PANEL, "panel")


def test_package_zips_integration_with_panel(tmp_path):
    _fake_repo(tmp_path)
    out = package(tmp_path, tmp_path / "dist" / "ha_controller.zip")

    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert names == {
        "manifest.json",
        "__init__.py",
        "emoji.json",
        "brand/icon.png",
        "frontend/dist/ha-controller-panel.js",
    }


def test_package_requires_built_panel(tmp_path):
    _fake_repo(tmp_path, with_panel=False)
    with pytest.raises(FileNotFoundError, match="Build the panel first"):
        package(tmp_path, tmp_path / "ha_controller.zip")


def _release(releases: Path, version: str) -> None:
    _write(releases / version / f"ha-controller-{version}.factory.bin", f"f{version}".encode())
    ota = f"o{version}".encode()
    _write(releases / version / f"ha-controller-{version}.ota.bin", ota)
    _write(
        releases / version / f"ha-controller-{version}.ota.bin.md5",
        hashlib.md5(ota).hexdigest(),
    )


def _web(tmp_path: Path) -> Path:
    return _write(
        tmp_path / "web" / "index.html", "<p>Firmware {{VERSION}}</p><a href='v{{VERSION}}'>"
    ).parent


def test_build_site_manifest(tmp_path):
    releases = tmp_path / "releases"
    _release(releases, "0.2.0")
    out = tmp_path / "site"

    build_site(_web(tmp_path), releases, "0.2.0", out)

    manifest = json.loads((out / "firmware" / "manifest.json").read_text())
    assert manifest == {
        "name": "HA Controller",
        "version": "0.2.0",
        "home_assistant_domain": "esphome",
        "new_install_prompt_erase": True,
        "builds": [
            {
                "chipFamily": "ESP32-S3",
                "parts": [{"path": "ha-controller.factory.bin", "offset": 0}],
                "ota": {
                    "path": "0.2.0/ha-controller.ota.bin",
                    "md5": hashlib.md5(b"o0.2.0").hexdigest(),
                    "release_url": "https://github.com/pyxel-dev/HA-controller/releases/tag/v0.2.0",
                },
            }
        ],
    }
    assert (out / "firmware" / "ha-controller.factory.bin").read_bytes() == b"f0.2.0"


def test_build_site_keeps_every_release(tmp_path):
    releases = tmp_path / "releases"
    _release(releases, "0.1.0")
    _release(releases, "0.2.0")
    out = tmp_path / "site"

    build_site(_web(tmp_path), releases, "0.2.0", out)

    for version in ("0.1.0", "0.2.0"):
        folder = out / "firmware" / version
        assert (folder / "ha-controller.ota.bin").read_bytes() == f"o{version}".encode()
        assert (folder / "ha-controller.ota.bin.md5").read_text() == hashlib.md5(
            f"o{version}".encode()
        ).hexdigest()
    assert (out / "firmware" / "ha-controller.factory.bin").read_bytes() == b"f0.2.0"


def test_build_site_renders_version(tmp_path):
    releases = tmp_path / "releases"
    _release(releases, "0.2.0")
    out = tmp_path / "site"

    build_site(_web(tmp_path), releases, "0.2.0", out)

    html = (out / "index.html").read_text()
    assert "Firmware 0.2.0" in html
    assert "{{VERSION}}" not in html
    assert (out / ".nojekyll").exists()


def test_build_site_requires_latest_assets(tmp_path):
    releases = tmp_path / "releases"
    _release(releases, "0.1.0")
    with pytest.raises(FileNotFoundError):
        build_site(_web(tmp_path), releases, "0.2.0", tmp_path / "site")


def test_web_page_template():
    html = (REPO_ROOT / "esphome" / "web" / "index.html").read_text(encoding="utf-8")
    assert html.count("{{VERSION}}") >= 2
    assert "esp-web-tools@10.5.2" in html
