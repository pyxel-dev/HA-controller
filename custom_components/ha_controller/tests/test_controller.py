"""Tests for the layout store and the screen sync engine."""

import json
from datetime import timedelta

from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.ha_controller.const import DOMAIN
from custom_components.ha_controller.controller import InvalidLayout
from custom_components.ha_controller.layout import LayoutError

from .helpers import NODE, hello, register_screen, setup_screen
from .test_compiler import load_layout

REFERENCE_REV = "90538742"


def mock_screen(hass):
    layouts = async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_layout")
    states = async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_states")
    return layouts, states


async def start(hass, *, saved=True):
    """Set up a screen, optionally with the reference layout saved (offline)."""
    device = await register_screen(hass)
    entry = await setup_screen(hass, device)
    if saved:
        await entry.runtime_data.async_save_layout(load_layout("reference"))
    return device, entry, entry.runtime_data


async def send_hello(hass, device, **overrides):
    hass.bus.async_fire("esphome.ha_controller_hello", hello(device, **overrides))
    await hass.async_block_till_done()


async def test_hello_with_unknown_revision_pushes_layout_and_states(hass):
    layouts, states = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, revision="none", reason="heartbeat")
    assert len(layouts) == 1
    assert json.loads(layouts[0].data["layout"])["rev"] == REFERENCE_REV
    assert len(states) >= 1


async def test_hello_connected_with_current_revision_pushes_states_only(hass):
    layouts, states = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, revision=REFERENCE_REV, reason="connected")
    assert layouts == []
    assert len(states) >= 1


async def test_heartbeat_with_current_revision_pushes_nothing(hass):
    layouts, states = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, revision=REFERENCE_REV, reason="heartbeat")
    assert layouts == []
    assert states == []


async def test_stale_revision_is_retried_at_most_every_300s(hass, freezer):
    layouts, _ = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, reason="heartbeat")
    freezer.tick(timedelta(seconds=299))
    await send_hello(hass, device, reason="heartbeat")
    assert len(layouts) == 1
    freezer.tick(timedelta(seconds=2))
    await send_hello(hass, device, reason="heartbeat")
    assert len(layouts) == 2
    await send_hello(hass, device, reason="connected")
    assert len(layouts) == 3


async def test_hello_with_other_protocol_pushes_nothing(hass):
    layouts, states = mock_screen(hass)
    device, entry, controller = await start(hass)
    await send_hello(hass, device, protocol="2", reason="connected")
    assert layouts == []
    assert states == []
    assert controller.status()["protocol_ok"] is False


async def test_hello_from_other_device_is_ignored(hass):
    layouts, _ = mock_screen(hass)
    device, _, controller = await start(hass)
    other = await register_screen(hass, name="Other", mac="11:22:33:44:55:66")
    await send_hello(hass, other)
    assert layouts == []
    assert controller.device.last_seen is None
    assert controller.status()["protocol_ok"] is None


async def test_state_changes_are_coalesced(hass, freezer):
    _, states = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, revision=REFERENCE_REV, reason="heartbeat")
    hass.states.async_set("light.kitchen", "on", {"brightness": 255})
    freezer.tick(timedelta(milliseconds=100))
    hass.states.async_set("light.living_room", "on", {"brightness": 255})
    await hass.async_block_till_done()
    assert states == []
    freezer.tick(timedelta(milliseconds=300))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(states) == 1
    ids = {u["id"] for u in json.loads(states[0].data["states"])}
    assert ids == {"b1", "b2"}


async def test_state_change_not_pushed_when_offline(hass, freezer):
    _, states = mock_screen(hass)
    device, _, _ = await start(hass)
    await send_hello(hass, device, revision=REFERENCE_REV, reason="heartbeat")
    freezer.tick(timedelta(seconds=151))
    hass.states.async_set("light.kitchen", "on", {"brightness": 255})
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert states == []


async def test_save_layout_pushes_when_online(hass):
    layouts, states = mock_screen(hass)
    device, entry, controller = await start(hass, saved=False)
    await send_hello(hass, device, revision="none", reason="heartbeat")
    assert (await controller.async_save_layout(load_layout("reference"))) == (
        REFERENCE_REV,
        True,
    )
    assert json.loads(layouts[-1].data["layout"])["rev"] == REFERENCE_REV
    assert len(states) >= 1


