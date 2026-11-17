"""Firmware locations and version rules."""

import re

from .const import FIRMWARE_BASE_URL

_RELEASE = re.compile(r"^\d+\.\d+\.\d+$")


def firmware_urls(version: str) -> tuple[str, str]:
    """Return the OTA image URL and its MD5 URL for a version."""
    url = f"{FIRMWARE_BASE_URL}/{version}/ha-controller.ota.bin"
    return url, f"{url}.md5"


def is_release_version(version: str) -> bool:
    """Return True for a plain release version such as 1.2.3."""
    return _RELEASE.match(version) is not None
