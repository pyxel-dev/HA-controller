#pragma once
// Pure geometry for the custom block: vertical stack of items kept inside the safe circles.
#include <algorithm>
#include <cmath>
#include <vector>

namespace esphome {
namespace ha_controller {

struct StackItem {
  int height;
  int half_width;
  bool interactive;  // must stay inside the control radius; other items only inside the visible circle
};

struct StackLayout {
  std::vector<int> top;  // top edge of each item, relative to the screen centre
  int gap{0};
  bool fits{false};
};

// Half of the chord of a circle of `radius` at horizontal half extent `half_width`.
inline int chord_limit(int radius, int half_width) {
  double v = (double) radius * radius - (double) half_width * half_width;
  return v > 0 ? (int) std::floor(std::sqrt(v)) : 0;
}

// Centres the stack. If an item leaves its circle, the gap shrinks 8 -> 4 -> 0 px; if it still does not fit,
// the whole stack shifts as little as possible. `fits` is false when no shift can satisfy every item.
inline StackLayout layout_stack(const std::vector<StackItem> &items, int control_radius = 185,
                                int visible_radius = 233) {
  StackLayout out;
  const int n = (int) items.size();
  out.top.assign(n, 0);
  if (n == 0) {
    out.fits = true;
    return out;
  }
  int sum = 0;
  for (const auto &it : items)
    sum += it.height;
  const int gaps[3] = {8, 4, 0};
  int lo = 0, hi = 0;
  for (int gi = 0; gi < 3; gi++) {
    int gap = gaps[gi];
    int y = -(sum + gap * (n - 1)) / 2;
    lo = -100000;
    hi = 100000;
    for (int i = 0; i < n; i++) {
      out.top[i] = y;
      int lim = chord_limit(items[i].interactive ? control_radius : visible_radius, items[i].half_width);
      lo = std::max(lo, -lim - y);
      hi = std::min(hi, lim - (y + items[i].height));
      y += items[i].height + gap;
    }
    out.gap = gap;
    if (lo <= 0 && hi >= 0) {
      out.fits = true;
      return out;
    }
  }
  int shift = 0;
  if (lo <= hi) {
    shift = lo > 0 ? lo : (hi < 0 ? hi : 0);
    out.fits = true;
  } else {
    shift = (lo + hi) / 2;
  }
  for (auto &t : out.top)
    t += shift;
  return out;
}

}  // namespace ha_controller
}  // namespace esphome
