#pragma once
#include <cstdint>

namespace esphome {
namespace ha_controller {

// Edge-swipe gesture model (spec 5.2-5.3). Pure logic, no ESPHome or LVGL.
enum class Edge : uint8_t { NONE, LEFT, RIGHT, TOP, BOTTOM };

struct GridStep {
  int dx;
  int dy;
};

// Classifies a touch point in a size x size screen. Only points in the outer ring
// (distance from centre >= size/2 - edge_width) belong to an edge. The dominant axis wins.
Edge classify_edge(int x, int y, int size, int edge_width);

// Grid direction of the block reached by swiping from the given edge towards the centre.
GridStep step_for(Edge edge);

struct SwipeConfig {
  int size = 466;
  float commit_ratio = 0.25f;
  float flick_velocity = 0.6f;  // px per ms
  int flick_min_px = 24;
  float rubber_factor = 0.3f;
  int rubber_max_px = 48;
  uint32_t velocity_window_ms = 100;
};

class SwipeTracker {
 public:
  explicit SwipeTracker(SwipeConfig cfg = {});

  // Starts a swipe. has_target is false when no block exists in that direction (rubber band only).
  void begin(Edge edge, bool has_target, int x, int y, uint32_t t_ms);
  // Returns the visual offset (px) along the navigation axis.
  int update(int x, int y, uint32_t t_ms);
  // True = commit the navigation. The tracker becomes inactive either way.
  bool release(uint32_t t_ms);
  // Aborts the swipe without a decision.
  void reset();

  bool active() const { return active_; }
  Edge edge() const { return edge_; }
  // Last visual offset (px), as returned by update().
  int progress() const { return visual_; }

 private:
  struct Sample {
    uint32_t t_ms;
    int raw;
  };
  static constexpr int kMaxSamples = 16;

  void push_sample(uint32_t t_ms, int raw);
  float velocity_at(uint32_t t_ms) const;

  SwipeConfig cfg_;
  bool active_{false};
  bool has_target_{false};
  Edge edge_{Edge::NONE};
  int start_x_{0};
  int start_y_{0};
  int raw_{0};
  int visual_{0};
  Sample samples_[kMaxSamples]{};
  int sample_count_{0};
};

// Settle animation length: clamp(220 * remaining / size, 80, 220) ms.
uint32_t settle_duration_ms(int remaining_px, int size);

}  // namespace ha_controller
}  // namespace esphome
