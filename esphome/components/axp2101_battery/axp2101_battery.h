#pragma once

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/i2c/i2c.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/core/component.h"

namespace esphome {
namespace axp2101_battery {

class AXP2101Battery : public PollingComponent, public i2c::I2CDevice {
 public:
  void setup() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_battery_level(sensor::Sensor *s) { this->battery_level_ = s; }
  void set_battery_voltage(sensor::Sensor *s) { this->battery_voltage_ = s; }
  void set_charging(binary_sensor::BinarySensor *s) { this->charging_ = s; }

 protected:
  sensor::Sensor *battery_level_{nullptr};
  sensor::Sensor *battery_voltage_{nullptr};
  binary_sensor::BinarySensor *charging_{nullptr};
};

}  // namespace axp2101_battery
}  // namespace esphome
