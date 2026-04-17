#!/usr/bin/env python3
"""
Test script for RNNoise API
"""

import requests
import numpy as np
from scipy.io import wavfile
import tempfile
import os

def create_test_audio():
    """Create a simple test audio file with noise"""
    # Generate 2 seconds of audio at 48kHz
    duration = 2.0
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a simple sine wave (speech-like signal)
    frequency = 440  # A4 note
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Add some noise
    noise = np.random.normal(0, 0.3, len(signal))
    noisy_signal = signal + noise
    
    # Convert to int16
    noisy_signal = (noisy_signal * 32767).astype(np.int16)
    
    return sample_rate, noisy_signal

def test_api_endpoints():
    """Test all API endpoints"""
    base_url = "http://localhost:5000"
    
    print("Testing RNNoise API...")
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test info endpoint
    print("\n2. Testing info endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"Info: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Info failed: {e}")
    
    # Test denoise info
    print("\n3. Testing denoise info...")
    try:
        response = requests.get(f"{base_url}/denoise/info")
        print(f"Denoise info: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Denoise info failed: {e}")
    
    # Create test audio
    print("\n4. Creating test audio...")
    sample_rate, test_audio = create_test_audio()
    
    # Save test audio to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        wavfile.write(temp_file.name, sample_rate, test_audio)
        test_file_path = temp_file.name
    
    try:
        # Test audio denoising
        print("\n5. Testing audio denoising...")
        with open(test_file_path, 'rb') as f:
            files = {'audio': f}
            response = requests.post(f"{base_url}/denoise", files=files)
            
        print(f"Denoise: {response.status_code}")
        
        if response.status_code == 200:
            # Save denoised audio
            with open('denoised_output.wav', 'wb') as f:
                f.write(response.content)
            print("Denoised audio saved as 'denoised_output.wav'")
        else:
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"Audio denoising failed: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)
    
    # Test raw PCM denoising
    print("\n6. Testing raw PCM denoising...")
    try:
        # Convert test audio to raw PCM
        raw_data = test_audio.tobytes()
        
        files = {'audio': ('test.pcm', raw_data, 'application/octet-stream')}
        data = {
            'sample_rate': sample_rate,
            'channels': 1
        }
        
        response = requests.post(f"{base_url}/denoise/raw", files=files, data=data)
        print(f"Raw denoise: {response.status_code}")
        
        if response.status_code == 200:
            with open('denoised_raw.pcm', 'wb') as f:
                f.write(response.content)
            print("Denoised raw PCM saved as 'denoised_raw.pcm'")
        else:
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"Raw PCM denoising failed: {e}")
    
    print("\nAPI testing completed!")

if __name__ == '__main__':
    test_api_endpoints()