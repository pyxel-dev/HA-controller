from esphome import automation
import esphome.codegen as cg
from esphome.components import binary_sensor, font, number, sensor, touchscreen
from esphome.components.lvgl.defines import add_lv_use
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_SIZE, CONF_TRIGGER_ID

CODEOWNERS = ["@pyxel-dev"]
DEPENDENCIES = ["lvgl"]
AUTO_LOAD = ["json"]

CONF_EDGE_WIDTH = "edge_width"
CONF_TEXT_FONTS = "text_fonts"
CONF_VALUE_FONTS = "value_fonts"
CONF_EMOJI_FONTS = "emoji_fonts"
CONF_BATTERY_LEVEL = "battery_level"
CONF_BATTERY_CHARGING = "battery_charging"
CONF_SCREEN_BRIGHTNESS = "screen_brightness"
CONF_ON_CONTROL = "on_control"
CONF_TOUCHSCREEN = "touchscreen"
CONF_ON_SLEEP = "on_sleep"
CONF_ON_WAKE = "on_wake"

ha_controller_ns = cg.esphome_ns.namespace("ha_controller")
HaController = ha_controller_ns.class_("HaController", cg.Component)
ControlTrigger = ha_controller_ns.class_(
    "ControlTrigger",
    automation.Trigger.template(cg.std_string, cg.std_string, cg.std_string, cg.float_),
)
SleepTrigger = ha_controller_ns.class_("SleepTrigger", automation.Trigger.template())
WakeTrigger = ha_controller_ns.class_("WakeTrigger", automation.Trigger.template())
FontRole = ha_controller_ns.enum("FontRole", is_class=True)
FontSize = ha_controller_ns.enum("FontSize", is_class=True)

SIZES = ("s", "m", "l", "xl")
ROLES = (
    (CONF_TEXT_FONTS, "TEXT"),
    (CONF_VALUE_FONTS, "VALUE"),
    (CONF_EMOJI_FONTS, "EMOJI"),
)


def font_set_schema():
    return cv.Schema({cv.Required(s): cv.use_id(font.Font) for s in SIZES})


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(HaController),
        cv.Optional(CONF_SIZE, default=466): cv.int_range(min=100, max=1000),
        cv.Optional(CONF_EDGE_WIDTH, default=36): cv.int_range(min=8, max=120),
        cv.Required(CONF_TEXT_FONTS): font_set_schema(),
        cv.Required(CONF_VALUE_FONTS): font_set_schema(),
        cv.Required(CONF_EMOJI_FONTS): font_set_schema(),
        cv.Optional(CONF_BATTERY_LEVEL): cv.use_id(sensor.Sensor),
        cv.Optional(CONF_BATTERY_CHARGING): cv.use_id(binary_sensor.BinarySensor),
        cv.Optional(CONF_SCREEN_BRIGHTNESS): cv.use_id(number.Number),
        cv.Required(CONF_TOUCHSCREEN): cv.use_id(touchscreen.Touchscreen),
        cv.Optional(CONF_ON_SLEEP): automation.validate_automation(
            {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SleepTrigger)}
        ),
        cv.Optional(CONF_ON_WAKE): automation.validate_automation(
            {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(WakeTrigger)}
        ),
        cv.Optional(CONF_ON_CONTROL): automation.validate_automation(
            {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(ControlTrigger)}
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    add_lv_use("font")  # makes ESPHome fonts expose their lv_font_t

    cg.add(var.set_geometry(config[CONF_SIZE], config[CONF_EDGE_WIDTH]))
    for key, role in ROLES:
        for size in SIZES:
            fnt = await cg.get_variable(config[key][size])
            cg.add(var.set_font(getattr(FontRole, role), getattr(FontSize, size.upper()), fnt))

    if CONF_BATTERY_LEVEL in config:
        cg.add(var.set_battery_sensor(await cg.get_variable(config[CONF_BATTERY_LEVEL])))
    if CONF_BATTERY_CHARGING in config:
        cg.add(var.set_charging_sensor(await cg.get_variable(config[CONF_BATTERY_CHARGING])))
    if CONF_SCREEN_BRIGHTNESS in config:
        cg.add(var.set_brightness_number(await cg.get_variable(config[CONF_SCREEN_BRIGHTNESS])))

    cg.add(var.set_touchscreen(await cg.get_variable(config[CONF_TOUCHSCREEN])))

    for key, trigger_type in ((CONF_ON_SLEEP, SleepTrigger), (CONF_ON_WAKE, WakeTrigger)):
        for conf in config.get(key, []):
            trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
            await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_CONTROL, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(
            trigger,
            [
                (cg.std_string, "block"),
                (cg.std_string, "item"),
                (cg.std_string, "op"),
                (cg.float_, "value"),
            ],
            conf,
        )
