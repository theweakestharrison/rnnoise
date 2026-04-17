#!/usr/bin/env python3
"""
RNNoise API Server
Provides HTTP endpoints for audio denoising using RNNoise
"""

import os
import io
import tempfile
import ctypes
from ctypes import c_void_p, c_char_p, c_int, c_short, POINTER
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import numpy as np
from scipy.io import wavfile
import wave
from pydub import AudioSegment
from pydub.utils import which
import base64
import threading
import queue
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rnnoise_websocket_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Load the RNNoise wrapper library
lib_path = "/root/rnnoise/librnnoise_wrapper.so"
if not os.path.exists(lib_path):
    raise RuntimeError(f"RNNoise wrapper library not found at {lib_path}")

# Load the library
rnnoise_lib = ctypes.CDLL(lib_path)

# Define function signatures
rnnoise_lib.rnnoise_wrapper_init.restype = c_void_p
rnnoise_lib.rnnoise_wrapper_init.argtypes = []

rnnoise_lib.rnnoise_wrapper_init_with_model.restype = c_void_p
rnnoise_lib.rnnoise_wrapper_init_with_model.argtypes = [c_char_p]

rnnoise_lib.rnnoise_wrapper_process.restype = c_int
rnnoise_lib.rnnoise_wrapper_process.argtypes = [c_void_p, POINTER(c_short), POINTER(c_short), c_int]

rnnoise_lib.rnnoise_wrapper_process_file.restype = c_int
rnnoise_lib.rnnoise_wrapper_process_file.argtypes = [c_void_p, c_char_p, c_char_p]

rnnoise_lib.rnnoise_wrapper_get_frame_size.restype = c_int
rnnoise_lib.rnnoise_wrapper_get_frame_size.argtypes = []

rnnoise_lib.rnnoise_wrapper_destroy.restype = None
rnnoise_lib.rnnoise_wrapper_destroy.argtypes = [c_void_p]

class RNNoiseWrapper:
    def __init__(self, model_path=None):
        if model_path:
            self.wrapper = rnnoise_lib.rnnoise_wrapper_init_with_model(model_path.encode('utf-8'))
        else:
            self.wrapper = rnnoise_lib.rnnoise_wrapper_init()
        
        if not self.wrapper:
            raise RuntimeError("Failed to initialize RNNoise")
    
    def process_audio(self, audio_data):
        """Process audio data (numpy array of int16)"""
        if audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)
        
        # Create output array
        output_data = np.zeros_like(audio_data, dtype=np.int16)
        
        # Convert to ctypes arrays
        input_ptr = audio_data.ctypes.data_as(POINTER(c_short))
        output_ptr = output_data.ctypes.data_as(POINTER(c_short))
        
        # Process
        processed_samples = rnnoise_lib.rnnoise_wrapper_process(
            self.wrapper, input_ptr, output_ptr, len(audio_data)
        )
        
        if processed_samples < 0:
            raise RuntimeError("Failed to process audio")
        
        return output_data[:processed_samples]
    
    def process_file(self, input_path, output_path):
        """Process a raw PCM file"""
        result = rnnoise_lib.rnnoise_wrapper_process_file(
            self.wrapper, 
            input_path.encode('utf-8'), 
            output_path.encode('utf-8')
        )
        return result > 0
    
    def get_frame_size(self):
        return rnnoise_lib.rnnoise_wrapper_get_frame_size()
    
    def __del__(self):
        if hasattr(self, 'wrapper') and self.wrapper:
            rnnoise_lib.rnnoise_wrapper_destroy(self.wrapper)

class AudioStreamProcessor:
    def __init__(self, rnnoise_wrapper):
        self.rnnoise = rnnoise_wrapper
        self.frame_size = rnnoise_wrapper.get_frame_size()
        self.buffer = np.array([], dtype=np.int16)
        self.lock = threading.Lock()
        
    def add_audio_chunk(self, audio_data):
        """Add audio chunk to buffer and process if enough data available"""
        with self.lock:
            # Convert base64 to numpy array if needed
            if isinstance(audio_data, str):
                try:
                    audio_bytes = base64.b64decode(audio_data)
                    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                except Exception as e:
                    raise ValueError(f"Failed to decode audio data: {str(e)}")
            
            # Add to buffer
            self.buffer = np.concatenate([self.buffer, audio_data])
            
            # Process complete frames
            processed_chunks = []
            while len(self.buffer) >= self.frame_size:
                # Extract one frame
                frame = self.buffer[:self.frame_size]
                self.buffer = self.buffer[self.frame_size:]
                
                # Process frame
                try:
                    denoised_frame = self.rnnoise.process_audio(frame)
                    processed_chunks.append(denoised_frame)
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    continue
            
            return processed_chunks
    
    def clear_buffer(self):
        """Clear the audio buffer"""
        with self.lock:
            self.buffer = np.array([], dtype=np.int16)

