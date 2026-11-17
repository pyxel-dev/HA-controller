#include "axp2101_battery.h"

#include <cmath>

#include "axp2101_regs.h"
#include "esphome/core/log.h"

namespace esphome {
namespace axp2101_battery {

static const char *const TAG = "axp2101_battery";

void AXP2101Battery::setup() {
  // Enable the battery voltage ADC channel and battery detection (bit 0 of each register).
  for (uint8_t reg : {REG_ADC_CTRL, REG_BAT_DET}) {
    uint8_t value = 0;
    if (this->read_register(reg, &value, 1) != i2c::ERROR_OK) {
      ESP_LOGE(TAG, "Failed to read register 0x%02X", reg);
      this->mark_failed();
      return;
    }
    value |= 0x01;
    if (this->write_register(reg, &value, 1) != i2c::ERROR_OK) {
      ESP_LOGE(TAG, "Failed to write register 0x%02X", reg);
      this->mark_failed();
      return;
    }
  }
}

void AXP2101Battery::update() {
  uint8_t status1 = 0, status2 = 0;
  if (this->read_register(REG_STATUS1, &status1, 1) != i2c::ERROR_OK ||
      this->read_register(REG_STATUS2, &status2, 1) != i2c::ERROR_OK) {
    ESP_LOGW(TAG, "Failed to read status registers");
    this->status_set_warning();
    return;
  }
  this->status_clear_warning();

  const bool present = battery_present(status1);
  if (this->charging_ != nullptr)
    this->charging_->publish_state(is_charging(status2));

  float level = NAN;
  float volts = NAN;
  if (present) {
    uint8_t pct = 0, hi = 0, lo = 0;
    if (this->read_register(REG_BAT_PERCENT, &pct, 1) == i2c::ERROR_OK)
      level = battery_percent(pct);
    if (this->read_register(REG_VBAT_H, &hi, 1) == i2c::ERROR_OK &&
        this->read_register(REG_VBAT_L, &lo, 1) == i2c::ERROR_OK)
      volts = battery_millivolts(hi, lo) / 1000.0f;
  }
  if (this->battery_level_ != nullptr)
    this->battery_level_->publish_state(level);
  if (this->battery_voltage_ != nullptr)
    this->battery_voltage_->publish_state(volts);
}

void AXP2101Battery::dump_config() {
  ESP_LOGCONFIG(TAG, "AXP2101 battery:");
  LOG_I2C_DEVICE(this);
  LOG_UPDATE_INTERVAL(this);
  LOG_SENSOR("  ", "Battery level", this->battery_level_);
  LOG_SENSOR("  ", "Battery voltage", this->battery_voltage_);
  LOG_BINARY_SENSOR("  ", "Charging", this->charging_);
  if (this->is_failed())
    ESP_LOGE(TAG, "Communication with the AXP2101 failed");
}

}  // namespace axp2101_battery
}  // namespace esphome
