#include "gesture.h"

namespace esphome {
namespace ha_controller {

Edge classify_edge(int x, int y, int size, int edge_width) {
  const float centre = size / 2.0f;
  const float dx = x - centre;
  const float dy = y - centre;
  const float inner = size / 2.0f - edge_width;
  if (inner > 0 && dx * dx + dy * dy < inner * inner) {
    return Edge::NONE;
  }
  const float abs_dx = dx < 0 ? -dx : dx;
  const float abs_dy = dy < 0 ? -dy : dy;
  if (abs_dx >= abs_dy) {
    return dx < 0 ? Edge::LEFT : Edge::RIGHT;
  }
  return dy < 0 ? Edge::TOP : Edge::BOTTOM;
}

GridStep step_for(Edge edge) {
  switch (edge) {
    case Edge::RIGHT:
      return {1, 0};
    case Edge::LEFT:
      return {-1, 0};
    case Edge::TOP:
      return {0, -1};
    case Edge::BOTTOM:
      return {0, 1};
    case Edge::NONE:
    default:
      return {0, 0};
  }
}

SwipeTracker::SwipeTracker(SwipeConfig cfg) : cfg_(cfg) {}

void SwipeTracker::begin(Edge edge, bool has_target, int x, int y, uint32_t t_ms) {
  edge_ = edge;
  has_target_ = has_target;
  start_x_ = x;
  start_y_ = y;
  raw_ = 0;
  visual_ = 0;
  sample_count_ = 0;
  active_ = edge != Edge::NONE;
  if (active_) {
    push_sample(t_ms, 0);
  }
}

int SwipeTracker::update(int x, int y, uint32_t t_ms) {
  if (!active_) {
    return 0;
  }
  // Progress is movement towards the centre along the navigation axis; outward movement counts as zero.
  const GridStep step = step_for(edge_);
  int moved = -(step.dx * (x - start_x_) + step.dy * (y - start_y_));
  if (moved < 0) {
    moved = 0;
  }
  if (moved > cfg_.size) {
    moved = cfg_.size;
  }
  raw_ = moved;
  if (has_target_) {
    visual_ = raw_;
  } else {
    // No block in that direction: rubber band, capped.
    const int banded = static_cast<int>(raw_ * cfg_.rubber_factor + 0.5f);
    visual_ = banded < cfg_.rubber_max_px ? banded : cfg_.rubber_max_px;
  }
  push_sample(t_ms, raw_);
  return visual_;
}

bool SwipeTracker::release(uint32_t t_ms) {
  if (!active_) {
    return false;
  }
  bool commit = false;
  if (has_target_) {
    const bool far_enough = raw_ >= cfg_.commit_ratio * cfg_.size;
    const bool flick = velocity_at(t_ms) >= cfg_.flick_velocity && raw_ >= cfg_.flick_min_px;
    commit = far_enough || flick;
  }
  active_ = false;
  return commit;
}

void SwipeTracker::reset() {
  active_ = false;
  raw_ = 0;
  visual_ = 0;
  sample_count_ = 0;
}

void SwipeTracker::push_sample(uint32_t t_ms, int raw) {
  if (sample_count_ == kMaxSamples) {
    for (int i = 1; i < kMaxSamples; ++i) {
      samples_[i - 1] = samples_[i];
    }
    sample_count_ = kMaxSamples - 1;
  }
  samples_[sample_count_++] = Sample{t_ms, raw};
}

// Velocity in px per ms between the oldest sample inside the window and the latest sample.
float SwipeTracker::velocity_at(uint32_t t_ms) const {
  if (sample_count_ == 0) {
    return 0.0f;
  }
  const Sample &latest = samples_[sample_count_ - 1];
  for (int i = 0; i < sample_count_; ++i) {
    const uint32_t age = t_ms - samples_[i].t_ms;  // unsigned: survives millis() wraparound
    if (age <= cfg_.velocity_window_ms) {
      const uint32_t dt = t_ms - samples_[i].t_ms;
      if (dt == 0) {
        return 0.0f;
      }
      return static_cast<float>(latest.raw - samples_[i].raw) / static_cast<float>(dt);
    }
  }
  return 0.0f;
}

uint32_t settle_duration_ms(int remaining_px, int size) {
  if (remaining_px < 0) {
    remaining_px = 0;
  }
  if (size <= 0) {
    return 220;
  }
  const uint32_t scaled = 220u * static_cast<uint32_t>(remaining_px) / static_cast<uint32_t>(size);
  if (scaled < 80u) {
    return 80u;
  }
  if (scaled > 220u) {
    return 220u;
  }
  return scaled;
}

}  // namespace ha_controller
}  // namespace esphome