# Global RNNoise instance
rnnoise = RNNoiseWrapper()

# Global stream processors (one per client session)
stream_processors = {}

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
        
        return audio_data, 48000, audio.channels
        
    except Exception as e:
        raise ValueError(f"Failed to load audio file: {str(e)}")

def convert_to_48khz_mono(audio_data, sample_rate):
    """Convert audio to 48kHz mono if needed (fallback method)"""
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Resample to 48kHz if needed
    if sample_rate != 48000:
        from scipy import signal
        # Simple resampling - for production use librosa or similar
        num_samples = int(len(audio_data) * 48000 / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)
    
    return audio_data.astype(np.int16)

@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        'name': 'RNNoise API',
        'version': '1.1.0',
        'description': 'Audio denoising API using RNNoise with WebSocket streaming support',
        'frame_size': rnnoise.get_frame_size(),
        'endpoints': {
            '/': 'GET - API information',
            '/denoise': 'POST - Denoise audio file',
            '/denoise/raw': 'POST - Denoise raw PCM data',
            '/denoise/info': 'GET - Audio processing information',
            '/health': 'GET - Health check'
        },
        'websocket_events': {
            'connect': 'Connect to WebSocket for real-time streaming',
            'disconnect': 'Disconnect from WebSocket',
            'audio_chunk': 'Send audio chunk for real-time denoising',
            'denoised_chunk': 'Receive denoised audio chunk',
            'clear_buffer': 'Clear audio buffer',
            'stream_info': 'Get streaming configuration info',
            'error': 'Error messages'
        },
        'websocket_url': 'ws://localhost:5000/socket.io/',
        'streaming_info': {
            'sample_rate': 48000,
            'channels': 1,
            'bit_depth': 16,
            'frame_size': rnnoise.get_frame_size(),
            'encoding': 'base64'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'frame_size': rnnoise.get_frame_size()})

