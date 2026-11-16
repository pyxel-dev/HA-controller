"""Config flow for HA Controller."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(
            selector.DeviceSelectorConfig(
                filter=[
                    selector.DeviceFilterSelectorConfig(
                        integration="esphome", manufacturer=MANUFACTURER, model=MODEL
                    )
                ]
            )
        )
    }
)


class HaControllerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Link one ESPHome screen device per config entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            device = dr.async_get(self.hass).async_get(user_input[CONF_DEVICE_ID])
            if device is None or not self._is_screen(device):
                errors["base"] = "not_ha_controller"
            else:
                await self.async_set_unique_id(device.id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device.name_by_user or device.name or "HA Controller",
                    data={CONF_DEVICE_ID: device.id},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )

    def _is_screen(self, device: dr.DeviceEntry) -> bool:
        if device.manufacturer != MANUFACTURER or device.model != MODEL:
            return False
        return any(
            (entry := self.hass.config_entries.async_get_entry(entry_id)) is not None
            and entry.domain == "esphome"
            for entry_id in device.config_entries
        )
