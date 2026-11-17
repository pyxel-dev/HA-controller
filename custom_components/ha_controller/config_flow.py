"""Config flow for HA Controller."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import CONF_AUTO_UPDATE, CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        return OptionsFlowHandler()

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


class OptionsFlowHandler(OptionsFlow):
    """Options of one screen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_AUTO_UPDATE, True)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_AUTO_UPDATE, default=current): bool}),
        )
