# ==============================================================================
# Fetch anira via FetchContent
# ==============================================================================

include(FetchContent)

set(ANIRA_WITH_LIBTORCH OFF CACHE BOOL "Disable LibTorch backend")
set(ANIRA_WITH_TFLITE OFF CACHE BOOL "Disable TensorFlow Lite backend")
set(ANIRA_WITH_ONNXRUNTIME ON CACHE BOOL "Enable ONNX Runtime backend")
set(ANIRA_WITH_BENCHMARK OFF CACHE BOOL "Disable Anira Benchmark module")

# Enable WASM wrappers build when targeting Emscripten
if(WASM)
  set(ANIRA_BUILD_WASM ON CACHE BOOL "Build anira WASM wrappers lib")
  if(EMSCRIPTEN_VERSION AND NOT DEFINED EMSDK_VERSION)
    set(EMSDK_VERSION "${EMSCRIPTEN_VERSION}" CACHE STRING "Emscripten SDK version for anira")
  endif()
else()
  set(ANIRA_BUILD_WASM OFF CACHE BOOL "")
endif()

FetchContent_Declare(anira
  SOURCE_DIR ${CMAKE_CURRENT_LIST_DIR}/../../anira
)
FetchContent_MakeAvailable(anira)
