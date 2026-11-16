"""Compile a stored layout into the compact payload sent to the screen."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .const import PROTOCOL_VERSION
from .layout import normalize_emoji


def _compile_item(item: dict[str, Any], block_font: str) -> dict[str, Any]:
    kind = item["kind"]
    out: dict[str, Any] = {
        "id": item["id"],
        "kind": kind,
        "font": item["font_size"] or block_font,
    }
    if kind == "text":
        out["text"] = item["text"]
    elif kind == "emoji":
        out["text"] = normalize_emoji(item["emoji"])
    return out


def _compile_block(block: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": block["id"],
        "x": block["x"],
        "y": block["y"],
        "name": block["name"].strip(),
        "bg": block["background"].lstrip("#").upper(),
        "font": block["font_size"],
    }
    if block["type"] == "entity":
        out["widget"] = block["entity_id"].split(".", 1)[0]
    else:
        out["widget"] = "custom"
        out["items"] = [_compile_item(i, block["font_size"]) for i in block["items"]]
    return out


def payload_revision(payload: dict[str, Any]) -> str:
    """Return the 8-hex-char revision of a payload, ignoring any `rev` key."""
    body = {k: v for k, v in payload.items() if k != "rev"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def compile_layout(layout: dict[str, Any]) -> dict[str, Any]:
    """Compile a valid stored layout into a payload including its `rev`."""
    payload: dict[str, Any] = {
        "v": PROTOCOL_VERSION,
        "start": layout["start"],
        "sleep": layout["settings"]["sleep_timeout"],
        "blocks": [_compile_block(b) for b in layout["blocks"]],
    }
    return {
        "v": PROTOCOL_VERSION,
        "rev": payload_revision(payload),
        **{k: v for k, v in payload.items() if k != "v"},
    }


def encode_payload(payload: dict[str, Any]) -> str:
    """Return the compact JSON transport encoding of a payload."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
