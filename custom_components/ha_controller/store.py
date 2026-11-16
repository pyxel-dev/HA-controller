"""Persistent storage of one screen's layout."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1


class LayoutStore:
    """Wrap the Home Assistant store that keeps a screen's layout."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.layout.{entry_id}"
        )

    async def async_load(self) -> dict[str, Any] | None:
        """Return the stored layout, or None when nothing was saved yet."""
        return await self._store.async_load()

    async def async_save(self, layout: dict[str, Any]) -> None:
        """Persist the layout."""
        await self._store.async_save(layout)

    async def async_remove(self) -> None:
        """Delete the stored layout."""
        await self._store.async_remove()
