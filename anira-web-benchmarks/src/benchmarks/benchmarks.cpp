#include <anira/anira.h>
#include <vector>
#include <chrono>
#include <random>
#include <cstdio>
#include <algorithm>
#include <numeric>
#include <functional>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <atomic>

#ifdef __EMSCRIPTEN__
#include <emscripten/emscripten.h>
#endif

#if defined(__i386__) || defined(__x86_64__)
#include <immintrin.h>
#endif

#include "model_configs/hybrid-nn/HybridNNPrePostProcessor.h"
#include "model_configs/steerable-nafx/SteerableNafxPrePostProcessor.h"

// Spin-loop hint: yields the SMT pipeline / saves power while busy-waiting,
// without the fixed scheduler-quantum penalty of std::this_thread::sleep_for.
static inline void cpu_relax() {
#if defined(__i386__) || defined(__x86_64__)
    _mm_pause();
#elif defined(__aarch64__) || defined(__arm__)
    __asm__ __volatile__("yield");
#else
    // No portable WASM pause intrinsic; a compiler barrier keeps the load live.
    std::atomic_signal_fence(std::memory_order_acq_rel);
#endif
}

/* ============================================================ *
 * ============= BENCHMARK CONFIGURATION SPEC ================= *
 * ============================================================ */

// One spec per model/config. Backend, processor, and label are NOT part of the
// spec – they are provided per-run by the caller (JS or native main()).
struct BenchmarkSpec {
    anira::HostConfig host_config;
    float max_inference_time;
    size_t warm_up;
    size_t num_parallel_processors;
    std::vector<anira::TensorShape> tensor_shapes;
    anira::ProcessingSpec processing_spec;
    std::vector<anira::ModelData> model_data;  ///< path-based on both targets
    std::string model_filename;                ///< bare filename, for logging

    using PPFactory = std::function<std::unique_ptr<anira::PrePostProcessor>(anira::InferenceConfig&)>;
    PPFactory make_pp;
};

// Native-only: one backend run over a spec.
#ifndef __EMSCRIPTEN__
struct NativeRun {
    int spec_idx;
    std::string label;
    anira::InferenceBackend backend;
};
#endif

/* ============================================================ *
 * ========= INLINE SPEC CONSTANTS (platform-shared) ========== *
 * ============================================================ */

static constexpr int   STEERABLENAFX_RECEPTIVE_FIELD = 13332;
static constexpr float STEERABLENAFX_SAMPLE_RATE     = 44100.0f;
static constexpr int   HYBRIDNN_CONTEXT_SAMPLES      = 150;
static constexpr float HYBRIDNN_SAMPLE_RATE          = 44100.0f;

static const std::vector<int> STEERABLENAFX_BUFFER_SIZES = {128, 1024, 8192};
static const std::vector<int> HYBRIDNN_BUFFER_SIZES      = {128, 1024, 8192};

/* ============================================================ *
 * =================== SPEC REGISTRY ========================== *
 * ============================================================ */

static std::vector<BenchmarkSpec> build_benchmark_specs() {
    std::vector<BenchmarkSpec> specs;

    // ---- SteerableNAFX: one spec per buffer size ----
    for (int bs : STEERABLENAFX_BUFFER_SIZES) {
        int input_size = bs + STEERABLENAFX_RECEPTIVE_FIELD;
        BenchmarkSpec s;
        s.host_config             = { static_cast<float>(bs), STEERABLENAFX_SAMPLE_RATE };
        s.max_inference_time      = static_cast<float>(bs) / STEERABLENAFX_SAMPLE_RATE * 1000.0f;
        s.warm_up                 = 5;
        s.num_parallel_processors = 1;
        s.tensor_shapes           = { { {{1, 1, input_size}}, {{1, 1, bs}} } };
        s.processing_spec         = { {1}, {1}, {static_cast<size_t>(bs)}, {static_cast<size_t>(bs)} };
        s.model_data = {
            { STEERABLENAFX_MODELS_PATH_PYTORCH + std::string("/model_0/steerable-nafx-libtorch-dynamic.onnx"), anira::InferenceBackend::ONNX },
        };
        s.model_filename = "steerable-nafx-libtorch-dynamic.onnx";
        s.make_pp        = [](anira::InferenceConfig& c) { return std::make_unique<SteerableNafxPrePostProcessor>(c); };
        specs.push_back(std::move(s));
    }

    // ---- HybridNN (GuitarLSTM): one spec per buffer size ----
    for (int bs : HYBRIDNN_BUFFER_SIZES) {
        BenchmarkSpec s;
        s.host_config             = { static_cast<float>(bs), HYBRIDNN_SAMPLE_RATE };
        s.max_inference_time      = 5.33f;
        s.warm_up                 = 3;
        s.num_parallel_processors = 1;
        s.tensor_shapes           = { { {{bs, 1, HYBRIDNN_CONTEXT_SAMPLES}}, {{bs, 1}} } };
        s.processing_spec         = { {1}, {1}, {static_cast<size_t>(bs)}, {static_cast<size_t>(bs)} };
        s.model_data = {
            { GUITARLSTM_MODELS_PATH_PYTORCH + std::string("/model_0/GuitarLSTM-libtorch-dynamic.onnx"), anira::InferenceBackend::ONNX },
        };
        s.model_filename = "GuitarLSTM-libtorch-dynamic.onnx";
        s.make_pp        = [](anira::InferenceConfig& c) { return std::make_unique<HybridNNPrePostProcessor>(c); };
        specs.push_back(std::move(s));
    }

    return specs;
}

