"""Tests for the firmware update entity, automatic updates and the options flow."""

import asyncio
from datetime import timedelta

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.ha_controller.const import CONF_AUTO_UPDATE
from custom_components.ha_controller.firmware import firmware_urls, is_release_version

from .helpers import hello, register_screen, setup_screen

ENTITY = "update.mock_title_ha_controller_firmware"
URL = "https://pyxel-dev.github.io/HA-controller/firmware/0.1.0/ha-controller.ota.bin"


def test_firmware_urls():
    assert firmware_urls("0.1.0") == (URL, URL + ".md5")


def test_is_release_version():
    assert is_release_version("1.2.3")
    assert not is_release_version("0.2.0.dev0")
    assert not is_release_version("0.2.0-rc1")


async def start(hass, *, auto_update=False):
    installs = async_mock_service(hass, "esphome", "ha_controller_aabbcc_install_firmware")
    async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_layout")
    async_mock_service(hass, "esphome", "ha_controller_aabbcc_set_states")
    device = await register_screen(hass)
    entry = await setup_screen(hass, device)
    hass.config_entries.async_update_entry(entry, options={CONF_AUTO_UPDATE: auto_update})
    await hass.async_block_till_done()
    return device, entry, installs


async def send_hello(hass, device, **overrides):
    hass.bus.async_fire("esphome.ha_controller_hello", hello(device, **overrides))
    await hass.async_block_till_done()


async def start_install(hass):
    """Start the install service call and let it reach its wait for the hello."""
    task = hass.async_create_background_task(
        hass.services.async_call("update", "install", {"entity_id": ENTITY}, blocking=True),
        "test install",
    )
    for _ in range(20):
        await asyncio.sleep(0)
    return task


async def test_unknown_before_first_hello(hass):
    await start(hass)
    assert hass.states.get(ENTITY).state == "unknown"


async def test_update_entity_reports_versions(hass):
    device, _, _ = await start(hass)
    await send_hello(hass, device, version="0.0.9")
    state = hass.states.get(ENTITY)
    assert state.state == "on"
    assert state.attributes["installed_version"] == "0.0.9"
    assert state.attributes["latest_version"] == "0.1.0"
    assert state.attributes["release_url"].endswith("/tag/v0.1.0")


async def test_update_entity_off_when_versions_match(hass):
    device, _, _ = await start(hass)
    await send_hello(hass, device, version="0.1.0")
    assert hass.states.get(ENTITY).state == "off"


async def test_newer_firmware_is_offered_as_update(hass):
    device, _, _ = await start(hass)
    await send_hello(hass, device, version="0.2.0")
    assert hass.states.get(ENTITY).state == "on"


async def test_install_calls_device_and_completes_on_hello(hass):
    device, _, installs = await start(hass)
    await send_hello(hass, device, version="0.0.9")
    task = await start_install(hass)
    assert len(installs) == 1
    assert installs[0].data == {"url": URL, "md5_url": URL + ".md5"}
    assert hass.states.get(ENTITY).attributes["in_progress"] is True
    await send_hello(hass, device, version="0.1.0")
    await task
    state = hass.states.get(ENTITY)
    assert state.state == "off"
    assert state.attributes["in_progress"] is False


async def test_install_times_out(hass, freezer):
    device, entry, _ = await start(hass)
    await send_hello(hass, device, version="0.0.9")
    task = await start_install(hass)
    assert entry.runtime_data.install_in_progress
    freezer.tick(timedelta(seconds=301))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError, match="did not complete"):
        await task
    assert not entry.runtime_data.install_in_progress
    assert hass.states.get(ENTITY).attributes["in_progress"] is False


async def test_install_when_offline_raises(hass):
    _, entry, installs = await start(hass)
    with pytest.raises(HomeAssistantError, match="offline"):
        await entry.runtime_data.async_install_firmware("0.1.0")
    assert installs == []


async def test_install_while_in_progress_raises(hass):
    device, entry, installs = await start(hass)
    await send_hello(hass, device, version="0.0.9")
    task = await start_install(hass)
    with pytest.raises(HomeAssistantError, match="already running"):
        await entry.runtime_data.async_install_firmware("0.1.0")
    assert len(installs) == 1
    await send_hello(hass, device, version="0.1.0")
    await task


async def test_auto_update_installs_at_most_once_per_hour(hass, freezer):
    device, entry, installs = await start(hass, auto_update=True)
    await send_hello(hass, device, version="0.0.9")
    assert len(installs) == 1
    freezer.tick(timedelta(seconds=301))
    async_fire_time_changed(hass)  # the first install gives up waiting
    await hass.async_block_till_done()
    assert not entry.runtime_data.install_in_progress
    freezer.tick(timedelta(seconds=1))
    await send_hello(hass, device, version="0.0.9")  # inside the one hour window
    assert len(installs) == 1
    freezer.tick(timedelta(seconds=3601 - 302))
    await send_hello(hass, device, version="0.0.9")  # 3601 s after the first attempt
    assert len(installs) == 2
    await send_hello(hass, device, version="0.1.0")


async def test_auto_update_ignores_protocol_mismatch(hass):
    device, _, installs = await start(hass, auto_update=True)
    await send_hello(hass, device, version="0.0.9", protocol="2")
    assert len(installs) == 1
    await send_hello(hass, device, version="0.1.0", protocol="2")


async def test_unload_ends_pending_install(hass):
    device, entry, installs = await start(hass)
    await send_hello(hass, device, version="0.0.9")
    task = await start_install(hass)
    controller = entry.runtime_data
    assert controller.install_in_progress
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert task.done()  # ended without waiting for the 300 s timeout
    with pytest.raises(HomeAssistantError, match="unloaded"):
        await task
    assert not controller.install_in_progress
    assert controller._install_waiter is None


async def test_auto_update_disabled_by_option(hass):
    device, _, installs = await start(hass, auto_update=False)
    await send_hello(hass, device, version="0.0.9")
    assert installs == []


async def test_auto_update_skipped_for_dev_versions(hass):
    device, entry, installs = await start(hass, auto_update=True)
    entry.runtime_data._integration_version = "0.2.0.dev0"
    await send_hello(hass, device, version="0.0.9")
    assert installs == []


async def test_options_flow_toggles_auto_update(hass):
    _, entry, _ = await start(hass, auto_update=True)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_AUTO_UPDATE: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_AUTO_UPDATE] is False
