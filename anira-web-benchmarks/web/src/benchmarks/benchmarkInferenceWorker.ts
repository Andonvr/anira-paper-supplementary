import { setupInferenceWorker, ONNXRuntimeWebBackend } from '@anira-project/anira'
import { AniraBenchmarkWeb } from '../benchmark-lib'
import { JSBypassBackend } from '../benchmark-lib/backends/JSBypassBackend'

setupInferenceWorker({ JSBypassBackend, ONNXRuntimeWebBackend }, AniraBenchmarkWeb.create)
