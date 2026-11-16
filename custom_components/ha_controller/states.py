"""Build the display-ready state updates the screen receives."""

import json
from collections.abc import Collection
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import STATE_CHUNK_BYTES

MISSING_TEXT = "—"
MAX_TEXT_LENGTH = 64
_UNUSABLE = (STATE_UNAVAILABLE, STATE_UNKNOWN)


def _precision(hass: HomeAssistant, entity_id: str) -> int | None:
    entry = er.async_get(hass).async_get(entity_id)
    if entry is None:
        return None
    options = entry.options.get("sensor") or {}
    precision = options.get("display_precision")
    if precision is None:
        precision = options.get("suggested_display_precision")
    return precision


def format_entity_text(hass: HomeAssistant, entity_id: str, attribute: str | None) -> str:
    """Return the display text of an entity item."""
    state = hass.states.get(entity_id)
    if state is None or state.state in _UNUSABLE:
        return MISSING_TEXT
    if attribute:
        if attribute not in state.attributes:
            return MISSING_TEXT
        return str(state.attributes[attribute])[:MAX_TEXT_LENGTH]
    text = state.state
    precision = _precision(hass, entity_id)
    if precision is not None:
        try:
            text = f"{float(text):.{int(precision)}f}"
        except ValueError:
            pass
    unit = state.attributes.get("unit_of_measurement")
    if unit:
        text = f"{text} {unit}"
    return text[:MAX_TEXT_LENGTH]


def _light_update(block_id: str, state: Any) -> dict[str, Any]:
    modes = state.attributes.get("supported_color_modes") or []
    dimmable = any(mode != "onoff" for mode in modes)
    is_on = state.state == "on"
    brightness = None
    if dimmable:
        brightness = round((state.attributes.get("brightness") or 255) * 100 / 255) if is_on else 0
    return {"id": block_id, "available": True, "on": is_on, "brightness": brightness}


def _climate_update(hass: HomeAssistant, block_id: str, state: Any) -> dict[str, Any]:
    attrs = state.attributes
    unit = hass.config.units.temperature_unit
    current = attrs.get("current_temperature")
    action = attrs.get("hvac_action") or state.state
    action = str(action).replace("_", " ")
    return {
        "id": block_id,
        "available": True,
        "target": attrs.get("temperature"),
        "min": attrs.get("min_temp", 7),
        "max": attrs.get("max_temp", 35),
        "step": attrs.get("target_temp_step") or (0.5 if unit == "°C" else 1),
        "unit": unit,
        "current": MISSING_TEXT if current is None else f"{current} {unit}",
        "action": action[:1].upper() + action[1:],
    }


def build_updates(
    hass: HomeAssistant, layout: dict[str, Any], entity_ids: Collection[str] | None = None
) -> list[dict[str, Any]]:
    """Build the updates for the bound entities, in layout order."""
    wanted = None if entity_ids is None else set(entity_ids)
    updates: list[dict[str, Any]] = []
    for block in layout["blocks"]:
        if block["type"] == "entity":
            entity_id = block["entity_id"]
            if wanted is not None and entity_id not in wanted:
                continue
            state = hass.states.get(entity_id)
            if state is None or state.state in _UNUSABLE:
                updates.append({"id": block["id"], "available": False})
            elif entity_id.startswith("light."):
                updates.append(_light_update(block["id"], state))
            elif entity_id.startswith("climate."):
                updates.append(_climate_update(hass, block["id"], state))
            else:
                updates.append({"id": block["id"], "available": True})
        elif block["type"] == "custom":
            for item in block["items"]:
                if item["kind"] != "entity":
                    continue
                if wanted is not None and item["entity_id"] not in wanted:
                    continue
                text = format_entity_text(hass, item["entity_id"], item.get("attribute"))
                updates.append({"id": item["id"], "text": text})
    return updates


def chunk_updates(updates: list[dict[str, Any]], max_bytes: int = STATE_CHUNK_BYTES) -> list[str]:
    """Split updates into JSON arrays of at most max_bytes bytes each."""

    def encode(items: list[dict[str, Any]]) -> str:
        return json.dumps(items, separators=(",", ":"), ensure_ascii=False)

    chunks: list[str] = []
    current: list[dict[str, Any]] = []
    for update in updates:
        candidate = [*current, update]
        if current and len(encode(candidate).encode("utf-8")) > max_bytes:
            chunks.append(encode(current))
            current = [update]
        else:
            current = candidate
    if current:
        chunks.append(encode(current))
    return chunks
