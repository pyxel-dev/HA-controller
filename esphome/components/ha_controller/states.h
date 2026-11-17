#pragma once
#include <optional>
#include <string>
#include <vector>

namespace esphome {
namespace ha_controller {

struct StateUpdate {
  std::string id;
  bool available{true};
  std::optional<bool> on;
  std::optional<int> brightness;  // light; nullopt = on/off only
  std::optional<float> target;    // climate
  float min{7}, max{35}, step{0.5f};
  std::string unit, current, action;  // climate
  std::optional<std::string> text;    // entity item
};

// False on bad JSON or when the root is not an array. Elements without a string id are skipped.
bool parse_states(const std::string &json, std::vector<StateUpdate> &out);

}  // namespace ha_controller
}  // namespace esphome
