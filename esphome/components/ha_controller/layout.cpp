#include "layout.h"

#include <ArduinoJson.h>

#include <limits>

#include "color.h"

namespace esphome {
namespace ha_controller {

const Block *Layout::find(const std::string &id) const {
  for (const auto &b : this->blocks)
    if (b.id == id)
      return &b;
  return nullptr;
}

const Block *Layout::find_at(int x, int y) const {
  for (const auto &b : this->blocks)
    if (b.x == x && b.y == y)
      return &b;
  return nullptr;
}

const char *parse_error_code(ParseError e) {
  switch (e) {
    case ParseError::NONE:
      return "none";
    case ParseError::BAD_JSON:
      return "bad_json";
    case ParseError::UNSUPPORTED_VERSION:
      return "unsupported_version";
    case ParseError::INVALID_PAYLOAD:
      return "invalid_payload";
  }
  return "invalid_payload";
}

namespace {

bool has_key(JsonVariantConst obj, const char *key) {
  for (JsonPairConst kv : obj.as<JsonObjectConst>())
    if (kv.key() == key)
      return true;
  return false;
}

bool get_string(JsonVariantConst obj, const char *key, std::string &out) {
  JsonVariantConst v = obj[key];
  if (!v.is<const char *>())
    return false;
  out = v.as<const char *>();
  return true;
}

bool get_int(JsonVariantConst obj, const char *key, int &out) {
  JsonVariantConst v = obj[key];
  if (!v.is<int>())
    return false;
  out = v.as<int>();
  return true;
}

bool parse_font(JsonVariantConst obj, FontSize &out) {
  std::string s;
  if (!get_string(obj, "font", s))
    return false;
  if (s == "s")
    out = FontSize::S;
  else if (s == "m")
    out = FontSize::M;
  else if (s == "l")
    out = FontSize::L;
  else if (s == "xl")
    out = FontSize::XL;
  else
    return false;
  return true;
}

// Removes every U+FE0F (UTF-8 EF B8 8F).
std::string strip_variation_selector(const std::string &s) {
  std::string out;
  out.reserve(s.size());
  for (size_t i = 0; i < s.size(); i++) {
    if (i + 2 < s.size() && static_cast<uint8_t>(s[i]) == 0xEF && static_cast<uint8_t>(s[i + 1]) == 0xB8 &&
        static_cast<uint8_t>(s[i + 2]) == 0x8F) {
      i += 2;
      continue;
    }
    out += s[i];
  }
  return out;
}

bool parse_item(JsonVariantConst j, Item &item) {
  if (!j.is<JsonObjectConst>())
    return false;
  std::string kind;
  if (!get_string(j, "id", item.id) || !get_string(j, "kind", kind) || !parse_font(j, item.font))
    return false;
  if (kind == "text")
    item.kind = ItemKind::TEXT;
  else if (kind == "emoji")
    item.kind = ItemKind::EMOJI;
  else if (kind == "entity")
    item.kind = ItemKind::ENTITY;
  else if (kind == "battery")
    item.kind = ItemKind::BATTERY;
  else if (kind == "brightness")
    item.kind = ItemKind::BRIGHTNESS;
  else
    return false;
  if (item.kind == ItemKind::TEXT || item.kind == ItemKind::EMOJI) {
    if (!get_string(j, "text", item.text))
      return false;
    if (item.kind == ItemKind::EMOJI)
      item.text = strip_variation_selector(item.text);
  }
  return true;
}

bool parse_block(JsonVariantConst j, Block &b) {
  if (!j.is<JsonObjectConst>())
    return false;
  std::string bg, widget;
  if (!get_string(j, "id", b.id) || !get_int(j, "x", b.x) || !get_int(j, "y", b.y) || !get_string(j, "name", b.name) ||
      !get_string(j, "bg", bg) || !parse_font(j, b.font) || !get_string(j, "widget", widget))
    return false;
  if (bg.size() != 6 || !parse_hex_rgb(bg, b.bg))
    return false;
  if (widget == "light")
    b.widget = Widget::LIGHT;
  else if (widget == "climate")
    b.widget = Widget::CLIMATE;
  else if (widget == "custom")
    b.widget = Widget::CUSTOM;
  else
    return false;
  if (b.widget == Widget::CUSTOM) {
    JsonVariantConst items = j["items"];
    if (!items.is<JsonArrayConst>())
      return false;
    for (JsonVariantConst ij : items.as<JsonArrayConst>()) {
      Item item;
      if (!parse_item(ij, item))
        return false;
      b.items.push_back(std::move(item));
    }
  }
  return true;
}

}  // namespace

ParseError parse_layout(const std::string &json, Layout &out) {
  JsonDocument doc;
  if (deserializeJson(doc, json) || !doc.is<JsonObject>())
    return ParseError::BAD_JSON;
  JsonVariantConst root = doc.as<JsonVariantConst>();

  int v = 0;
  if (!get_int(root, "v", v) || v != PROTOCOL_VERSION)
    return ParseError::UNSUPPORTED_VERSION;

  Layout l;
  JsonVariantConst start = root["start"];
  int sleep = 0;
  if (!get_string(root, "rev", l.rev) || !get_int(root, "sleep", sleep) || sleep < 0 || sleep > 3600)
    return ParseError::INVALID_PAYLOAD;
  l.sleep_s = static_cast<uint32_t>(sleep);
  if (start.is<const char *>())
    l.start = start.as<const char *>();
  else if (!start.isNull() || !has_key(root, "start"))
    return ParseError::INVALID_PAYLOAD;

  JsonVariantConst blocks = root["blocks"];
  if (!blocks.is<JsonArrayConst>())
    return ParseError::INVALID_PAYLOAD;
  for (JsonVariantConst bj : blocks.as<JsonArrayConst>()) {
    Block b;
    if (!parse_block(bj, b))
      return ParseError::INVALID_PAYLOAD;
    l.blocks.push_back(std::move(b));
  }
  out = std::move(l);
  return ParseError::NONE;
}

}  // namespace ha_controller
}  // namespace esphome
