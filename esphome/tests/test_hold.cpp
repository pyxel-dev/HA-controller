#include <doctest/doctest.h>

#include "ha_controller/hold.h"

using namespace esphome::ha_controller;

TEST_CASE("interaction hold") {
  InteractionHold h;
  CHECK_FALSE(h.active(0));
  h.touch(1000);
  CHECK(h.active(2499));
  CHECK_FALSE(h.active(2500));
  h.touch(0xFFFFFF00u);
  CHECK(h.active(0x00000100u));
}
