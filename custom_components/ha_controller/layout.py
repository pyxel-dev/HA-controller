"""Layout model helpers and validation (protocol v1, spec section 6)."""

from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any, NamedTuple

from homeassistant.core import HomeAssistant

from .const import (
    COORD_LIMIT,
    DEFAULT_SLEEP_TIMEOUT,
    ENTITY_BLOCK_DOMAINS,
    FONT_SIZES,
    ITEM_KINDS,
    MAX_BLOCKS,
    MAX_ITEMS,
    MAX_NAME_LEN,
    MAX_SLEEP_TIMEOUT,
    MAX_TEXT_LEN,
    MIN_SLEEP_TIMEOUT,
)

EMOJI_FILE = Path(__file__).parent / "emoji.json"

_ID_RE = re.compile(r"[a-z][a-z0-9]{0,7}")
_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")
_ENTITY_RE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+")
_MAX_ATTRIBUTE_LEN = 64


class LayoutError(NamedTuple):
    """A validation error; ref is the offending block or item id, or None."""

    code: str
    ref: str | None


def empty_layout() -> dict[str, Any]:
    """Return the layout of a screen that has no blocks yet."""
    return {
        "version": 1,
        "start": None,
        "settings": {"sleep_timeout": DEFAULT_SLEEP_TIMEOUT},
        "blocks": [],
    }


def normalize_emoji(text: str) -> str:
    """Remove the emoji variation selector U+FE0F."""
    return text.replace("️", "")


def load_emoji_file(path: Path) -> frozenset[str]:
    """Read the supported emoji list (blocking)."""
    return frozenset(json.loads(path.read_text(encoding="utf-8")))


async def async_load_emoji(hass: HomeAssistant) -> frozenset[str]:
    """Read the supported emoji list without blocking the event loop."""
    return await hass.async_add_executor_job(load_emoji_file, EMOJI_FILE)


def bound_entities(layout: dict[str, Any]) -> dict[str, list[str]]:
    """Map entity_id to the ids of the blocks and items bound to it."""
    bound: dict[str, list[str]] = {}
    for block in layout["blocks"]:
        if block["type"] == "entity":
            bound.setdefault(block["entity_id"], []).append(block["id"])
        elif block["type"] == "custom":
            for item in block["items"]:
                if item["kind"] == "entity":
                    bound.setdefault(item["entity_id"], []).append(item["id"])
    return bound


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_id(value: Any) -> bool:
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def _check_structure(layout: Any) -> bool:
    if not isinstance(layout, dict):
        return False
    version = layout.get("version")
    if not _is_int(version) or version != 1:
        return False
    if not isinstance(layout.get("settings"), dict):
        return False
    blocks = layout.get("blocks")
    if not isinstance(blocks, list) or not all(isinstance(b, dict) for b in blocks):
        return False
    for block in blocks:
        if block.get("type") == "custom":
            items = block.get("items")
            if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
                return False
    return True


def _is_entity_id(value: Any) -> bool:
    return isinstance(value, str) and _ENTITY_RE.fullmatch(value) is not None


def _valid_entity_item(item: dict[str, Any]) -> bool:
    entity_id = item.get("entity_id")
    if not _is_entity_id(entity_id):
        return False
    attribute = item.get("attribute")
    return attribute is None or (
        isinstance(attribute, str) and 1 <= len(attribute) <= _MAX_ATTRIBUTE_LEN
    )


def _valid_entity_block(block: dict[str, Any]) -> bool:
    entity_id = block.get("entity_id")
    if not _is_entity_id(entity_id):
        return False
    return entity_id.split(".", 1)[0] in ENTITY_BLOCK_DOMAINS


