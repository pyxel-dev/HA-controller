#pragma once
// Internal to the component: shared pieces of the block views (widgets.cpp builds them).
#include "color.h"
#include "hold.h"
#include "knob.h"
#include "widgets.h"

namespace esphome {
namespace ha_controller {

// Interactive controls stay inside this radius so they never touch the edge ring (spec 5.5).
constexpr int CONTROL_RADIUS = 185;
constexpr int KNOB_DIAMETER = 370;
constexpr int KNOB_WIDTH = 28;
constexpr int NAME_TOP = 96;

inline int font_index(FontSize f) { return static_cast<int>(f); }

// Full-screen page filled with the block background.
inline lv_obj_t *make_page_root(lv_obj_t *parent, const Block &block, const Theme &theme) {
  lv_obj_t *root = lv_obj_create(parent);
  lv_obj_remove_style_all(root);
  lv_obj_set_size(root, theme.size, theme.size);
  lv_obj_set_pos(root, 0, 0);
  lv_obj_remove_flag(root, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_bg_opa(root, LV_OPA_COVER, 0);
  lv_obj_set_style_bg_color(root, lv_color_hex(block.bg), 0);
  return root;
}

inline lv_obj_t *make_label(lv_obj_t *parent, const lv_font_t *font, uint32_t color, const char *text) {
  lv_obj_t *label = lv_label_create(parent);
  lv_obj_set_style_text_font(label, font, 0);
  lv_obj_set_style_text_color(label, lv_color_hex(color), 0);
  lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
  lv_label_set_text(label, text);
  return label;
}

// Places `left` and `right` side by side inside `row`, vertically centred, and sizes the row to fit.
void layout_row(lv_obj_t *row, lv_obj_t *left, lv_obj_t *right, int gap);

// Shared part of the light and climate pages: name, 270 degree arc knob, centre value and a small label.
// Subclasses decide what the arc means and how an update is drawn.
class KnobBlockView : public BlockView {
 public:
  void apply(const StateUpdate &u, uint32_t now_ms) override;
  void loop(uint32_t now_ms) override;

 protected:
  KnobBlockView(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink, bool tappable_centre);

  virtual void render_(const StateUpdate &u) = 0;
  virtual void on_arc_changed_(int value) = 0;   // drag in progress: update the centre label only
  virtual void on_arc_released_(int value) = 0;  // drag finished: send the value
  virtual void on_centre_tap_() {}

  void touch_();
  void set_disabled_(bool disabled);
  // Renders an update, then re-centres the value and sub labels (no flex layout in this LVGL build).
  void draw_(const StateUpdate &u);
  void layout_centre_();

  static void arc_event_(lv_event_t *e);
  static void centre_event_(lv_event_t *e);

  ControlSink &sink_;
  const Theme &theme_;
  uint32_t fg_;  // text colour for the block background
  uint32_t bg_;
  InteractionHold hold_;
  bool has_pending_{false};
  StateUpdate pending_;
  bool available_{false};
  lv_obj_t *arc_{nullptr};
  lv_obj_t *centre_{nullptr};
  lv_obj_t *value_label_{nullptr};
  lv_obj_t *sub_label_{nullptr};
};

std::unique_ptr<BlockView> make_light_view(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink);
std::unique_ptr<BlockView> make_climate_view(lv_obj_t *parent, const Block &block, const Theme &theme,
                                             ControlSink &sink);
std::unique_ptr<BlockView> make_custom_view(lv_obj_t *parent, const Block &block, const Theme &theme,
                                            const LocalSources &local);

}  // namespace ha_controller
}  // namespace esphome
