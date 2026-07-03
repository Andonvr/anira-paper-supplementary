import type { InferenceConfig, JSBackendBase, JSPrePostProcessor, PrePostProcessor } from '@anira-project/anira'
import type { PossiblePointer } from '@anira-project/anira'
import { AniraBenchmarkWeb } from './AniraBenchmarkWeb'
import { type ConfigMeta, logConfigHeader, logSingleRep, logAggregate } from './logging'

export { AniraBenchmarkWeb } from './AniraBenchmarkWeb'

export type BackendToBenchmark = {
  label: string
  backendEnum: number
  /** Called once per repetition to create a JS-side inference backend. */
  processorFn?: (
    anira: AniraBenchmarkWeb,
    inferenceConfig: PossiblePointer<InferenceConfig>,
    configIdx: number
  ) => Promise<JSBackendBase>
  /**
   * If present, a JSPrePostProcessor is created via this factory instead of
   * the default WASM PrePostProcessor from benchmarkCreatePP().
   */
  ppFactory?: (
    anira: AniraBenchmarkWeb,
    inferenceConfig: PossiblePointer<InferenceConfig>,
    configIdx: number
  ) => JSPrePostProcessor | PrePostProcessor
  /** When provided, this backend is skipped for configs where the predicate returns false. */
  specFilter?: (configIdx: number) => boolean
}

export type InferenceWorkerFactory = () => Worker

export const setupBenchmarks = (inferenceWorkerFactory: InferenceWorkerFactory) => {
  const NUM_ITERATIONS = 50
  const NUM_REPETITIONS = 10

  const executeBenchmark = async (backends: BackendToBenchmark[]) => {
    const output: string[] = []
    const log = (str: string) => {
      output.push(str)
      console.log(str)
    }

    // Single shared WASM memory reused across all AniraBenchmarkWeb instances
    // to avoid accumulating 512 MB SharedArrayBuffer allocations (one per config).
    const sharedWasmMemory = new WebAssembly.Memory({
      initial: 8192,
      maximum: 8192,
      shared: true,
    })

    // Read config metadata from an initial instance
    const initAnira = await AniraBenchmarkWeb.create({
      print: (str: string) => log(str),
      printErr: () => {},
    }, sharedWasmMemory)
    initAnira.benchmarkLogTimerResolution()
    const configCount = initAnira.benchmarkGetConfigCount()
    const configMetas: ConfigMeta[] = []
    for (let i = 0; i < configCount; i++) {
      configMetas.push({
        modelFilename: initAnira.benchmarkGetModelFilename(i),
        bufferSize: initAnira.benchmarkGetBufferSize(i),
        sampleRate: initAnira.benchmarkGetSampleRate(i),
      })
    }

    // Create persistent benchmark worker
    const benchmarkWorker = new Worker(
      new URL('./workers/benchmarkWorker.ts', import.meta.url),
      { type: 'module' }
    )

    for (let configIdx = 0; configIdx < configCount; configIdx++) {
      // Fresh WASM instance per config, sharing the same underlying memory
      const anira = await AniraBenchmarkWeb.create({
        print: () => {},
        printErr: (str: string) => {
          log(`Error: ${str}`)
        },
      }, sharedWasmMemory)

      const { performBenchmark, cleanup: cleanupBenchmarkWorker } = await anira.configureBenchmarkWorker(benchmarkWorker)

      for (const backend of backends) {
        if (backend.specFilter && !backend.specFilter(configIdx)) continue

        log(
          logConfigHeader(
            configMetas[configIdx],
            backend.label,
            NUM_ITERATIONS,
            NUM_REPETITIONS
          )
        )

        const allTimes: number[] = []
        const inferenceConfig = anira.benchmarkCreateInferenceConfig(configIdx)
        const hostConfig = anira.benchmarkGetHostConfig(configIdx)
        const bufferCh = inferenceConfig.getPreprocessInputChannels(0)

        const inferenceWorker = await anira.spinUpInferenceWorker(inferenceWorkerFactory())

        for (let rep = 0; rep < NUM_REPETITIONS; rep++) {
          const processor = backend.processorFn
            ? await backend.processorFn(anira, inferenceConfig, configIdx)
            : undefined

          const pp = backend.ppFactory
            ? backend.ppFactory(anira, inferenceConfig, configIdx)
            : anira.benchmarkCreatePP(configIdx, inferenceConfig)

          const inferenceHandler = anira.InferenceHandler(pp, inferenceConfig, processor)
          inferenceHandler.setInferenceBackend(backend.backendEnum)
          inferenceHandler.prepare(hostConfig)

          const buffer = anira.Buffer(bufferCh, hostConfig.bufferSize)

          const ppInfo =
            backend.ppFactory !== undefined
              ? ({ ppPtr: pp.getPointer(), configIdx })
              : undefined

          const times = await performBenchmark(
            inferenceHandler,
            buffer,
            inferenceConfig,
            hostConfig,
            NUM_ITERATIONS,
            ppInfo
          )

          log(
            logSingleRep(
              configMetas[configIdx],
              backend.label,
              rep,
              NUM_REPETITIONS,
              times
            )
          )
          allTimes.push(...times)

          buffer.destroy()
          inferenceHandler.destroy()
          pp.destroy()
          processor?.destroy()
          if (processor) await anira.unregisterProcessor(processor)
        }

        await inferenceWorker.stop()
        inferenceConfig.destroy()
        log(logAggregate(configMetas[configIdx], backend.label, allTimes))
      }
      cleanupBenchmarkWorker()
    }

    benchmarkWorker.terminate()
    return output
  }

  return { executeBenchmark }
}
