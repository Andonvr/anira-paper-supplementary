if(NOT WASM)
  message(FATAL_ERROR "Cannot build WASM benchmarks without Emscripten toolchain")
endif()

if(NOT BUILD_BENCHMARKS)
  message(STATUS "BUILD_BENCHMARKS is OFF — no WASM target to build.")
  return()
endif()

# ==============================================================================
# AniraWeb Benchmarks WASM target
# ==============================================================================

set(TARGET_NAME "AniraWebBenchmarks")
set(OUTPUT_FOLDER "${CMAKE_SOURCE_DIR}/web/wasm")
message(STATUS "Building AniraWeb Benchmark Wrappers...")

include(${CMAKE_SOURCE_DIR}/cmake/SetupBenchmarkModels.cmake)

set(EXPORTED_FUNCTIONS "\"_free\",\"_malloc\",\"_benchmark_get_config_count\",\"_benchmark_get_model_filename\",\"_benchmark_get_host_config_ptr\",\"_benchmark_get_buffer_size\",\"_benchmark_get_sample_rate\",\"_benchmark_create_inference_config\",\"_benchmark_create_inference_config_binary\",\"_benchmark_create_pp\",\"_benchmark_run_single_rep\"")

set(BENCHMARK_SOURCES src/benchmarks/benchmarks.cpp)

set(EMBED_FLAGS "\
  --embed-file ${STEERABLENAFX_MODELS_PATH_PYTORCH}@/${STEERABLENAFX_MODELS_PATH_PYTORCH} \
  --embed-file ${GUITARLSTM_MODELS_PATH_TENSORFLOW}@/${GUITARLSTM_MODELS_PATH_TENSORFLOW} \
  --embed-file ${GUITARLSTM_MODELS_PATH_PYTORCH}@/${GUITARLSTM_MODELS_PATH_PYTORCH} \
  --embed-file ${STATEFULLSTM_MODELS_PATH_TENSORFLOW}@/${STATEFULLSTM_MODELS_PATH_TENSORFLOW} \
  --embed-file ${STATEFULLSTM_MODELS_PATH_PYTORCH}@/${STATEFULLSTM_MODELS_PATH_PYTORCH} \
  --embed-file ${SIMPLEGAIN_MODEL_PATH}@/${SIMPLEGAIN_MODEL_PATH} \
  ")

# Set flags if Debug
if(NOT CMAKE_BUILD_TYPE STREQUAL "Release")
  set(DEBUG_FLAGS "-O0 -gsource-map")
else()
  set(DEBUG_FLAGS "")
endif()

set(LINK_FLAGS "\
  --no-entry \
  ${EMBED_FLAGS} \
  --emit-tsd=${OUTPUT_FOLDER}/${TARGET_NAME}.d.ts \
  -s STACK_OVERFLOW_CHECK=0 \
  -s IMPORTED_MEMORY=1 \
  -s INITIAL_MEMORY=536870912 \
  -s SHARED_MEMORY=1 \
  -s ALLOW_MEMORY_GROWTH=0 \
  -s MALLOC=emmalloc \
  -s EXPORT_ES6=1 \
  -s MODULARIZE=1 \
  -s ENVIRONMENT=worklet,web \
  -s ASSERTIONS=1 \
  -s NO_DISABLE_EXCEPTION_CATCHING \
  -s STACK_SIZE=33554432 \
  -s EXPORTED_FUNCTIONS='[${EXPORTED_FUNCTIONS}]' \
  -s EXPORT_KEEPALIVE=1 \
  -s EXPORTED_RUNTIME_METHODS='[\"UTF8ToString\",\"HEAPU32\",\"HEAPF32\",\"stackSave\",\"stackRestore\"]' \
  ")

add_executable(${TARGET_NAME} ${BENCHMARK_SOURCES})

target_link_libraries(${TARGET_NAME} PUBLIC
    -Wl,--whole-archive anira::wasm_wrappers -Wl,--no-whole-archive)
target_compile_features(${TARGET_NAME} PUBLIC cxx_std_20)
target_compile_options(${TARGET_NAME} PRIVATE -matomics -mbulk-memory -msimd128)

set_target_properties(${TARGET_NAME} PROPERTIES
  OUTPUT_NAME ${TARGET_NAME}
  LINK_FLAGS "${DEBUG_FLAGS} ${LINK_FLAGS}"
  RUNTIME_OUTPUT_DIRECTORY ${OUTPUT_FOLDER}
)
