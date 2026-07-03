import { ONNXRuntimeWebBackend } from '@anira-project/anira'
import { AniraBenchmarkWeb, setupBenchmarks, type BackendToBenchmark } from '../benchmark-lib'
import { JSBypassBackend } from '../benchmark-lib/backends/JSBypassBackend'
import { JSHybridNNPrePostProcessor } from '../benchmark-lib/preprocessors/JSHybridNNPrePostProcessor'
import { JSSteerableNafxPrePostProcessor } from '../benchmark-lib/preprocessors/JSSteerableNafxPrePostProcessor'

const inferenceWorkerFactory = () =>
  new Worker(new URL('./benchmarkInferenceWorker.ts', import.meta.url), {
    type: 'module',
  })

const { executeBenchmark } = setupBenchmarks(inferenceWorkerFactory)

// We need an AniraBenchmarkWeb instance to access the InferenceBackend enum.
// This is a lightweight read — the actual per-config instances are created inside executeBenchmark.
const tempAnira = await AniraBenchmarkWeb.create({
  print: () => {},
  printErr: () => {},
})

// Specs 0-2 are SteerableNAFX, specs 3-5 are GuitarLSTM.
const STEERABLE_NAFX_SPEC_COUNT = 3

// Picks the correct JS PrePostProcessor class for the given spec index.
const makeJSPP = (anira: AniraBenchmarkWeb, config: any, configIdx: number) =>
  configIdx < STEERABLE_NAFX_SPEC_COUNT
    ? new JSSteerableNafxPrePostProcessor(
        anira.getWasmInstance(), config, anira.benchmarkGetBufferSize(configIdx)
      )
    : new JSHybridNNPrePostProcessor(
        anira.getWasmInstance(), config, anira.benchmarkGetBufferSize(configIdx)
      )

const runs = [
  // ---- WASM backend + WASM PP (all specs) ----
  {
    label: 'bypass',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
  },
  {
    label: 'onnx',
    backendEnum: tempAnira.InferenceBackend.ONNX,
  },

  // ---- JS backends + WASM PP (all specs) ----
  {
    label: 'js-bypass',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
    processorFn: async (anira: AniraBenchmarkWeb, config, _configIdx) => {
      const backend = new JSBypassBackend(anira.getWasmInstance(), config)
      await anira.registerProcessor(backend, 'JSBypassBackend')
      return backend
    },
  },
  {
    label: 'onnxrt-web',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
    processorFn: async (anira: AniraBenchmarkWeb, _config, configIdx) => {
      // ONNXRuntimeWebBackend cannot fetch() from embedded VFS paths, so we
      // provide a binary InferenceConfig that it can read from WASM heap.
      const binaryConfig = anira.benchmarkCreateInferenceConfigBinary(configIdx)
      const backend = new ONNXRuntimeWebBackend(anira.getWasmInstance(), binaryConfig)
      await anira.registerProcessor(backend, 'ONNXRuntimeWebBackend')
      // Safe to destroy: init() has already extracted model bytes into ORT memory.
      binaryConfig.destroy()
      return backend
    },
  },

  // ---- WASM backends + JS PP (all specs) ----
  {
    label: 'bypass-jspp',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
    ppFactory: makeJSPP,
  },
  {
    label: 'onnx-jspp',
    backendEnum: tempAnira.InferenceBackend.ONNX,
    ppFactory: makeJSPP,
  },

  // ---- JS backends + JS PP (all specs) ----
  {
    label: 'js-bypass-jspp',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
    processorFn: async (anira: AniraBenchmarkWeb, config, _configIdx) => {
      const backend = new JSBypassBackend(anira.getWasmInstance(), config)
      await anira.registerProcessor(backend, 'JSBypassBackend')
      return backend
    },
    ppFactory: makeJSPP,
  },
  {
    label: 'onnxrt-web-jspp',
    backendEnum: tempAnira.InferenceBackend.CUSTOM,
    processorFn: async (anira: AniraBenchmarkWeb, _config, configIdx) => {
      const binaryConfig = anira.benchmarkCreateInferenceConfigBinary(configIdx)
      const backend = new ONNXRuntimeWebBackend(anira.getWasmInstance(), binaryConfig)
      await anira.registerProcessor(backend, 'ONNXRuntimeWebBackend')
      binaryConfig.destroy()
      return backend
    },
    ppFactory: makeJSPP,
  },
] satisfies BackendToBenchmark[]

// -------------------
// ------- UI --------
// -------------------

document.getElementById('loading-indicator')?.remove()

const startBenchmarkBtn = document.getElementById(
  'start-benchmark-btn'
) as HTMLButtonElement
const downloadBtn = document.getElementById('download-results-btn') as HTMLButtonElement

startBenchmarkBtn.disabled = false

startBenchmarkBtn.addEventListener('click', async () => {
  startBenchmarkBtn.disabled = true
  downloadBtn.disabled = true

  const output = await executeBenchmark(runs)

  startBenchmarkBtn.disabled = false

  downloadBtn.disabled = false
  downloadBtn.addEventListener('click', () => {
    const blob = new Blob([output.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'benchmark_output.txt'
    a.click()
    URL.revokeObjectURL(url)
  })
})
