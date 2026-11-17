#pragma once
#include <lvgl.h>

#include <string>
#include <vector>

#include "gesture.h"

namespace esphome {
namespace ha_controller {

struct PageRef {
  std::string id;
  int x;
  int y;
  lv_obj_t *obj;
};

// Edge-swipe navigation between pages placed on a grid (spec 5.1-5.4). Every method runs on the main loop.
class Pager {
 public:
  // Creates the viewport (under `screen`), the edge overlay and the four hint arcs (on lv_layer_top()).
  void attach(lv_obj_t *screen, int size, int edge_width);
  lv_obj_t *viewport() const { return this->viewport_; }
  // Replaces the pages. Cancels animations, resets the tracker and shows one page (show_id, else the first).
  void set_pages(std::vector<PageRef> pages, const std::string &show_id);
  // False while a message is shown: swipes and hints are off.
  void set_enabled(bool enabled);
  const std::string &current_id() const { return this->current_id_; }

 protected:
  static void on_edge_event_(lv_event_t *e);
  static void anim_exec_(void *var, int32_t value);
  static void anim_done_(lv_anim_t *a);

  void on_pressed_();
  void on_pressing_();
  void on_released_();
  const PageRef *page_at_(int x, int y) const;
  const PageRef *current_page_() const;
  void place_(int offset);
  void finish_(bool commit);
  void abort_swipe_();
  void refresh_hints_();

  lv_obj_t *viewport_{nullptr};
  lv_obj_t *edge_{nullptr};
  lv_obj_t *hints_[4]{};  // RIGHT, BOTTOM, LEFT, TOP
  int size_{466};
  int edge_width_{36};
  bool enabled_{true};
  bool animating_{false};
  bool anim_commit_{false};
  int dx_{0};
  int dy_{0};
  std::vector<PageRef> pages_;
  std::string current_id_;
  int current_idx_{-1};
  int target_idx_{-1};
  SwipeTracker tracker_;
};

}  // namespace ha_controller
}  // namespace esphome
