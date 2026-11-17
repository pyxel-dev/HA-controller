#pragma once
#include <cmath>
#include <cstdio>
#include <string>

namespace esphome {
namespace ha_controller {

// One decimal when step < 1, none otherwise.
inline std::string format_value(float value, float step) {
  char buf[32];
  std::snprintf(buf, sizeof buf, step < 1.0f ? "%.1f" : "%.0f", (double) value);
  return buf;
}

inline std::string format_percent(float pct) {
  if (std::isnan(pct))
    return "— %";
  char buf[32];
  std::snprintf(buf, sizeof buf, "%.0f %%", (double) pct);
  return buf;
}

}  // namespace ha_controller
}  // namespace esphome
