#ifndef ANIRA_STEERABLENAFXPREPOSTPROCESSOR_H
#define ANIRA_STEERABLENAFXPREPOSTPROCESSOR_H

#include <anira/anira.h>

class SteerableNafxPrePostProcessor : public anira::PrePostProcessor
{
public:
    using anira::PrePostProcessor::PrePostProcessor;

    void pre_process(std::vector<anira::RingBuffer>& input, std::vector<anira::BufferF>& output, [[maybe_unused]] anira::InferenceBackend current_inference_backend) override {
        pop_samples_from_buffer(
            input[0], output[0],
            m_inference_config.get_tensor_output_size()[0],
            m_inference_config.get_tensor_input_size()[0] - m_inference_config.get_tensor_output_size()[0]
        );
    }
};

#endif //ANIRA_STEERABLENAFXPREPOSTPROCESSOR_H
