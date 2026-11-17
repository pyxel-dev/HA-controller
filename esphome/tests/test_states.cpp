#include <doctest/doctest.h>

#include <vector>

#include "fixtures.h"
#include "ha_controller/states.h"

using namespace esphome::ha_controller;

static std::vector<StateUpdate> load(const char *name) {
  std::vector<StateUpdate> out;
  REQUIRE(parse_states(json_field(std::string("states/") + name + ".json", "updates"), out));
  return out;
}

TEST_CASE("parses light updates") {
  auto v = load("light-dimmable-on");
  REQUIRE(v.size() == 1);
  CHECK(v[0].on == true);
  CHECK(v[0].brightness == 50);
  auto o = load("light-onoff");
  REQUIRE(o.size() == 1);
  CHECK(o[0].on == true);
  CHECK(!o[0].brightness.has_value());
  auto u = load("light-unavailable");
  REQUIRE(u.size() == 1);
  CHECK(u[0].available == false);
}

TEST_CASE("parses climate updates") {
  auto v = load("climate-heating");
  REQUIRE(v.size() == 1);
  const StateUpdate &u = v[0];
  REQUIRE(u.target.has_value());
  CHECK(*u.target == doctest::Approx(20.5));
  CHECK(u.step == doctest::Approx(0.5));
  CHECK(u.unit == "°C");
  CHECK(u.current == "19.8 °C");
  CHECK(u.action == "Heating");
  auto d = load("climate-defaults");
  REQUIRE(d.size() == 1);
  CHECK(!d[0].target.has_value());
  CHECK(d[0].current == "—");
}

TEST_CASE("parses entity updates") {
  auto v = load("entity-precision");
  REQUIRE(!v.empty());
  bool found = false;
  for (auto &u : v)
    if (u.text.has_value() && *u.text == "12.3 °C")
      found = true;
  CHECK(found);
  auto m = load("entity-missing");
  REQUIRE(m.size() == 1);
  CHECK(*m[0].text == "—");
  CHECK(load("all-missing").size() == 4);
}

TEST_CASE("rejects bad input and skips elements without id") {
  std::vector<StateUpdate> out;
  CHECK_FALSE(parse_states("{\"id\":1}", out));
  CHECK_FALSE(parse_states("not json", out));
  REQUIRE(parse_states("[{\"id\":1},{\"id\":\"a\"},5]", out));
  CHECK(out.size() == 1);
}
