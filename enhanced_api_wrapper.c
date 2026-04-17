#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "include/rnnoise.h"

#define FRAME_SIZE 480
#define MAX_SMOOTHING_FRAMES 5

// Enhanced wrapper structure with configurable parameters
typedef struct {
    DenoiseState *st;
    RNNModel *model;
    
    // Configurable parameters
    float vad_threshold;        // Voice Activity Detection threshold (0.0-1.0)
    float denoise_strength;     // Denoising strength (0.0-1.0)
    float smoothing_factor;     // Temporal smoothing (0.0-1.0)
    float gain_factor;          // Output gain adjustment (0.1-3.0)
    int enable_vad;             // Enable/disable VAD
    int enable_smoothing;       // Enable/disable temporal smoothing
    
    // Internal state for smoothing
    float prev_frames[MAX_SMOOTHING_FRAMES][FRAME_SIZE];
    int frame_count;
    float prev_gain;
} EnhancedRNNoiseWrapper;

// Calculate RMS energy of a frame
float calculate_rms(float *frame, int size) {
    float sum = 0.0f;
    for (int i = 0; i < size; i++) {
        sum += frame[i] * frame[i];
    }
    return sqrtf(sum / size);
}

// Simple Voice Activity Detection
int detect_voice_activity(float *frame, int size, float threshold) {
    float rms = calculate_rms(frame, size);
    float normalized_rms = rms / 32768.0f; // Normalize to 0-1 range
    return normalized_rms > threshold;
}

// Apply temporal smoothing
void apply_temporal_smoothing(EnhancedRNNoiseWrapper *wrapper, float *current_frame, float *output_frame) {
    if (!wrapper->enable_smoothing || wrapper->frame_count == 0) {
        memcpy(output_frame, current_frame, FRAME_SIZE * sizeof(float));
        return;
    }
    
    float alpha = wrapper->smoothing_factor;
    int frames_to_use = (wrapper->frame_count < MAX_SMOOTHING_FRAMES) ? wrapper->frame_count : MAX_SMOOTHING_FRAMES;
    
    for (int i = 0; i < FRAME_SIZE; i++) {
        float smoothed = current_frame[i];
        
        // Weighted average with previous frames
        for (int f = 0; f < frames_to_use; f++) {
            float weight = alpha * powf(0.8f, f + 1); // Exponential decay
            smoothed = (1.0f - weight) * smoothed + weight * wrapper->prev_frames[f][i];
        }
        
        output_frame[i] = smoothed;
    }
}

// Store frame for smoothing
void store_frame_for_smoothing(EnhancedRNNoiseWrapper *wrapper, float *frame) {
    if (!wrapper->enable_smoothing) return;
    
    // Shift previous frames
    for (int f = MAX_SMOOTHING_FRAMES - 1; f > 0; f--) {
        memcpy(wrapper->prev_frames[f], wrapper->prev_frames[f-1], FRAME_SIZE * sizeof(float));
    }
    
    // Store current frame
    memcpy(wrapper->prev_frames[0], frame, FRAME_SIZE * sizeof(float));
    wrapper->frame_count++;
}

// Initialize enhanced RNNoise with default parameters
EnhancedRNNoiseWrapper* enhanced_rnnoise_init() {
    EnhancedRNNoiseWrapper *wrapper = malloc(sizeof(EnhancedRNNoiseWrapper));
    if (!wrapper) return NULL;
    
    wrapper->model = NULL;
    wrapper->st = rnnoise_create(wrapper->model);
    
    if (!wrapper->st) {
        free(wrapper);
        return NULL;
    }
    
    // Set default parameters for natural sound
    wrapper->vad_threshold = 0.02f;      // Low threshold for sensitive VAD
    wrapper->denoise_strength = 0.7f;    // Moderate denoising
    wrapper->smoothing_factor = 0.3f;    // Moderate smoothing
    wrapper->gain_factor = 1.0f;         // No gain adjustment
    wrapper->enable_vad = 1;             // Enable VAD by default
    wrapper->enable_smoothing = 1;       // Enable smoothing by default
    
    // Initialize internal state
    memset(wrapper->prev_frames, 0, sizeof(wrapper->prev_frames));
    wrapper->frame_count = 0;
    wrapper->prev_gain = 1.0f;
    
    return wrapper;
}

