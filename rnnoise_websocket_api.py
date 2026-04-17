#!/usr/bin/env python3
"""
RNNoise API Server with Native WebSocket
Provides HTTP endpoints and WebSocket streaming for audio denoising using RNNoise
"""

import os
import io
import tempfile
import ctypes
from ctypes import c_void_p, c_char_p, c_int, c_short, POINTER
from flask import Flask, request, jsonify, send_file
import numpy as np
from scipy.io import wavfile
import wave
from pydub import AudioSegment
from pydub.utils import which
import base64
import threading
import queue
import time
import asyncio
import websockets
import json
from threading import Thread

app = Flask(__name__)

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
        if model_path and os.path.exists(model_path):
            self.state = rnnoise_lib.rnnoise_wrapper_init_with_model(model_path.encode('utf-8'))
        else:
            self.state = rnnoise_lib.rnnoise_wrapper_init()
        
        if not self.state:
            raise RuntimeError("Failed to initialize RNNoise")
    
    def process_audio(self, audio_data):
        """Process audio data and return denoised version"""
        if len(audio_data) == 0:
            return np.array([], dtype=np.int16)
        
        # Ensure audio_data is int16
        if audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)
        
        # Create output buffer
        output_data = np.zeros_like(audio_data, dtype=np.int16)
        
        # Process the audio
        input_ptr = audio_data.ctypes.data_as(POINTER(c_short))
        output_ptr = output_data.ctypes.data_as(POINTER(c_short))
        
        result = rnnoise_lib.rnnoise_wrapper_process(self.state, input_ptr, output_ptr, len(audio_data))
        
        if result != 0:
            raise RuntimeError(f"RNNoise processing failed with code {result}")
        
        return output_data
    
    def process_file(self, input_path, output_path):
        """Process an entire audio file"""
        result = rnnoise_lib.rnnoise_wrapper_process_file(
            self.state, 
            input_path.encode('utf-8'), 
            output_path.encode('utf-8')
        )
        return result == 0
    
    def get_frame_size(self):
        """Get the frame size used by RNNoise"""
        return rnnoise_lib.rnnoise_wrapper_get_frame_size()
    
    def __del__(self):
        if hasattr(self, 'state') and self.state:
            rnnoise_lib.rnnoise_wrapper_destroy(self.state)

class AudioStreamProcessor:
    def __init__(self, rnnoise_wrapper):
        self.rnnoise = rnnoise_wrapper
        self.buffer = queue.Queue()
        self.frame_size = rnnoise_wrapper.get_frame_size()
        
    def add_audio_chunk(self, audio_data):
        """Add audio chunk to buffer and process if we have enough data"""
        # Handle base64 encoded data
        if isinstance(audio_data, str):
            try:
                audio_bytes = base64.b64decode(audio_data)
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            except Exception as e:
                raise ValueError(f"Failed to decode base64 audio data: {e}")
        
        # Ensure it's numpy array
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.int16)
        
        # Add to buffer
        for sample in audio_data:
            self.buffer.put(sample)
        
        # Process complete frames
        processed_chunks = []
        while self.buffer.qsize() >= self.frame_size:
            # Extract one frame
            frame = []
            for _ in range(self.frame_size):
                frame.append(self.buffer.get())
            
            frame_array = np.array(frame, dtype=np.int16)
            denoised_frame = self.rnnoise.process_audio(frame_array)
            processed_chunks.append(denoised_frame)
        
        return processed_chunks
    
    def clear_buffer(self):
        """Clear the audio buffer"""
        while not self.buffer.empty():
            self.buffer.get()

# Global instances
rnnoise = RNNoiseWrapper()
websocket_clients = set()
stream_processors = {}

def load_audio_with_pydub(file_path):
    """Load audio file using pydub with format detection"""
    try:
        # Try to load the audio file
        audio = AudioSegment.from_file(file_path)
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples(), dtype=np.int16)
        
        # Handle stereo audio
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
            samples = samples.mean(axis=1).astype(np.int16)  # Convert to mono
        
        return samples, audio.frame_rate
    except Exception as e:
        raise ValueError(f"Failed to load audio file: {e}")

def convert_to_48khz_mono(audio_data, sample_rate):
    """Convert audio to 48kHz mono format required by RNNoise"""
    if sample_rate == 48000:
        return audio_data
    
    # Use scipy for resampling
    from scipy import signal
    
    # Calculate resampling ratio
    ratio = 48000 / sample_rate
    num_samples = int(len(audio_data) * ratio)
    
    # Resample
    resampled = signal.resample(audio_data, num_samples)
    return resampled.astype(np.int16)

# HTTP Routes
@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        "name": "RNNoise API with Native WebSocket",
        "version": "2.0.0",
        "description": "Audio denoising API using RNNoise with native WebSocket streaming support",
        "endpoints": [
            "/denoise",
            "/denoise/raw", 
            "/denoise/info",
            "/health"
        ],
        "websocket_url": "ws://localhost:8080",
        "websocket_protocol": {
            "connect": "Establish WebSocket connection",
            "audio_chunk": "Send audio data for processing",
            "denoised_chunk": "Receive processed audio data",
            "stream_info": "Get streaming format information",
            "clear_buffer": "Clear audio buffer",
            "error": "Error messages"
        },
        "streaming_info": {
            "sample_rate": 48000,
            "channels": 1,
            "bit_depth": 16,
            "frame_size": rnnoise.get_frame_size(),
            "encoding": "base64"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "frame_size": rnnoise.get_frame_size()})

