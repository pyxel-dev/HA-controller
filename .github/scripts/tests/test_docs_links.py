"""Documentation checks: relative links resolve and the docs index is complete."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC_ROOTS = ["README.md", ".claude/CLAUDE.md", "docs"]  # docs/superpowers/** is excluded
EXCLUDED = ROOT / "docs" / "superpowers"
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def _markdown_files() -> list[Path]:
    files: list[Path] = []
    for name in DOC_ROOTS:
        path = ROOT / name
        if path.is_dir():
            files.extend(p for p in path.rglob("*.md") if EXCLUDED not in p.parents)
        elif path.exists():
            files.append(path)
    return sorted(files)


def test_relative_links_resolve():
    broken = []
    for md_file in _markdown_files():
        for target in LINK_RE.findall(md_file.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL_PREFIXES):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (md_file.parent / relative).resolve().exists():
                broken.append(f"{md_file.relative_to(ROOT)} -> {target}")
    assert not broken, "Broken relative links:\n" + "\n".join(broken)


def test_docs_index_lists_every_doc():
    index = ROOT / "docs" / "README.md"
    assert index.exists(), "docs/README.md is missing"
    linked = {
        (index.parent / t.split("#", 1)[0]).resolve()
        for t in LINK_RE.findall(index.read_text(encoding="utf-8"))
        if not t.startswith(EXTERNAL_PREFIXES)
    }
    docs = ROOT / "docs"
    candidates = [*docs.glob("*.md"), *docs.glob("*/README.md")]
    missing = [
        str(p.relative_to(docs))
        for p in candidates
        if p != index and EXCLUDED not in p.parents and p.resolve() not in linked
    ]
    assert not missing, f"Docs not linked from docs/README.md: {missing}"