async def test_save_layout_offline_returns_not_pushed(hass, hass_storage):
    layouts, _ = mock_screen(hass)
    _, entry, controller = await start(hass, saved=False)
    result = await controller.async_save_layout(load_layout("reference"))
    assert result == (REFERENCE_REV, False)
    assert layouts == []
    key = f"{DOMAIN}.layout.{entry.entry_id}"
    assert hass_storage[key]["data"] == load_layout("reference")


async def test_save_invalid_layout_raises(hass):
    _, _, controller = await start(hass, saved=False)
    layout = load_layout("reference")
    layout["blocks"][1]["name"] = ""
    try:
        await controller.async_save_layout(layout)
    except InvalidLayout as err:
        assert err.errors == [LayoutError("invalid_name", "b2")]
    else:
        raise AssertionError("InvalidLayout not raised")
    assert controller.revision != REFERENCE_REV


async def test_save_too_large_layout_raises_payload_too_large(hass):
    _, _, controller = await start(hass, saved=False)
    text = "漢" * 64
    layout = {
        "version": 1,
        "start": "b0",
        "settings": {"sleep_timeout": 20},
        "blocks": [
            {
                "id": f"b{n}",
                "x": n,
                "y": 0,
                "name": "Big",
                "background": "#000000",
                "font_size": "m",
                "type": "custom",
                "items": [
                    {"id": f"i{n}x{k}", "kind": "text", "text": text, "font_size": None}
                    for k in range(6)
                ],
            }
            for n in range(32)
        ],
    }
    try:
        await controller.async_save_layout(layout)
    except InvalidLayout as err:
        assert err.errors == [LayoutError("payload_too_large", None)]
    else:
        raise AssertionError("InvalidLayout not raised")


async def test_push_failure_is_logged_not_raised(hass, caplog):
    async def fail(call):
        raise HomeAssistantError("boom")

    hass.services.async_register("esphome", "ha_controller_aabbcc_set_layout", fail)
    device, _, controller = await start(hass)
    await send_hello(hass, device, reason="heartbeat")
    assert await controller.async_push_layout() is False
    assert "ha_controller_aabbcc_set_layout" in caplog.text
    assert "boom" in caplog.text


async def test_call_device_without_hello_returns_false(hass):
    layouts, _ = mock_screen(hass)
    _, _, controller = await start(hass)
    assert await controller.async_call_device("set_layout", {"layout": "{}"}) is False
    assert layouts == []


async def test_invalid_stored_layout_falls_back_to_empty(hass, hass_storage, caplog):
    device = await register_screen(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={"device_id": device.id}, unique_id=device.id)
    entry.add_to_hass(hass)
    key = f"{DOMAIN}.layout.{entry.entry_id}"
    stored = {"version": 1, "start": "zz", "settings": {"sleep_timeout": 20}, "blocks": "bad"}
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": stored}
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    controller = entry.runtime_data
    assert controller.layout["blocks"] == []
    assert "Ignoring invalid stored layout" in caplog.text
    assert hass_storage[key]["data"] == stored


async def test_layout_survives_reload(hass):
    _, entry, _ = await start(hass)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.layout == load_layout("reference")
    assert entry.runtime_data.revision == REFERENCE_REV


async def test_remove_entry_deletes_storage(hass, hass_storage):
    _, entry, _ = await start(hass)
    key = f"{DOMAIN}.layout.{entry.entry_id}"
    assert key in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage


async def test_listeners_are_notified_on_hello(hass):
    mock_screen(hass)
    device, _, controller = await start(hass)
    calls = []
    remove = controller.async_add_listener(lambda: calls.append(1))
    await send_hello(hass, device, reason="heartbeat")
    assert calls == [1]
    remove()
    await send_hello(hass, device, reason="heartbeat")
    assert calls == [1]


async def test_status_reports_device(hass):
    mock_screen(hass)
    device, entry, controller = await start(hass)
    await send_hello(hass, device, revision=REFERENCE_REV, reason="heartbeat")
    assert controller.status() == {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "device_id": device.id,
        "online": True,
        "firmware_version": "0.1.0",
        "integration_version": "0.1.0",
        "protocol_ok": True,
        "revision": REFERENCE_REV,
        "device_revision": REFERENCE_REV,
    }
    assert controller.device.node == NODE
