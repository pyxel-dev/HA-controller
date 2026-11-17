"""Tests for the HA Controller config flow."""

import json
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_controller.const import DOMAIN

from .helpers import register_screen, setup_screen

COMPONENT = Path(__file__).parents[1]


async def start_flow_and_submit(hass, user_input):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_user_step_shows_device_selector(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_step_creates_entry(hass):
    device = await register_screen(hass)
    result = await start_flow_and_submit(hass, {"device_id": device.id})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HA Controller" and result["data"] == {"device_id": device.id}
    assert result["result"].unique_id == device.id


async def test_user_step_rejects_other_device(hass):
    device = await register_screen(hass, model="other")
    result = await start_flow_and_submit(hass, {"device_id": device.id})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_ha_controller"}


async def test_user_step_aborts_when_already_configured(hass):
    device = await register_screen(hass)
    await setup_screen(hass, device)
    result = await start_flow_and_submit(hass, {"device_id": device.id})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_setup_and_unload_entry(hass):
    device = await register_screen(hass)
    entry = await setup_screen(hass, device)
    assert entry.state is ConfigEntryState.LOADED
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


def test_strings_match_english_translation():
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    assert strings == english
