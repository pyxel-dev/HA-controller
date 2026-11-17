"""Check and bump the single SemVer version shared by the whole repository.

The version lives in four files:
- custom_components/ha_controller/manifest.json ("version")
- esphome/version.yaml (substitutions.project_version)
- custom_components/ha_controller/frontend/package.json ("version")
- custom_components/ha_controller/frontend/package-lock.json (root and packages[""] "version")

Usage:
    python .github/scripts/versioning.py check [--tag vX.Y.Z]
    python .github/scripts/versioning.py bump X.Y.Z
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

MANIFEST = Path("custom_components/ha_controller/manifest.json")
ESPHOME = Path("esphome/version.yaml")
FRONTEND = Path("custom_components/ha_controller/frontend/package.json")
FRONTEND_LOCK = Path("custom_components/ha_controller/frontend/package-lock.json")

SOURCE_PATHS = {
    "manifest": MANIFEST,
    "esphome": ESPHOME,
    "frontend": FRONTEND,
    "frontend-lock": FRONTEND_LOCK,
}

ESPHOME_LINE_RE = re.compile(r'^(\s*project_version:\s*")([^"]*)(")', re.MULTILINE)
MANIFEST_VERSION_RE = re.compile(r'^(\s*"version"\s*:\s*")([^"]*)(")', re.MULTILINE)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_esphome(root: Path) -> str:
    match = ESPHOME_LINE_RE.search((root / ESPHOME).read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("project_version not found")
    return match.group(2)


def _read_lock(root: Path) -> str:
    lock = _read_json(root / FRONTEND_LOCK)
    root_version = lock["version"]
    package_version = lock["packages"][""]["version"]
    if root_version != package_version:
        raise ValueError(
            f'version {root_version} differs from packages[""] version {package_version}'
        )
    return root_version


READERS = {
    "manifest": lambda root: _read_json(root / MANIFEST)["version"],
    "esphome": _read_esphome,
    "frontend": lambda root: _read_json(root / FRONTEND)["version"],
    "frontend-lock": _read_lock,
}


def _collect(root: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []
    for key, reader in READERS.items():
        try:
            values[key] = reader(root)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{key} ({SOURCE_PATHS[key]}): cannot read version ({exc})")
    return values, errors


def read_versions(root: Path) -> dict[str, str]:
    """Return the version found in each source, keyed by source name."""
    values, errors = _collect(root)
    if errors:
        raise ValueError("; ".join(errors))
    return values


def check_versions(root: Path, tag: str | None = None) -> list[str]:
    """Return human-readable errors; an empty list means the repository is consistent."""
    values, errors = _collect(root)

    for key, value in values.items():
        if not VERSION_RE.fullmatch(value):
            errors.append(f"{key} ({SOURCE_PATHS[key]}) version {value!r} is not SemVer X.Y.Z")

    if values:
        # The first source (manifest) wins a tie, so the reference is stable.
        expected, _ = Counter(values.values()).most_common(1)[0]
        for key, value in values.items():
            if value != expected:
                errors.append(f"{key} ({SOURCE_PATHS[key]}) is {value}, expected {expected}")

        if tag is not None and tag != f"v{expected}":
            errors.append(f"tag {tag} does not match version v{expected}")
    elif tag is not None:
        errors.append(f"tag {tag} cannot be checked without a readable version")

    return errors


def _bump_manifest_text(text: str, version: str) -> str:
    """Replace only the top-level version value, leaving every other byte unchanged."""
    old = json.loads(text)
    if not isinstance(old, dict) or "version" not in old:
        raise ValueError(f"{MANIFEST}: top-level version not found")

    match = MANIFEST_VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"{MANIFEST}: top-level version not found")
    new_text = text[: match.start(2)] + version + text[match.end(2) :]

    # Guard against matching a nested "version" key: the only change must be the top-level one.
    if json.loads(new_text) != {**old, "version": version}:
        raise ValueError(f"{MANIFEST}: could not locate the top-level version safely")
    return new_text


def bump_version(root: Path, version: str) -> None:
    """Write version to every source. Nothing is written unless all sources can be updated."""
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"version {version!r} is not SemVer X.Y.Z")

    manifest_text = (root / MANIFEST).read_text(encoding="utf-8", newline="")
    manifest_new = _bump_manifest_text(manifest_text, version)

    frontend = _read_json(root / FRONTEND)
    frontend["version"] = version

    lock = _read_json(root / FRONTEND_LOCK)
    lock["version"] = version
    lock["packages"][""]["version"] = version

    esphome_text = (root / ESPHOME).read_text(encoding="utf-8")
    esphome_new, count = ESPHOME_LINE_RE.subn(
        lambda match: f"{match.group(1)}{version}{match.group(3)}", esphome_text, count=1
    )
    if count != 1:
        raise ValueError(f"{ESPHOME}: project_version not found")

    (root / MANIFEST).write_text(manifest_new, encoding="utf-8", newline="")
    _write_json(root / FRONTEND, frontend)
    _write_json(root / FRONTEND_LOCK, lock)
    (root / ESPHOME).write_text(esphome_new, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="versioning.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="verify that every source has the same version")
    check.add_argument("--tag", help="release tag that must equal v + version")

    bump = commands.add_parser("bump", help="set the version in every source")
    bump.add_argument("version", help="new SemVer version X.Y.Z")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if args.command == "check":
            errors = check_versions(REPO_ROOT, args.tag)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print(f"versions consistent: {next(iter(read_versions(REPO_ROOT).values()))}")
            return 0

        bump_version(REPO_ROOT, args.version)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"version bumped to {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
