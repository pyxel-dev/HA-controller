#include "views.h"

#include "esphome/core/hal.h"
#include "format.h"

namespace esphome {
namespace ha_controller {

namespace {

constexpr int ITEM_GAP = 8;
constexpr int COLUMN_WIDTH = 320;
constexpr int SLIDER_WIDTH = 220;
constexpr uint32_t BRIGHTNESS_THROTTLE_MS = 100;

const char *const DASH = "\xE2\x80\x94";

// Items stacked vertically and centred. Entity text arrives through apply(); battery and brightness follow
// the local sources through on_local_update().
class CustomView final : public BlockView {
 public:
  CustomView(lv_obj_t *parent, const Block &block, const Theme &theme, const LocalSources &local)
      : local_(local), fg_(text_color_for(block.bg)) {
    this->id_ = block.id;
    this->root_ = make_page_root(parent, block, theme);

    if (block.items.empty()) {
      lv_obj_t *name = make_label(this->root_, theme.text[font_index(block.font)], this->fg_, block.name.c_str());
      lv_obj_set_width(name, theme.size * 7 / 10);
      lv_obj_center(name);
      return;
    }

    for (const auto &item : block.items)
      this->add_item_(this->root_, item, theme);
    this->on_local_update();
    this->layout_items_();
  }

  bool owns(const std::string &id) const override {
    if (id == this->id_)
      return true;
    for (const auto &e : this->entities_) {
      if (e.id == id)
        return true;
    }
    return false;
  }

  void apply(const StateUpdate &u, uint32_t) override {
    for (const auto &e : this->entities_) {
      if (e.id == u.id && u.text.has_value())
        lv_label_set_text(e.label, u.text->c_str());
    }
    this->layout_items_();
  }

  void on_local_update() override {
    if (this->battery_label_ != nullptr) {
      float level = this->local_.battery != nullptr ? this->local_.battery->state : NAN;
      bool charging = this->local_.charging != nullptr && this->local_.charging->has_state() &&
                      this->local_.charging->state;
      lv_label_set_text(this->battery_icon_, charging ? "\xE2\x9A\xA1" : "\xF0\x9F\x94\x8B");
      lv_label_set_text(this->battery_label_, format_percent(level).c_str());
    }
    if (this->slider_ != nullptr && this->local_.brightness != nullptr && this->local_.brightness->has_state() &&
        !lv_slider_is_dragged(this->slider_)) {
      lv_slider_set_value(this->slider_, (int) lroundf(this->local_.brightness->state), LV_ANIM_OFF);
    }
    this->layout_items_();
  }

 protected:
  struct Entity {
    std::string id;
    lv_obj_t *label;
  };

  // Stacks the items vertically, centred as a block with an 8 px gap.
  void layout_items_() {
    if (this->stack_.empty())
      return;
    for (auto &row : this->rows_)
      layout_row(row.row, row.left, row.right, row.gap);
    int total = ITEM_GAP * ((int) this->stack_.size() - 1);
    for (lv_obj_t *o : this->stack_) {
      lv_obj_update_layout(o);
      total += lv_obj_get_height(o);
    }
    int y = (lv_obj_get_height(this->root_) - total) / 2;
    for (lv_obj_t *o : this->stack_) {
      lv_obj_align(o, LV_ALIGN_TOP_MID, 0, y);
      y += lv_obj_get_height(o) + ITEM_GAP;
    }
  }

