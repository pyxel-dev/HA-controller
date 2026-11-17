#include "ha_controller.h"

#include "esphome/core/application.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#include "states.h"

namespace esphome {
namespace ha_controller {

static const char *const TAG = "ha_controller";

void HaController::set_font(FontRole role, FontSize size, font::Font *font) {
  const lv_font_t *f = font->get_lv_font();
  int i = static_cast<int>(size);
  switch (role) {
    case FontRole::TEXT:
      this->theme_.text[i] = f;
      break;
    case FontRole::VALUE:
      this->theme_.value[i] = f;
      break;
    case FontRole::EMOJI:
      this->theme_.emoji[i] = f;
      break;
  }
}

void HaController::setup() {
  this->screen_ = lv_obj_create(nullptr);
  lv_obj_remove_flag(this->screen_, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_bg_color(this->screen_, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(this->screen_, LV_OPA_COVER, 0);
  lv_screen_load(this->screen_);
  this->pager_.attach(this->screen_, this->theme_.size, this->theme_.edge_width);

  // Local sources are subscribed once here and forwarded to the live view.
  if (this->local_.battery != nullptr)
    this->local_.battery->add_on_state_callback([this](float) { this->on_local_update_(); });
  if (this->local_.charging != nullptr)
    this->local_.charging->add_on_state_callback([this](bool) { this->on_local_update_(); });
  if (this->local_.brightness != nullptr)
    this->local_.brightness->add_on_state_callback([this](float) { this->on_local_update_(); });

  this->refresh_mode_();
}

void HaController::loop() {
  uint32_t now = millis();
  for (auto &view : this->views_)
    view->loop(now);
}

void HaController::on_local_update_() {
  for (auto &view : this->views_)
    view->on_local_update();
}

void HaController::set_layout(const std::string &json) {
  Layout parsed;
  ParseError err = parse_layout(json, parsed);
  if (err == ParseError::UNSUPPORTED_VERSION) {
    ESP_LOGW(TAG, "Layout protocol not supported");
    this->show_message("Firmware update required", "Open Home Assistant to update");
    return;
  }
  if (err != ParseError::NONE) {
    ESP_LOGW(TAG, "Invalid layout: %s", parse_error_code(err));
    this->show_message("Invalid layout", parse_error_code(err));
    return;
  }
  this->layout_ = std::move(parsed);
  this->has_layout_ = true;
  ESP_LOGI(TAG, "Layout %s applied (%u blocks)", this->layout_.rev.c_str(), (unsigned) this->layout_.blocks.size());
  this->rebuild_views_();
  this->refresh_mode_();
}

void HaController::rebuild_views_() {
  // Keep the block on screen when it still exists, else the start block, else the first one.
  std::string show = this->pager_.current_id();
  if (this->layout_.find(show) == nullptr)
    show = this->layout_.start;
  if (this->layout_.find(show) == nullptr && !this->layout_.blocks.empty())
    show = this->layout_.blocks.front().id;
  // The pager forgets the old pages (and cancels any swipe or animation) before their objects are deleted.
  this->pager_.set_pages({}, "");
  this->views_.clear();
  std::vector<PageRef> pages;
  for (const auto &block : this->layout_.blocks) {
    auto view = make_block_view(this->pager_.viewport(), block, this->theme_, *this, this->local_);
    pages.push_back({block.id, block.x, block.y, view->root()});
    this->views_.push_back(std::move(view));
  }
  this->pager_.set_pages(std::move(pages), show);
}

void HaController::set_states(const std::string &json) {
  std::vector<StateUpdate> updates;
  if (!parse_states(json, updates)) {
    ESP_LOGW(TAG, "Invalid states payload");
    return;
  }
  // Every view receives its states, visible or not: the integration does not resend them on navigation.
  uint32_t now = millis();
  for (const auto &u : updates) {
    for (auto &view : this->views_) {
      if (view->owns(u.id))
        view->apply(u, now);
    }
  }
}

void HaController::refresh_mode_() {
  if (!this->has_layout_) {
    std::string detail = App.get_name();
#ifdef ESPHOME_PROJECT_VERSION
    detail += " \xC2\xB7 v" ESPHOME_PROJECT_VERSION;
#endif
    this->show_message("Waiting for Home Assistant", detail);
  } else if (this->layout_.blocks.empty()) {
    this->show_message("No blocks yet", "Add blocks in Home Assistant \xE2\x80\xBA HA Controller");
  } else {
    if (this->overlay_ != nullptr)
      lv_obj_add_flag(this->overlay_, LV_OBJ_FLAG_HIDDEN);
    this->pager_.set_enabled(true);
  }
}

void HaController::show_message(const std::string &title, const std::string &detail) {
  this->pager_.set_enabled(false);
  if (this->overlay_ == nullptr) {
    this->overlay_ = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(this->overlay_);
    lv_obj_set_size(this->overlay_, this->theme_.size, this->theme_.size);
    lv_obj_set_pos(this->overlay_, 0, 0);
    lv_obj_remove_flag(this->overlay_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(this->overlay_, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(this->overlay_, LV_OPA_COVER, 0);
    int width = this->theme_.size * 7 / 10;

    this->title_label_ = lv_label_create(this->overlay_);
    lv_obj_set_width(this->title_label_, width);
    lv_obj_set_style_text_align(this->title_label_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(this->title_label_, this->theme_.text[static_cast<int>(FontSize::M)], 0);
    lv_obj_set_style_text_color(this->title_label_, lv_color_white(), 0);
    lv_obj_align(this->title_label_, LV_ALIGN_CENTER, 0, -30);

    this->detail_label_ = lv_label_create(this->overlay_);
    lv_obj_set_width(this->detail_label_, width);
    lv_obj_set_style_text_align(this->detail_label_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(this->detail_label_, this->theme_.text[static_cast<int>(FontSize::S)], 0);
    lv_obj_set_style_text_color(this->detail_label_, lv_color_hex(0x9CA3AF), 0);
    lv_obj_align(this->detail_label_, LV_ALIGN_CENTER, 0, 40);
  }
  lv_label_set_text(this->title_label_, title.c_str());
  lv_label_set_text(this->detail_label_, detail.c_str());
  lv_obj_remove_flag(this->overlay_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(this->overlay_);
  lv_refr_now(nullptr);
}

void HaController::hide_message() { this->refresh_mode_(); }

void HaController::on_control(const std::string &block, const std::string &item, const char *op, float value) {
  for (auto &cb : this->control_callbacks_)
    cb(block, item, op, value);
}

}  // namespace ha_controller
}  // namespace esphome
