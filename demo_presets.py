#!/usr/bin/env python3
"""
Demo script để thử nghiệm các preset khác nhau của Enhanced RNNoise API
"""

import requests
import numpy as np
import wave
import tempfile
import os
import time

# API base URL
BASE_URL = "http://localhost:5001"

def create_demo_audio(filename, audio_type="speech"):
    """Tạo file âm thanh demo với nhiễu"""
    duration = 3.0
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    if audio_type == "speech":
        # Tạo tín hiệu giống giọng nói
        speech = (np.sin(2 * np.pi * 440 * t) * 0.3 +  # A4
                  np.sin(2 * np.pi * 880 * t) * 0.2 +  # A5
                  np.sin(2 * np.pi * 220 * t) * 0.1)   # A3
        
        # Thêm envelope để giống giọng nói hơn
        envelope = np.exp(-t * 0.3) * (1 + 0.8 * np.sin(2 * np.pi * 3 * t))
        speech = speech * envelope
        
    elif audio_type == "music":
        # Tạo tín hiệu giống âm nhạc
        speech = (np.sin(2 * np.pi * 261.63 * t) * 0.4 +  # C4
                  np.sin(2 * np.pi * 329.63 * t) * 0.3 +  # E4
                  np.sin(2 * np.pi * 392.00 * t) * 0.3)   # G4
        
        # Thêm dynamics cho âm nhạc
        envelope = 0.8 + 0.2 * np.sin(2 * np.pi * 1 * t)
        speech = speech * envelope
    
    # Thêm nhiễu trắng
    noise = np.random.normal(0, 0.15, len(speech))
    
    # Thêm nhiễu tần số thấp (hum)
    hum = 0.1 * np.sin(2 * np.pi * 50 * t)
    
    # Tín hiệu cuối cùng
    signal = speech + noise + hum
    
    # Normalize và convert sang int16
    signal = signal / np.max(np.abs(signal)) * 0.8
    audio_data = (signal * 32767).astype(np.int16)
    
    # Lưu file WAV
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return filename

def test_preset(preset_name, input_file, description=""):
    """Test một preset cụ thể"""
    print(f"\n--- Testing preset: {preset_name} ---")
    if description:
        print(f"Mô tả: {description}")
    
    # Áp dụng preset
    response = requests.post(f"{BASE_URL}/denoise/presets/{preset_name}")
    if response.status_code != 200:
        print(f"❌ Lỗi khi áp dụng preset: {response.status_code}")
        return None
    
    result = response.json()
    print(f"✓ Đã áp dụng preset với thông số:")
    for param, value in result['applied_parameters'].items():
        print(f"  - {param}: {value}")
    
    # Xử lý âm thanh
    with open(input_file, 'rb') as f:
        files = {'audio': f}
        response = requests.post(f"{BASE_URL}/denoise", files=files)
    
    if response.status_code == 200:
        output_file = f"/tmp/demo_{preset_name}.wav"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(output_file)
        print(f"✓ Đã lưu kết quả: {output_file} ({file_size} bytes)")
        return output_file
    else:
        print(f"❌ Lỗi khi xử lý âm thanh: {response.status_code}")
        return None

