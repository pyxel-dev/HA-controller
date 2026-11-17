"""Firmware update entity of a screen."""

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HaControllerConfigEntry
from .const import RELEASE_URL
from .controller import ScreenController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HaControllerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the firmware update entity of a screen."""
    controller = entry.runtime_data
    device = dr.async_get(hass).async_get(controller.device_id)
    if device is None:
        return
    async_add_entities([FirmwareUpdateEntity(controller, device.connections)])


class FirmwareUpdateEntity(UpdateEntity):
    """Keeps the screen firmware on the integration version."""

    _attr_has_entity_name = True
    _attr_translation_key = "firmware"
    _attr_title = "HA Controller"
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
    _attr_should_poll = False

    def __init__(self, controller: ScreenController, connections: set[tuple[str, str]]) -> None:
        self._controller = controller
        self._attr_unique_id = f"{controller.device_id}-firmware"
        self._attr_device_info = DeviceInfo(connections=connections)

    @property
    def installed_version(self) -> str | None:
        return self._controller.device.version

    @property
    def latest_version(self) -> str:
        return self._controller.integration_version

    @property
    def release_url(self) -> str:
        return RELEASE_URL.format(version=self.latest_version)

    @property
    def in_progress(self) -> bool:
        return self._controller.install_in_progress

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Offer any different version, so a downgrade is shown as an update."""
        return latest_version != installed_version

    async def async_install(self, version: str | None, backup: bool, **kwargs: object) -> None:
        await self._controller.async_install_firmware(self.latest_version)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._controller.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
