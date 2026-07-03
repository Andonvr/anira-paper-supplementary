import AniraWebBenchmarksFactory from '../../wasm/AniraWebBenchmarks'
import jsUrl from '../../wasm/AniraWebBenchmarks.js?url&no-inline'
import wasmUrl from '../../wasm/AniraWebBenchmarks.wasm?url&no-inline'
import type { AniraWasmConfig } from '@anira-project/anira'

export { wasmUrl }

export const createBenchmarkWasm = async (
  wasmMemory: WebAssembly.Memory,
  config?: AniraWasmConfig & Record<string, unknown>
) => {
  const { processBuffers, processPrePost, wasmBinary, ...rest } = config ?? {}
  const out = await AniraWebBenchmarksFactory({
    processBuffers: processBuffers ?? (() => {}),
    processPrePost: processPrePost ?? (() => {}),
    wasmBinary,
    ...rest,
    wasmMemory,
    locateFile: (path: string) => {
      if (path.endsWith('.wasm')) {
        return wasmUrl
      }
      if (path.endsWith('.js')) {
        return jsUrl
      }
      return path
    },
  })

  return {
    ...out,
    HEAPF32: out.HEAPF32 as Float32Array,
    HEAPU32: out.HEAPU32 as Float32Array,
  }
}

export type AniraBenchmarkWasmInstance = Awaited<ReturnType<typeof createBenchmarkWasm>>
