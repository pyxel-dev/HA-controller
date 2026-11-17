"""Sidebar panel registration."""

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, PANEL_COMPONENT, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH, STATIC_URL

_LOGGER = logging.getLogger(__name__)

BUNDLE = Path(__file__).parent / "frontend" / "dist" / "ha-controller-panel.js"
STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant, version: str) -> None:
    """Serve the panel bundle and add the sidebar panel."""
    if not hass.data.get(STATIC_REGISTERED):
        hass.data[STATIC_REGISTERED] = True
        await hass.http.async_register_static_paths(
            [StaticPathConfig(f"{STATIC_URL}/ha-controller-panel.js", str(BUNDLE), True)]
        )
        if not await hass.async_add_executor_job(BUNDLE.is_file):
            _LOGGER.warning("The panel bundle %s is missing; build it with npm", BUNDLE)

    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/ha-controller-panel.js?v={version}",
        require_admin=True,
        config={},
    )


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
