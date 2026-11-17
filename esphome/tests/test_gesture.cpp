#include <doctest/doctest.h>

#include "ha_controller/gesture.h"

using namespace esphome::ha_controller;

TEST_CASE("edge classification") {
  CHECK(classify_edge(233, 233, 466, 36) == Edge::NONE);
  CHECK(classify_edge(460, 233, 466, 36) == Edge::RIGHT);
  CHECK(classify_edge(5, 233, 466, 36) == Edge::LEFT);
  CHECK(classify_edge(233, 4, 466, 36) == Edge::TOP);
  CHECK(classify_edge(233, 462, 466, 36) == Edge::BOTTOM);
  CHECK(classify_edge(430, 233, 466, 36) == Edge::RIGHT);  // r = 197, boundary
  CHECK(classify_edge(429, 233, 466, 36) == Edge::NONE);
  CHECK(classify_edge(10, 10, 466, 36) == Edge::LEFT);     // diagonal tie -> horizontal
  CHECK(classify_edge(456, 10, 466, 36) == Edge::RIGHT);   // outside the visible circle still classifies
}

TEST_CASE("grid step per edge") {
  CHECK(step_for(Edge::RIGHT).dx == 1);
  CHECK(step_for(Edge::RIGHT).dy == 0);
  CHECK(step_for(Edge::LEFT).dx == -1);
  CHECK(step_for(Edge::LEFT).dy == 0);
  CHECK(step_for(Edge::TOP).dx == 0);
  CHECK(step_for(Edge::TOP).dy == -1);
  CHECK(step_for(Edge::BOTTOM).dx == 0);
  CHECK(step_for(Edge::BOTTOM).dy == 1);
  CHECK(step_for(Edge::NONE).dx == 0);
  CHECK(step_for(Edge::NONE).dy == 0);
}

TEST_CASE("swipe tracker") {
  SwipeTracker t;
  t.begin(Edge::RIGHT, true, 460, 233, 0);
  CHECK(t.update(400, 233, 50) == 60);
  CHECK(t.update(300, 240, 300) == 160);
  CHECK(t.release(400));

  t.begin(Edge::RIGHT, true, 460, 233, 0);
  CHECK(t.update(420, 233, 500) == 40);
  CHECK_FALSE(t.release(600));  // slow and short

  t.begin(Edge::LEFT, true, 5, 233, 0);
  t.update(25, 233, 10);
  CHECK(t.update(65, 233, 40) == 60);
  CHECK(t.release(45));  // flick

  t.begin(Edge::RIGHT, true, 460, 233, 0);
  CHECK(t.update(470, 233, 50) == 0);  // outward ignored

  t.begin(Edge::TOP, false, 233, 4, 0);
  CHECK(t.update(233, 204, 100) == 48);
  CHECK_FALSE(t.release(150));  // rubber band

  t.begin(Edge::BOTTOM, true, 233, 462, 0);
  CHECK(t.update(233, -600, 50) == 466);  // clamp to size

  t.begin(Edge::LEFT, true, 5, 233, 0xFFFFFFF0u);
  t.update(65, 233, 0x00000020u);
  CHECK(t.release(0x00000020u));  // wraparound flick

  t.begin(Edge::LEFT, true, 5, 233, 0);
  t.update(300, 233, 10);
  t.reset();
  CHECK_FALSE(t.active());
  CHECK_FALSE(t.release(20));
}

TEST_CASE("settle duration") {
  CHECK(settle_duration_ms(466, 466) == 220);
  CHECK(settle_duration_ms(0, 466) == 80);
  CHECK(settle_duration_ms(233, 466) == 110);
}
