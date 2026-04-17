#!/usr/bin/env python3
"""
Enhanced RNNoise API with configurable parameters to reduce robotic artifacts
"""

import os
import io
import tempfile
import ctypes
from ctypes import c_void_p, c_char_p, c_int, c_short, c_float, POINTER
from flask import Flask, request, jsonify, send_file
import numpy as np
from scipy.io import wavfile
import wave
from pydub import AudioSegment
from pydub.utils import which

app = Flask(__name__)

# Load enhanced wrapper library
lib_path = "/root/rnnoise/libenhanced_rnnoise_wrapper.so"
if not os.path.exists(lib_path):
    raise RuntimeError(f"Enhanced RNNoise wrapper library not found at {lib_path}")

# Load the library
enhanced_lib = ctypes.CDLL(lib_path)

# Define function signatures
enhanced_lib.enhanced_rnnoise_init.restype = c_void_p
enhanced_lib.enhanced_rnnoise_init.argtypes = []

enhanced_lib.enhanced_rnnoise_destroy.restype = None
enhanced_lib.enhanced_rnnoise_destroy.argtypes = [c_void_p]

enhanced_lib.enhanced_rnnoise_process.restype = c_int
enhanced_lib.enhanced_rnnoise_process.argtypes = [c_void_p, POINTER(c_short), POINTER(c_short), c_int]

enhanced_lib.enhanced_rnnoise_get_frame_size.restype = c_int
enhanced_lib.enhanced_rnnoise_get_frame_size.argtypes = []

# Parameter setting functions
enhanced_lib.enhanced_rnnoise_set_vad_threshold.restype = None
enhanced_lib.enhanced_rnnoise_set_vad_threshold.argtypes = [c_void_p, c_float]

enhanced_lib.enhanced_rnnoise_set_denoise_strength.restype = None
enhanced_lib.enhanced_rnnoise_set_denoise_strength.argtypes = [c_void_p, c_float]

enhanced_lib.enhanced_rnnoise_set_smoothing_factor.restype = None
enhanced_lib.enhanced_rnnoise_set_smoothing_factor.argtypes = [c_void_p, c_float]

enhanced_lib.enhanced_rnnoise_set_gain_factor.restype = None
enhanced_lib.enhanced_rnnoise_set_gain_factor.argtypes = [c_void_p, c_float]

enhanced_lib.enhanced_rnnoise_enable_vad.restype = None
enhanced_lib.enhanced_rnnoise_enable_vad.argtypes = [c_void_p, c_int]

enhanced_lib.enhanced_rnnoise_enable_smoothing.restype = None
enhanced_lib.enhanced_rnnoise_enable_smoothing.argtypes = [c_void_p, c_int]

class EnhancedRNNoiseWrapper:
    def __init__(self):
        self.wrapper = enhanced_lib.enhanced_rnnoise_init()
        if not self.wrapper:
            raise RuntimeError("Failed to initialize enhanced RNNoise")
        
        # Default parameters (optimized for natural sound)
        self.current_params = {
            'vad_threshold': 0.02,      # Low threshold for sensitive detection
            'denoise_strength': 0.7,    # Moderate denoising
            'smoothing_factor': 0.3,    # Moderate smoothing
            'gain_factor': 1.0,         # No gain adjustment
            'enable_vad': True,         # Enable VAD
            'enable_smoothing': True    # Enable smoothing
        }
    
    def set_parameters(self, **kwargs):
        """Set denoising parameters"""
        for param, value in kwargs.items():
            if param in self.current_params:
                self.current_params[param] = value
                
                if param == 'vad_threshold':
                    enhanced_lib.enhanced_rnnoise_set_vad_threshold(self.wrapper, c_float(value))
                elif param == 'denoise_strength':
                    enhanced_lib.enhanced_rnnoise_set_denoise_strength(self.wrapper, c_float(value))
                elif param == 'smoothing_factor':
                    enhanced_lib.enhanced_rnnoise_set_smoothing_factor(self.wrapper, c_float(value))
                elif param == 'gain_factor':
                    enhanced_lib.enhanced_rnnoise_set_gain_factor(self.wrapper, c_float(value))
                elif param == 'enable_vad':
                    enhanced_lib.enhanced_rnnoise_enable_vad(self.wrapper, c_int(1 if value else 0))
                elif param == 'enable_smoothing':
                    enhanced_lib.enhanced_rnnoise_enable_smoothing(self.wrapper, c_int(1 if value else 0))
    
    def get_parameters(self):
        """Get current parameters"""
        return self.current_params.copy()
    
    def process_audio(self, audio_data):
        """Process audio data with enhanced algorithm"""
        if audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)
        
        # Create output array
        output_data = np.zeros_like(audio_data, dtype=np.int16)
        
        # Convert to ctypes arrays
        input_ptr = audio_data.ctypes.data_as(POINTER(c_short))
        output_ptr = output_data.ctypes.data_as(POINTER(c_short))
        
        # Process
        processed_samples = enhanced_lib.enhanced_rnnoise_process(
            self.wrapper, input_ptr, output_ptr, len(audio_data)
        )
        
        if processed_samples < 0:
            raise RuntimeError("Failed to process audio")
        
        return output_data[:processed_samples]
    
    def get_frame_size(self):
        return enhanced_lib.enhanced_rnnoise_get_frame_size()
    
    def __del__(self):
        if hasattr(self, 'wrapper') and self.wrapper:
            enhanced_lib.enhanced_rnnoise_destroy(self.wrapper)

