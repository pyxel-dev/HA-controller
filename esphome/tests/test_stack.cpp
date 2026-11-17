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

TEST_CASE("stack: slider row alone in the middle of tall text is shifted or reported") {
  std::vector<StackItem> items = {{60, 160, false}, {60, 160, false}, {60, 160, false},
                                  {60, 160, false}, {60, 160, false}, {40, 135, true}};
  auto l = layout_stack(items);
  if (l.fits) {
    for (size_t i = 0; i < items.size(); i++)
      CHECK(inside(items[i], l.top[i], items[i].interactive ? 185 : 233));
  }
}
