# RNNoise API - Hướng Dẫn Sử Dụng

## Giới Thiệu

RNNoise API là một dịch vụ web để khử tiếng ồn từ file âm thanh sử dụng thư viện RNNoise của Xiph.org. API này có thể xử lý cả file WAV và dữ liệu PCM thô.

## Tính Năng

- ✅ Khử tiếng ồn real-time cho file âm thanh
- ✅ Hỗ trợ định dạng WAV và PCM thô
- ✅ Tự động chuyển đổi định dạng âm thanh (48kHz mono 16-bit)
- ✅ RESTful API đơn giản và dễ sử dụng
- ✅ Xử lý frame-by-frame với độ trễ thấp

## Cài Đặt và Chạy

### Yêu Cầu Hệ Thống
- Python 3.6+
- Flask
- NumPy
- Thư viện RNNoise đã được build

### Khởi Động Server
```bash
cd /root/rnnoise
python3 rnnoise_api.py
```

Server sẽ chạy tại: **http://localhost:5000**

## API Endpoints

### 1. Thông Tin API
```
GET /
```
Trả về thông tin tổng quan về API và các endpoint có sẵn.

**Ví dụ Response:**
```json
{
  "name": "RNNoise API",
  "version": "1.0.0",
  "description": "Audio denoising API using RNNoise",
  "endpoints": {
    "/": "GET - API information",
    "/health": "GET - Health check",
    "/denoise": "POST - Denoise audio file",
    "/denoise/raw": "POST - Denoise raw PCM data",
    "/denoise/info": "GET - Audio format info"
  }
}
```

### 2. Kiểm Tra Sức Khỏe
```
GET /health
```
Kiểm tra trạng thái hoạt động của API.

**Response:**
```json
{
  "status": "healthy",
  "frame_size": 480
}
```

### 3. Thông Tin Định Dạng Âm Thanh
```
GET /denoise/info
```
Trả về thông tin về yêu cầu định dạng âm thanh.

**Response:**
```json
{
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 16,
  "frame_size": 480,
  "supported_formats": ["WAV", "raw PCM"],
  "notes": [
    "Audio is automatically converted to 48kHz mono 16-bit",
    "Frame size is 480 samples (10ms at 48kHz)",
    "First frame is skipped in processing (RNNoise behavior)"
  ]
}
```

### 4. Khử Tiếng Ồn File WAV
```
POST /denoise
```
Upload file WAV để khử tiếng ồn.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `audio` (file WAV)

**Response:**
- Content-Type: `audio/wav`
- File WAV đã được khử tiếng ồn

**Ví dụ sử dụng với curl:**
```bash
curl -X POST -F "audio=@input.wav" http://localhost:5000/denoise -o denoised.wav
```

### 5. Khử Tiếng Ồn Dữ Liệu PCM Thô
```
POST /denoise/raw
```
Gửi dữ liệu PCM thô để khử tiếng ồn.

**Request:**
- Content-Type: `application/octet-stream`
- Body: Dữ liệu PCM 16-bit mono 48kHz

**Response:**
- Content-Type: `application/octet-stream`
- Dữ liệu PCM đã được khử tiếng ồn

**Ví dụ sử dụng với curl:**
```bash
curl -X POST --data-binary @input.pcm http://localhost:5000/denoise/raw -o denoised.pcm
```

## Ví Dụ Sử Dụng

### Python
```python
import requests

# Khử tiếng ồn file WAV
with open('noisy_audio.wav', 'rb') as f:
    files = {'audio': f}
    response = requests.post('http://localhost:5000/denoise', files=files)
    
    if response.status_code == 200:
        with open('clean_audio.wav', 'wb') as output:
            output.write(response.content)
        print("Khử tiếng ồn thành công!")

# Khử tiếng ồn dữ liệu PCM thô
with open('noisy_audio.pcm', 'rb') as f:
    response = requests.post('http://localhost:5000/denoise/raw', data=f.read())
    
    if response.status_code == 200:
        with open('clean_audio.pcm', 'wb') as output:
            output.write(response.content)
        print("Khử tiếng ồn PCM thành công!")
```

