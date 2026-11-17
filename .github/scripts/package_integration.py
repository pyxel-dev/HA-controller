"""Zip the integration for HACS, with the built panel and without development files."""

import argparse
import zipfile
from pathlib import Path

INTEGRATION = Path("custom_components") / "ha_controller"
PANEL = Path("frontend") / "dist" / "ha-controller-panel.js"
BUILD_HINT = (
    "Build the panel first: npm --prefix custom_components/ha_controller/frontend run build"
)


def _included(relative: Path) -> bool:
    parts = relative.parts
    if "__pycache__" in parts or "tests" == parts[0]:
        return False
    if relative.name.startswith(".") or relative.suffix == ".pyc":
        return False
    if parts[0] == "frontend":
        return relative == PANEL
    return True


def package(root: Path, out_file: Path) -> Path:
    """Write the zip with the integration contents at the zip root."""
    source = root / INTEGRATION
    if not (source / PANEL).is_file():
        raise FileNotFoundError(BUILD_HINT)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if path.is_file() and _included(relative):
                zf.write(path, relative.as_posix())
    return out_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    print(package(args.root, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
