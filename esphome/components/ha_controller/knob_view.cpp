#include "views.h"

#include <algorithm>

#include "esphome/core/hal.h"

namespace esphome {
namespace ha_controller {

KnobBlockView::KnobBlockView(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink,
                             bool tappable_centre)
    : sink_(sink), theme_(theme), fg_(text_color_for(block.bg)), bg_(block.bg) {
  this->id_ = block.id;
  this->root_ = make_page_root(parent, block, theme);
  const int f = font_index(block.font);

  lv_obj_t *name = make_label(this->root_, theme.text[f], this->fg_, block.name.c_str());
  lv_obj_set_width(name, 180);
  lv_label_set_long_mode(name, LV_LABEL_LONG_MODE_DOTS);
  lv_obj_align(name, LV_ALIGN_TOP_MID, 0, NAME_TOP);

  // Centre first (below the arc) so the ring always wins the touches it covers.
  this->centre_ = lv_obj_create(this->root_);
  lv_obj_remove_style_all(this->centre_);
  lv_obj_set_size(this->centre_, 290, 290);
  lv_obj_align(this->centre_, LV_ALIGN_CENTER, 0, 0);
  lv_obj_remove_flag(this->centre_, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_radius(this->centre_, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_pad_all(this->centre_, 0, 0);
  if (tappable_centre) {
    lv_obj_add_flag(this->centre_, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_flag(this->centre_, LV_OBJ_FLAG_ADV_HITTEST);
    lv_obj_add_event_cb(this->centre_, KnobBlockView::centre_event_, LV_EVENT_CLICKED, this);
  } else {
    lv_obj_remove_flag(this->centre_, LV_OBJ_FLAG_CLICKABLE);
  }
  lv_obj_set_style_opa(this->centre_, LV_OPA_40, LV_STATE_DISABLED);

  this->value_label_ = make_label(this->centre_, theme.value[f], this->fg_, "\xE2\x80\x94");
  this->sub_label_ = make_label(this->centre_, theme.text[font_index(FontSize::S)], this->fg_, "");
  lv_obj_set_width(this->sub_label_, 240);
  lv_obj_add_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);

  this->arc_ = lv_arc_create(this->root_);
  lv_obj_set_size(this->arc_, KNOB_DIAMETER, KNOB_DIAMETER);
  lv_obj_align(this->arc_, LV_ALIGN_CENTER, 0, 0);
  lv_arc_set_rotation(this->arc_, 0);
  lv_arc_set_bg_angles(this->arc_, 135, 45);
  lv_arc_set_range(this->arc_, 0, 100);
  lv_arc_set_value(this->arc_, 0);
  lv_obj_add_flag(this->arc_, LV_OBJ_FLAG_ADV_HITTEST);
  lv_obj_set_style_arc_width(this->arc_, KNOB_WIDTH, LV_PART_MAIN);
  lv_obj_set_style_arc_width(this->arc_, KNOB_WIDTH, LV_PART_INDICATOR);
  lv_obj_set_style_arc_color(this->arc_, lv_color_hex(this->fg_), LV_PART_MAIN);
  lv_obj_set_style_arc_opa(this->arc_, LV_OPA_30, LV_PART_MAIN);
  lv_obj_set_style_arc_color(this->arc_, lv_color_hex(this->fg_), LV_PART_INDICATOR);
  lv_obj_set_style_arc_opa(this->arc_, LV_OPA_COVER, LV_PART_INDICATOR);
  lv_obj_set_style_bg_color(this->arc_, lv_color_hex(this->fg_), LV_PART_KNOB);
  lv_obj_set_style_bg_opa(this->arc_, LV_OPA_COVER, LV_PART_KNOB);
  lv_obj_set_style_pad_all(this->arc_, 0, LV_PART_KNOB);
  lv_obj_set_style_opa(this->arc_, LV_OPA_40, LV_STATE_DISABLED);
  lv_obj_add_event_cb(this->arc_, KnobBlockView::arc_event_, LV_EVENT_ALL, this);
}

void layout_row(lv_obj_t *row, lv_obj_t *left, lv_obj_t *right, int gap) {
  lv_obj_update_layout(left);
  lv_obj_update_layout(right);
  int h = std::max(lv_obj_get_height(left), lv_obj_get_height(right));
  lv_obj_set_size(row, lv_obj_get_width(left) + gap + lv_obj_get_width(right), h);
  lv_obj_align(left, LV_ALIGN_LEFT_MID, 0, 0);
  lv_obj_align(right, LV_ALIGN_RIGHT_MID, 0, 0);
}

void KnobBlockView::draw_(const StateUpdate &u) {
  this->render_(u);
  this->layout_centre_();
}

// Value label with the optional small label below it, as a block centred in the centre object.
void KnobBlockView::layout_centre_() {
  lv_obj_update_layout(this->centre_);
  const int gap = 4;
  int hv = lv_obj_get_height(this->value_label_);
  bool has_sub = !lv_obj_has_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
  int hs = has_sub ? lv_obj_get_height(this->sub_label_) : 0;
  int total = hv + (has_sub ? gap + hs : 0);
  lv_obj_align(this->value_label_, LV_ALIGN_CENTER, 0, -total / 2 + hv / 2);
  if (has_sub)
    lv_obj_align(this->sub_label_, LV_ALIGN_CENTER, 0, total / 2 - hs / 2);
}

void KnobBlockView::touch_() { this->hold_.touch(millis()); }

void KnobBlockView::set_disabled_(bool disabled) {
  lv_obj_t *targets[2] = {this->arc_, this->centre_};
  for (lv_obj_t *o : targets) {
    if (disabled)
      lv_obj_add_state(o, LV_STATE_DISABLED);
    else
      lv_obj_remove_state(o, LV_STATE_DISABLED);
  }
}

void KnobBlockView::arc_event_(lv_event_t *e) {
  if (lv_event_get_code(e) == LV_EVENT_DELETE)
    return;
  auto *self = static_cast<KnobBlockView *>(lv_event_get_user_data(e));
  if (!self->available_)
    return;
  lv_obj_t *arc = static_cast<lv_obj_t *>(lv_event_get_target(e));
  switch (lv_event_get_code(e)) {
    case LV_EVENT_PRESSED:
      self->touch_();
      break;
    case LV_EVENT_VALUE_CHANGED:
      self->touch_();
      self->on_arc_changed_(lv_arc_get_value(arc));
      break;
    case LV_EVENT_RELEASED:
      self->touch_();
      self->on_arc_released_(lv_arc_get_value(arc));
      break;
    default:
      break;
  }
}

void KnobBlockView::centre_event_(lv_event_t *e) {
  auto *self = static_cast<KnobBlockView *>(lv_event_get_user_data(e));
  if (!self->available_)
    return;
  self->touch_();
  self->on_centre_tap_();
}

// While the hold is active the latest update waits; loop() applies it once the hold has expired.
void KnobBlockView::apply(const StateUpdate &u, uint32_t now_ms) {
  if (this->hold_.active(now_ms)) {
    this->pending_ = u;
    this->has_pending_ = true;
    return;
  }
  this->has_pending_ = false;
  this->draw_(u);
}

void KnobBlockView::loop(uint32_t now_ms) {
  if (this->has_pending_ && !this->hold_.active(now_ms) && !lv_obj_has_state(this->arc_, LV_STATE_PRESSED)) {
    this->has_pending_ = false;
    this->draw_(this->pending_);
  }
}

}  // namespace ha_controller
}  // namespace esphome
