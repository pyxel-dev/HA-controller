"""Per-screen controller: owns the layout and keeps the screen in sync."""

import logging
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .compiler import compile_layout, encode_payload
from .const import (
    ACTION_SET_LAYOUT,
    ACTION_SET_STATES,
    CONF_DEVICE_ID,
    EVENT_HELLO,
    MAX_PAYLOAD_BYTES,
    ONLINE_TIMEOUT,
    PROTOCOL_VERSION,
    PUSH_RETRY,
    STATE_COALESCE_SECONDS,
)
from .layout import LayoutError, bound_entities, empty_layout, validate_layout
from .states import build_updates, chunk_updates
from .store import LayoutStore

_LOGGER = logging.getLogger(__name__)

REASON_CONNECTED = "connected"
NO_REVISION = "none"


@dataclass
class DeviceStatus:
    """What the screen last told us about itself."""

    node: str | None = None
    version: str | None = None
    revision: str | None = None
    protocol: int | None = None
    last_seen: datetime | None = None

    def online(self) -> bool:
        """Return True when a hello arrived within the online timeout."""
        return self.last_seen is not None and dt_util.utcnow() - self.last_seen <= ONLINE_TIMEOUT


class InvalidLayout(HomeAssistantError):
    """Raised when a layout cannot be saved."""

    def __init__(self, errors: list[LayoutError]) -> None:
        super().__init__(", ".join(f"{e.code}@{e.ref}" for e in errors))
        self.errors = errors


