#include "states.h"

#include <ArduinoJson.h>

namespace esphome {
namespace ha_controller {

bool parse_states(const std::string &json, std::vector<StateUpdate> &out) {
  JsonDocument doc;
  if (deserializeJson(doc, json))
    return false;
  if (!doc.is<JsonArray>())
    return false;
  out.clear();
  for (JsonVariant el : doc.as<JsonArray>()) {
    if (!el["id"].is<const char *>())
      continue;
    StateUpdate u;
    u.id = el["id"].as<std::string>();
    if (el["available"].is<bool>())
      u.available = el["available"].as<bool>();
    if (el["on"].is<bool>())
      u.on = el["on"].as<bool>();
    if (el["brightness"].is<int>())
      u.brightness = el["brightness"].as<int>();
    if (el["target"].is<float>())
      u.target = el["target"].as<float>();
    if (el["min"].is<float>())
      u.min = el["min"].as<float>();
    if (el["max"].is<float>())
      u.max = el["max"].as<float>();
    if (el["step"].is<float>())
      u.step = el["step"].as<float>();
    if (el["unit"].is<const char *>())
      u.unit = el["unit"].as<std::string>();
    if (el["current"].is<const char *>())
      u.current = el["current"].as<std::string>();
    if (el["action"].is<const char *>())
      u.action = el["action"].as<std::string>();
    if (el["text"].is<const char *>())
      u.text = el["text"].as<std::string>();
    out.push_back(std::move(u));
  }
  return true;
}

}  // namespace ha_controller
}  // namespace esphome
