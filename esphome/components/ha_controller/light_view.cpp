#include "views.h"

#include <cstdio>

namespace esphome {
namespace ha_controller {

namespace {

const char *const DASH = "\xE2\x80\x94";

// Dimmable light: arc 0-100 with the percentage in the centre. On/off-only light: the centre becomes a
// 220 px round toggle button. Tapping the centre toggles in both cases.
class LightView final : public KnobBlockView {
 public:
  LightView(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink)
      : KnobBlockView(parent, block, theme, sink, true) {
    StateUpdate none;
    none.id = block.id;
    none.available = false;
    this->draw_(none);
  }

 protected:
  void render_(const StateUpdate &u) override {
    this->available_ = u.available;
    if (u.available)
      this->dimmable_ = u.brightness.has_value();
    this->apply_mode_();
    this->set_disabled_(!u.available);
    if (!u.available) {
      if (!this->dimmable_)
        this->style_toggle_(false);
      lv_label_set_text(this->value_label_, DASH);
      lv_label_set_text(this->sub_label_, "Unavailable");
      lv_obj_remove_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
      lv_arc_set_value(this->arc_, 0);
      return;
    }
    lv_obj_add_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
    if (this->dimmable_) {
      int b = *u.brightness;
      b = b < 0 ? 0 : (b > 100 ? 100 : b);
      bool on = u.on.value_or(b > 0) && b > 0;
      this->on_ = on;
      if (b > 0)
        this->last_brightness_ = b;
      lv_arc_set_value(this->arc_, on ? b : 0);
      this->show_percent_(on ? b : 0);
    } else {
      this->on_ = u.on.value_or(false);
      this->style_toggle_(this->on_);
    }
  }

  void on_arc_changed_(int value) override { this->show_percent_(value); }
  void on_arc_released_(int value) override { this->sink_.on_control(this->id_, "", "set", (float) value); }
  // Local feedback right away; the hold only defers incoming states.
  void on_centre_tap_() override {
    this->sink_.on_control(this->id_, "", "toggle", 0);
    this->on_ = !this->on_;
    if (this->dimmable_) {
      int b = this->on_ ? (this->last_brightness_ > 0 ? this->last_brightness_ : 100) : 0;
      lv_arc_set_value(this->arc_, b);
      this->show_percent_(b);
    } else {
      this->style_toggle_(this->on_);
    }
    this->layout_centre_();
  }

  void show_percent_(int value) {
    if (value <= 0) {
      lv_label_set_text(this->value_label_, "Off");
      return;
    }
    char buf[16];
    std::snprintf(buf, sizeof buf, "%d%%", value);
    lv_label_set_text(this->value_label_, buf);
  }

  // Dimmable: transparent 290 px centre and visible arc. On/off-only: filled 220 px button, no arc.
  void apply_mode_() {
    if (this->dimmable_) {
      lv_obj_remove_flag(this->arc_, LV_OBJ_FLAG_HIDDEN);
      lv_obj_set_size(this->centre_, 290, 290);
      lv_obj_set_style_bg_opa(this->centre_, LV_OPA_TRANSP, 0);
      lv_obj_set_style_text_color(this->value_label_, lv_color_hex(this->fg_), 0);
      lv_obj_set_style_text_color(this->sub_label_, lv_color_hex(this->fg_), 0);
    } else {
      lv_obj_add_flag(this->arc_, LV_OBJ_FLAG_HIDDEN);
      lv_obj_set_size(this->centre_, 220, 220);
    }
  }

  void style_toggle_(bool on) {
    lv_obj_set_style_bg_color(this->centre_, lv_color_hex(this->fg_), 0);
    lv_obj_set_style_bg_opa(this->centre_, on ? LV_OPA_COVER : LV_OPA_20, 0);
    uint32_t label_color = on ? this->bg_ : this->fg_;
    lv_obj_set_style_text_color(this->value_label_, lv_color_hex(label_color), 0);
    lv_obj_set_style_text_color(this->sub_label_, lv_color_hex(label_color), 0);
    lv_label_set_text(this->value_label_, on ? "On" : "Off");
  }

  bool dimmable_{true};
  bool on_{false};
  int last_brightness_{0};
};

}  // namespace

std::unique_ptr<BlockView> make_light_view(lv_obj_t *parent, const Block &block, const Theme &theme,
                                           ControlSink &sink) {
  return std::make_unique<LightView>(parent, block, theme, sink);
}

}  // namespace ha_controller
}  // namespace esphome
