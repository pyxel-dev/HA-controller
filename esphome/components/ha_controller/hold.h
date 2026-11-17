#pragma once
#include <cstdint>

namespace esphome {
namespace ha_controller {

// Ignores incoming state for window_ms after the last local touch.
class InteractionHold {
 public:
  explicit InteractionHold(uint32_t window_ms = 1500) : window_ms_(window_ms) {}
  void touch(uint32_t now_ms) {
    last_ = now_ms;
    touched_ = true;
  }
  bool active(uint32_t now_ms) const { return touched_ && (uint32_t) (now_ms - last_) < window_ms_; }

 private:
  uint32_t window_ms_;
  uint32_t last_{0};
  bool touched_{false};
};

}  // namespace ha_controller
}  // namespace esphome
