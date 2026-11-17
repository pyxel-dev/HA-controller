#include <doctest/doctest.h>

#include "ha_controller/knob.h"

using namespace esphome::ha_controller;

TEST_CASE("knob scale") {
  CHECK(KnobScale{0, 100, 1}.steps() == 100);
  CHECK(KnobScale{7, 35, 0.5f}.steps() == 56);
  CHECK(KnobScale{7, 35, 0.5f}.index_of(20.5f) == 27);
  CHECK(KnobScale{7, 35, 0.5f}.value_at(27) == doctest::Approx(20.5));
  CHECK(KnobScale{7, 35, 0.5f}.index_of(100) == 56);
  CHECK(KnobScale{7, 35, 0.5f}.index_of(-5) == 0);
  CHECK(KnobScale{10, 10, 0.5f}.steps() == 0);
  CHECK(KnobScale{7, 35, 0}.steps() == 28);
  CHECK(KnobScale{7, 35, 0.5f}.value_at(999) == doctest::Approx(35));
  CHECK(KnobScale{7, 35, 0.5f}.value_at(-3) == doctest::Approx(7));
}
