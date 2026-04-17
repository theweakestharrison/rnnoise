#ifndef ENHANCED_API_WRAPPER_H
#define ENHANCED_API_WRAPPER_H

#ifdef __cplusplus
extern "C" {
#endif

// Forward declaration
typedef struct EnhancedRNNoiseWrapper EnhancedRNNoiseWrapper;

// Initialization and cleanup
EnhancedRNNoiseWrapper* enhanced_rnnoise_init();
void enhanced_rnnoise_destroy(EnhancedRNNoiseWrapper *wrapper);

// Parameter configuration
void enhanced_rnnoise_set_vad_threshold(EnhancedRNNoiseWrapper *wrapper, float threshold);
void enhanced_rnnoise_set_denoise_strength(EnhancedRNNoiseWrapper *wrapper, float strength);
void enhanced_rnnoise_set_smoothing_factor(EnhancedRNNoiseWrapper *wrapper, float factor);
void enhanced_rnnoise_set_gain_factor(EnhancedRNNoiseWrapper *wrapper, float gain);
void enhanced_rnnoise_enable_vad(EnhancedRNNoiseWrapper *wrapper, int enable);
void enhanced_rnnoise_enable_smoothing(EnhancedRNNoiseWrapper *wrapper, int enable);

// Audio processing
int enhanced_rnnoise_process(EnhancedRNNoiseWrapper *wrapper, short *input, short *output, int num_frames);

// Utility
int enhanced_rnnoise_get_frame_size();

#ifdef __cplusplus
}
#endif

#endif // ENHANCED_API_WRAPPER_H