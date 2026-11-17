#include <doctest/doctest.h>

#include <dirent.h>

#include <algorithm>
#include <vector>

#include "fixtures.h"
#include "ha_controller/layout.h"

using namespace esphome::ha_controller;

TEST_CASE("parses the reference payload") {
  Layout l;
  REQUIRE(parse_layout(json_field("payloads/valid/reference.json", "payload"), l) == ParseError::NONE);
  CHECK(l.rev == "90538742");
  CHECK(l.start == "b1");
  CHECK(l.sleep_s == 20);
  CHECK(l.blocks.size() == 4);
  REQUIRE(l.find("b3") != nullptr);
  CHECK(l.find("b3")->widget == Widget::CUSTOM);
  CHECK(l.find("b3")->items.size() == 5);
  CHECK(l.find("b3")->items[1].kind == ItemKind::EMOJI);
  CHECK(l.find("b3")->items[1].text == "👋");
  CHECK(l.find("b3")->items[1].font == FontSize::XL);
  CHECK(l.find("b3")->items[2].font == FontSize::S);
  CHECK(l.find("b3")->items[2].kind == ItemKind::ENTITY);
  CHECK(l.find("b3")->items[3].kind == ItemKind::BATTERY);
  CHECK(l.find("b3")->items[4].kind == ItemKind::BRIGHTNESS);
  CHECK(l.find("b3")->items[0].text == "Hello World");
  REQUIRE(l.find("b4") != nullptr);
  CHECK(l.find("b4")->widget == Widget::CLIMATE);
  REQUIRE(l.find("b1") != nullptr);
  CHECK(l.find("b1")->bg == 0x5B9E4D);
  CHECK(l.find("b1")->name == "Kitchen");
  CHECK(l.find("b1")->font == FontSize::M);
  REQUIRE(l.find_at(0, -1) != nullptr);
  CHECK(l.find_at(0, -1)->id == "b2");
  CHECK(l.find_at(5, 5) == nullptr);
  CHECK(l.find("nope") == nullptr);
}

TEST_CASE("parses the empty payload") {
  Layout l;
  l.start = "stale";
  REQUIRE(parse_layout(json_field("payloads/valid/empty.json", "payload"), l) == ParseError::NONE);
  CHECK(l.rev == "c4aad3fa");
  CHECK(l.start == "");
  CHECK(l.sleep_s == 20);
  CHECK(l.blocks.empty());
}

TEST_CASE("parses sleep 0 and 3600") {
  Layout l;
  CHECK(parse_layout(R"({"v":1,"rev":"x","start":null,"sleep":0,"blocks":[]})", l) == ParseError::NONE);
  CHECK(l.sleep_s == 0);
  CHECK(parse_layout(R"({"v":1,"rev":"x","start":null,"sleep":3600,"blocks":[]})", l) == ParseError::NONE);
  CHECK(l.sleep_s == 3600);
}

TEST_CASE("strips U+FE0F from emoji text") {
  Layout l;
  const std::string json =
      "{\"v\":1,\"rev\":\"x\",\"start\":null,\"sleep\":20,\"blocks\":[{\"id\":\"b1\",\"x\":0,\"y\":0,\"name\":\"A\","
      "\"bg\":\"FFFFFF\",\"font\":\"m\",\"widget\":\"custom\",\"items\":[{\"id\":\"i1\",\"kind\":\"emoji\","
      "\"text\":\"\xE2\x9D\x84\xEF\xB8\x8F\",\"font\":\"xl\"}]}]}";
  REQUIRE(parse_layout(json, l) == ParseError::NONE);
  CHECK(l.blocks[0].items[0].text == "\xE2\x9D\x84");
}

TEST_CASE("parses the emoji-variation fixture") {
  Layout l;
  REQUIRE(parse_layout(json_field("payloads/valid/emoji-variation.json", "payload"), l) == ParseError::NONE);
  CHECK(l.sleep_s == 3600);
  CHECK(l.blocks[0].items[0].text == "\xE2\x9D\x84");
}

static ParseError expected_code(const std::string &s) {
  if (s == "bad_json")
    return ParseError::BAD_JSON;
  if (s == "unsupported_version")
    return ParseError::UNSUPPORTED_VERSION;
  if (s == "invalid_payload")
    return ParseError::INVALID_PAYLOAD;
  FAIL("unknown expectation " << s);
  return ParseError::NONE;
}

