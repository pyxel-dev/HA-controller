"""Tests for the control event mapping."""

import logging

import pytest
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.ha_controller.const import EVENT_CONTROL
from custom_components.ha_controller.controls import resolve_control

from .helpers import FIXTURES, load_fixture, register_screen, setup_screen
from .test_compiler import load_layout

CONTROL_FIXTURES = sorted((FIXTURES / "controls").glob("*.json"))


@pytest.mark.parametrize("path", CONTROL_FIXTURES, ids=lambda p: p.stem)
async def test_control_fixtures(hass, path):
    case = load_fixture("controls", path.name)
    for entity_id, s in case["hass_states"].items():
        hass.states.async_set(entity_id, s["state"], s["attributes"])
    call = resolve_control(load_layout(case["layout"]), hass, case["event"])
    assert (call and call._asdict()) == case["expect_call"]


async def test_climate_defaults_without_state(hass):
    event = {"block": "b4", "item": "", "op": "set", "value": "50"}
    call = resolve_control(load_layout("reference"), hass, event)
    assert call.data["temperature"] == 35
    event["value"] = "1"
    assert resolve_control(load_layout("reference"), hass, event).data["temperature"] == 7


async def test_non_finite_value_is_ignored(hass):
    event = {"block": "b2", "item": "", "op": "set", "value": "nan"}
    assert resolve_control(load_layout("reference"), hass, event) is None
    event["value"] = "inf"
    assert resolve_control(load_layout("reference"), hass, event) is None


async def start(hass):
    device = await register_screen(hass)
    entry = await setup_screen(hass, device)
    await entry.runtime_data.async_save_layout(load_layout("reference"))
    return device


def control(device_id, **overrides):
    data = {"device_id": device_id, "block": "b1", "item": "", "op": "toggle", "value": "0"}
    data.update(overrides)
    return data


async def test_control_event_calls_service(hass):
    calls = async_mock_service(hass, "light", "toggle")
    device = await start(hass)
    hass.bus.async_fire(EVENT_CONTROL, control(device.id))
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data == {"entity_id": "light.kitchen"}


async def test_control_from_other_device_is_ignored(hass):
    calls = async_mock_service(hass, "light", "toggle")
    await start(hass)
    hass.bus.async_fire(EVENT_CONTROL, control("other-device"))
    await hass.async_block_till_done()
    assert calls == []


async def test_service_error_is_swallowed(hass, caplog):
    def fail(call):
        raise HomeAssistantError("boom")

    hass.services.async_register("light", "turn_on", fail)
    device = await start(hass)
    with caplog.at_level(logging.WARNING):
        hass.bus.async_fire(EVENT_CONTROL, control(device.id, block="b2", op="set", value="50"))
        await hass.async_block_till_done()
    assert "light.turn_on" in caplog.text
    assert "boom" in caplog.text
