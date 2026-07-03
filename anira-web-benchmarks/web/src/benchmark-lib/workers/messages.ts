// -------------------------------
// ------ General Responses ------
// -------------------------------

export type ReadyRespose = {
  type: 'ready'
}

export type DoneResponse = {
  type: 'done'
  times: number[]
}

// ---------------------------------
// ------- Benchmark Messages ------
// ---------------------------------

export type BenchmarkConfigureMessage = {
  type: 'configure'
  wasmMemory: WebAssembly.Memory
  wasmBinary: ArrayBuffer
  stackPtr: number
}

export type RunBenchmarkMessage = {
  type: 'runBenchmark'
  inferenceHandlerPtr: number
  bufferPtr: number
  inferenceConfigPtr: number
  hostConfigPtr: number
  numIterations: number
  // Present when the PrePostProcessor is a JS class (JSHybridNNPrePostProcessor).
  // The worker registers it in its own prePostRegistry before timing starts.
  ppPtr?: number
  configIdx?: number
}

export type BenchmarkWorkerMessage = BenchmarkConfigureMessage | RunBenchmarkMessage
