#include <doctest/doctest.h>

#include <cmath>

#include "ha_controller/format.h"

using namespace esphome::ha_controller;

TEST_CASE("format helpers") {
  CHECK(format_value(20.5f, 0.5f) == "20.5");
  CHECK(format_value(21, 1) == "21");
  CHECK(format_value(21, 0.5f) == "21.0");
  CHECK(format_percent(87.4f) == "87 %");
  CHECK(format_percent(NAN) == "— %");
}