def _check_item(
    item: dict[str, Any],
    seen_ids: set[str],
    emoji: frozenset[str],
    errors: list[LayoutError],
) -> None:
    item_id = item.get("id")
    ref = item_id if isinstance(item_id, str) else None
    if not _is_id(item_id):
        errors.append(LayoutError("invalid_id", ref))
    if isinstance(item_id, str):
        if item_id in seen_ids:
            errors.append(LayoutError("duplicate_id", item_id))
        seen_ids.add(item_id)
    kind = item.get("kind")
    if kind not in ITEM_KINDS:
        errors.append(LayoutError("invalid_item", ref))
    font_size = item.get("font_size")
    if font_size is not None and font_size not in FONT_SIZES:
        errors.append(LayoutError("invalid_font_size", ref))
    if kind == "text":
        text = item.get("text")
        if not isinstance(text, str) or not 1 <= len(text) <= MAX_TEXT_LEN:
            errors.append(LayoutError("invalid_text", ref))
    elif kind == "emoji":
        value = item.get("emoji")
        if not isinstance(value, str) or normalize_emoji(value) not in emoji:
            errors.append(LayoutError("unsupported_emoji", ref))
    elif kind == "entity" and not _valid_entity_item(item):
        errors.append(LayoutError("invalid_entity", ref))


def _check_block(
    block: dict[str, Any],
    seen_ids: set[str],
    positions: set[tuple[int, int]],
    emoji: frozenset[str],
    errors: list[LayoutError],
) -> None:
    block_id = block.get("id")
    ref = block_id if isinstance(block_id, str) else None
    if not _is_id(block_id):
        errors.append(LayoutError("invalid_id", ref))
    if isinstance(block_id, str):
        if block_id in seen_ids:
            errors.append(LayoutError("duplicate_id", block_id))
        seen_ids.add(block_id)

    x, y = block.get("x"), block.get("y")
    if not all(_is_int(v) and -COORD_LIMIT <= v <= COORD_LIMIT for v in (x, y)):
        errors.append(LayoutError("coordinate_out_of_range", ref))
    else:
        if (x, y) in positions:
            errors.append(LayoutError("duplicate_position", ref))
        positions.add((x, y))

    name = block.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= MAX_NAME_LEN:
        errors.append(LayoutError("invalid_name", ref))
    background = block.get("background")
    if not isinstance(background, str) or _COLOR_RE.fullmatch(background) is None:
        errors.append(LayoutError("invalid_background", ref))
    if block.get("font_size") not in FONT_SIZES:
        errors.append(LayoutError("invalid_font_size", ref))

    block_type = block.get("type")
    if block_type == "entity":
        if not _valid_entity_block(block):
            errors.append(LayoutError("invalid_entity", ref))
    elif block_type == "custom":
        items = block["items"]
        if len(items) > MAX_ITEMS:
            errors.append(LayoutError("too_many_items", ref))
        for item in items:
            _check_item(item, seen_ids, emoji, errors)
    else:
        errors.append(LayoutError("invalid_type", ref))


def _unreachable(layout: dict[str, Any]) -> list[LayoutError]:
    if not layout["blocks"]:
        return []
    cells = {(b["x"], b["y"]): b["id"] for b in layout["blocks"]}
    start = next(b for b in layout["blocks"] if b["id"] == layout["start"])
    reached = {(start["x"], start["y"])}
    queue = deque(reached)
    while queue:
        x, y = queue.popleft()
        for cell in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if cell in cells and cell not in reached:
                reached.add(cell)
                queue.append(cell)
    return [
        LayoutError("disconnected", b["id"])
        for b in layout["blocks"]
        if (b["x"], b["y"]) not in reached
    ]


def validate_layout(layout: Any, emoji: frozenset[str]) -> list[LayoutError]:
    """Validate a layout; an empty list means it is valid."""
    if not _check_structure(layout):
        return [LayoutError("invalid_structure", None)]

    errors: list[LayoutError] = []
    blocks = layout["blocks"]
    if len(blocks) > MAX_BLOCKS:
        errors.append(LayoutError("too_many_blocks", None))
    timeout = layout["settings"].get("sleep_timeout")
    if not _is_int(timeout) or not (
        timeout == 0 or MIN_SLEEP_TIMEOUT <= timeout <= MAX_SLEEP_TIMEOUT
    ):
        errors.append(LayoutError("invalid_sleep_timeout", None))

    seen_ids: set[str] = set()
    positions: set[tuple[int, int]] = set()
    for block in blocks:
        _check_block(block, seen_ids, positions, emoji, errors)

    start = layout.get("start")
    if start is None:
        start_ok = not blocks
    else:
        start_ok = isinstance(start, str) and any(b.get("id") == start for b in blocks)
    if not start_ok:
        errors.append(LayoutError("invalid_start", None))

    if errors:
        return errors
    return _unreachable(layout)
