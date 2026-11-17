#pragma once
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/font/font.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/touchscreen/touchscreen.h"
#include "esphome/core/automation.h"
#include "esphome/core/component.h"

#include "layout.h"
#include "pager.h"
#include "sleep.h"
#include "widgets.h"

namespace esphome {
namespace ha_controller {

enum class FontRole : uint8_t { TEXT, VALUE, EMOJI };

class HaController;

// Wakes the screen when a touch is released while it sleeps.
class WakeListener : public touchscreen::TouchListener {
 public:
  explicit WakeListener(HaController *parent) : parent_(parent) {}
  void release() override;

 protected:
  HaController *parent_;
};

class HaController : public Component, public ControlSink {
 public:
  void setup() override;
  void loop() override;
  float get_setup_priority() const override { return setup_priority::LATE; }

  void set_geometry(int size, int edge_width) {
    this->theme_.size = size;
    this->theme_.edge_width = edge_width;
  }
  // The ESPHome font already carries the lv_font_t used by LVGL (font::Font::get_lv_font()).
  void set_font(FontRole role, FontSize size, font::Font *font);
  void set_battery_sensor(sensor::Sensor *s) { this->local_.battery = s; }
  void set_charging_sensor(binary_sensor::BinarySensor *s) { this->local_.charging = s; }
  void set_brightness_number(number::Number *n) { this->local_.brightness = n; }
  void set_touchscreen(touchscreen::Touchscreen *ts) { ts->register_listener(&this->wake_listener_); }
  void set_sleep_timeout(uint32_t seconds) { this->sleep_timeout_s_ = seconds; }
  bool is_sleeping() const { return this->sleeping_; }
  void wake();
  void add_on_sleep_callback(std::function<void()> &&cb) { this->sleep_callbacks_.push_back(std::move(cb)); }
  void add_on_wake_callback(std::function<void()> &&cb) { this->wake_callbacks_.push_back(std::move(cb)); }
  void add_on_control_callback(std::function<void(std::string, std::string, std::string, float)> &&cb) {
    this->control_callbacks_.push_back(std::move(cb));
  }

  void set_layout(const std::string &json);
  void set_states(const std::string &json);
  void show_message(const std::string &title, const std::string &detail);
  void hide_message();
  std::string get_revision() const { return this->has_layout_ ? this->layout_.rev : "none"; }

  void on_control(const std::string &block, const std::string &item, const char *op, float value) override;

 protected:
  void rebuild_views_();
  void refresh_mode_();
  void on_local_update_();

  Theme theme_{{}, {}, {}, 466, 36};
  LocalSources local_;
  Layout layout_;
  bool has_layout_{false};
  Pager pager_;
  std::vector<std::unique_ptr<BlockView>> views_;
  lv_obj_t *screen_{nullptr};
  lv_obj_t *overlay_{nullptr};
  lv_obj_t *title_label_{nullptr};
  lv_obj_t *detail_label_{nullptr};
  std::vector<std::function<void(std::string, std::string, std::string, float)>> control_callbacks_;
  std::vector<std::function<void()>> sleep_callbacks_;
  std::vector<std::function<void()>> wake_callbacks_;
  WakeListener wake_listener_{this};
  uint32_t sleep_timeout_s_{DEFAULT_SLEEP_S};
  bool sleeping_{false};
};

class SleepTrigger : public Trigger<> {
 public:
  explicit SleepTrigger(HaController *parent) {
    parent->add_on_sleep_callback([this]() { this->trigger(); });
  }
};

class WakeTrigger : public Trigger<> {
 public:
  explicit WakeTrigger(HaController *parent) {
    parent->add_on_wake_callback([this]() { this->trigger(); });
  }
};

class ControlTrigger : public Trigger<std::string, std::string, std::string, float> {
 public:
  explicit ControlTrigger(HaController *parent) {
    parent->add_on_control_callback([this](std::string block, std::string item, std::string op, float value) {
      this->trigger(std::move(block), std::move(item), std::move(op), value);
    });
  }
};

}  // namespace ha_controller
}  // namespace esphome
