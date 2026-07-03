import { JSBackendBase, BufferF, VectorBufferF } from '@anira-project/anira'

/**
 * JS-side bypass backend. Mirrors the behaviour of the C++ CUSTOM (no-op) backend:
 * copies input tensors to output tensors in JavaScript, crossing the WASM→JS boundary
 * on every inference call. Used to measure that boundary overhead in isolation.
 */
export class JSBypassBackend extends JSBackendBase {
  override process(inputVecPtr: number, outputVecPtr: number): void {
    const heapF32 = this.wasmInstance.HEAPF32
    const inputVec = this.wrapPointer(VectorBufferF, inputVecPtr)
    const outputVec = this.wrapPointer(VectorBufferF, outputVecPtr)

    const inputSize = inputVec.size()
    const outputSize = outputVec.size()

    for (let tensorIdx = 0; tensorIdx < Math.min(inputSize, outputSize); tensorIdx++) {
      const inputBuffer = this.wrapPointer(BufferF, inputVec.get(tensorIdx))
      const outputBuffer = this.wrapPointer(BufferF, outputVec.get(tensorIdx))

      const inputChannels = inputBuffer.getNumChannels()
      const inputSamples = inputBuffer.getNumSamples()
      const outputChannels = outputBuffer.getNumChannels()
      const outputSamples = outputBuffer.getNumSamples()

      const equalChannels = inputChannels === outputChannels
      const sampleDiff = inputSamples - outputSamples

      if (equalChannels && sampleDiff >= 0) {
        for (let channel = 0; channel < inputChannels; channel++) {
          const readPtr = inputBuffer.getReadPointer(channel)
          const writePtr = outputBuffer.getWritePointer(channel)

          const inputOffset = readPtr >> 2
          const outputOffset = writePtr >> 2

          for (let i = 0; i < outputSamples; i++) {
            heapF32[outputOffset + i] = heapF32[inputOffset + i + sampleDiff]
          }
        }
      } else {
        outputBuffer.clear()
      }
    }
  }
}