# Global enhanced RNNoise instance
enhanced_rnnoise = EnhancedRNNoiseWrapper()

def load_audio_with_pydub(file_path):
    """Load audio file using pydub to support various formats"""
    try:
        # Try to load with pydub (supports many formats including MULAW)
        audio = AudioSegment.from_file(file_path)
        
        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Convert to 48kHz
        if audio.frame_rate != 48000:
            audio = audio.set_frame_rate(48000)
        
        # Convert to 16-bit
        audio = audio.set_sample_width(2)  # 2 bytes = 16 bits
        
        # Get raw audio data
        raw_data = audio.raw_data
        
        # Convert to numpy array
        audio_data = np.frombuffer(raw_data, dtype=np.int16)
        
        return audio_data, 48000, 1
        
    except Exception as e:
        raise Exception(f"Failed to load audio with pydub: {str(e)}")

def convert_to_48khz_mono(audio_data, sample_rate):
    """Convert audio to 48kHz mono 16-bit (fallback function)"""
    # Convert to float for processing
    if audio_data.dtype == np.int16:
        audio_float = audio_data.astype(np.float32) / 32768.0
    else:
        audio_float = audio_data.astype(np.float32)
    
    # Handle multi-channel audio
    if len(audio_float.shape) > 1:
        audio_float = np.mean(audio_float, axis=1)
    
    # Resample if needed (simple linear interpolation)
    if sample_rate != 48000:
        ratio = 48000 / sample_rate
        new_length = int(len(audio_float) * ratio)
        audio_float = np.interp(np.linspace(0, len(audio_float), new_length), 
                               np.arange(len(audio_float)), audio_float)
    
    # Convert back to int16
    audio_int16 = (audio_float * 32767).astype(np.int16)
    return audio_int16

# API Routes
@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        'name': 'Enhanced RNNoise API',
        'version': '2.0',
        'description': 'Advanced noise reduction with configurable parameters',
        'endpoints': {
            '/': 'API information',
            '/health': 'Health check',
            '/denoise': 'POST - Denoise audio file',
            '/denoise/raw': 'POST - Denoise raw PCM data',
            '/denoise/info': 'GET - Audio processing information',
            '/denoise/params': 'GET/POST - Get/Set denoising parameters',
            '/denoise/presets': 'GET - Available parameter presets'
        },
        'features': [
            'Voice Activity Detection (VAD)',
            'Configurable denoising strength',
            'Temporal smoothing',
            'Gain control',
            'Multiple audio format support'
        ]
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'frame_size': enhanced_rnnoise.get_frame_size()})

