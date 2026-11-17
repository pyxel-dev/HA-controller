"""Build the GitHub Pages site: web installer, ESP Web Tools manifest and every OTA image."""

import argparse
import json
import shutil
from pathlib import Path

RELEASE_URL = "https://github.com/pyxel-dev/HA-controller/releases/tag/v{version}"


def build_site(web_dir: Path, releases_dir: Path, latest: str, out_dir: Path) -> None:
    """Write the site to out_dir from web_dir and releases_dir/<version>/ asset folders."""
    latest_dir = releases_dir / latest
    latest_factory = latest_dir / f"ha-controller-{latest}.factory.bin"
    latest_ota = latest_dir / f"ha-controller-{latest}.ota.bin"
    for required in (latest_factory, latest_ota):
        if not required.is_file():
            raise FileNotFoundError(f"Missing release asset: {required}")

    firmware = out_dir / "firmware"
    firmware.mkdir(parents=True, exist_ok=True)

    page = (web_dir / "index.html").read_text(encoding="utf-8")
    (out_dir / "index.html").write_text(page.replace("{{VERSION}}", latest), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    for folder in sorted(p for p in releases_dir.iterdir() if p.is_dir()):
        version = folder.name
        ota = folder / f"ha-controller-{version}.ota.bin"
        md5 = folder / f"ha-controller-{version}.ota.bin.md5"
        if not (ota.is_file() and md5.is_file()):
            continue
        target = firmware / version
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ota, target / "ha-controller.ota.bin")
        shutil.copyfile(md5, target / "ha-controller.ota.bin.md5")

    shutil.copyfile(latest_factory, firmware / "ha-controller.factory.bin")
    md5_latest = (latest_dir / f"ha-controller-{latest}.ota.bin.md5").read_text().strip()
    manifest = {
        "name": "HA Controller",
        "version": latest,
        "home_assistant_domain": "esphome",
        "new_install_prompt_erase": True,
        "builds": [
            {
                "chipFamily": "ESP32-S3",
                "parts": [{"path": "ha-controller.factory.bin", "offset": 0}],
                "ota": {
                    "path": f"{latest}/ha-controller.ota.bin",
                    "md5": md5_latest,
                    "release_url": RELEASE_URL.format(version=latest),
                },
            }
        ],
    }
    (firmware / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", type=Path, required=True)
    parser.add_argument("--releases", type=Path, required=True)
    parser.add_argument("--latest", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    build_site(args.web, args.releases, args.latest, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
