#include <doctest/doctest.h>

#include "ha_controller/sleep.h"

using namespace esphome::ha_controller;

TEST_CASE("sleep: default delay is 20 seconds") { CHECK(DEFAULT_SLEEP_S == 20); }

TEST_CASE("sleep: a timeout of 0 never sleeps") { CHECK_FALSE(should_sleep(10'000'000, 0)); }

TEST_CASE("sleep: sleeps exactly at the timeout") {
  CHECK_FALSE(should_sleep(19'999, 20));
  CHECK(should_sleep(20'000, 20));
  CHECK_FALSE(should_sleep(3'599'999, 3600));
  CHECK(should_sleep(3'600'000, 3600));
}
