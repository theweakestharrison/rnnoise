#!/usr/bin/env python3
"""
Test script for MULAW audio format support in RNNoise API
"""

import requests
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
import tempfile
import os

def create_mulaw_test_file():
    """Create a test MULAW audio file"""
    # Generate a 2-second sine wave at 440Hz
    duration_ms = 2000
    sine_wave = Sine(440).to_audio_segment(duration=duration_ms)
    
    # Convert to mono and set sample rate to 8kHz (common for MULAW)
    sine_wave = sine_wave.set_channels(1).set_frame_rate(8000)
    
    # Add some noise to make denoising more apparent
    noise = AudioSegment.silent(duration=duration_ms).set_channels(1).set_frame_rate(8000)
    noise_array = np.random.normal(0, 0.1, len(sine_wave.get_array_of_samples()))
    noise = noise._spawn(noise_array.astype(np.int16).tobytes())
    
    # Mix signal with noise
    mixed = sine_wave.overlay(noise)
    
    # Export as MULAW
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        # Export as MULAW format
        mixed.export(temp_file.name, format="wav", codec="pcm_mulaw")
        return temp_file.name

def test_mulaw_support():
    """Test MULAW format support"""
    print("🎵 Testing MULAW format support...")
    
    # Create test MULAW file
    mulaw_file = create_mulaw_test_file()
    print(f"✅ Created test MULAW file: {mulaw_file}")
    
    try:
        # Test the API
        url = "http://127.0.0.1:5000/denoise"
        
        with open(mulaw_file, 'rb') as f:
            files = {'audio': ('test_mulaw.wav', f, 'audio/wav')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            # Save the denoised output
            output_file = "denoised_mulaw_output.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ MULAW processing successful! Output saved to: {output_file}")
            
            # Get file info
            original_size = os.path.getsize(mulaw_file)
            output_size = os.path.getsize(output_file)
            print(f"📊 Original file size: {original_size} bytes")
            print(f"📊 Denoised file size: {output_size} bytes")
            
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    finally:
        # Clean up
        if os.path.exists(mulaw_file):
            os.unlink(mulaw_file)
            print(f"🧹 Cleaned up test file: {mulaw_file}")

def test_api_info():
    """Test the updated API info endpoint"""
    print("\n📋 Testing API info endpoint...")
    
    try:
        response = requests.get("http://127.0.0.1:5000/denoise/info")
        if response.status_code == 200:
            info = response.json()
            print("✅ API Info:")
            print(f"   Sample Rate: {info['sample_rate']} Hz")
            print(f"   Channels: {info['channels']}")
            print(f"   Bit Depth: {info['bit_depth']}")
            print(f"   Frame Size: {info['frame_size']}")
            print("   Supported Formats:")
            for fmt in info['supported_formats']:
                print(f"     - {fmt}")
            print("   Notes:")
            for note in info['notes']:
                print(f"     - {note}")
        else:
            print(f"❌ Failed to get API info: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to get API info: {str(e)}")

if __name__ == "__main__":
    print("🚀 RNNoise API MULAW Format Test")
    print("=" * 50)
    
    test_api_info()
    test_mulaw_support()
    
    print("\n✨ Test completed!")