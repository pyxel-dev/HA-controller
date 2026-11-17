"""Tests for the layout compiler against the shared protocol fixtures."""

from typing import Any

import pytest

from custom_components.ha_controller.compiler import (
    compile_layout,
    encode_payload,
    payload_revision,
)
from custom_components.ha_controller.const import MAX_PAYLOAD_BYTES

from .helpers import FIXTURES, load_fixture

VALID_PAYLOADS = sorted((FIXTURES / "payloads" / "valid").glob("*.json"))


def load_layout(stem: str) -> dict[str, Any]:
    return load_fixture("layouts", "valid", f"{stem}.json")


@pytest.mark.parametrize("path", VALID_PAYLOADS, ids=lambda p: p.stem)
def test_golden_payloads(path):
    case = load_fixture("payloads", "valid", path.name)
    assert compile_layout(load_layout(case["layout"])) == case["payload"]


def test_revision_ignores_rev_key():
    payload = {"v": 1, "rev": "zzz", "start": None, "sleep": 20, "blocks": []}
    assert payload_revision(payload) == "c4aad3fa"


def test_names_are_trimmed():
    layout = load_layout("single")
    layout["blocks"][0]["name"] = f"  {layout['blocks'][0]['name']}\t"
    assert (
        compile_layout(layout)["blocks"][0]["name"]
        == compile_layout(load_layout("single"))["blocks"][0]["name"].strip()
    )


def test_encode_payload_is_compact_utf8():
    text = encode_payload(compile_layout(load_layout("reference")))
    assert ", " not in text and ": " not in text and "👋" in text


def test_huge_layout_exceeds_payload_limit():
    huge = {
        "version": 1,
        "start": "b0",
        "settings": {"sleep_timeout": 20},
        "blocks": [
            {
                "id": f"b{n}",
                "x": n,
                "y": 0,
                "name": "é" * 32,
                "background": "#112233",
                "font_size": "m",
                "type": "custom",
                "items": [
                    {"id": f"i{n}_{k}", "kind": "text", "text": "é" * 64, "font_size": None}
                    for k in range(6)
                ],
            }
            for n in range(32)
        ],
    }
    assert len(encode_payload(compile_layout(huge)).encode()) > MAX_PAYLOAD_BYTES
