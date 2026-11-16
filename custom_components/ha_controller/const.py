"""Constants for HA Controller. Protocol v1 values are defined here once."""

from datetime import timedelta

DOMAIN = "ha_controller"
MANUFACTURER = "pyxel-dev"
MODEL = "ha-controller"

CONF_DEVICE_ID = "device_id"
CONF_AUTO_UPDATE = "auto_update"

PROTOCOL_VERSION = 1

EVENT_HELLO = "esphome.ha_controller_hello"
EVENT_CONTROL = "esphome.ha_controller_control"

ACTION_SET_LAYOUT = "set_layout"
ACTION_SET_STATES = "set_states"
ACTION_INSTALL_FIRMWARE = "install_firmware"

MAX_BLOCKS = 32
MAX_ITEMS = 6
MAX_NAME_LEN = 32
MAX_TEXT_LEN = 64
COORD_LIMIT = 32
MAX_PAYLOAD_BYTES = 24576
STATE_CHUNK_BYTES = 8192

FONT_SIZES = ("s", "m", "l", "xl")
ENTITY_BLOCK_DOMAINS = ("light", "climate")
ITEM_KINDS = ("text", "emoji", "entity", "battery", "brightness")

# Screen sleep, in seconds. 0 means never.
DEFAULT_SLEEP_TIMEOUT = 20
MIN_SLEEP_TIMEOUT = 5
MAX_SLEEP_TIMEOUT = 3600

ONLINE_TIMEOUT = timedelta(seconds=150)
PUSH_RETRY = timedelta(seconds=300)
STATE_COALESCE_SECONDS = 0.2
INSTALL_TIMEOUT = 300
AUTO_UPDATE_RETRY = timedelta(seconds=3600)

PANEL_URL_PATH = "ha-controller"
PANEL_COMPONENT = "ha-controller-panel"
PANEL_TITLE = "HA Controller"
PANEL_ICON = "mdi:remote"
STATIC_URL = "/ha_controller_static"

FIRMWARE_BASE_URL = "https://pyxel-dev.github.io/HA-controller/firmware"
RELEASE_URL = "https://github.com/pyxel-dev/HA-controller/releases/tag/v{version}"