@app.route('/denoise', methods=['POST'])
def denoise_audio():
    """Denoise uploaded audio file"""
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
                            'supported_formats': ['WAV (PCM, IEEE_FLOAT)', 'MP3', 'FLAC', 'OGG', 'M4A', 'MULAW', 'ALAW', 'and many more via FFmpeg']
                        }), 400
                
                # Process with RNNoise
                denoised_data = rnnoise.process_audio(audio_data)
                
                # Create output file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_output:
                    wavfile.write(temp_output.name, 48000, denoised_data)
                    
                    # Return the denoised file
                    return send_file(temp_output.name, 
                                   as_attachment=True, 
                                   download_name='denoised_audio.wav',
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
        # Get parameters
        sample_rate = int(request.form.get('sample_rate', 48000))
        channels = int(request.form.get('channels', 1))
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio data provided'}), 400
        
        audio_file = request.files['audio']
        
        # Read raw PCM data
        raw_data = audio_file.read()
        audio_data = np.frombuffer(raw_data, dtype=np.int16)
        
        # Handle stereo to mono conversion
        if channels == 2:
            audio_data = audio_data.reshape(-1, 2)
            audio_data = np.mean(audio_data, axis=1).astype(np.int16)
        
        # Convert sample rate if needed
        if sample_rate != 48000:
            audio_data = convert_to_48khz_mono(audio_data, sample_rate)
        
        # Process with RNNoise
        denoised_data = rnnoise.process_audio(audio_data)
        
        # Return raw PCM data
        output_buffer = io.BytesIO()
        output_buffer.write(denoised_data.tobytes())
        output_buffer.seek(0)
        
        return send_file(
            output_buffer,
            as_attachment=True,
            download_name='denoised_audio.pcm',
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to process raw audio: {str(e)}'}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    # Create a new stream processor for this client
    stream_processors[request.sid] = AudioStreamProcessor(rnnoise)
    emit('connected', {
        'status': 'connected',
        'session_id': request.sid,
        'frame_size': rnnoise.get_frame_size(),
        'sample_rate': 48000,
        'channels': 1,
        'bit_depth': 16
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")
    # Clean up stream processor
    if request.sid in stream_processors:
        del stream_processors[request.sid]

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """Handle incoming audio chunk for real-time processing"""
    try:
        session_id = request.sid
        if session_id not in stream_processors:
            emit('error', {'error': 'Session not found. Please reconnect.'})
            return
        
        processor = stream_processors[session_id]
        
        # Extract audio data
        audio_data = data.get('audio_data')
        if not audio_data:
            emit('error', {'error': 'No audio data provided'})
            return
        
        # Process audio chunk
        processed_chunks = processor.add_audio_chunk(audio_data)
        
        # Send back processed chunks
        for chunk in processed_chunks:
            # Convert to base64 for transmission
            chunk_b64 = base64.b64encode(chunk.tobytes()).decode('utf-8')
            emit('denoised_chunk', {
                'audio_data': chunk_b64,
                'frame_size': len(chunk),
                'timestamp': time.time()
            })
            
    except Exception as e:
        emit('error', {'error': f'Failed to process audio chunk: {str(e)}'})

@socketio.on('clear_buffer')
def handle_clear_buffer():
    """Clear the audio buffer for this session"""
    try:
        session_id = request.sid
        if session_id in stream_processors:
            stream_processors[session_id].clear_buffer()
            emit('buffer_cleared', {'status': 'success'})
        else:
            emit('error', {'error': 'Session not found'})
    except Exception as e:
        emit('error', {'error': f'Failed to clear buffer: {str(e)}'})

@socketio.on('stream_info')
def handle_stream_info():
    """Get streaming information"""
    emit('stream_info', {
        'frame_size': rnnoise.get_frame_size(),
        'sample_rate': 48000,
        'channels': 1,
        'bit_depth': 16,
        'format': 'PCM signed 16-bit little-endian',
        'encoding': 'base64',
        'notes': [
            'Send audio data as base64 encoded PCM',
            'Audio will be processed in frames of 480 samples',
            'Optimal chunk size is multiples of frame size',
            'Real-time processing with minimal latency'
        ]
    })

@app.route('/denoise/info', methods=['GET'])
def denoise_info():
    """Get information about audio processing requirements"""
    return jsonify({
        'sample_rate': 48000,
        'channels': 1,
        'bit_depth': 16,
        'frame_size': rnnoise.get_frame_size(),
        'supported_formats': [
            'WAV (PCM, IEEE_FLOAT, MULAW, ALAW)',
            'MP3', 'FLAC', 'OGG', 'M4A', 'AAC',
            'raw PCM', 'and many more via FFmpeg'
        ],
        'notes': [
            'Audio is automatically converted to 48kHz mono 16-bit',
            'Frame size is 480 samples (10ms at 48kHz)',
            'First frame is skipped in processing (RNNoise behavior)',
            'Uses pydub + FFmpeg for format conversion'
        ],
        'websocket_streaming': {
            'enabled': True,
            'url': 'ws://localhost:5000/socket.io/',
            'events': {
                'audio_chunk': 'Send audio data for real-time processing',
                'denoised_chunk': 'Receive processed audio data',
                'stream_info': 'Get streaming configuration',
                'clear_buffer': 'Clear audio buffer'
            },
            'audio_format': {
                'encoding': 'base64',
                'sample_rate': 48000,
                'channels': 1,
                'bit_depth': 16,
                'frame_size': rnnoise.get_frame_size()
            },
            'usage_example': {
                'send': "socket.emit('audio_chunk', {'audio_data': base64_encoded_pcm})",
                'receive': "socket.on('denoised_chunk', function(data) { /* process data.audio_data */ })"
            }
        }
    })

if __name__ == '__main__':
    print("Starting RNNoise API Server with WebSocket support...")
    print(f"Frame size: {rnnoise.get_frame_size()}")
    print("HTTP API will run on http://0.0.0.0:5000")
    print("WebSocket will run on ws://0.0.0.0:5000/socket.io/")
    print("Available endpoints:")
    print("  - HTTP: /denoise, /denoise/raw, /denoise/info, /health")
    print("  - WebSocket: audio_chunk, denoised_chunk, stream_info, clear_buffer")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)