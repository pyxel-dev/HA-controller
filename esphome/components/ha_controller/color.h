#pragma once
#include <cmath>
#include <cstdint>
#include <string>

namespace esphome {
namespace ha_controller {

// Parses "RRGGBB" or "#RRGGBB" (either case). `out` is untouched on failure.
inline bool parse_hex_rgb(const std::string &hex, uint32_t &out) {
  size_t start = (!hex.empty() && hex[0] == '#') ? 1 : 0;
  if (hex.size() - start != 6)
    return false;
  uint32_t v = 0;
  for (size_t i = start; i < hex.size(); i++) {
    char c = hex[i];
    uint32_t d;
    if (c >= '0' && c <= '9')
      d = c - '0';
    else if (c >= 'a' && c <= 'f')
      d = c - 'a' + 10;
    else if (c >= 'A' && c <= 'F')
      d = c - 'A' + 10;
    else
      return false;
    v = (v << 4) | d;
  }
  out = v;
  return true;
}

// WCAG 2.x relative luminance of an 0xRRGGBB colour.
inline float relative_luminance(uint32_t rgb) {
  auto lin = [](uint32_t c8) {
    float c = c8 / 255.0f;
    return c <= 0.03928f ? c / 12.92f : std::pow((c + 0.055f) / 1.055f, 2.4f);
  };
  return 0.2126f * lin((rgb >> 16) & 0xFF) + 0.7152f * lin((rgb >> 8) & 0xFF) + 0.0722f * lin(rgb & 0xFF);
}

inline uint32_t text_color_for(uint32_t rgb) { return relative_luminance(rgb) > 0.30f ? 0x000000 : 0xFFFFFF; }

}  // namespace ha_controller
}  // namespace esphome
