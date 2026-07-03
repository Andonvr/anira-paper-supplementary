import {
  JSPrePostProcessor,
  resolvePtr,
  type AniraWasmInstance,
  type InferenceConfig,
  type PossiblePointer,
  type VectorBufferF,
  type VectorRingBuffer,
} from '@anira-project/anira'

const RECEPTIVE_FIELD = 13332

/**
 * JS reimplementation of SteerableNafxPrePostProcessor::pre_process().
 *
 * Pops bufferSize new samples plus a 13332-sample receptive field window
 * from the ring buffer into the model input in a single call.
 */
export class JSSteerableNafxPrePostProcessor extends JSPrePostProcessor {
  bufferSize: number = 0

  constructor(
    wasmInstance: AniraWasmInstance,
    inferenceConfig: PossiblePointer<InferenceConfig>,
    bufferSize: number
  ) {
    super(wasmInstance, inferenceConfig)
    this.bufferSize = bufferSize
  }

  override preProcess(
    ringBuffers: PossiblePointer<VectorRingBuffer>,
    buffers: PossiblePointer<VectorBufferF>,
    _backend: number
  ): void {
    const ringBuffer0 = this.wasmInstance._vector_ring_buffer_get(
      ringBuffers as number,
      0
    )
    const buffer0 = this.wasmInstance._vector_buffer_f_get(resolvePtr(buffers), 0)

    this.wasmInstance._prepostprocessor_pop_samples_from_buffer_window_offset(
      this.getPointer(),
      ringBuffer0,
      buffer0,
      this.bufferSize,
      RECEPTIVE_FIELD,
      0
    )
  }
}
