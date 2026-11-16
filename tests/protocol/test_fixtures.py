"""Executable protocol contract: shape and golden values of protocol/fixtures."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "protocol" / "fixtures"
EMOJI = ROOT / "custom_components" / "ha_controller" / "emoji.json"

LAYOUT_CODES = {
    "invalid_structure",
    "too_many_blocks",
    "invalid_sleep_timeout",
    "invalid_id",
    "duplicate_id",
    "coordinate_out_of_range",
    "duplicate_position",
    "invalid_start",
    "disconnected",
    "invalid_name",
    "invalid_background",
    "invalid_font_size",
    "invalid_type",
    "invalid_entity",
    "too_many_items",
    "invalid_item",
    "invalid_text",
    "unsupported_emoji",
}  # the 18 codes of spec section 6 except payload_too_large

VALID_LAYOUTS = sorted((FIXTURES / "layouts" / "valid").glob("*.json"))
INVALID_LAYOUTS = sorted((FIXTURES / "layouts" / "invalid").glob("*.json"))
VALID_PAYLOADS = sorted((FIXTURES / "payloads" / "valid").glob("*.json"))
COLORS_FILE = FIXTURES / "colors.json"


def _load(path: Path):
    return json.loads(path.read_text("utf-8"))


def canonical_rev(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "rev"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def luminance(color: str) -> float:
    channels = []
    for i in (1, 3, 5):
        c = int(color[i : i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_emoji_list_is_well_formed():
    emoji = _load(EMOJI)
    assert len(emoji) == 64 and len(set(emoji)) == 64
    assert all(len(e) == 1 for e in emoji)  # one code point each
    assert "️" not in "".join(emoji)
    assert {"💡", "🔋", "⚡", "☀", "👋"} <= set(emoji) and "🦄" not in emoji


def test_all_fixtures_are_utf8_json():
    files = sorted(FIXTURES.rglob("*.json"))
    assert files
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM in {path}"
        json.loads(raw.decode("utf-8"))


def test_invalid_layout_fixtures_declare_known_codes():
    assert INVALID_LAYOUTS
    for path in INVALID_LAYOUTS:
        data = _load(path)
        code, ref = data["expect"]["code"], data["expect"]["ref"]
        assert code in LAYOUT_CODES, path.name
        assert ref is None or isinstance(ref, str), path.name
        assert path.stem == code or path.stem.startswith(code + "-"), path.name
        assert isinstance(data["layout"], dict)


def test_every_layout_code_has_an_invalid_fixture():
    covered = {_load(p)["expect"]["code"] for p in INVALID_LAYOUTS}
    assert covered == LAYOUT_CODES


def test_payload_revisions_match_canonical_hash():
    revs = {p.stem: _load(p)["payload"]["rev"] for p in VALID_PAYLOADS}
    assert revs == {
        "empty": "c4aad3fa",
        "reference": "90538742",
        "emoji-variation": "5387d4ea",
    }
    for path in VALID_PAYLOADS:
        payload = _load(path)["payload"]
        assert canonical_rev(payload) == payload["rev"], path.name


def test_fixtures_reference_existing_layouts():
    names = {p.stem for p in VALID_LAYOUTS}
    checked = 0
    for folder in ("payloads/valid", "states", "controls"):
        for path in sorted((FIXTURES / folder).glob("*.json")):
            assert _load(path)["layout"] in names, path
            checked += 1
    assert checked


def test_color_fixture_matches_luminance_rule():
    colors = _load(COLORS_FILE)
    assert colors
    for case in colors:
        expected = "#000000" if luminance(case["bg"]) > 0.30 else "#FFFFFF"
        assert case["text"] == expected, case