static std::vector<BenchmarkSpec>& benchmark_specs() {
    static std::vector<BenchmarkSpec> s = build_benchmark_specs();
    return s;
}

#ifndef __EMSCRIPTEN__
static std::vector<NativeRun> build_native_runs() {
    std::vector<NativeRun> runs;
    for (int i = 0; i < static_cast<int>(benchmark_specs().size()); ++i) {
        runs.push_back({ i, "bypass", anira::InferenceBackend::CUSTOM });
        runs.push_back({ i, "onnx",   anira::InferenceBackend::ONNX   });
    }
    return runs;
}
#endif

/* ============================================================ *
 * ================== TIMING CORE (shared) ==================== *
 * ============================================================ */

static float random_sample() {
    static std::mt19937 gen(42);
    static std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
    return dist(gen);
}

static void run_iterations(
    anira::InferenceHandler&      handler,
    anira::Buffer<float>&         buffer,
    const anira::InferenceConfig& config,
    const anira::HostConfig&      host_config,
    int                           num_iterations,
    double*                       times_out) {
    size_t channels = config.get_preprocess_input_channels()[0];
    for (int i = 0; i < num_iterations; ++i) {
        for (size_t ch = 0; ch < channels; ++ch)
            for (size_t s = 0; s < host_config.m_buffer_size; ++s)
                buffer.set_sample(ch, s, random_sample());

        size_t prev_available = handler.get_available_samples(0);

        auto t0 = std::chrono::steady_clock::now();
        handler.process(buffer.get_array_of_write_pointers(), host_config.m_buffer_size);
        // Busy-wait for async inference completion. Spinning detects completion
        // within one clock tick instead of rounding up to the ~µs sleep_for
        // scheduler quantum. Requires the inference worker to run on a separate
        // core (true on the benchmark machines and WASM thread pool).
        while (handler.get_available_samples(0) < prev_available)
            cpu_relax();
        auto t1 = std::chrono::steady_clock::now();

        times_out[i] = std::chrono::duration<double, std::milli>(t1 - t0).count();
    }
}

/* ============================================================ *
 * ========================= LOGGING ========================== *
 * ============================================================ */

static double calc_mean(const std::vector<double>& v) {
    return std::accumulate(v.begin(), v.end(), 0.0) / static_cast<double>(v.size());
}

static double calc_min(const std::vector<double>& v) {
    return *std::min_element(v.begin(), v.end());
}

static double calc_max(const std::vector<double>& v) {
    return *std::max_element(v.begin(), v.end());
}

static double calc_percentile(std::vector<double> v, double p) {
    std::sort(v.begin(), v.end());
    return v[static_cast<size_t>(p * (v.size() - 1))];
}

