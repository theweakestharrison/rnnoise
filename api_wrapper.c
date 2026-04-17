#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "include/rnnoise.h"

#define FRAME_SIZE 480

// Simple wrapper structure to hold state
typedef struct {
    DenoiseState *st;
    RNNModel *model;
} RNNoiseWrapper;

// Initialize RNNoise with default model
RNNoiseWrapper* rnnoise_wrapper_init() {
    RNNoiseWrapper *wrapper = malloc(sizeof(RNNoiseWrapper));
    if (!wrapper) return NULL;
    
    wrapper->model = NULL;  // Use default model
    wrapper->st = rnnoise_create(wrapper->model);
    
    if (!wrapper->st) {
        free(wrapper);
        return NULL;
    }
    
    return wrapper;
}

// Initialize RNNoise with custom model file
RNNoiseWrapper* rnnoise_wrapper_init_with_model(const char* model_path) {
    RNNoiseWrapper *wrapper = malloc(sizeof(RNNoiseWrapper));
    if (!wrapper) return NULL;
    
    wrapper->model = rnnoise_model_from_filename(model_path);
    if (!wrapper->model) {
        free(wrapper);
        return NULL;
    }
    
    wrapper->st = rnnoise_create(wrapper->model);
    if (!wrapper->st) {
        rnnoise_model_free(wrapper->model);
        free(wrapper);
        return NULL;
    }
    
    return wrapper;
}

// Process audio data (expects 16-bit PCM at 48kHz)
int rnnoise_wrapper_process(RNNoiseWrapper *wrapper, short *input, short *output, int num_frames) {
    if (!wrapper || !wrapper->st || !input || !output) return -1;
    
    float x[FRAME_SIZE];
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
        
        // Process frame
        rnnoise_process_frame(wrapper->st, x, x);
        
        // Convert back to short
        for (int i = 0; i < samples_to_process; i++) {
            output[frame + i] = (short)x[i];
        }
        
        processed_frames += samples_to_process;
    }
    
    return processed_frames;
}

// Process a file
int rnnoise_wrapper_process_file(RNNoiseWrapper *wrapper, const char *input_file, const char *output_file) {
    if (!wrapper || !wrapper->st || !input_file || !output_file) return -1;
    
    FILE *f_in = fopen(input_file, "rb");
    FILE *f_out = fopen(output_file, "wb");
    
    if (!f_in || !f_out) {
        if (f_in) fclose(f_in);
        if (f_out) fclose(f_out);
        return -1;
    }
    
    float x[FRAME_SIZE];
    short tmp[FRAME_SIZE];
    int first = 1;
    int frames_processed = 0;
    
    while (1) {
        size_t read_samples = fread(tmp, sizeof(short), FRAME_SIZE, f_in);
        if (read_samples == 0) break;
        
        // Convert to float
        for (int i = 0; i < FRAME_SIZE; i++) {
            if (i < read_samples) {
                x[i] = tmp[i];
            } else {
                x[i] = 0.0f;  // Pad with zeros
            }
        }
        
        // Process frame
        rnnoise_process_frame(wrapper->st, x, x);
        
        // Convert back to short
        for (int i = 0; i < FRAME_SIZE; i++) {
            tmp[i] = (short)x[i];
        }
        
        // Skip first frame (as in original demo)
        if (!first) {
            fwrite(tmp, sizeof(short), read_samples, f_out);
        }
        first = 0;
        frames_processed++;
    }
    
    fclose(f_in);
    fclose(f_out);
    
    return frames_processed;
}

// Get frame size
int rnnoise_wrapper_get_frame_size() {
    return rnnoise_get_frame_size();
}

// Cleanup
void rnnoise_wrapper_destroy(RNNoiseWrapper *wrapper) {
    if (!wrapper) return;
    
    if (wrapper->st) {
        rnnoise_destroy(wrapper->st);
    }
    
    if (wrapper->model) {
        rnnoise_model_free(wrapper->model);
    }
    
    free(wrapper);
}