#pragma once
#include <cmath>

namespace esphome {
namespace ha_controller {

struct KnobScale {
  float min, max, step;

  int steps() const {
    if (max <= min)
      return 0;
    float s = step > 0 ? step : 1.0f;
    return (int) std::lround((max - min) / s);
  }
  int index_of(float value) const {
    float s = step > 0 ? step : 1.0f;
    int i = (int) std::lround((value - min) / s);
    int n = steps();
    return i < 0 ? 0 : (i > n ? n : i);
  }
  float value_at(int index) const {
    float s = step > 0 ? step : 1.0f;
    float v = min + (float) index * s;
    return v < min ? min : (v > max ? max : v);
  }
};

}  // namespace ha_controller
}  // namespace esphome
