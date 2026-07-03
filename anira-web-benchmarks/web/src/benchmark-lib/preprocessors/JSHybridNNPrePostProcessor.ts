import {
  JSPrePostProcessor,
  resolvePtr,
  type AniraWasmInstance,
  type InferenceConfig,
  type PossiblePointer,
  type VectorBufferF,
  type VectorRingBuffer,
} from '@anira-project/anira'

const CONTEXT_SAMPLES = 150
const NUM_OUTPUT_SAMPLES = 1

/**
 * JS reimplementation of HybridNNPrePostProcessor::pre_process().
 *
 * Constructs the batched sliding-window tensor expected by GuitarLSTM:
 * for each batch element, pops one new sample plus 149 past samples from
 * the ring buffer into the model input at the correct offset.
 *
 * batchSize must be set before preProcess() is called. When constructing
 * via createFromPointer() (benchmark worker), set it manually afterwards.
 */
export class JSHybridNNPrePostProcessor extends JSPrePostProcessor {
  batchSize: number = 0

  constructor(
    wasmInstance: AniraWasmInstance,
    inferenceConfig: PossiblePointer<InferenceConfig>,
    batchSize: number
  ) {
    super(wasmInstance, inferenceConfig)
    this.batchSize = batchSize
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

    for (let batch = 0; batch < this.batchSize; batch++) {
      const offset = batch * CONTEXT_SAMPLES
      this.wasmInstance._prepostprocessor_pop_samples_from_buffer_window_offset(
        this.getPointer(),
        ringBuffer0,
        buffer0,
        NUM_OUTPUT_SAMPLES,
        CONTEXT_SAMPLES - NUM_OUTPUT_SAMPLES,
        offset
      )
    }
  }
}
