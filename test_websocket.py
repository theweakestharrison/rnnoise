#!/usr/bin/env python3
"""
Test script for RNNoise WebSocket streaming API
Demonstrates real-time audio denoising via WebSocket
"""

import socketio
import numpy as np
import base64
import time
import wave

# Create a SocketIO client
sio = socketio.Client()

# Global variables for testing
received_chunks = []
session_info = {}

@sio.event
def connect():
    print("Connected to RNNoise WebSocket server")

@sio.event
def connected(data):
    global session_info
    session_info = data
    print(f"Session established: {data}")
    print(f"Frame size: {data['frame_size']}")
    print(f"Sample rate: {data['sample_rate']}")

@sio.event
def disconnect():
    print("Disconnected from server")

@sio.event
def denoised_chunk(data):
    global received_chunks
    print(f"Received denoised chunk: {data['frame_size']} samples")
    
    # Decode base64 audio data
    audio_bytes = base64.b64decode(data['audio_data'])
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    received_chunks.append(audio_data)

@sio.event
def error(data):
    print(f"Error: {data['error']}")

@sio.event
def stream_info(data):
    print("Stream info:", data)

@sio.event
def buffer_cleared(data):
    print("Buffer cleared:", data)

def generate_test_audio(duration_seconds=2, sample_rate=48000):
    """Generate test audio signal (sine wave with noise)"""
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    
    # Generate sine wave (440 Hz)
    signal = np.sin(2 * np.pi * 440 * t)
    
    # Add some noise
    noise = np.random.normal(0, 0.1, len(signal))
    noisy_signal = signal + noise
    
    # Convert to 16-bit PCM
    audio_data = (noisy_signal * 32767).astype(np.int16)
    
    return audio_data

def test_websocket_streaming():
    """Test WebSocket streaming functionality"""
    try:
        # Connect to server
        print("Connecting to WebSocket server...")
        sio.connect('http://localhost:5000')
        
        # Wait for connection
        time.sleep(1)
        
        # Request stream info
        print("\nRequesting stream info...")
        sio.emit('stream_info')
        time.sleep(0.5)
        
        # Generate test audio
        print("\nGenerating test audio...")
        test_audio = generate_test_audio(duration_seconds=1)
        
        # Split into chunks (frame size)
        frame_size = session_info.get('frame_size', 480)
        print(f"Splitting audio into chunks of {frame_size} samples...")
        
        chunks = []
        for i in range(0, len(test_audio), frame_size):
            chunk = test_audio[i:i+frame_size]
            if len(chunk) == frame_size:  # Only send complete frames
                chunks.append(chunk)
        
        print(f"Sending {len(chunks)} audio chunks...")
        
        # Send audio chunks
        for i, chunk in enumerate(chunks):
            # Encode as base64
            chunk_b64 = base64.b64encode(chunk.tobytes()).decode('utf-8')
            
            # Send via WebSocket
            sio.emit('audio_chunk', {'audio_data': chunk_b64})
            
            # Small delay to simulate real-time streaming
            time.sleep(0.01)  # 10ms delay
            
            if i % 10 == 0:
                print(f"Sent chunk {i+1}/{len(chunks)}")
        
        # Wait for processing to complete
        print("Waiting for processing to complete...")
        time.sleep(2)
        
        print(f"\nReceived {len(received_chunks)} denoised chunks")
        
        # Save received audio to file
        if received_chunks:
            combined_audio = np.concatenate(received_chunks)
            
            # Save as WAV file
            with wave.open('test_websocket_output.wav', 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(48000)  # 48kHz
                wav_file.writeframes(combined_audio.tobytes())
            
            print(f"Saved denoised audio to test_websocket_output.wav")
            print(f"Original length: {len(test_audio)} samples")
            print(f"Processed length: {len(combined_audio)} samples")
        
        # Test buffer clearing
        print("\nTesting buffer clear...")
        sio.emit('clear_buffer')
        time.sleep(0.5)
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Disconnect
        sio.disconnect()
        print("Test completed")

if __name__ == '__main__':
    print("RNNoise WebSocket Streaming Test")
    print("=================================")
    print("Make sure the RNNoise API server is running on localhost:5000")
    print("Starting test in 3 seconds...")
    time.sleep(3)
    
    test_websocket_streaming()