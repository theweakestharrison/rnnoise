#!/usr/bin/env python3
"""
Test script for RNNoise API with Native WebSocket
Tests real-time audio streaming and denoising using native WebSocket
"""

import asyncio
import websockets
import json
import numpy as np
import base64
import wave
import time
from scipy.io import wavfile

class WebSocketAudioTester:
    def __init__(self, server_url="ws://localhost:9000"):
        self.server_url = server_url
        self.websocket = None
        self.received_chunks = []
        self.connected = False
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            print(f"Connected to {self.server_url}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Disconnected from server")
    
    async def send_message(self, message):
        """Send JSON message to server"""
        if self.websocket and self.connected:
            await self.websocket.send(json.dumps(message))
    
    async def receive_messages(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.connected = False
        except Exception as e:
            print(f"Error receiving messages: {e}")
    
    async def handle_message(self, data):
        """Handle incoming messages from server"""
        message_type = data.get("type")
        
        if message_type == "connected":
            print(f"Server confirmed connection. Client ID: {data.get('client_id')}")
            print(f"Frame size: {data.get('frame_size')}")
            print(f"Sample rate: {data.get('sample_rate')}")
            
        elif message_type == "denoised_chunk":
            # Decode and store denoised audio chunk
            chunk_data = data.get("data")
            if chunk_data:
                audio_bytes = base64.b64decode(chunk_data)
                audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                self.received_chunks.append(audio_chunk)
                print(f"Received denoised chunk: {len(audio_chunk)} samples")
                
        elif message_type == "buffer_cleared":
            print("Server confirmed buffer cleared")
            
        elif message_type == "stream_info":
            print("Stream info received:")
            for key, value in data.items():
                if key != "type":
                    print(f"  {key}: {value}")
                    
        elif message_type == "error":
            print(f"Server error: {data.get('message')}")
            
        else:
            print(f"Unknown message type: {message_type}")
    
    async def request_stream_info(self):
        """Request stream information from server"""
        await self.send_message({"type": "stream_info"})
    
    async def clear_buffer(self):
        """Clear audio buffer on server"""
        await self.send_message({"type": "clear_buffer"})
    
    async def send_audio_chunk(self, audio_data):
        """Send audio chunk to server for processing"""
        # Convert audio data to base64
        if isinstance(audio_data, np.ndarray):
            audio_bytes = audio_data.astype(np.int16).tobytes()
        else:
            audio_bytes = audio_data
            
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        await self.send_message({
            "type": "audio_chunk",
            "data": audio_b64
        })
    
    def generate_test_audio(self, duration=5.0, sample_rate=48000, frequency=440):
        """Generate test audio signal (sine wave with noise)"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Generate sine wave
        sine_wave = np.sin(2 * np.pi * frequency * t)
        
        # Add noise
        noise = np.random.normal(0, 0.3, len(sine_wave))
        noisy_signal = sine_wave + noise
        
        # Convert to int16
        audio_data = (noisy_signal * 32767).astype(np.int16)
        
        return audio_data
    
    def save_audio(self, filename, audio_data, sample_rate=48000):
        """Save audio data to WAV file"""
        if len(self.received_chunks) > 0:
            # Concatenate all received chunks
            full_audio = np.concatenate(self.received_chunks)
            wavfile.write(filename, sample_rate, full_audio)
            print(f"Saved {len(full_audio)} samples to {filename}")
        else:
            print("No audio data to save")

async def test_websocket_streaming():
    """Test WebSocket streaming functionality"""
    tester = WebSocketAudioTester()
    
    # Connect to server
    if not await tester.connect():
        return
    
    try:
        # Start listening for messages in background
        receive_task = asyncio.create_task(tester.receive_messages())
        
        # Wait a bit for connection confirmation
        await asyncio.sleep(1)
        
        # Request stream info
        print("\n--- Requesting stream info ---")
        await tester.request_stream_info()
        await asyncio.sleep(1)
        
        # Generate test audio
        print("\n--- Generating test audio ---")
        test_audio = tester.generate_test_audio(duration=2.0)  # 2 seconds of audio
        print(f"Generated {len(test_audio)} samples of test audio")
        
        # Clear buffer before starting
        print("\n--- Clearing buffer ---")
        await tester.clear_buffer()
        await asyncio.sleep(0.5)
        
        # Send audio in chunks
        print("\n--- Sending audio chunks ---")
        chunk_size = 480  # RNNoise frame size
        chunks_sent = 0
        
        for i in range(0, len(test_audio), chunk_size):
            chunk = test_audio[i:i+chunk_size]
            if len(chunk) == chunk_size:  # Only send complete frames
                await tester.send_audio_chunk(chunk)
                chunks_sent += 1
                print(f"Sent chunk {chunks_sent}: {len(chunk)} samples")
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)  # 10ms delay
        
        # Wait for all responses
        print(f"\n--- Waiting for responses (sent {chunks_sent} chunks) ---")
        await asyncio.sleep(2)
        
        # Test buffer clearing
        print("\n--- Testing buffer clear ---")
        await tester.clear_buffer()
        await asyncio.sleep(0.5)
        
        # Save received audio
        print("\n--- Saving results ---")
        if tester.received_chunks:
            combined_audio = np.concatenate(tester.received_chunks)
            tester.save_audio("test_native_websocket_output.wav", combined_audio)
        else:
            print("No audio chunks received to save")
        
        print(f"\nTest completed!")
        print(f"Chunks sent: {chunks_sent}")
        print(f"Chunks received: {len(tester.received_chunks)}")
        
        if len(tester.received_chunks) > 0:
            total_samples = sum(len(chunk) for chunk in tester.received_chunks)
            print(f"Total samples received: {total_samples}")
            print(f"Duration: {total_samples / 48000:.2f} seconds")
        
        # Cancel the receive task
        receive_task.cancel()
        
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        await tester.disconnect()

async def test_connection_only():
    """Simple connection test"""
    print("Testing WebSocket connection...")
    
    try:
        websocket = await websockets.connect("ws://localhost:9000")
        print("✓ Connection successful")
        
        # Send a simple message
        await websocket.send(json.dumps({"type": "stream_info"}))
        
        # Wait for response
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(response)
        print(f"✓ Received response: {data.get('type')}")
        
        await websocket.close()
        print("✓ Connection closed successfully")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    print("RNNoise Native WebSocket Test")
    print("=" * 40)
    
    # First test simple connection
    print("\n1. Testing connection...")
    asyncio.run(test_connection_only())
    
    print("\n" + "=" * 40)
    print("2. Testing full streaming...")
    
    # Then test full streaming
    asyncio.run(test_websocket_streaming())