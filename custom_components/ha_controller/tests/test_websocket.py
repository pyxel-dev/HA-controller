"""Tests for the websocket API used by the panel."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_controller.const import DOMAIN

from .helpers import register_screen, setup_screen
from .test_compiler import load_layout

REFERENCE_REV = "90538742"


async def start(hass, *, name="HA Controller", mac="aa:bb:cc:dd:ee:ff", saved=True):
    device = await register_screen(hass, name=name, mac=mac)
    entry = await setup_screen(hass, device)
    hass.config_entries.async_update_entry(entry, title=name)
    if saved:
        await entry.runtime_data.async_save_layout(load_layout("reference"))
    return entry


async def test_screens_lists_entries(hass, hass_ws_client):
    second = await start(hass, name="Bedroom", mac="aa:bb:cc:dd:ee:01", saved=False)
    first = await start(hass, name="Attic", mac="aa:bb:cc:dd:ee:02", saved=False)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/screens"})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"screens": [first.runtime_data.status(), second.runtime_data.status()]}


async def test_screens_skips_unloaded_entries(hass, hass_ws_client):
    entry = await start(hass, saved=False)
    await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/screens"})
    msg = await client.receive_json()
    assert msg["result"] == {"screens": []}


async def test_layout_get_returns_stored_layout(hass, hass_ws_client):
    entry = await start(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/layout/get", "entry_id": entry.entry_id})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"layout": load_layout("reference")}


async def test_layout_get_unknown_entry_returns_not_found(hass, hass_ws_client):
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/layout/get", "entry_id": "missing"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"


async def test_layout_get_foreign_entry_returns_not_found(hass, hass_ws_client):
    assert await async_setup_component(hass, DOMAIN, {})
    other = MockConfigEntry(domain="other")
    other.add_to_hass(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/layout/get", "entry_id": other.entry_id})
    msg = await client.receive_json()
    assert msg["error"]["code"] == "not_found"


async def test_layout_get_unloaded_entry_returns_not_found(hass, hass_ws_client):
    entry = await start(hass, saved=False)
    await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "ha_controller/layout/get", "entry_id": entry.entry_id})
    msg = await client.receive_json()
    assert msg["error"]["code"] == "not_found"


async def test_layout_save_valid(hass, hass_ws_client):
    entry = await start(hass, saved=False)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "ha_controller/layout/save",
            "entry_id": entry.entry_id,
            "layout": load_layout("reference"),
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"revision": REFERENCE_REV, "pushed": False}
    assert entry.runtime_data.layout == load_layout("reference")


async def test_layout_save_invalid(hass, hass_ws_client):
    entry = await start(hass, saved=False)
    layout = load_layout("reference")
    layout["blocks"][1]["name"] = ""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "ha_controller/layout/save",
            "entry_id": entry.entry_id,
            "layout": layout,
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {"code": "invalid_layout", "message": "invalid_name@b2"}


async def test_layout_save_unknown_entry_returns_not_found(hass, hass_ws_client):
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "ha_controller/layout/save",
            "entry_id": "missing",
            "layout": load_layout("reference"),
        }
    )
    msg = await client.receive_json()
    assert msg["error"]["code"] == "not_found"


async def test_commands_require_admin(hass, hass_ws_client, hass_admin_user):
    entry = await start(hass)
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)
    commands = [
        {"type": "ha_controller/screens"},
        {"type": "ha_controller/layout/get", "entry_id": entry.entry_id},
        {
            "type": "ha_controller/layout/save",
            "entry_id": entry.entry_id,
            "layout": load_layout("reference"),
        },
    ]
    for command in commands:
        await client.send_json_auto_id(command)
        msg = await client.receive_json()
        assert not msg["success"]
        assert msg["error"]["code"] == "unauthorized"
