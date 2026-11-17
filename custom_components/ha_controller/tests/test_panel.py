"""Tests for the sidebar panel registration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ha_controller.const import PANEL_URL_PATH

from .helpers import register_screen, setup_screen


async def test_panel_registered_on_setup(hass: HomeAssistant) -> None:
    """The panel is registered for admins with the first entry."""
    await setup_screen(hass, await register_screen(hass))

    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH]
    assert panel.require_admin is True
    assert panel.sidebar_title == "HA Controller"
    assert panel.sidebar_icon == "mdi:remote"


async def test_panel_kept_while_another_entry_is_loaded(hass: HomeAssistant) -> None:
    """Unloading one of two entries keeps the panel."""
    first = await setup_screen(hass, await register_screen(hass, mac="aa:bb:cc:dd:ee:01"))
    await setup_screen(hass, await register_screen(hass, mac="aa:bb:cc:dd:ee:02"))

    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()

    assert PANEL_URL_PATH in hass.data[frontend.DATA_PANELS]


async def test_panel_removed_when_last_entry_unloaded(hass: HomeAssistant) -> None:
    """Unloading the last entry removes the panel."""
    entry = await setup_screen(hass, await register_screen(hass))

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_static_path_registered_once(hass: HomeAssistant) -> None:
    """The bundle route is registered once for several entries."""
    assert await async_setup_component(hass, "http", {})
    with patch.object(hass.http, "async_register_static_paths", AsyncMock()) as register:
        await setup_screen(hass, await register_screen(hass, mac="aa:bb:cc:dd:ee:01"))
        await setup_screen(hass, await register_screen(hass, mac="aa:bb:cc:dd:ee:02"))

    ours = [
        config
        for call in register.await_args_list
        for config in call.args[0]
        if config.url_path.startswith("/ha_controller_static")
    ]
    assert len(ours) == 1
    assert ours[0].url_path == "/ha_controller_static/ha-controller-panel.js"
    assert ours[0].path.endswith("frontend/dist/ha-controller-panel.js")
    assert ours[0].cache_headers is True


async def test_missing_bundle_warns(hass: HomeAssistant, caplog) -> None:
    """A missing bundle only logs a warning."""
    with patch(
        "custom_components.ha_controller.panel.BUNDLE", Path("/nonexistent/ha-controller-panel.js")
    ):
        entry = await setup_screen(hass, await register_screen(hass))

    assert entry.state.name == "LOADED"
    assert "bundle" in caplog.text
