import {
  AniraWeb,
  BufferF,
  HostConfig,
  InferenceConfig,
  InferenceHandler,
  JSPrePostProcessor,
  PrePostProcessor,
  resolvePtr,
  type AniraWasmConfig,
} from '@anira-project/anira'
import type { PossiblePointer } from '@anira-project/anira'
import { createBenchmarkWasm, wasmUrl } from './factory'
import type { AniraBenchmarkWasmInstance } from './factory'
import type {
  BenchmarkConfigureMessage,
  BenchmarkWorkerMessage,
  DoneResponse,
  ReadyRespose,
} from './workers/messages'

function waitForWorkerResponse<T extends { type: string }>(
  worker: Worker,
  messageType: T['type']
): Promise<T> {
  return new Promise<T>((resolve) => {
    const listener = (e: MessageEvent<T>) => {
      if (e.data.type !== messageType) return
      worker.removeEventListener('message', listener)
      resolve(e.data)
    }
    worker.addEventListener('message', listener)
  })
}

export class AniraBenchmarkWeb extends AniraWeb {
  static async create(
    config?: AniraWasmConfig & Record<string, unknown>,
    memory?: WebAssembly.Memory
  ): Promise<AniraBenchmarkWeb> {
    const wasmMemory =
      memory ??
      new WebAssembly.Memory({
        initial: 8192,
        maximum: 8192,
        shared: true,
      })
    const prePostRegistry = new Map<number, JSPrePostProcessor>()
    const { processPrePost: externalProcessPrePost, ...restConfig } = config ?? {}
    const wasmInstance = await createBenchmarkWasm(wasmMemory, {
      ...restConfig,
      processPrePost: (
        prePostProcessorPtr: number,
        inputPtr: number,
        outputPtr: number,
        backend: number,
        phase: number
      ) => {
        const prePostProcessor = prePostRegistry.get(prePostProcessorPtr)
        if (prePostProcessor) {
          if (phase === 0) {
            prePostProcessor.preProcess(inputPtr, outputPtr, backend)
            return
          }
          if (phase === 1) {
            prePostProcessor.postProcess(inputPtr, outputPtr, backend)
            return
          }
          throw new Error(`Unknown pre/post phase: ${phase}`)
        }

        if (externalProcessPrePost) {
          externalProcessPrePost(prePostProcessorPtr, inputPtr, outputPtr, backend, phase)
          return
        }

        throw new Error(
          `JSPrePostProcessor with pointer ${prePostProcessorPtr} is not registered. ` +
            `Call this.prePostRegistry.set(prePostProcessorPtr, ppProcessor) before processing.`
        )
      },
    })
    return new AniraBenchmarkWeb(
      wasmInstance as unknown as ConstructorParameters<typeof AniraBenchmarkWeb>[0],
      wasmMemory
    )
  }

  protected async ensureWasmBinary(): Promise<ArrayBuffer> {
    if (!this.wasmBinary) {
      const res = await fetch(wasmUrl)
      this.wasmBinary = await res.arrayBuffer()
    }
    return this.wasmBinary
  }

  private getBenchmarkWasm() {
    return this.wasmInstance as unknown as AniraBenchmarkWasmInstance
  }

  benchmarkLogTimerResolution(): void {
    this.getBenchmarkWasm()._benchmark_log_timer_resolution()
  }

  benchmarkGetConfigCount(): number {
    return this.getBenchmarkWasm()._benchmark_get_config_count()
  }

  benchmarkGetModelFilename(configIdx: number): string {
    const ptr = this.getBenchmarkWasm()._benchmark_get_model_filename(configIdx)
    return this.getBenchmarkWasm().UTF8ToString(ptr)
  }

  benchmarkGetHostConfig(configIdx: number): HostConfig {
    const ptr = this.getBenchmarkWasm()._benchmark_get_host_config_ptr(configIdx)
    return this.HostConfig.fromPointer(ptr)
  }

  benchmarkGetBufferSize(configIdx: number): number {
    return this.getBenchmarkWasm()._benchmark_get_buffer_size(configIdx)
  }