TEST_CASE("rejects every invalid payload fixture") {
  std::vector<std::string> names;
  const std::string dir = std::string(FIXTURES_DIR) + "/payloads/invalid";
  DIR *d = opendir(dir.c_str());
  REQUIRE(d != nullptr);
  while (dirent *e = readdir(d)) {
    std::string n = e->d_name;
    if (n.size() > 5 && n.substr(n.size() - 5) == ".json")
      names.push_back(n);
  }
  closedir(d);
  std::sort(names.begin(), names.end());
  REQUIRE(names.size() >= 6);
  for (const auto &n : names) {
    INFO(n);
    const std::string file = "payloads/invalid/" + n;
    Layout l;
    l.rev = "keep";
    l.start = "b9";
    l.sleep_s = 77;
    l.blocks.push_back(Block{});
    CHECK(parse_layout(json_string_field(file, "text"), l) == expected_code(json_string_field(file, "expect")));
    CHECK(l.rev == "keep");
    CHECK(l.start == "b9");
    CHECK(l.sleep_s == 77);
    CHECK(l.blocks.size() == 1);
  }
}

static std::string block(const std::string &fields) {
  return "{\"v\":1,\"rev\":\"x\",\"start\":null,\"sleep\":20,\"blocks\":[{" + fields + "}]}";
}
static const std::string OK_BLOCK =
    "\"id\":\"b1\",\"x\":0,\"y\":0,\"name\":\"A\",\"bg\":\"FFFFFF\",\"font\":\"m\",\"widget\":\"light\"";

TEST_CASE("accepts the baseline block used by the hostile cases") {
  Layout l;
  CHECK(parse_layout(block(OK_BLOCK), l) == ParseError::NONE);
}

TEST_CASE("rejects hostile payloads") {
  auto replace = [](std::string s, const std::string &from, const std::string &to) {
    auto p = s.find(from);
    REQUIRE(p != std::string::npos);
    return s.replace(p, from.size(), to);
  };
  std::vector<std::string> cases = {
      block(replace(OK_BLOCK, "\"x\":0", "\"x\":1e40")),
      block(replace(OK_BLOCK, "\"x\":0", "\"x\":\"1\"")),
      block(replace(OK_BLOCK, "\"x\":0", "\"x\":1.5")),
      block(replace(OK_BLOCK, "\"x\":0", "\"x\":3000000000")),
      block(replace(OK_BLOCK, "\"name\":\"A\"", "\"name\":5")),
      block(replace(OK_BLOCK, "\"widget\":\"light\"", "\"widget\":\"custom\"")),  // custom without items
      block(replace(OK_BLOCK, "\"font\":\"m\"", "\"font\":\"xxl\"")),
      block(replace(OK_BLOCK, "\"bg\":\"FFFFFF\"", "\"bg\":\"GGGGGG\"")),
      block(replace(OK_BLOCK, "\"bg\":\"FFFFFF\"", "\"bg\":\"#FFFFFF\"")),
      block(replace(OK_BLOCK, "\"widget\":\"light\"", "\"widget\":\"custom\",\"items\":[{\"id\":\"i\",\"kind\":\"text\",\"font\":\"m\"}]")),
      block(replace(OK_BLOCK, "\"widget\":\"light\"", "\"widget\":\"custom\",\"items\":[{\"id\":\"i\",\"kind\":\"gif\",\"font\":\"m\"}]")),
      R"({"v":1,"rev":"x","start":null,"sleep":-1,"blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"sleep":4000,"blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"sleep":1.5,"blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"sleep":"20","blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"sleep":20})",
      R"({"v":1,"rev":"x","sleep":20,"blocks":[]})",
      R"({"v":1,"rev":5,"start":null,"sleep":20,"blocks":[]})",
      R"({"v":1,"rev":"x","start":5,"sleep":20,"blocks":[]})",
      R"({"v":1,"rev":"x","start":null,"sleep":20,"blocks":{}})",
      R"({"v":1,"rev":"x","start":null,"sleep":20,"blocks":[5]})",
      "{\"v\":1,\"rev\":\"x\",\"start\":null,\"sleep\":20,\"blocks\":" + std::string(64, '[') + std::string(64, ']') + "}",
      std::string(64, '[') + std::string(64, ']'),
  };
  for (const auto &c : cases) {
    INFO(c);
    Layout l;
    l.rev = "keep";
    ParseError e = parse_layout(c, l);
    CHECK((e == ParseError::INVALID_PAYLOAD || e == ParseError::BAD_JSON));
    CHECK(l.rev == "keep");
  }
}

TEST_CASE("parse_error_code names") {
  CHECK(std::string(parse_error_code(ParseError::NONE)) == "none");
  CHECK(std::string(parse_error_code(ParseError::BAD_JSON)) == "bad_json");
  CHECK(std::string(parse_error_code(ParseError::UNSUPPORTED_VERSION)) == "unsupported_version");
  CHECK(std::string(parse_error_code(ParseError::INVALID_PAYLOAD)) == "invalid_payload");
}
