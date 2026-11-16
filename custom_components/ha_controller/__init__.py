"""The HA Controller integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .controller import ScreenController
from .layout import async_load_emoji
from .store import LayoutStore
from .websocket import async_register_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type HaControllerConfigEntry = ConfigEntry[ScreenController]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration."""
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HaControllerConfigEntry) -> bool:
    """Set up one screen."""
    integration = await async_get_integration(hass, DOMAIN)
    controller = ScreenController(
        hass,
        entry,
        LayoutStore(hass, entry.entry_id),
        await async_load_emoji(hass),
        str(integration.version),
    )
    await controller.async_start()
    entry.runtime_data = controller
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaControllerConfigEntry) -> bool:
    """Unload one screen."""
    await entry.runtime_data.async_stop()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: HaControllerConfigEntry) -> None:
    """Delete the stored layout of a removed screen."""
    await LayoutStore(hass, entry.entry_id).async_remove()
