import type { JSPrePostProcessor } from '@anira-project/anira'
import { AniraBenchmarkWeb } from '../AniraBenchmarkWeb'
import { JSHybridNNPrePostProcessor } from '../preprocessors/JSHybridNNPrePostProcessor'
import { JSSteerableNafxPrePostProcessor } from '../preprocessors/JSSteerableNafxPrePostProcessor'
import type { BenchmarkWorkerMessage, DoneResponse, ReadyRespose } from './messages'

let aniraWeb: AniraBenchmarkWeb | null = null
let prePostRegistry = new Map<number, JSPrePostProcessor>()

self.onmessage = async (e: MessageEvent<BenchmarkWorkerMessage>) => {
  if (e.data.type === 'configure') {
    const { wasmMemory, wasmBinary, stackPtr } = e.data
    aniraWeb = await AniraBenchmarkWeb.create(
      {
        wasmBinary,
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

          throw new Error(
            `JSPrePostProcessor with pointer ${prePostProcessorPtr} is not registered. ` +
              `Call this.prePostRegistry.set(prePostProcessorPtr, prePostProcessor) before processing.`
          )
        },
      },
      wasmMemory
    )
    aniraWeb.stackRestore(stackPtr)
    self.postMessage({ type: 'ready' } satisfies ReadyRespose)
  }
  if (e.data.type === 'runBenchmark') {
    if (!aniraWeb) {
      console.error('Worker not configured yet')
      return
    }
    const {
      inferenceHandlerPtr,
      bufferPtr,
      inferenceConfigPtr,
      hostConfigPtr,
      numIterations,
      ppPtr,
      configIdx,
    } = e.data

    // If the active PrePostProcessor is a JS class, register a view of it on
    // this worker's WASM instance so the processPrePost callback can reach it.
    if (ppPtr !== undefined && configIdx !== undefined) {
      const filename   = aniraWeb.benchmarkGetModelFilename(configIdx)
      const bufferSize = aniraWeb.benchmarkGetBufferSize(configIdx)
      const jsPP = filename.includes('steerable-nafx')
        ? JSSteerableNafxPPFromPointer(aniraWeb, ppPtr, bufferSize)
        : JSHybridNNPPFromPointer(aniraWeb, ppPtr, bufferSize)
      prePostRegistry.set(ppPtr, jsPP)
    }

    const times = aniraWeb.benchmarkRunSingleRep(
      inferenceHandlerPtr,
      bufferPtr,
      inferenceConfigPtr,
      hostConfigPtr,
      numIterations
    )
    self.postMessage({ type: 'done', times } satisfies DoneResponse)
    if (ppPtr) {
      prePostRegistry.delete(ppPtr)
    }
  }
}

function JSHybridNNPPFromPointer(
  aniraWeb: AniraBenchmarkWeb,
  ptr: number,
  batchSize: number
): JSHybridNNPrePostProcessor {
  const pp = (JSHybridNNPrePostProcessor as any).createFromPointer(
    aniraWeb.getWasmInstance(),
    ptr
  ) as JSHybridNNPrePostProcessor
  pp.batchSize = batchSize
  return pp
}

function JSSteerableNafxPPFromPointer(
  aniraWeb: AniraBenchmarkWeb,
  ptr: number,
  bufferSize: number
): JSSteerableNafxPrePostProcessor {
  const pp = (JSSteerableNafxPrePostProcessor as any).createFromPointer(
    aniraWeb.getWasmInstance(),
    ptr
  ) as JSSteerableNafxPrePostProcessor
  pp.bufferSize = bufferSize
  return pp
}
