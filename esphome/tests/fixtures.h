#pragma once
#include <ArduinoJson.h>

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

#ifndef FIXTURES_DIR
#error "FIXTURES_DIR must be defined by the build"
#endif

inline std::string read_fixture(const std::string &relative) {
  std::ifstream in(std::string(FIXTURES_DIR) + "/" + relative, std::ios::binary);
  if (!in)
    throw std::runtime_error("cannot open fixture " + relative);
  std::stringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

// Re-serialises one top-level field of a fixture file as compact JSON.
inline std::string json_field(const std::string &file, const char *key) {
  JsonDocument doc;
  if (deserializeJson(doc, read_fixture(file)))
    throw std::runtime_error("fixture is not JSON: " + file);
  std::string out;
  serializeJson(doc[key], out);
  return out;
}

// Returns a top-level string field of a fixture file as is (no JSON quoting).
inline std::string json_string_field(const std::string &file, const char *key) {
  JsonDocument doc;
  if (deserializeJson(doc, read_fixture(file)))
    throw std::runtime_error("fixture is not JSON: " + file);
  return doc[key].as<std::string>();
}
