cmake_minimum_required(VERSION 3.20)
project(ha_controller_host_tests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(doctest
  GIT_REPOSITORY https://github.com/doctest/doctest.git
  GIT_TAG v2.4.12)
FetchContent_Declare(ArduinoJson
  GIT_REPOSITORY https://github.com/bblanchon/ArduinoJson.git
  GIT_TAG v7.4.2)
FetchContent_MakeAvailable(doctest ArduinoJson)

set(COMPONENT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../components/ha_controller)

file(GLOB TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/test_*.cpp)
set(PURE_SOURCES
  ${COMPONENT_DIR}/gesture.cpp
  ${COMPONENT_DIR}/layout.cpp
  ${COMPONENT_DIR}/states.cpp)

add_executable(unit_tests ${TEST_SOURCES} ${PURE_SOURCES})
target_include_directories(unit_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../components)
target_compile_definitions(unit_tests PRIVATE
  FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../../docs/protocol/fixtures")
target_compile_options(unit_tests PRIVATE -Wall -Wextra)
target_link_libraries(unit_tests PRIVATE doctest::doctest ArduinoJson)

enable_testing()
add_test(NAME unit_tests COMMAND unit_tests)
