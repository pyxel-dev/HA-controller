"""Tests for layout validation against the shared protocol fixtures."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.ha_controller.const import DEFAULT_SLEEP_TIMEOUT
from custom_components.ha_controller.layout import (
    LayoutError,
    async_load_emoji,
    bound_entities,
    empty_layout,
    load_emoji_file,
    normalize_emoji,
    validate_layout,
)

from .helpers import FIXTURES, load_fixture

EMOJI_FILE = Path(__file__).parents[1] / "emoji.json"
EMOJI = load_emoji_file(EMOJI_FILE)
VALID_LAYOUTS = sorted((FIXTURES / "layouts" / "valid").glob("*.json"))
INVALID_LAYOUTS = sorted((FIXTURES / "layouts" / "invalid").glob("*.json"))


def reference() -> dict[str, Any]:
    return copy.deepcopy(load_fixture("layouts", "valid", "reference.json"))


def test_fixture_sets_are_complete() -> None:
    assert len(VALID_LAYOUTS) == 4
    assert len(INVALID_LAYOUTS) == 23


@pytest.mark.parametrize("path", VALID_LAYOUTS, ids=lambda p: p.stem)
def test_valid_fixtures(path: Path) -> None:
    assert validate_layout(json.loads(path.read_text(encoding="utf-8")), EMOJI) == []


@pytest.mark.parametrize("path", INVALID_LAYOUTS, ids=lambda p: p.stem)
def test_invalid_fixtures(path: Path) -> None:
    case = json.loads(path.read_text(encoding="utf-8"))
    expect = case["expect"]
    assert validate_layout(case["layout"], EMOJI) == [
        LayoutError(expect["code"], expect["ref"])
    ]


def test_connectivity_is_skipped_when_fields_are_invalid() -> None:
    layout = reference()
    layout["blocks"][0]["name"] = ""
    layout["blocks"][1]["y"] = -5  # would be disconnected
    assert validate_layout(layout, EMOJI) == [LayoutError("invalid_name", "b1")]


def test_normalize_emoji_strips_variation_selector() -> None:
    assert normalize_emoji("❄️") == "❄"


def test_bound_entities_reference() -> None:
    assert bound_entities(reference()) == {
        "light.kitchen": ["b1"],
        "light.living_room": ["b2"],
        "sensor.outdoor_temperature": ["i3"],
        "climate.bedroom": ["b4"],
    }


def test_bool_is_not_a_coordinate() -> None:
    layout = reference()
    layout["blocks"][0]["x"] = True
    assert LayoutError("coordinate_out_of_range", "b1") in validate_layout(layout, EMOJI)


@pytest.mark.parametrize(
    ("value", "ok"),
    [(0, True), (5, True), (3600, True), (4, False), (3601, False), (True, False), ("20", False)],
)
def test_sleep_timeout_bounds(value: Any, ok: bool) -> None:
    layout = reference()
    layout["settings"]["sleep_timeout"] = value
    expected = [] if ok else [LayoutError("invalid_sleep_timeout", None)]
    assert validate_layout(layout, EMOJI) == expected


def test_non_dict_layout_is_invalid_structure() -> None:
    assert validate_layout([], EMOJI) == [LayoutError("invalid_structure", None)]


def test_empty_layout_is_valid() -> None:
    layout = empty_layout()
    assert layout == {
        "version": 1,
        "start": None,
        "settings": {"sleep_timeout": DEFAULT_SLEEP_TIMEOUT},
        "blocks": [],
    }
    assert validate_layout(layout, EMOJI) == []


def test_load_emoji_file() -> None:
    assert "💡" in EMOJI
    assert len(EMOJI) == 64


async def test_async_load_emoji(hass) -> None:
    assert await async_load_emoji(hass) == EMOJI
