
include(${CMAKE_SOURCE_DIR}/cmake/SetupBenchmarkModels.cmake)

# ==============================================================================
# Native-only benchmark target
# ==============================================================================

set(BENCHMARK_TARGET_NAME "AniraNativeBenchmarks")
message(STATUS "Building native benchmark executable...")

if(NOT CMAKE_BUILD_TYPE STREQUAL "Release")
  set(DEBUG_FLAGS "-O0 -g")
else()
  set(DEBUG_FLAGS "")
endif()

add_executable(${BENCHMARK_TARGET_NAME} src/benchmarks/benchmarks.cpp)
target_link_libraries(${BENCHMARK_TARGET_NAME} PUBLIC anira::anira)
target_compile_features(${BENCHMARK_TARGET_NAME} PUBLIC cxx_std_20)

# No google benchmark or gtest — this is a plain executable with main()
set_target_properties(${BENCHMARK_TARGET_NAME} PROPERTIES
  OUTPUT_NAME ${BENCHMARK_TARGET_NAME}
  LINK_FLAGS "${DEBUG_FLAGS}"
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
