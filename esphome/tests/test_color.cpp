#include <doctest/doctest.h>

#include "fixtures.h"
#include "ha_controller/color.h"

using namespace esphome::ha_controller;

TEST_CASE("parse_hex_rgb accepts RRGGBB and #RRGGBB") {
  uint32_t v = 0;
  CHECK(parse_hex_rgb("5B9E4D", v));
  CHECK(v == 0x5B9E4D);
  CHECK(parse_hex_rgb("#c94f3d", v));
  CHECK(v == 0xC94F3D);
  v = 7;
  CHECK_FALSE(parse_hex_rgb("GGGGGG", v));
  CHECK_FALSE(parse_hex_rgb("12345", v));
  CHECK_FALSE(parse_hex_rgb("#1234567", v));
  CHECK_FALSE(parse_hex_rgb("", v));
  CHECK(v == 7);
}

TEST_CASE("text colour follows colors.json") {
  JsonDocument doc;
  REQUIRE_FALSE(deserializeJson(doc, read_fixture("colors.json")));
  REQUIRE(doc.as<JsonArray>().size() > 0);
  for (JsonObject e : doc.as<JsonArray>()) {
    uint32_t bg = 0, text = 0;
    REQUIRE(parse_hex_rgb(e["bg"].as<std::string>(), bg));
    REQUIRE(parse_hex_rgb(e["text"].as<std::string>(), text));
    INFO(e["bg"].as<std::string>());
    CHECK(text_color_for(bg) == text);
  }
}
