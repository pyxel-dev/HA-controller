#include <doctest/doctest.h>

#include "ha_controller/stack.h"

using namespace esphome::ha_controller;

static bool inside(const StackItem &it, int top, int radius) {
  int lim = chord_limit(radius, it.half_width);
  return top >= -lim && top + it.height <= lim;
}

TEST_CASE("stack: few items stay centred with the default gap") {
  std::vector<StackItem> items = {{40, 160, false}, {40, 160, false}, {40, 135, true}};
  auto l = layout_stack(items);
  CHECK(l.fits);
  CHECK(l.gap == 8);
  CHECK(l.top[0] == -(120 + 16) / 2);
}

TEST_CASE("stack: six items with the slider row last keep every control inside radius 185") {
  std::vector<StackItem> items = {{50, 160, false}, {50, 160, false}, {50, 160, false},
                                  {50, 160, false}, {50, 160, false}, {40, 135, true}};
  auto l = layout_stack(items);
  CHECK(l.fits);
  for (size_t i = 0; i < items.size(); i++)
    CHECK(inside(items[i], l.top[i], items[i].interactive ? 185 : 233));
  for (size_t i = 1; i < items.size(); i++)
    CHECK(l.top[i] >= l.top[i - 1] + items[i - 1].height);
}

TEST_CASE("stack: slider row alone in the middle of tall text is reported as not fitting") {
  std::vector<StackItem> items = {{60, 160, false}, {60, 160, false}, {60, 160, false},
                                  {60, 160, false}, {60, 160, false}, {40, 135, true}};
  auto l = layout_stack(items);
  CHECK_FALSE(l.fits);
}

TEST_CASE("stack: single-line capped labels fit where wrapped text does not") {
  std::vector<StackItem> wrapped = {{60, 160, false}, {60, 160, false}, {60, 160, false},
                                    {60, 160, false}, {60, 160, false}, {40, 135, true}};
  std::vector<StackItem> capped = {{30, 160, false}, {30, 160, false}, {30, 160, false},
                                   {30, 160, false}, {30, 160, false}, {40, 135, true}};
  CHECK_FALSE(layout_stack(wrapped).fits);
  auto l = layout_stack(capped);
  CHECK(l.fits);
  for (size_t i = 0; i < capped.size(); i++)
    CHECK(inside(capped[i], l.top[i], capped[i].interactive ? 185 : 233));
}
