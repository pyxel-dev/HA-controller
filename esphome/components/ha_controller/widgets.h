#pragma once
#include <lvgl.h>

#include <memory>
#include <string>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"

#include "layout.h"
#include "states.h"

namespace esphome {
namespace ha_controller {

// Receives the control events of the views (knob, toggle). Implemented by HaController.
class ControlSink {
 public:
  virtual ~ControlSink() = default;
  virtual void on_control(const std::string &block, const std::string &item, const char *op, float value) = 0;
};

struct Theme {
  const lv_font_t *text[4];
  const lv_font_t *value[4];
  const lv_font_t *emoji[4];
  int size;
  int edge_width;
};

struct LocalSources {
  sensor::Sensor *battery{};
  binary_sensor::BinarySensor *charging{};
  number::Number *brightness{};
};

// One full-screen view per block. Every method runs on the ESPHome main loop.
class BlockView {
 public:
  virtual ~BlockView();
  lv_obj_t *root() const { return this->root_; }
  const std::string &id() const { return this->id_; }
  // True when a state update with this id belongs to the view (the block or one of its items).
  virtual bool owns(const std::string &id) const;
  virtual void apply(const StateUpdate &u, uint32_t now_ms);
  // Battery, charging or brightness changed.
  virtual void on_local_update();
  virtual void loop(uint32_t now_ms);

 protected:
  lv_obj_t *root_{nullptr};
  std::string id_;
};

std::unique_ptr<BlockView> make_block_view(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink,
                                           const LocalSources &local);

}  // namespace ha_controller
}  // namespace esphome