static void log_config_header(const BenchmarkSpec& spec, const std::string& label, int num_iter, int num_reps) {
    float bs_ms = spec.host_config.m_buffer_size * 1000.0f / spec.host_config.m_sample_rate;
    printf("\n----------------------------------------------------------------------------------------------------------------------------------------\n");
    printf("Model: %s | Run: %s | Host Sample Rate: %.0f Hz | Host Buffer Size: %d = %.4f ms\n",
           spec.model_filename.c_str(),
           label.c_str(),
           spec.host_config.m_sample_rate,
           static_cast<int>(spec.host_config.m_buffer_size),
           bs_ms);
    printf("----------------------------------------------------------------------------------------------------------------------------------------\n\n");
    printf("Benchmark: %d repetitions x %d iterations\n\n", num_reps, num_iter);
}

static void log_single_rep(
    const BenchmarkSpec&       spec,
    const std::string&         label,
    int                        rep_idx,
    int                        num_reps,
    const std::vector<double>& times) {
    for (int i = 0; i < static_cast<int>(times.size()); ++i) {
        printf("ProcessBlock/%s/%s/%d/iteration:%d/repetition:%d\t\t\t%.4f ms\n",
               spec.model_filename.c_str(),
               label.c_str(),
               static_cast<int>(spec.host_config.m_buffer_size),
               i, rep_idx + 1, times[i]);
    }
    printf("  Repetition %d/%d: mean=%.4f ms\n\n", rep_idx + 1, num_reps, calc_mean(times));
}

static void log_timer_resolution() {
    using clock = std::chrono::steady_clock;
    auto t1 = clock::now();
    auto t2 = clock::now();
    while (t2 == t1) t2 = clock::now();
    auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count();
    printf("Timer resolution: %lld ns\n", static_cast<long long>(ns));
}

static void log_aggregate(const BenchmarkSpec& spec, const std::string& label, const std::vector<double>& all_times) {
    printf("\nAggregate (%d total iterations):\n", static_cast<int>(all_times.size()));
    printf("  ProcessBlock/%s/%s: mean=%.4f ms, min=%.4f ms, max=%.4f ms, p99.9=%.4f ms\n",
           spec.model_filename.c_str(),
           label.c_str(),
           calc_mean(all_times),
           calc_min(all_times),
           calc_max(all_times),
           calc_percentile(all_times, 0.999));
    printf("\n----------------------------------------------------------------------------------------------------------------------------------------\n");
}

/* ============================================================ *
 * ====================== ENTRY POINTS ======================== *
 * ============================================================ */

#ifdef __EMSCRIPTEN__