def demo_custom_parameters():
    """Demo điều chỉnh thông số tùy chỉnh"""
    print(f"\n{'='*50}")
    print("DEMO: Điều chỉnh thông số tùy chỉnh")
    print(f"{'='*50}")
    
    # Tạo file âm thanh test
    input_file = "/tmp/demo_custom_input.wav"
    create_demo_audio(input_file, "speech")
    print(f"✓ Đã tạo file test: {input_file}")
    
    # Test các cài đặt khác nhau
    test_configs = [
        {
            "name": "Khử nhiễu nhẹ",
            "params": {
                "vad_threshold": 0.05,
                "denoise_strength": 0.4,
                "smoothing_factor": 0.5,
                "gain_factor": 1.0,
                "enable_vad": True,
                "enable_smoothing": True
            }
        },
        {
            "name": "Khử nhiễu vừa phải",
            "params": {
                "vad_threshold": 0.03,
                "denoise_strength": 0.7,
                "smoothing_factor": 0.3,
                "gain_factor": 1.0,
                "enable_vad": True,
                "enable_smoothing": True
            }
        },
        {
            "name": "Khử nhiễu mạnh (có thể robot)",
            "params": {
                "vad_threshold": 0.01,
                "denoise_strength": 0.95,
                "smoothing_factor": 0.1,
                "gain_factor": 1.1,
                "enable_vad": True,
                "enable_smoothing": True
            }
        }
    ]
    
    for config in test_configs:
        print(f"\n--- {config['name']} ---")
        
        # Áp dụng thông số
        response = requests.post(f"{BASE_URL}/denoise/params", 
                               json=config['params'],
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            print("✓ Đã áp dụng thông số:")
            for param, value in config['params'].items():
                print(f"  - {param}: {value}")
            
            # Xử lý âm thanh
            with open(input_file, 'rb') as f:
                files = {'audio': f}
                response = requests.post(f"{BASE_URL}/denoise", files=files)
            
            if response.status_code == 200:
                output_file = f"/tmp/demo_custom_{config['name'].replace(' ', '_')}.wav"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Đã lưu: {output_file}")
            else:
                print(f"❌ Lỗi xử lý: {response.status_code}")
        else:
            print(f"❌ Lỗi áp dụng thông số: {response.status_code}")

def main():
    """Chạy demo chính"""
    print("🎵 DEMO: Enhanced RNNoise API với Thông Số Điều Chỉnh")
    print("="*60)
    
    # Kiểm tra server
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server không phản hồi. Vui lòng khởi động server trước:")
            print("   python3 enhanced_rnnoise_api.py")
            return
    except requests.exceptions.RequestException:
        print("❌ Không thể kết nối đến server. Vui lòng khởi động server trước:")
        print("   python3 enhanced_rnnoise_api.py")
        return
    
    print("✓ Server đang hoạt động!")
    
    # Demo 1: Test các preset với giọng nói
    print(f"\n{'='*50}")
    print("DEMO 1: Các preset cho giọng nói")
    print(f"{'='*50}")
    
    speech_file = "/tmp/demo_speech_input.wav"
    create_demo_audio(speech_file, "speech")
    print(f"✓ Đã tạo file giọng nói có nhiễu: {speech_file}")
    
    speech_presets = [
        ("natural", "Cân bằng tốt nhất, khuyến nghị sử dụng"),
        ("gentle", "Khử nhiễu nhẹ, giữ nguyên âm thanh gốc"),
        ("speech", "Tối ưu cho giọng nói"),
        ("aggressive", "Khử nhiễu mạnh, có thể gây robot")
    ]
    
    for preset, desc in speech_presets:
        test_preset(preset, speech_file, desc)
        time.sleep(0.5)  # Tránh spam server
    
    # Demo 2: Test preset cho âm nhạc
    print(f"\n{'='*50}")
    print("DEMO 2: Preset cho âm nhạc")
    print(f"{'='*50}")
    
    music_file = "/tmp/demo_music_input.wav"
    create_demo_audio(music_file, "music")
    print(f"✓ Đã tạo file âm nhạc có nhiễu: {music_file}")
    
    test_preset("music", music_file, "Tối ưu cho âm nhạc, tắt VAD")
    
    # Demo 3: Điều chỉnh thông số tùy chỉnh
    demo_custom_parameters()
    
    # Tổng kết
    print(f"\n{'='*60}")
    print("🎉 DEMO HOÀN THÀNH!")
    print(f"{'='*60}")
    print("\nCác file đã tạo trong /tmp/:")
    print("📁 File đầu vào:")
    print("   - demo_speech_input.wav (giọng nói có nhiễu)")
    print("   - demo_music_input.wav (âm nhạc có nhiễu)")
    print("   - demo_custom_input.wav (test tùy chỉnh)")
    
    print("\n📁 File đầu ra (đã khử nhiễu):")
    output_files = [
        "demo_natural.wav",
        "demo_gentle.wav", 
        "demo_speech.wav",
        "demo_aggressive.wav",
        "demo_music.wav"
    ]
    
    for file in output_files:
        full_path = f"/tmp/{file}"
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"   ✓ {file} ({size} bytes)")
    
    print("\n💡 Khuyến nghị:")
    print("1. Nghe thử các file để so sánh chất lượng")
    print("2. Preset 'natural' thường cho kết quả tốt nhất")
    print("3. Điều chỉnh thông số theo nhu cầu cụ thể")
    print("4. Đọc HUONG_DAN_SU_DUNG.md để biết thêm chi tiết")
    
    print(f"\n📖 Tài liệu:")
    print("   - HUONG_DAN_SU_DUNG.md: Hướng dẫn chi tiết")
    print("   - API endpoints: http://localhost:5001/")

if __name__ == "__main__":
    main()