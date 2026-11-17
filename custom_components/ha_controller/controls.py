"""Map screen control events to Home Assistant service calls (spec §7.6)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, NamedTuple

from homeassistant.core import HomeAssistant

DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35


class ControlCall(NamedTuple):
    """A service call to make for a control event."""

    domain: str
    service: str
    data: dict[str, Any]


def _parse_value(raw: Any) -> float | None:
    try:
        value = float(raw)
    except TypeError, ValueError:
        return None
    return value if math.isfinite(value) else None


def _bound(hass: HomeAssistant, entity_id: str, attribute: str, default: float) -> float:
    state = hass.states.get(entity_id)
    value = _parse_value(state.attributes.get(attribute)) if state else None
    return default if value is None else value


def resolve_control(
    layout: dict[str, Any], hass: HomeAssistant, data: Mapping[str, Any]
) -> ControlCall | None:
    """Return the service call for a control event, or None to ignore it."""
    block = next((b for b in layout["blocks"] if b["id"] == data.get("block")), None)
    if block is None or block["type"] != "entity":
        return None
    entity_id = block["entity_id"]
    domain = entity_id.split(".", 1)[0]
    op = data.get("op")
    if domain == "light":
        if op == "toggle":
            return ControlCall("light", "toggle", {"entity_id": entity_id})
        if op == "set":
            value = _parse_value(data.get("value"))
            if value is None:
                return None
            if value <= 0:
                return ControlCall("light", "turn_off", {"entity_id": entity_id})
            pct = round(min(max(value, 1), 100))
            return ControlCall("light", "turn_on", {"entity_id": entity_id, "brightness_pct": pct})
    elif domain == "climate" and op == "set":
        value = _parse_value(data.get("value"))
        if value is None:
            return None
        low = _bound(hass, entity_id, "min_temp", DEFAULT_MIN_TEMP)
        high = _bound(hass, entity_id, "max_temp", DEFAULT_MAX_TEMP)
        return ControlCall(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, "temperature": min(max(value, low), high)},
        )
    return None
