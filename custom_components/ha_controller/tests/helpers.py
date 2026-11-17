"""Helpers shared by the HA Controller tests."""

import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_controller.const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL

NODE = "ha-controller-aabbcc"
FIXTURES = Path(__file__).parents[3] / "docs" / "protocol" / "fixtures"
VERSION = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())["version"]


async def register_screen(
    hass: HomeAssistant,
    *,
    name: str = "HA Controller",
    manufacturer: str = MANUFACTURER,
    model: str = MODEL,
    mac: str = "aa:bb:cc:dd:ee:ff",
) -> dr.DeviceEntry:
    """Add an ESPHome config entry and a screen device that belongs to it."""
    esphome_entry = MockConfigEntry(domain="esphome", title=name)
    esphome_entry.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=esphome_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        name=name,
        manufacturer=manufacturer,
        model=model,
    )


async def setup_screen(hass: HomeAssistant, device: dr.DeviceEntry) -> MockConfigEntry:
    """Add and set up the ha_controller entry for a screen device."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_DEVICE_ID: device.id}, unique_id=device.id)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def hello(device: dr.DeviceEntry, **overrides: Any) -> dict[str, Any]:
    """Return a default hello event payload for the screen."""
    data: dict[str, Any] = {
        "device_id": device.id,
        "node": NODE,
        "version": VERSION,
        "protocol": "1",
        "revision": "none",
        "reason": "connected",
    }
    data.update(overrides)
    return data


def load_fixture(*parts: str) -> Any:
    """Read a shared protocol fixture from docs/protocol/fixtures."""
    return json.loads(FIXTURES.joinpath(*parts).read_text(encoding="utf-8"))
