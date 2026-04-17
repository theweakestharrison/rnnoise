#!/usr/bin/env python3
"""
Comprehensive test script for multiple audio formats in RNNoise API
"""

import requests
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
import tempfile
import os
import time

def create_test_audio(format_name, export_format, **kwargs):
    """Create a test audio file in specified format"""
    # Generate a 1-second sine wave at 440Hz
    duration_ms = 1000
    sine_wave = Sine(440).to_audio_segment(duration=duration_ms)
    
    # Convert to mono
    sine_wave = sine_wave.set_channels(1)
    
    # Add some noise to make denoising more apparent
    noise = AudioSegment.silent(duration=duration_ms).set_channels(1)
    noise_array = np.random.normal(0, 0.05, len(sine_wave.get_array_of_samples()))
    noise = noise._spawn(noise_array.astype(np.int16).tobytes())
    
    # Mix signal with noise
    mixed = sine_wave.overlay(noise)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=f'.{export_format}', delete=False) as temp_file:
        mixed.export(temp_file.name, format=export_format, **kwargs)
        return temp_file.name

def test_format(format_name, file_path):
    """Test a specific audio format"""
    print(f"🎵 Testing {format_name}...")
    
    try:
        # Test the API
        url = "http://127.0.0.1:5000/denoise"
        
        with open(file_path, 'rb') as f:
            files = {'audio': (f'test_{format_name.lower()}.{file_path.split(".")[-1]}', f, 'audio/*')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            # Save the denoised output
            output_file = f"denoised_{format_name.lower()}_output.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            # Get file info
            original_size = os.path.getsize(file_path)
            output_size = os.path.getsize(output_file)
            
            print(f"  ✅ {format_name} processing successful!")
            print(f"     Original: {original_size} bytes → Denoised: {output_size} bytes")
            return True
            
        else:
            print(f"  ❌ {format_name} failed with status {response.status_code}")
            print(f"     Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ {format_name} test failed: {str(e)}")
        return False

def main():
    """Run comprehensive format tests"""
    print("🚀 RNNoise API Multiple Format Test")
    print("=" * 60)
    
    # Test formats
    test_formats = [
        ("WAV_PCM", "wav", {}),
        ("WAV_MULAW", "wav", {"codec": "pcm_mulaw"}),
        ("WAV_ALAW", "wav", {"codec": "pcm_alaw"}),
        ("MP3", "mp3", {"bitrate": "128k"}),
        ("FLAC", "flac", {}),
        ("OGG", "ogg", {}),
    ]
    
    results = {}
    test_files = []
    
    print("📁 Creating test files...")
    for format_name, export_format, kwargs in test_formats:
        try:
            file_path = create_test_audio(format_name, export_format, **kwargs)
            test_files.append((format_name, file_path))
            print(f"  ✅ Created {format_name}: {file_path}")
        except Exception as e:
            print(f"  ❌ Failed to create {format_name}: {str(e)}")
            results[format_name] = False
    
    print(f"\n🧪 Testing {len(test_files)} formats...")
    print("-" * 40)
    
    # Test each format
    for format_name, file_path in test_files:
        results[format_name] = test_format(format_name, file_path)
        time.sleep(0.5)  # Small delay between tests
    
    # Clean up test files
    print(f"\n🧹 Cleaning up test files...")
    for format_name, file_path in test_files:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"  🗑️  Removed {format_name} test file")
        except Exception as e:
            print(f"  ⚠️  Failed to remove {format_name} test file: {str(e)}")
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 30)
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    for format_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {format_name:12} {status}")
    
    print(f"\n🎯 Overall: {successful}/{total} formats supported")
    
    if successful == total:
        print("🎉 All formats tested successfully!")
    elif successful > 0:
        print("⚠️  Some formats are supported, others may need additional codecs")
    else:
        print("❌ No formats worked - check server status")

if __name__ == "__main__":
    main()