#!/usr/bin/env python3
"""
Test script for Enhanced RNNoise API with configurable parameters
"""

import requests
import numpy as np
import wave
import tempfile
import os
import json
import time

# API base URL
BASE_URL = "http://localhost:5001"

def create_test_audio(filename, duration=3.0, sample_rate=48000, add_noise=True):
    """Create a test audio file with speech-like signal and noise"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create speech-like signal (multiple frequencies)
    speech = (np.sin(2 * np.pi * 440 * t) * 0.3 +  # A4 note
              np.sin(2 * np.pi * 880 * t) * 0.2 +  # A5 note
              np.sin(2 * np.pi * 220 * t) * 0.1)   # A3 note
    
    # Add envelope to make it more speech-like
    envelope = np.exp(-t * 0.5) * (1 + 0.5 * np.sin(2 * np.pi * 2 * t))
    speech = speech * envelope
    
    if add_noise:
        # Add white noise
        noise = np.random.normal(0, 0.1, len(speech))
        signal = speech + noise
    else:
        signal = speech
    
    # Normalize and convert to int16
    signal = signal / np.max(np.abs(signal)) * 0.8
    audio_data = (signal * 32767).astype(np.int16)
    
    # Save as WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return filename

def test_api_info():
    """Test API information endpoints"""
    print("=== Testing API Information ===")
    
    # Test main endpoint
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        info = response.json()
        print(f"✓ API Name: {info['name']}")
        print(f"✓ Version: {info['version']}")
        print(f"✓ Features: {', '.join(info['features'])}")
    else:
        print(f"✗ Failed to get API info: {response.status_code}")
        return False
    
    # Test health check
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✓ Health: {health['status']}")
        print(f"✓ Frame size: {health['frame_size']}")
    else:
        print(f"✗ Health check failed: {response.status_code}")
        return False
    
    # Test denoise info
    response = requests.get(f"{BASE_URL}/denoise/info")
    if response.status_code == 200:
        info = response.json()
        print(f"✓ Sample rate: {info['sample_rate']} Hz")
        print(f"✓ Supported formats: {len(info['supported_formats'])} formats")
        print(f"✓ Current parameters: {info['current_parameters']}")
    else:
        print(f"✗ Denoise info failed: {response.status_code}")
        return False
    
    return True

def test_parameter_management():
    """Test parameter getting and setting"""
    print("\n=== Testing Parameter Management ===")
    
    # Get current parameters
    response = requests.get(f"{BASE_URL}/denoise/params")
    if response.status_code == 200:
        params_info = response.json()
        print(f"✓ Current parameters: {params_info['current_parameters']}")
        print(f"✓ Parameter descriptions available: {len(params_info['parameter_descriptions'])}")
    else:
        print(f"✗ Failed to get parameters: {response.status_code}")
        return False
    
    # Test setting parameters
    new_params = {
        'vad_threshold': 0.03,
        'denoise_strength': 0.8,
        'smoothing_factor': 0.4,
        'gain_factor': 1.1,
        'enable_vad': True,
        'enable_smoothing': True
    }
    
    response = requests.post(f"{BASE_URL}/denoise/params", 
                           json=new_params,
                           headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Parameters updated: {result['updated_parameters']}")
    else:
        print(f"✗ Failed to set parameters: {response.status_code}")
        return False
    
    # Test invalid parameters
    invalid_params = {'vad_threshold': 2.0}  # Invalid value > 1.0
    response = requests.post(f"{BASE_URL}/denoise/params", 
                           json=invalid_params,
                           headers={'Content-Type': 'application/json'})
    if response.status_code == 400:
        print("✓ Invalid parameters correctly rejected")
    else:
        print(f"✗ Invalid parameters should be rejected: {response.status_code}")
    
    return True

def test_presets():
    """Test parameter presets"""
    print("\n=== Testing Parameter Presets ===")
    
    # Get available presets
    response = requests.get(f"{BASE_URL}/denoise/presets")
    if response.status_code == 200:
        presets = response.json()['presets']
        print(f"✓ Available presets: {list(presets.keys())}")
        
        # Test each preset
        for preset_name in presets.keys():
            response = requests.post(f"{BASE_URL}/denoise/presets/{preset_name}")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Applied preset '{preset_name}': {result['applied_parameters']}")
            else:
                print(f"✗ Failed to apply preset '{preset_name}': {response.status_code}")
                return False
    else:
        print(f"✗ Failed to get presets: {response.status_code}")
        return False
    
    # Test invalid preset
    response = requests.post(f"{BASE_URL}/denoise/presets/invalid_preset")
    if response.status_code == 400:
        print("✓ Invalid preset correctly rejected")
    else:
        print(f"✗ Invalid preset should be rejected: {response.status_code}")
    
    return True

def test_audio_processing():
    """Test audio processing with different presets"""
    print("\n=== Testing Audio Processing ===")
    
    # Create test audio file
    test_file = "/tmp/test_noisy_audio.wav"
    create_test_audio(test_file, duration=2.0, add_noise=True)
    print(f"✓ Created test audio: {test_file}")
    
    presets_to_test = ['natural', 'gentle', 'speech', 'aggressive']
    
    for preset in presets_to_test:
        print(f"\n--- Testing with '{preset}' preset ---")
        
        # Apply preset
        response = requests.post(f"{BASE_URL}/denoise/presets/{preset}")
        if response.status_code != 200:
            print(f"✗ Failed to apply preset '{preset}'")
            continue
        
        # Process audio
        with open(test_file, 'rb') as f:
            files = {'audio': f}
            response = requests.post(f"{BASE_URL}/denoise", files=files)
        
        if response.status_code == 200:
            output_file = f"/tmp/denoised_{preset}.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✓ Processed audio saved: {output_file}")
            
            # Check file size
            file_size = os.path.getsize(output_file)
            print(f"✓ Output file size: {file_size} bytes")
        else:
            print(f"✗ Failed to process audio with '{preset}': {response.status_code}")
            if response.headers.get('content-type') == 'application/json':
                print(f"   Error: {response.json()}")
    
    # Clean up
    if os.path.exists(test_file):
        os.unlink(test_file)
    
    return True

def test_raw_audio_processing():
    """Test raw PCM audio processing"""
    print("\n=== Testing Raw Audio Processing ===")
    
    # Create raw audio data (16-bit PCM)
    duration = 1.0
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t) * 0.5  # 440 Hz sine wave
    noise = np.random.normal(0, 0.1, len(signal))
    noisy_signal = signal + noise
    
    # Convert to int16
    audio_data = (noisy_signal * 32767).astype(np.int16)
    raw_data = audio_data.tobytes()
    
    print(f"✓ Created raw audio data: {len(raw_data)} bytes")
    
    # Send to API
    response = requests.post(f"{BASE_URL}/denoise/raw", 
                           data=raw_data,
                           headers={'Content-Type': 'application/octet-stream'})
    
    if response.status_code == 200:
        denoised_raw = response.content
        print(f"✓ Received denoised data: {len(denoised_raw)} bytes")
        
        # Convert back to numpy array
        denoised_audio = np.frombuffer(denoised_raw, dtype=np.int16)
        print(f"✓ Denoised audio samples: {len(denoised_audio)}")
        
        # Save as WAV for verification
        output_file = "/tmp/denoised_raw.wav"
        with wave.open(output_file, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            wav_file.writeframes(denoised_raw)
        print(f"✓ Saved denoised raw audio: {output_file}")
        
        return True
    else:
        print(f"✗ Failed to process raw audio: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("Enhanced RNNoise API Test Suite")
    print("=" * 50)
    
    # Wait for server to be ready
    print("Waiting for server to be ready...")
    for i in range(10):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✓ Server is ready!")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        print("✗ Server is not responding. Please start the enhanced API server first.")
        print("Run: python3 enhanced_rnnoise_api.py")
        return False
    
    # Run tests
    tests = [
        ("API Information", test_api_info),
        ("Parameter Management", test_parameter_management),
        ("Parameter Presets", test_presets),
        ("Audio Processing", test_audio_processing),
        ("Raw Audio Processing", test_raw_audio_processing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {str(e)}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced RNNoise API is working correctly.")
        print("\nYou can now:")
        print("1. Use different presets: natural, gentle, speech, aggressive, music")
        print("2. Adjust parameters manually via /denoise/params")
        print("3. Process audio with reduced robotic artifacts")
    else:
        print("❌ Some tests failed. Please check the server logs.")
    
    return passed == total

if __name__ == "__main__":
    main()