@app.route('/denoise/params', methods=['GET', 'POST'])
def denoise_params():
    """Get or set denoising parameters"""
    if request.method == 'GET':
        return jsonify({
            'current_parameters': enhanced_rnnoise.get_parameters(),
            'parameter_descriptions': {
                'vad_threshold': 'Voice Activity Detection threshold (0.0-1.0). Lower = more sensitive',
                'denoise_strength': 'Denoising strength (0.0-1.0). Higher = more aggressive',
                'smoothing_factor': 'Temporal smoothing (0.0-1.0). Higher = smoother but may blur',
                'gain_factor': 'Output gain (0.1-3.0). 1.0 = no change',
                'enable_vad': 'Enable Voice Activity Detection (true/false)',
                'enable_smoothing': 'Enable temporal smoothing (true/false)'
            }
        })
    
    elif request.method == 'POST':
        try:
            params = request.get_json()
            if not params:
                return jsonify({'error': 'No parameters provided'}), 400
            
            # Validate parameters
            valid_params = {}
            for key, value in params.items():
                if key == 'vad_threshold' and 0.0 <= value <= 1.0:
                    valid_params[key] = value
                elif key == 'denoise_strength' and 0.0 <= value <= 1.0:
                    valid_params[key] = value
                elif key == 'smoothing_factor' and 0.0 <= value <= 1.0:
                    valid_params[key] = value
                elif key == 'gain_factor' and 0.1 <= value <= 3.0:
                    valid_params[key] = value
                elif key in ['enable_vad', 'enable_smoothing'] and isinstance(value, bool):
                    valid_params[key] = value
                else:
                    return jsonify({'error': f'Invalid parameter: {key}={value}'}), 400
            
            # Apply parameters
            enhanced_rnnoise.set_parameters(**valid_params)
            
            return jsonify({
                'message': 'Parameters updated successfully',
                'updated_parameters': valid_params,
                'current_parameters': enhanced_rnnoise.get_parameters()
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to update parameters: {str(e)}'}), 500

@app.route('/denoise/presets', methods=['GET'])
def denoise_presets():
    """Get available parameter presets"""
    presets = {
        'natural': {
            'description': 'Natural sound with minimal artifacts (recommended)',
            'vad_threshold': 0.02,
            'denoise_strength': 0.7,
            'smoothing_factor': 0.3,
            'gain_factor': 1.0,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'aggressive': {
            'description': 'Strong noise reduction (may sound robotic)',
            'vad_threshold': 0.01,
            'denoise_strength': 0.95,
            'smoothing_factor': 0.1,
            'gain_factor': 1.1,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'gentle': {
            'description': 'Light noise reduction, preserves original sound',
            'vad_threshold': 0.05,
            'denoise_strength': 0.4,
            'smoothing_factor': 0.5,
            'gain_factor': 1.0,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'speech': {
            'description': 'Optimized for speech/voice recordings',
            'vad_threshold': 0.03,
            'denoise_strength': 0.8,
            'smoothing_factor': 0.4,
            'gain_factor': 1.05,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'music': {
            'description': 'Optimized for music (preserves dynamics)',
            'vad_threshold': 0.01,
            'denoise_strength': 0.5,
            'smoothing_factor': 0.6,
            'gain_factor': 1.0,
            'enable_vad': False,
            'enable_smoothing': True
        }
    }
    return jsonify({'presets': presets})

@app.route('/denoise/presets/<preset_name>', methods=['POST'])
def apply_preset(preset_name):
    """Apply a parameter preset"""
    presets = {
        'natural': {
            'vad_threshold': 0.02,
            'denoise_strength': 0.7,
            'smoothing_factor': 0.3,
            'gain_factor': 1.0,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'aggressive': {
            'vad_threshold': 0.01,
            'denoise_strength': 0.95,
            'smoothing_factor': 0.1,
            'gain_factor': 1.1,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'gentle': {
            'vad_threshold': 0.05,
            'denoise_strength': 0.4,
            'smoothing_factor': 0.5,
            'gain_factor': 1.0,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'speech': {
            'vad_threshold': 0.03,
            'denoise_strength': 0.8,
            'smoothing_factor': 0.4,
            'gain_factor': 1.05,
            'enable_vad': True,
            'enable_smoothing': True
        },
        'music': {
            'vad_threshold': 0.01,
            'denoise_strength': 0.5,
            'smoothing_factor': 0.6,
            'gain_factor': 1.0,
            'enable_vad': False,
            'enable_smoothing': True
        }
    }
    
    if preset_name not in presets:
        return jsonify({'error': f'Unknown preset: {preset_name}'}), 400
    
    try:
        enhanced_rnnoise.set_parameters(**presets[preset_name])
        return jsonify({
            'message': f'Applied preset: {preset_name}',
            'applied_parameters': presets[preset_name],
            'current_parameters': enhanced_rnnoise.get_parameters()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to apply preset: {str(e)}'}), 500

@app.route('/denoise', methods=['POST'])
def denoise_audio():
    """Denoise uploaded audio file with current parameters"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            file.save(temp_input.name)
            
            try:
                # Try to load with pydub first (supports more formats)
                try:
                    audio_data, sample_rate, channels = load_audio_with_pydub(temp_input.name)
                except Exception as pydub_error:
                    # Fallback to scipy.io.wavfile for basic WAV files
                    try:
                        sample_rate, audio_data = wavfile.read(temp_input.name)
                        audio_data = convert_to_48khz_mono(audio_data, sample_rate)
                    except Exception as scipy_error:
                        return jsonify({
                            'error': f'Failed to process audio: {str(pydub_error)}. Fallback error: {str(scipy_error)}',
                            'supported_formats': ['WAV (PCM, IEEE_FLOAT, MULAW, ALAW)', 'MP3', 'FLAC', 'OGG', 'M4A', 'AAC', 'and many more via FFmpeg']
                        }), 400
                
                # Process with Enhanced RNNoise
                denoised_data = enhanced_rnnoise.process_audio(audio_data)
                
                # Create output file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_output:
                    wavfile.write(temp_output.name, 48000, denoised_data)
                    
                    # Return the denoised file
                    return send_file(temp_output.name, 
                                   as_attachment=True, 
                                   download_name='enhanced_denoised_audio.wav',
                                   mimetype='audio/wav')
                    
            except Exception as e:
                return jsonify({'error': f'Failed to process audio: {str(e)}'}), 500
            finally:
                # Clean up input file
                if os.path.exists(temp_input.name):
                    os.unlink(temp_input.name)
                    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/denoise/raw', methods=['POST'])
def denoise_raw():
    """Denoise raw PCM data"""
    try:
        # Get raw audio data
        raw_data = request.get_data()
        if len(raw_data) == 0:
            return jsonify({'error': 'No audio data provided'}), 400
        
        # Convert to numpy array (assuming 16-bit PCM)
        audio_data = np.frombuffer(raw_data, dtype=np.int16)
        
        # Process with Enhanced RNNoise
        denoised_data = enhanced_rnnoise.process_audio(audio_data)
        
        # Return raw denoised data
        return denoised_data.tobytes(), 200, {'Content-Type': 'application/octet-stream'}
        
    except Exception as e:
        return jsonify({'error': f'Failed to process raw audio: {str(e)}'}), 500

@app.route('/denoise/info', methods=['GET'])
def denoise_info():
    """Get information about audio processing requirements"""
    return jsonify({
        'sample_rate': 48000,
        'channels': 1,
        'bit_depth': 16,
        'frame_size': enhanced_rnnoise.get_frame_size(),
        'supported_formats': [
            'WAV (PCM, IEEE_FLOAT, MULAW, ALAW)',
            'MP3', 'FLAC', 'OGG', 'M4A', 'AAC',
            'raw PCM', 'and many more via FFmpeg'
        ],
        'current_parameters': enhanced_rnnoise.get_parameters(),
        'features': [
            'Voice Activity Detection (VAD)',
            'Configurable denoising strength',
            'Temporal smoothing to reduce artifacts',
            'Gain control for volume adjustment',
            'Parameter presets for different use cases'
        ],
        'notes': [
            'Audio is automatically converted to 48kHz mono 16-bit',
            'Frame size is 480 samples (10ms at 48kHz)',
            'Uses enhanced algorithm to reduce robotic artifacts',
            'Parameters can be adjusted via /denoise/params endpoint'
        ]
    })

if __name__ == '__main__':
    print("Starting Enhanced RNNoise API Server...")
    print(f"Frame size: {enhanced_rnnoise.get_frame_size()}")
    print(f"Current parameters: {enhanced_rnnoise.get_parameters()}")
    print("Server will run on http://0.0.0.0:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)