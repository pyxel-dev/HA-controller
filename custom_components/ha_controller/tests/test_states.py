"""Tests for the screen state builders."""

import json

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.ha_controller.const import STATE_CHUNK_BYTES
from custom_components.ha_controller.states import (
    build_updates,
    chunk_updates,
    format_entity_text,
)

from .helpers import FIXTURES, load_fixture
from .test_compiler import load_layout

STATE_FIXTURES = sorted((FIXTURES / "states").glob("*.json"))


@pytest.mark.parametrize("path", STATE_FIXTURES, ids=lambda p: p.stem)
async def test_state_fixtures(hass, path):
    case = load_fixture("states", path.name)
    hass.config.units = METRIC_SYSTEM
    registry = er.async_get(hass)
    for entity_id, options in case.get("registry_options", {}).items():
        domain, object_id = entity_id.split(".", 1)
        entry = registry.async_get_or_create(
            domain, "test", object_id, suggested_object_id=object_id
        )
        assert entry.entity_id == entity_id
        for option_domain, value in options.items():
            registry.async_update_entity_options(entity_id, option_domain, value)
    # Set states after registering: the registry avoids ids that already have a state.
    for entity_id, s in case["hass_states"].items():
        hass.states.async_set(entity_id, s["state"], s["attributes"])
    updates = build_updates(hass, load_layout(case["layout"]), case["entity_ids"])
    assert updates == case["updates"]


async def test_entity_text_truncated_to_64(hass):
    hass.states.async_set("sensor.long", "x" * 100)
    assert len(format_entity_text(hass, "sensor.long", None)) == 64


async def test_entity_text_uses_attribute(hass):
    hass.states.async_set("sensor.phone", "ok", {"battery": 80, "unit_of_measurement": "%"})
    assert format_entity_text(hass, "sensor.phone", "battery") == "80"
    assert format_entity_text(hass, "sensor.phone", "missing") == "—"


def test_chunk_updates_splits_by_size():
    updates = [{"id": f"i{n}", "text": "x" * 40} for n in range(300)]
    chunks = chunk_updates(updates, STATE_CHUNK_BYTES)
    assert len(chunks) > 1
    assert all(len(c.encode("utf-8")) <= STATE_CHUNK_BYTES for c in chunks)
    assert [u for c in chunks for u in json.loads(c)] == updates


def test_chunk_updates_keeps_oversize_update_alone():
    big = {"id": "i1", "text": "x" * 200}
    small = {"id": "i2", "text": "y"}
    chunks = chunk_updates([small, big, small], 100)
    assert [json.loads(c) for c in chunks] == [[small], [big], [small]]