// Set parameters
void enhanced_rnnoise_set_vad_threshold(EnhancedRNNoiseWrapper *wrapper, float threshold) {
    if (wrapper && threshold >= 0.0f && threshold <= 1.0f) {
        wrapper->vad_threshold = threshold;
    }
}

void enhanced_rnnoise_set_denoise_strength(EnhancedRNNoiseWrapper *wrapper, float strength) {
    if (wrapper && strength >= 0.0f && strength <= 1.0f) {
        wrapper->denoise_strength = strength;
    }
}

void enhanced_rnnoise_set_smoothing_factor(EnhancedRNNoiseWrapper *wrapper, float factor) {
    if (wrapper && factor >= 0.0f && factor <= 1.0f) {
        wrapper->smoothing_factor = factor;
    }
}

void enhanced_rnnoise_set_gain_factor(EnhancedRNNoiseWrapper *wrapper, float gain) {
    if (wrapper && gain >= 0.1f && gain <= 3.0f) {
        wrapper->gain_factor = gain;
    }
}

void enhanced_rnnoise_enable_vad(EnhancedRNNoiseWrapper *wrapper, int enable) {
    if (wrapper) {
        wrapper->enable_vad = enable;
    }
}

void enhanced_rnnoise_enable_smoothing(EnhancedRNNoiseWrapper *wrapper, int enable) {
    if (wrapper) {
        wrapper->enable_smoothing = enable;
    }
}

// Enhanced audio processing
int enhanced_rnnoise_process(EnhancedRNNoiseWrapper *wrapper, short *input, short *output, int num_frames) {
    if (!wrapper || !wrapper->st || !input || !output) return -1;
    
    float x[FRAME_SIZE];
    float processed[FRAME_SIZE];
    float smoothed[FRAME_SIZE];
    int processed_frames = 0;
    
    for (int frame = 0; frame < num_frames; frame += FRAME_SIZE) {
        int samples_to_process = (num_frames - frame < FRAME_SIZE) ? (num_frames - frame) : FRAME_SIZE;
        
        // Convert to float
        for (int i = 0; i < samples_to_process; i++) {
            x[i] = input[frame + i];
        }
        
        // Pad with zeros if needed
        for (int i = samples_to_process; i < FRAME_SIZE; i++) {
            x[i] = 0.0f;
        }
        
        // Voice Activity Detection
        int has_voice = 1; // Default to processing
        if (wrapper->enable_vad) {
            has_voice = detect_voice_activity(x, FRAME_SIZE, wrapper->vad_threshold);
        }
        
        if (has_voice) {
            // Process with RNNoise
            rnnoise_process_frame(wrapper->st, x, processed);
            
            // Apply denoising strength (blend original and denoised)
            for (int i = 0; i < FRAME_SIZE; i++) {
                processed[i] = x[i] * (1.0f - wrapper->denoise_strength) + 
                              processed[i] * wrapper->denoise_strength;
            }
        } else {
            // No voice detected, apply minimal processing
            for (int i = 0; i < FRAME_SIZE; i++) {
                processed[i] = x[i] * 0.95f; // Slight noise reduction
            }
        }
        
        // Apply temporal smoothing
        apply_temporal_smoothing(wrapper, processed, smoothed);
        
        // Store frame for next smoothing operation
        store_frame_for_smoothing(wrapper, processed);
        
        // Apply gain and convert back to short
        for (int i = 0; i < samples_to_process; i++) {
            float sample = smoothed[i] * wrapper->gain_factor;
            
            // Clamp to prevent clipping
            if (sample > 32767.0f) sample = 32767.0f;
            if (sample < -32768.0f) sample = -32768.0f;
            
            output[frame + i] = (short)sample;
        }
        
        processed_frames += samples_to_process;
    }
    
    return processed_frames;
}

// Get frame size
int enhanced_rnnoise_get_frame_size() {
    return FRAME_SIZE;
}

// Cleanup
void enhanced_rnnoise_destroy(EnhancedRNNoiseWrapper *wrapper) {
    if (!wrapper) return;
    
    if (wrapper->st) {
        rnnoise_destroy(wrapper->st);
    }
    
    if (wrapper->model) {
        rnnoise_model_free(wrapper->model);
    }
    
    free(wrapper);
}