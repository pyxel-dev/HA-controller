"""Collect the ESPHome factory and OTA images into versioned release assets."""

import argparse
import hashlib
import shutil
from pathlib import Path


def _only(build_dir: Path, pattern: str) -> Path:
    matches = sorted(build_dir.rglob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {pattern} under {build_dir}, found {len(matches)}")
    return matches[0]


def collect(build_dir: Path, version: str, out_dir: Path) -> list[Path]:
    """Copy the images to out_dir as ha-controller-<version>.* and write the OTA md5."""
    factory = _only(build_dir, "*.factory.bin")
    ota = _only(build_dir, "*.ota.bin")
    out_dir.mkdir(parents=True, exist_ok=True)

    factory_out = out_dir / f"ha-controller-{version}.factory.bin"
    ota_out = out_dir / f"ha-controller-{version}.ota.bin"
    md5_out = out_dir / f"ha-controller-{version}.ota.bin.md5"
    shutil.copyfile(factory, factory_out)
    shutil.copyfile(ota, ota_out)
    md5_out.write_text(hashlib.md5(ota.read_bytes()).hexdigest(), encoding="ascii")
    return [factory_out, ota_out, md5_out]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for path in collect(args.build_dir, args.version, args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