### JavaScript (Node.js)
```javascript
const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

// Khử tiếng ồn file WAV
async function denoiseWav() {
    const form = new FormData();
    form.append('audio', fs.createReadStream('noisy_audio.wav'));
    
    try {
        const response = await axios.post('http://localhost:5000/denoise', form, {
            headers: form.getHeaders(),
            responseType: 'stream'
        });
        
        response.data.pipe(fs.createWriteStream('clean_audio.wav'));
        console.log('Khử tiếng ồn thành công!');
    } catch (error) {
        console.error('Lỗi:', error.message);
    }
}

// Khử tiếng ồn dữ liệu PCM
async function denoisePcm() {
    const pcmData = fs.readFileSync('noisy_audio.pcm');
    
    try {
        const response = await axios.post('http://localhost:5000/denoise/raw', pcmData, {
            headers: { 'Content-Type': 'application/octet-stream' },
            responseType: 'arraybuffer'
        });
        
        fs.writeFileSync('clean_audio.pcm', Buffer.from(response.data));
        console.log('Khử tiếng ồn PCM thành công!');
    } catch (error) {
        console.error('Lỗi:', error.message);
    }
}
```

## Yêu Cầu Định Dạng Âm Thanh

### Định Dạng Đầu Vào
- **Định dạng hỗ trợ:** 
  - WAV (PCM, IEEE_FLOAT, MULAW, ALAW)
  - MP3, FLAC, OGG, M4A, AAC
  - Raw PCM
  - Và nhiều định dạng khác thông qua FFmpeg
- **Sample Rate:** Bất kỳ (sẽ được chuyển đổi thành 48kHz)
- **Channels:** Bất kỳ (sẽ được chuyển đổi thành mono)
- **Bit Depth:** Bất kỳ (sẽ được chuyển đổi thành 16-bit)
- **Công nghệ:** Sử dụng pydub + FFmpeg để chuyển đổi định dạng

### Định Dạng Đầu Ra
- **Sample Rate:** 48kHz
- **Channels:** 1 (mono)
- **Bit Depth:** 16-bit
- **Frame Size:** 480 samples (10ms)

## Kiểm Tra API

Chạy script test để kiểm tra tất cả các endpoint:

```bash
python3 test_api.py
```

Script này sẽ:
1. Kiểm tra endpoint health
2. Lấy thông tin API
3. Tạo file âm thanh test
4. Test khử tiếng ồn file WAV
5. Test khử tiếng ồn dữ liệu PCM thô

## Lưu Ý Quan Trọng

### Hiệu Suất
- RNNoise xử lý âm thanh theo frame 480 samples (10ms tại 48kHz)
- Frame đầu tiên sẽ bị bỏ qua trong quá trình xử lý (đặc tính của RNNoise)
- Độ trễ xử lý rất thấp, phù hợp cho ứng dụng real-time

### Giới Hạn
- Server development Flask không phù hợp cho production
- Đối với production, sử dụng WSGI server như Gunicorn
- Kích thước file upload có thể bị giới hạn bởi cấu hình Flask

### Bảo Mật
- API hiện tại không có authentication
- Cần thêm rate limiting cho production
- Validate input để tránh các cuộc tấn công

## Xử Lý Sự Cố

### Lỗi "Library not found"
```bash
# Cài đặt lại thư viện RNNoise
cd /root/rnnoise
make install
ldconfig
```

### Lỗi "Frame size mismatch"
- Đảm bảo âm thanh đầu vào có sample rate 48kHz
- API sẽ tự động chuyển đổi, nhưng chất lượng có thể bị ảnh hưởng

### Server không khởi động
```bash
# Kiểm tra dependencies
pip3 install flask numpy scipy

# Kiểm tra port 5000 có bị chiếm dụng
lsof -i :5000
```

## Phát Triển Thêm

### Thêm Authentication
```python
from functools import wraps
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != 'your-secret-key':
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

### Thêm Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)
```

## Liên Hệ và Hỗ Trợ

- **RNNoise Repository:** https://github.com/xiph/rnnoise
- **Documentation:** Xem file API_README.md để biết thêm chi tiết kỹ thuật

---

**Chúc bạn sử dụng API thành công! 🎵✨**