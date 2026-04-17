#ifndef RNNOISE_API_WRAPPER_H
#define RNNOISE_API_WRAPPER_H

#ifdef __cplusplus
extern "C" {
#endif

// Opaque wrapper structure
typedef struct RNNoiseWrapper RNNoiseWrapper;

/**
 * Initialize RNNoise with default model
 * Returns NULL on failure
 */
RNNoiseWrapper* rnnoise_wrapper_init();

/**
 * Initialize RNNoise with custom model file
 * Returns NULL on failure
 */
RNNoiseWrapper* rnnoise_wrapper_init_with_model(const char* model_path);

/**
 * Process audio data (expects 16-bit PCM at 48kHz)
 * input: input audio samples
 * output: output denoised audio samples
 * num_frames: number of samples to process
 * Returns number of processed samples, -1 on error
 */
int rnnoise_wrapper_process(RNNoiseWrapper *wrapper, short *input, short *output, int num_frames);

/**
 * Process a raw PCM file
 * input_file: path to input raw PCM file (16-bit, 48kHz)
 * output_file: path to output denoised file
 * Returns number of frames processed, -1 on error
 */
int rnnoise_wrapper_process_file(RNNoiseWrapper *wrapper, const char *input_file, const char *output_file);

/**
 * Get the frame size used by RNNoise
 */
int rnnoise_wrapper_get_frame_size();

/**
 * Cleanup and free resources
 */
void rnnoise_wrapper_destroy(RNNoiseWrapper *wrapper);

#ifdef __cplusplus
}
#endif

#endif // RNNOISE_API_WRAPPER_H