  void add_item_(lv_obj_t *parent, const Item &item, const Theme &theme) {
    const int f = font_index(item.font);
    switch (item.kind) {
      case ItemKind::TEXT:
      case ItemKind::EMOJI: {
        const lv_font_t *font = item.kind == ItemKind::TEXT ? theme.text[f] : theme.emoji[f];
        lv_obj_t *label = make_label(parent, font, this->fg_, item.text.c_str());
        lv_obj_set_width(label, COLUMN_WIDTH);
        this->stack_.push_back(label);
        break;
      }
      case ItemKind::ENTITY: {
        lv_obj_t *label = make_label(parent, theme.text[f], this->fg_, DASH);
        lv_obj_set_width(label, COLUMN_WIDTH);
        this->entities_.push_back({item.id, label});
        this->stack_.push_back(label);
        break;
      }
      case ItemKind::BATTERY: {
        lv_obj_t *row = this->make_row_(parent);
        this->battery_icon_ = make_label(row, theme.emoji[f], this->fg_, "\xF0\x9F\x94\x8B");
        this->battery_label_ = make_label(row, theme.text[f], this->fg_, "");
        this->rows_.push_back({row, this->battery_icon_, this->battery_label_, 12});
        break;
      }
      case ItemKind::BRIGHTNESS: {
        lv_obj_t *row = this->make_row_(parent);
        lv_obj_t *icon = make_label(row, theme.emoji[f], this->fg_, "\xE2\x98\x80");
        this->slider_ = lv_slider_create(row);
        lv_obj_set_size(this->slider_, SLIDER_WIDTH, 24);
        lv_slider_set_range(this->slider_, 5, 100);
        lv_slider_set_value(this->slider_, 80, LV_ANIM_OFF);
        lv_obj_set_ext_click_area(this->slider_, 12);
        lv_obj_set_style_bg_color(this->slider_, lv_color_hex(this->fg_), LV_PART_MAIN);
        lv_obj_set_style_bg_opa(this->slider_, LV_OPA_30, LV_PART_MAIN);
        lv_obj_set_style_bg_color(this->slider_, lv_color_hex(this->fg_), LV_PART_INDICATOR);
        lv_obj_set_style_bg_opa(this->slider_, LV_OPA_COVER, LV_PART_INDICATOR);
        lv_obj_set_style_bg_color(this->slider_, lv_color_hex(this->fg_), LV_PART_KNOB);
        lv_obj_set_style_bg_opa(this->slider_, LV_OPA_COVER, LV_PART_KNOB);
        lv_obj_add_event_cb(this->slider_, CustomView::slider_event_, LV_EVENT_ALL, this);
        this->rows_.push_back({row, icon, this->slider_, 12});
        break;
      }
    }
  }

  lv_obj_t *make_row_(lv_obj_t *parent) {
    lv_obj_t *row = lv_obj_create(parent);
    lv_obj_remove_style_all(row);
    lv_obj_remove_flag(row, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(row, LV_OBJ_FLAG_CLICKABLE);
    this->stack_.push_back(row);
    return row;
  }

  void set_brightness_(int value) {
    if (this->local_.brightness != nullptr)
      this->local_.brightness->make_call().set_value((float) value).perform();
  }

  // At most one call per 100 ms while dragging, and always one on release.
  static void slider_event_(lv_event_t *e) {
    auto *self = static_cast<CustomView *>(lv_event_get_user_data(e));
    lv_obj_t *slider = static_cast<lv_obj_t *>(lv_event_get_target(e));
    switch (lv_event_get_code(e)) {
      case LV_EVENT_VALUE_CHANGED: {
        uint32_t now = millis();
        if (now - self->last_call_ms_ >= BRIGHTNESS_THROTTLE_MS) {
          self->last_call_ms_ = now;
          self->set_brightness_(lv_slider_get_value(slider));
        }
        break;
      }
      case LV_EVENT_RELEASED:
        self->last_call_ms_ = millis();
        self->set_brightness_(lv_slider_get_value(slider));
        break;
      default:
        break;
    }
  }

  LocalSources local_;
  uint32_t fg_;
  struct Row {
    lv_obj_t *row, *left, *right;
    int gap;
  };
  std::vector<Entity> entities_;
  std::vector<lv_obj_t *> stack_;
  std::vector<Row> rows_;
  lv_obj_t *battery_icon_{nullptr};
  lv_obj_t *battery_label_{nullptr};
  lv_obj_t *slider_{nullptr};
  uint32_t last_call_ms_{0};
};

}  // namespace

std::unique_ptr<BlockView> make_custom_view(lv_obj_t *parent, const Block &block, const Theme &theme,
                                            const LocalSources &local) {
  return std::make_unique<CustomView>(parent, block, theme, local);
}

}  // namespace ha_controller
}  // namespace esphome
