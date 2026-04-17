#!/usr/bin/env python3
"""
Simple RNNoise WebSocket Server
Provides WebSocket streaming for audio denoising using RNNoise
"""

import os
import ctypes
from ctypes import c_void_p, c_char_p, c_int, c_short, POINTER
import numpy as np
import base64
import asyncio
import websockets
import json

# Load the RNNoise wrapper library
lib_path = "/home/primas/rnnoise/librnnoise_wrapper.so"
if not os.path.exists(lib_path):
    raise RuntimeError(f"RNNoise wrapper library not found at {lib_path}")

# Load the library
rnnoise_lib = ctypes.CDLL(lib_path)

# Define function signatures
rnnoise_lib.rnnoise_wrapper_init.restype = c_void_p
rnnoise_lib.rnnoise_wrapper_init.argtypes = []

rnnoise_lib.rnnoise_wrapper_process.restype = c_int
rnnoise_lib.rnnoise_wrapper_process.argtypes = [c_void_p, POINTER(c_short), POINTER(c_short), c_int]

rnnoise_lib.rnnoise_wrapper_get_frame_size.restype = c_int
rnnoise_lib.rnnoise_wrapper_get_frame_size.argtypes = []

rnnoise_lib.rnnoise_wrapper_destroy.restype = None
rnnoise_lib.rnnoise_wrapper_destroy.argtypes = [c_void_p]

class RNNoiseWrapper:
    def __init__(self):
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
        
        # Process - returns number of processed samples
        processed_samples = rnnoise_lib.rnnoise_wrapper_process(
            self.state, input_ptr, output_ptr, len(audio_data)
        )
        
        if processed_samples < 0:
            raise RuntimeError(f"RNNoise processing failed with code {processed_samples}")
        
        return output_data[:processed_samples]
    
    def get_frame_size(self):
        """Get the frame size used by RNNoise"""
        return rnnoise_lib.rnnoise_wrapper_get_frame_size()
    
    def __del__(self):
        if hasattr(self, 'state') and self.state:
            rnnoise_lib.rnnoise_wrapper_destroy(self.state)

class AudioStreamProcessor:
    def __init__(self, rnnoise_wrapper):
        self.rnnoise = rnnoise_wrapper
        self.buffer = []
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
        self.buffer.extend(audio_data.tolist())
        
        # Process complete frames
        processed_chunks = []
        while len(self.buffer) >= self.frame_size:
            # Extract one frame
            frame = self.buffer[:self.frame_size]
            self.buffer = self.buffer[self.frame_size:]
            
            frame_array = np.array(frame, dtype=np.int16)
            denoised_frame = self.rnnoise.process_audio(frame_array)
            processed_chunks.append(denoised_frame)
        
        return processed_chunks
    
    def clear_buffer(self):
        """Clear the audio buffer"""
        self.buffer = []

# Global instances
rnnoise = RNNoiseWrapper()
stream_processors = {}

async def handle_websocket(websocket):
    """Handle WebSocket connections"""
    client_id = id(websocket)
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
        if client_id in stream_processors:
            del stream_processors[client_id]
        print(f"WebSocket client {client_id} disconnected")

async def main():
    """Main server function"""
    print("Starting Simple RNNoise WebSocket Server...")
    print(f"Frame size: {rnnoise.get_frame_size()}")
    print("WebSocket server will run on ws://0.0.0.0:9000")
    print("Available message types:")
    print("  - audio_chunk: Send audio data for processing")
    print("  - denoised_chunk: Receive processed audio data")
    print("  - stream_info: Get streaming format information")
    print("  - clear_buffer: Clear audio buffer")
    
    # Start WebSocket server
    server = await websockets.serve(handle_websocket, "0.0.0.0", 9000)
    
    print("Server started successfully!")
    
    # Keep server running
    await server.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")