@app.route('/denoise', methods=['POST'])
def denoise_audio():
    """Denoise uploaded audio file"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            audio_file.save(temp_input.name)
            
            # Load and process audio
            audio_data, sample_rate = load_audio_with_pydub(temp_input.name)
            
            # Convert to 48kHz mono if needed
            if sample_rate != 48000:
                audio_data = convert_to_48khz_mono(audio_data, sample_rate)
            
            # Process with RNNoise
            denoised_audio = rnnoise.process_audio(audio_data)
            
            # Save denoised audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_output:
                wavfile.write(temp_output.name, 48000, denoised_audio)
                
                # Clean up input file
                os.unlink(temp_input.name)
                
                return send_file(temp_output.name, as_attachment=True, 
                               download_name='denoised_audio.wav', mimetype='audio/wav')
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/denoise/raw', methods=['POST'])
def denoise_raw():
    """Denoise raw PCM audio data"""
    try:
        # Get raw audio data from request
        audio_data = request.get_data()
        
        if len(audio_data) == 0:
            return jsonify({"error": "No audio data provided"}), 400
        
        # Convert bytes to numpy array (assuming 16-bit PCM)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Process with RNNoise
        denoised_audio = rnnoise.process_audio(audio_array)
        
        # Return raw PCM data
        return denoised_audio.tobytes(), 200, {'Content-Type': 'application/octet-stream'}
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/denoise/info', methods=['GET'])
def denoise_info():
    """Get detailed API information including WebSocket details"""
    return jsonify({
        "api_info": {
            "name": "RNNoise API with Native WebSocket",
            "version": "2.0.0",
            "description": "Audio denoising API using RNNoise with native WebSocket streaming"
        },
        "websocket": {
            "enabled": True,
            "url": "ws://localhost:8080",
            "protocol": "native WebSocket (not Socket.IO)",
            "message_format": "JSON",
            "events": {
                "audio_chunk": {
                    "direction": "client -> server",
                    "description": "Send audio data for real-time processing",
                    "format": {
                        "type": "audio_chunk",
                        "data": "base64 encoded PCM audio data"
                    }
                },
                "denoised_chunk": {
                    "direction": "server -> client", 
                    "description": "Receive processed audio data",
                    "format": {
                        "type": "denoised_chunk",
                        "data": "base64 encoded denoised PCM audio data"
                    }
                },
                "stream_info": {
                    "direction": "bidirectional",
                    "description": "Get/send streaming format information"
                },
                "clear_buffer": {
                    "direction": "client -> server",
                    "description": "Clear the audio processing buffer"
                },
                "error": {
                    "direction": "server -> client",
                    "description": "Error messages and notifications"
                }
            }
        },
        "audio_format": {
            "encoding": "PCM 16-bit",
            "sample_rate": 48000,
            "channels": 1,
            "bit_depth": 16,
            "frame_size": rnnoise.get_frame_size(),
            "transmission_encoding": "base64"
        },
        "usage_examples": {
            "send_audio": {
                "type": "audio_chunk",
                "data": "base64_encoded_pcm_data_here"
            },
            "receive_audio": {
                "type": "denoised_chunk", 
                "data": "base64_encoded_denoised_data_here"
            }
        }
    })

# WebSocket Handler
async def handle_websocket(websocket, path):
    """Handle WebSocket connections"""
    client_id = id(websocket)
    websocket_clients.add(websocket)
    stream_processors[client_id] = AudioStreamProcessor(rnnoise)
    
    print(f"WebSocket client {client_id} connected")
    
    # Send connection confirmation
    await websocket.send(json.dumps({
        "type": "connected",
        "client_id": client_id,
        "frame_size": rnnoise.get_frame_size(),
        "sample_rate": 48000
    }))
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "audio_chunk":
                    # Process audio chunk
                    audio_data = data.get("data")
                    if audio_data:
                        processor = stream_processors[client_id]
                        denoised_chunks = processor.add_audio_chunk(audio_data)
                        
                        # Send back denoised chunks
                        for chunk in denoised_chunks:
                            chunk_b64 = base64.b64encode(chunk.tobytes()).decode('utf-8')
                            await websocket.send(json.dumps({
                                "type": "denoised_chunk",
                                "data": chunk_b64
                            }))
                
                elif message_type == "clear_buffer":
                    # Clear audio buffer
                    if client_id in stream_processors:
                        stream_processors[client_id].clear_buffer()
                        await websocket.send(json.dumps({
                            "type": "buffer_cleared"
                        }))
                
                elif message_type == "stream_info":
                    # Send stream information
                    await websocket.send(json.dumps({
                        "type": "stream_info",
                        "sample_rate": 48000,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": rnnoise.get_frame_size(),
                        "encoding": "base64"
                    }))
                
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error", 
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Cleanup
        websocket_clients.discard(websocket)
        if client_id in stream_processors:
            del stream_processors[client_id]
        print(f"WebSocket client {client_id} disconnected")

def run_websocket_server():
    """Run the WebSocket server"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    start_server = websockets.serve(handle_websocket, "0.0.0.0", 8080)
    print("WebSocket server starting on ws://0.0.0.0:8080")
    
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == '__main__':
    print("Starting RNNoise API Server with Native WebSocket support...")
    print(f"Frame size: {rnnoise.get_frame_size()}")
    print("HTTP API will run on http://0.0.0.0:5000")
    print("WebSocket will run on ws://0.0.0.0:8080")
    print("Available endpoints:")
    print("  - HTTP: /denoise, /denoise/raw, /denoise/info, /health")
    print("  - WebSocket: audio_chunk, denoised_chunk, stream_info, clear_buffer")
    
    # Start WebSocket server in a separate thread
    websocket_thread = Thread(target=run_websocket_server, daemon=True)
    websocket_thread.start()
    
    # Start Flask HTTP server
    app.run(host='0.0.0.0', port=5000, debug=True)