def _parse_protocol(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


class ScreenController:
    """Owns the stored layout of one screen and pushes it to the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: LayoutStore,
        emoji: frozenset[str],
        integration_version: str,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self._store = store
        self._emoji = emoji
        self._integration_version = integration_version
        self._layout: dict[str, Any] = empty_layout()
        self._payload: dict[str, Any] = compile_layout(self._layout)
        self._device = DeviceStatus()
        self._last_push: tuple[str, datetime] | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub_hello: CALLBACK_TYPE | None = None
        self._unsub_states: CALLBACK_TYPE | None = None
        self._cancel_flush: CALLBACK_TYPE | None = None
        self._pending: set[str] = set()

    @property
    def device_id(self) -> str:
        return self.entry.data[CONF_DEVICE_ID]

    @property
    def layout(self) -> dict[str, Any]:
        return self._layout

    @property
    def revision(self) -> str:
        return self._payload["rev"]

    @property
    def device(self) -> DeviceStatus:
        return self._device

    @property
    def integration_version(self) -> str:
        return self._integration_version

    async def async_start(self) -> None:
        """Load the layout and subscribe to the screen and its entities."""
        stored = await self._store.async_load()
        if stored is not None:
            errors = validate_layout(stored, self._emoji)
            if errors:
                _LOGGER.warning(
                    "Ignoring invalid stored layout for %s: %s",
                    self.entry.title,
                    ", ".join(f"{e.code}@{e.ref}" for e in errors),
                )
            else:
                self._set_layout(stored)
        self._track_entities()
        device_id = self.device_id

        @callback
        def _is_ours(event_data: dict[str, Any] | Any) -> bool:
            return event_data.get("device_id") == device_id

        self._unsub_hello = self.hass.bus.async_listen(
            EVENT_HELLO, self._async_hello_event, event_filter=_is_ours
        )

    async def async_stop(self) -> None:
        """Cancel every subscription and pending timer."""
        if self._unsub_hello is not None:
            self._unsub_hello()
            self._unsub_hello = None
        self._untrack_entities()
        if self._cancel_flush is not None:
            self._cancel_flush()
            self._cancel_flush = None
        self._pending.clear()
        self._listeners.clear()

    @callback
    def async_add_listener(self, cb: Callable[[], None]) -> CALLBACK_TYPE:
        """Call cb after every hello is recorded."""
        self._listeners.append(cb)

        @callback
        def _remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _remove

    def _set_layout(self, layout: dict[str, Any]) -> None:
        self._layout = layout
        self._payload = compile_layout(layout)
        self._track_entities()

    def _untrack_entities(self) -> None:
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None

    def _track_entities(self) -> None:
        self._untrack_entities()
        entity_ids = list(bound_entities(self._layout))
        if entity_ids:
            self._unsub_states = async_track_state_change_event(
                self.hass, entity_ids, self._state_changed
            )

    def _can_push_states(self) -> bool:
        return (
            self._device.node is not None
            and self._device.protocol == PROTOCOL_VERSION
            and self._device.online()
        )

    @callback
    def _state_changed(self, event: Event) -> None:
        if not self._can_push_states():
            return
        self._pending.add(event.data["entity_id"])
        if self._cancel_flush is None:
            self._cancel_flush = async_call_later(
                self.hass, STATE_COALESCE_SECONDS, self._async_flush
            )

    async def _async_flush(self, _now: datetime) -> None:
        self._cancel_flush = None
        entity_ids, self._pending = self._pending, set()
        if entity_ids and self._can_push_states():
            await self.async_push_states(entity_ids)

    async def async_save_layout(self, layout: dict[str, Any]) -> tuple[str, bool]:
        """Validate, store and (when the screen is online) push a layout."""
        errors = validate_layout(layout, self._emoji)
        if errors:
            raise InvalidLayout(errors)
        payload = compile_layout(layout)
        if len(encode_payload(payload).encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise InvalidLayout([LayoutError("payload_too_large", None)])
        await self._store.async_save(layout)
        self._set_layout(layout)
        pushed = False
        if self._device.protocol == PROTOCOL_VERSION and self._device.online():
            pushed = await self.async_push_layout()
        return self.revision, pushed

    async def async_handle_hello(self, data: dict[str, Any]) -> None:
        """Record a hello and resync the screen (spec §7.5)."""
        revision = data.get("revision")
        self._device = DeviceStatus(
            node=data.get("node") or self._device.node,
            version=data.get("version"),
            revision=None if revision in (None, NO_REVISION) else revision,
            protocol=_parse_protocol(data.get("protocol")),
            last_seen=dt_util.utcnow(),
        )
        for cb in list(self._listeners):
            cb()
        if self._device.protocol != PROTOCOL_VERSION:
            return
        connected = data.get("reason") == REASON_CONNECTED
        if revision != self.revision:
            if connected or not self._recently_pushed():
                await self.async_push_layout()
        elif connected:
            await self.async_push_states()

    async def _async_hello_event(self, event: Event) -> None:
        await self.async_handle_hello(event.data)

    def _recently_pushed(self) -> bool:
        if self._last_push is None:
            return False
        revision, when = self._last_push
        return revision == self.revision and dt_util.utcnow() - when < PUSH_RETRY

    async def async_push_layout(self) -> bool:
        """Send the layout, then all states. Return True on success."""
        self._last_push = (self.revision, dt_util.utcnow())
        ok = await self.async_call_device(
            ACTION_SET_LAYOUT, {"layout": encode_payload(self._payload)}
        )
        return ok and await self.async_push_states()

    async def async_push_states(self, entity_ids: Collection[str] | None = None) -> bool:
        """Send the state updates for entity_ids (all when None)."""
        updates = build_updates(self.hass, self._layout, entity_ids)
        for chunk in chunk_updates(updates):
            if not await self.async_call_device(ACTION_SET_STATES, {"states": chunk}):
                return False
        return True

    async def async_call_device(self, action: str, data: dict[str, Any]) -> bool:
        """Call an ESPHome service of the screen. Return False on failure."""
        node = self._device.node
        if node is None:
            return False
        service = f"{node.replace('-', '_')}_{action}"
        try:
            await self.hass.services.async_call("esphome", service, data, blocking=True)
        except HomeAssistantError as err:
            _LOGGER.warning("Calling esphome.%s failed: %s", service, err)
            return False
        return True

    def status(self) -> dict[str, Any]:
        """Return this screen as one ha_controller/screens item."""
        device = self._device
        return {
            "entry_id": self.entry.entry_id,
            "title": self.entry.title,
            "device_id": self.device_id,
            "online": device.online(),
            "firmware_version": device.version,
            "integration_version": self._integration_version,
            "protocol_ok": None
            if device.last_seen is None
            else device.protocol == PROTOCOL_VERSION,
            "revision": self.revision,
            "device_revision": device.revision,
        }
