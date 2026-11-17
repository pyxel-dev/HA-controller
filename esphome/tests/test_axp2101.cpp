#include <doctest/doctest.h>

#include "axp2101_battery/axp2101_regs.h"

using namespace esphome::axp2101_battery;

TEST_CASE("axp2101 register helpers") {
  CHECK(battery_present(0x08));
  CHECK_FALSE(battery_present(0xF7));
  CHECK(is_charging(0x20));
  CHECK(is_charging(0x3F));
  CHECK_FALSE(is_charging(0x40));
  CHECK_FALSE(is_charging(0x00));
  CHECK_FALSE(is_charging(0xA0));
  CHECK(battery_millivolts(0x0F, 0xA0) == 4000);
  CHECK(battery_millivolts(0xFF, 0xFF) == 0x1FFF);
  CHECK(battery_percent(87) == 87.0f);
  CHECK(battery_percent(150) == 100.0f);
}