  benchmarkGetSampleRate(configIdx: number): number {
    return this.getBenchmarkWasm()._benchmark_get_sample_rate(configIdx)
  }

  benchmarkCreateInferenceConfig(configIdx: number): InferenceConfig {
    const ptr = this.getBenchmarkWasm()._benchmark_create_inference_config(configIdx)
    return this.InferenceConfig.fromPointer(ptr)
  }

  /**
   * Like benchmarkCreateInferenceConfig but with binary model data read from the
   * WASM virtual filesystem. Used by ONNXRuntimeWebBackend which cannot fetch()
   * embedded VFS paths. C++ caches the binary per index so subsequent calls are cheap.
   */
  benchmarkCreateInferenceConfigBinary(configIdx: number): InferenceConfig {
    const ptr = (
      this.getBenchmarkWasm() as any
    )._benchmark_create_inference_config_binary(configIdx)
    return this.InferenceConfig.fromPointer(ptr)
  }

  /** C++ transfers ownership of the returned PrePostProcessor to the caller. */
  benchmarkCreatePP(
    configIdx: number,
    inferenceConfig: PossiblePointer<InferenceConfig>
  ): PrePostProcessor {
    const ppPtr = this.getBenchmarkWasm()._benchmark_create_pp(
      configIdx,
      resolvePtr(inferenceConfig)
    )
    return this.PrePostProcessor.fromPointer(ppPtr)
  }

  /**
   * Runs a single repetition of the benchmark (num_iterations timed process calls).
   * Allocates a double[] on the WASM heap, calls C++ run_single_rep, reads times, frees buffer.
   */
  benchmarkRunSingleRep(
    handler: PossiblePointer<InferenceHandler>,
    buffer: PossiblePointer<BufferF>,
    inferenceConfig: PossiblePointer<InferenceConfig>,
    hostConfig: PossiblePointer<HostConfig>,
    numIterations: number
  ): number[] {
    const wasm = this.getBenchmarkWasm()

    // Allocate double[] on WASM heap (8 bytes per double)
    const bytesNeeded = numIterations * 8
    const timesPtr = wasm._malloc(bytesNeeded)

    try {
      wasm._benchmark_run_single_rep(
        resolvePtr(handler),
        resolvePtr(buffer),
        resolvePtr(inferenceConfig),
        resolvePtr(hostConfig),
        numIterations,
        timesPtr
      )

      // Read times from WASM heap as Float64Array
      const heapF64 = new Float64Array(this.memory.buffer, timesPtr, numIterations)
      return Array.from(heapF64)
    } finally {
      wasm._free(timesPtr)
    }
  }

  async configureBenchmarkWorker(benchmarkWorker: Worker) {
    const wasmBinary = await this.ensureWasmBinary()

    const stackPtr = this.allocateWorkerStack()
    benchmarkWorker.postMessage({
      type: 'configure',
      wasmMemory: this.memory,
      wasmBinary,
      stackPtr,
    } satisfies BenchmarkConfigureMessage)
    await waitForWorkerResponse<ReadyRespose>(benchmarkWorker, 'ready')

    const performBenchmark = async (
      handler: PossiblePointer,
      buffer: PossiblePointer,
      inferenceConfig: PossiblePointer,
      hostConfig: PossiblePointer,
      numIterations: number,
      ppInfo?: { ppPtr: number; configIdx: number }
    ): Promise<number[]> => {
      benchmarkWorker.postMessage({
        type: 'runBenchmark',
        inferenceHandlerPtr: resolvePtr(handler),
        bufferPtr: resolvePtr(buffer),
        inferenceConfigPtr: resolvePtr(inferenceConfig),
        hostConfigPtr: resolvePtr(hostConfig),
        numIterations,
        ...ppInfo,
      } satisfies BenchmarkWorkerMessage)

      const response = await waitForWorkerResponse<DoneResponse>(benchmarkWorker, 'done')
      return response.times
    }

    const cleanup = () => this.freeWorkerStack(stackPtr)

    return { worker: benchmarkWorker, performBenchmark, cleanup }
  }
}
