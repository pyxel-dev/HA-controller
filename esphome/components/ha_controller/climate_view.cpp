#include "views.h"

#include "format.h"

namespace esphome {
namespace ha_controller {

namespace {

const char *const DASH = "\xE2\x80\x94";
const char *const DEGREE = "\xC2\xB0";

// Arc over [min, max] in steps of `step`. The arc value is the step index, never the temperature.
class ClimateView final : public KnobBlockView {
 public:
  ClimateView(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink)
      : KnobBlockView(parent, block, theme, sink, false), scale_{7, 35, 0.5f} {
    StateUpdate none;
    none.id = block.id;
    none.available = false;
    this->draw_(none);
  }

 protected:
  void render_(const StateUpdate &u) override {
    this->scale_ = KnobScale{u.min, u.max, u.step};
    int steps = this->scale_.steps();
    this->available_ = u.available && u.target.has_value() && steps > 0;
    this->set_disabled_(!this->available_);
    lv_arc_set_range(this->arc_, 0, steps > 0 ? steps : 1);
    if (!this->available_) {
      lv_arc_set_value(this->arc_, 0);
      lv_label_set_text(this->value_label_, DASH);
      if (!u.available) {
        lv_label_set_text(this->sub_label_, "Unavailable");
        lv_obj_remove_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
      } else {
        this->show_sub_(u);
      }
      return;
    }
    lv_arc_set_value(this->arc_, this->scale_.index_of(*u.target));
    this->show_target_(this->scale_.value_at(this->scale_.index_of(*u.target)));
    this->show_sub_(u);
  }

  void on_arc_changed_(int value) override { this->show_target_(this->scale_.value_at(value)); }
  void on_arc_released_(int value) override {
    this->sink_.on_control(this->id_, "", "set", this->scale_.value_at(value));
  }

  void show_target_(float value) {
    std::string text = format_value(value, this->scale_.step) + DEGREE;
    lv_label_set_text(this->value_label_, text.c_str());
  }

  // "Now <current>" and the action on a second line.
  void show_sub_(const StateUpdate &u) {
    std::string text;
    if (!u.current.empty())
      text = "Now " + u.current;
    if (!u.action.empty())
      text += (text.empty() ? "" : "\n") + u.action;
    lv_label_set_text(this->sub_label_, text.c_str());
    if (text.empty())
      lv_obj_add_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
    else
      lv_obj_remove_flag(this->sub_label_, LV_OBJ_FLAG_HIDDEN);
  }

  KnobScale scale_;
};

}  // namespace

std::unique_ptr<BlockView> make_climate_view(lv_obj_t *parent, const Block &block, const Theme &theme,
                                             ControlSink &sink) {
  return std::make_unique<ClimateView>(parent, block, theme, sink);
}

}  // namespace ha_controller
}  // namespace esphome
