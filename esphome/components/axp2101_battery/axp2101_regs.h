#pragma once

#include <cstdint>

namespace esphome {
namespace axp2101_battery {

constexpr uint8_t REG_STATUS1 = 0x00;
constexpr uint8_t REG_STATUS2 = 0x01;
constexpr uint8_t REG_ADC_CTRL = 0x30;
constexpr uint8_t REG_VBAT_H = 0x34;
constexpr uint8_t REG_VBAT_L = 0x35;
constexpr uint8_t REG_BAT_DET = 0x68;
constexpr uint8_t REG_BAT_PERCENT = 0xA4;

inline bool battery_present(uint8_t status1) { return (status1 & 0x08) != 0; }

inline bool is_charging(uint8_t status2) { return (status2 >> 5) == 0x01; }

inline uint16_t battery_millivolts(uint8_t hi, uint8_t lo) {
  return static_cast<uint16_t>(((hi & 0x1F) << 8) | lo);
}

inline float battery_percent(uint8_t raw) { return raw > 100 ? 100.0f : static_cast<float>(raw); }

}  // namespace axp2101_battery
}  // namespace esphome
