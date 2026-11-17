#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace esphome {
namespace ha_controller {

constexpr int PROTOCOL_VERSION = 1;

enum class FontSize : uint8_t { S, M, L, XL };
enum class Widget : uint8_t { LIGHT, CLIMATE, CUSTOM };
enum class ItemKind : uint8_t { TEXT, EMOJI, ENTITY, BATTERY, BRIGHTNESS };
enum class ParseError : uint8_t { NONE, BAD_JSON, UNSUPPORTED_VERSION, INVALID_PAYLOAD };

struct Item {
  std::string id;
  ItemKind kind{ItemKind::TEXT};
  FontSize font{FontSize::M};
  std::string text;
};

struct Block {
  std::string id;
  int x{0};
  int y{0};
  std::string name;
  uint32_t bg{0};
  FontSize font{FontSize::M};
  Widget widget{Widget::CUSTOM};
  std::vector<Item> items;
};

struct Layout {
  std::string rev;
  std::string start;  // "" when the payload has null
  uint32_t sleep_s{20};  // payload "sleep"; 0 = never
  std::vector<Block> blocks;

  const Block *find(const std::string &id) const;
  const Block *find_at(int x, int y) const;
};

// `out` is replaced only when NONE is returned.
ParseError parse_layout(const std::string &json, Layout &out);
const char *parse_error_code(ParseError e);

}  // namespace ha_controller
}  // namespace esphome