extern "C" {

EMSCRIPTEN_KEEPALIVE
void benchmark_log_timer_resolution() {
    log_timer_resolution();
}

EMSCRIPTEN_KEEPALIVE
int benchmark_get_config_count() {
    return static_cast<int>(benchmark_specs().size());
}

EMSCRIPTEN_KEEPALIVE
const char* benchmark_get_model_filename(int idx) {
    return benchmark_specs()[idx].model_filename.c_str();
}

EMSCRIPTEN_KEEPALIVE
uintptr_t benchmark_get_host_config_ptr(int idx) {
    return reinterpret_cast<uintptr_t>(&benchmark_specs()[idx].host_config);
}

EMSCRIPTEN_KEEPALIVE
int benchmark_get_buffer_size(int idx) {
    return static_cast<int>(benchmark_specs()[idx].host_config.m_buffer_size);
}

EMSCRIPTEN_KEEPALIVE
float benchmark_get_sample_rate(int idx) {
    return benchmark_specs()[idx].host_config.m_sample_rate;
}

// Creates an InferenceConfig from the spec's model_data.
// Ownership is transferred to the caller (JS must destroy).
EMSCRIPTEN_KEEPALIVE
uintptr_t benchmark_create_inference_config(int idx) {
    const BenchmarkSpec& spec = benchmark_specs()[idx];
    auto* config = new anira::InferenceConfig(
        spec.model_data,
        spec.tensor_shapes,
        spec.processing_spec,
        spec.max_inference_time,
        spec.warm_up,
        false,
        0.0f,
        static_cast<unsigned int>(spec.num_parallel_processors)
    );
    return reinterpret_cast<uintptr_t>(config);
}

// Creates a PrePostProcessor via the spec's factory. Ownership is transferred to
// the caller: JS must call _prepostprocessor_destroy on the returned pointer.
EMSCRIPTEN_KEEPALIVE
uintptr_t benchmark_create_pp(int idx, uintptr_t config_ptr) {
    auto* config = reinterpret_cast<anira::InferenceConfig*>(config_ptr);
    return reinterpret_cast<uintptr_t>(benchmark_specs()[idx].make_pp(*config).release());
}

// Runs num_iterations timed process() calls. Writes per-iteration times (ms)
// into the caller-provided double[] buffer at times_out_ptr.
EMSCRIPTEN_KEEPALIVE
void benchmark_run_single_rep(
    uintptr_t handler_ptr,
    uintptr_t buffer_ptr,
    uintptr_t config_ptr,
    uintptr_t host_config_ptr,
    int num_iterations,
    uintptr_t times_out_ptr
) {
    auto* handler     = reinterpret_cast<anira::InferenceHandler*>(handler_ptr);
    auto* buffer      = reinterpret_cast<anira::Buffer<float>*>(buffer_ptr);
    auto* config      = reinterpret_cast<anira::InferenceConfig*>(config_ptr);
    auto* host_config = reinterpret_cast<anira::HostConfig*>(host_config_ptr);
    auto* times_out   = reinterpret_cast<double*>(times_out_ptr);

    run_iterations(*handler, *buffer, *config, *host_config, num_iterations, times_out);
}

// Creates an InferenceConfig with the model loaded as binary from the WASM
// virtual filesystem. Used by ONNXRuntimeWebBackend which cannot fetch() from
// embedded VFS paths. The model binary is cached per-index so repeated calls
// are cheap. Ownership is transferred to the caller (JS must destroy).
EMSCRIPTEN_KEEPALIVE
uintptr_t benchmark_create_inference_config_binary(int idx) {
    static std::map<int, std::vector<char>> model_cache;

    if (model_cache.find(idx) == model_cache.end()) {
        const char* path = reinterpret_cast<const char*>(benchmark_specs()[idx].model_data[0].m_data);
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        if (!file) return 0;
        const auto size = static_cast<std::size_t>(file.tellg());
        file.seekg(0, std::ios::beg);
        model_cache[idx].resize(size);
        file.read(model_cache[idx].data(), static_cast<std::streamsize>(size));
    }

    const auto& buf = model_cache[idx];
    // CUSTOM backend so ONNXRuntimeWebBackend's init() finds it via getModelData(CUSTOM).
    // Binary ModelData shallow-copies the pointer; the static cache keeps it alive.
    std::vector<anira::ModelData> binary_model_data = {
        anira::ModelData(const_cast<char*>(buf.data()), buf.size(), anira::InferenceBackend::CUSTOM)
    };

    const BenchmarkSpec& spec = benchmark_specs()[idx];
    auto* config = new anira::InferenceConfig(
        binary_model_data,
        spec.tensor_shapes,
        spec.processing_spec,
        spec.max_inference_time,
        spec.warm_up,
        false,
        0.0f,
        static_cast<unsigned int>(spec.num_parallel_processors)
    );
    return reinterpret_cast<uintptr_t>(config);
}

} // extern "C"

#else // Native

int main() {
    constexpr int NUM_ITERATIONS  = 50;
    constexpr int NUM_REPETITIONS = 10;

    log_timer_resolution();

    for (const NativeRun& run : build_native_runs()) {
        const BenchmarkSpec& spec = benchmark_specs()[run.spec_idx];
        log_config_header(spec, run.label, NUM_ITERATIONS, NUM_REPETITIONS);

        std::vector<double> all_times;

        for (int rep = 0; rep < NUM_REPETITIONS; ++rep) {
            // Cold start per repetition: same behaviour as WASM's per-rep teardown/setup.
            anira::InferenceConfig config(
                spec.model_data,
                spec.tensor_shapes,
                spec.processing_spec,
                spec.max_inference_time,
                spec.warm_up
            );
            auto pp = spec.make_pp(config);

            anira::InferenceHandler handler(*pp, config, anira::ContextConfig(1));
            handler.set_inference_backend(run.backend);
            handler.prepare(spec.host_config);

            anira::Buffer<float> buffer(
                config.get_preprocess_input_channels()[0],
                spec.host_config.m_buffer_size
            );

            std::vector<double> times(NUM_ITERATIONS);
            run_iterations(handler, buffer, config, spec.host_config, NUM_ITERATIONS, times.data());
            log_single_rep(spec, run.label, rep, NUM_REPETITIONS, times);
            all_times.insert(all_times.end(), times.begin(), times.end());
        }

        log_aggregate(spec, run.label, all_times);
    }

    return 0;
}

#endif
