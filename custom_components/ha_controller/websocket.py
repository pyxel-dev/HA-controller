"""Websocket API used by the HA Controller panel."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .controller import InvalidLayout, ScreenController, format_layout_errors


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the panel commands."""
    websocket_api.async_register_command(hass, ws_screens)
    websocket_api.async_register_command(hass, ws_layout_get)
    websocket_api.async_register_command(hass, ws_layout_save)


def _get_controller(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> ScreenController | None:
    """Return the controller of a loaded entry, or send not_found."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Screen not found")
        return None
    return entry.runtime_data


@websocket_api.websocket_command({vol.Required("type"): "ha_controller/screens"})
@websocket_api.require_admin
@callback
def ws_screens(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List the loaded screens."""
    entries = sorted(
        (
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ),
        key=lambda entry: entry.title,
    )
    connection.send_result(
        msg["id"], {"screens": [entry.runtime_data.status() for entry in entries]}
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "ha_controller/layout/get", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@callback
def ws_layout_get(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the stored layout of a screen."""
    if (controller := _get_controller(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], {"layout": controller.layout})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_controller/layout/save",
        vol.Required("entry_id"): str,
        vol.Required("layout"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_layout_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Validate, store and push a layout."""
    if (controller := _get_controller(hass, connection, msg)) is None:
        return
    try:
        revision, pushed = await controller.async_save_layout(msg["layout"])
    except InvalidLayout as err:
        connection.send_error(msg["id"], "invalid_layout", format_layout_errors(err.errors))
        return
    connection.send_result(msg["id"], {"revision": revision, "pushed": pushed})
