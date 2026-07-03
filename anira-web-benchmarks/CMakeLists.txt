cmake_minimum_required(VERSION 3.15)
project(anira_web_benchmarks VERSION 1.0 LANGUAGES CXX)

# Detect Emscripten toolchain
if("${CMAKE_CXX_COMPILER}" MATCHES "em\\+\\+")
  set(WASM true)
endif()

include(cmake/SetupAnira.cmake)

if(WASM)
  include(cmake/BuildWasm.cmake)
else()
  include(cmake/BuildNativeBenchmarks.cmake)
endif()
