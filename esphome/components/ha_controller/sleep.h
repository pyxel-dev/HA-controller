#pragma once
#include <cstdint>

namespace esphome {
namespace ha_controller {

// Inactivity delay used until the first layout arrives.
constexpr uint32_t DEFAULT_SLEEP_S = 20;

// True when the screen must sleep. A timeout of 0 means never.
inline bool should_sleep(uint32_t inactive_ms, uint32_t timeout_s) {
  if (timeout_s == 0)
    return false;
  return (uint64_t) inactive_ms >= (uint64_t) timeout_s * 1000u;
}

}  // namespace ha_controller
}  // namespace esphome
