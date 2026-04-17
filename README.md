# RNNoise - Real-time Audio Denoising

RNNoise là một thư viện khử tiếng ồn dựa trên mạng neural hồi quy (recurrent neural network), được phát triển bởi Xiph.Org Foundation. Dự án này cung cấp API REST và WebSocket để tích hợp RNNoise vào các ứng dụng web và mobile.

## 🎯 Tính năng chính

- **Khử tiếng ồn real-time**: Sử dụng deep learning để loại bỏ tiếng ồn nền
- **API REST**: Xử lý file audio với nhiều định dạng
- **WebSocket Streaming**: Xử lý audio real-time với độ trễ thấp
- **Hỗ trợ đa định dạng**: WAV, MP3, FLAC, OGG, M4A, AAC và nhiều định dạng khác
- **Tự động chuyển đổi**: Tự động convert audio về 48kHz mono 16-bit
- **High Performance**: Tối ưu hóa với AVX2/SSE4.1 support

## 📋 Yêu cầu hệ thống

- **OS**: Linux, macOS, Windows
- **Python**: 3.6+
- **Dependencies**: 
  - Flask, Flask-SocketIO (cho REST API)
  - websockets (cho WebSocket API)
  - numpy, scipy, pydub
  - FFmpeg (cho chuyển đổi định dạng)

## 🚀 Cài đặt và Chạy

### 1. Build RNNoise Library

```bash
# Clone repository
git clone https://gitlab.xiph.org/xiph/rnnoise.git
cd rnnoise

# Build library
./autogen.sh
./configure --enable-x86-rtcd  # Tùy chọn: enable AVX2/SSE4.1
make

# Tùy chọn: cài đặt system-wide
sudo make install
```

### 2. Compile API Wrapper

```bash
# Compile wrapper library
gcc -shared -fPIC -o librnnoise_wrapper.so api_wrapper.c -L.libs -lrnnoise -lm
```

### 3. Cài đặt Python Dependencies

```bash
# Cài đặt dependencies cho REST API
pip3 install flask flask-socketio numpy scipy pydub

# Cài đặt dependencies cho WebSocket API
pip3 install websockets numpy
```

### 4. Chạy Server

#### REST API + WebSocket (Socket.IO)
```bash
python3 rnnoise_api.py
# Server chạy tại: http://localhost:5000
# WebSocket: ws://localhost:5000/socket.io/
```

#### WebSocket thuần (Native WebSocket)
```bash
python3 simple_websocket_api.py
# WebSocket chạy tại: ws://localhost:9000
```

## 📡 REST API

### Endpoints

#### `GET /`
Thông tin về API và các endpoints có sẵn.

#### `GET /health`
Kiểm tra trạng thái server.

```json
{
  "status": "healthy",
  "frame_size": 480
}
```

#### `POST /denoise`
Khử tiếng ồn từ file audio.

**Request:**
```bash
curl -X POST -F "audio=@noisy_audio.wav" \
     http://localhost:5000/denoise \
     -o denoised_audio.wav
```

**Response:** File audio đã được khử tiếng ồn (WAV format)

#### `POST /denoise/raw`
Khử tiếng ồn từ raw PCM data.

```bash
curl -X POST \
  -F "audio=@audio.pcm" \
  -F "sample_rate=48000" \
  -F "channels=1" \
  http://localhost:5000/denoise/raw \
  -o denoised_audio.pcm
```

#### `GET /denoise/info`
Thông tin về cấu hình RNNoise.

```json
{
  "frame_size": 480,
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 16,
  "supported_formats": ["WAV", "MP3", "FLAC", "OGG", "M4A", "AAC", "raw PCM"]
}
```

## 🔌 WebSocket API

### Socket.IO WebSocket (rnnoise_api.py)

#### Kết nối
```javascript
const socket = io('http://localhost:5000');
```

#### Events

**`connect`** - Kết nối thành công
```json
{
  "status": "connected",
  "session_id": "unique_session_id",
  "frame_size": 480
}
```

**`audio_chunk`** - Gửi audio chunk
```javascript
socket.emit('audio_chunk', {
    audio_data: base64_encoded_pcm_data
});
```

**`denoised_chunk`** - Nhận audio đã khử tiếng ồn
```javascript
socket.on('denoised_chunk', (data) => {
    // data.audio_data: base64 encoded denoised audio
    // data.timestamp: processing timestamp
});
```

**`stream_info`** - Lấy thông tin streaming
**`clear_buffer`** - Xóa buffer audio
**`error`** - Thông báo lỗi

### Native WebSocket (simple_websocket_api.py)

#### Kết nối
```javascript
const ws = new WebSocket('ws://localhost:9000');
```

#### Message Types

**`audio_chunk`** - Gửi audio data
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_pcm_data"
}
```

**`denoised_chunk`** - Nhận audio đã xử lý
```json
{
  "type": "denoised_chunk",
  "data": "base64_encoded_denoised_audio",
  "timestamp": 1234567890.123
}
```

**`stream_info`** - Lấy thông tin cấu hình
**`clear_buffer`** - Xóa buffer
**`error`** - Thông báo lỗi

## 💻 Ví dụ sử dụng

### Python REST API Client

```python
import requests

# Upload và denoise file WAV
with open('noisy_audio.wav', 'rb') as f:
    files = {'audio': f}
    response = requests.post('http://localhost:5000/denoise', files=files)
    
if response.status_code == 200:
    with open('denoised_audio.wav', 'wb') as f:
        f.write(response.content)
    print("Audio đã được khử tiếng ồn!")
```

### JavaScript WebSocket Client

```javascript
// Socket.IO client
const socket = io('http://localhost:5000');

socket.on('connected', (data) => {
    console.log('Connected:', data);
});

socket.on('denoised_chunk', (data) => {
    // Decode base64 audio data
    const audioBytes = atob(data.audio_data);
    const audioArray = new Int16Array(audioBytes.length / 2);
    
    for (let i = 0; i < audioArray.length; i++) {
        audioArray[i] = (audioBytes.charCodeAt(i * 2 + 1) << 8) | 
                        audioBytes.charCodeAt(i * 2);
    }
    
    // Phát audio hoặc lưu vào buffer
    playAudio(audioArray);
});

// Gửi audio chunk
function sendAudioChunk(audioData) {
    const bytes = new Uint8Array(audioData.buffer);
    const base64 = btoa(String.fromCharCode(...bytes));
    
    socket.emit('audio_chunk', {
        audio_data: base64
    });
}
```

### Python WebSocket Client

```python
import socketio
import numpy as np
import base64

# Socket.IO client
sio = socketio.Client()

@sio.event
def connected(data):
    print(f"Connected: {data}")

@sio.event
def denoised_chunk(data):
    # Decode base64 audio
    audio_bytes = base64.b64decode(data['audio_data'])
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # Xử lý audio data
    process_audio(audio_data)

# Kết nối
sio.connect('http://localhost:5000')

# Gửi audio chunk
def send_audio_chunk(audio_data):
    chunk_b64 = base64.b64encode(audio_data.tobytes()).decode('utf-8')
    sio.emit('audio_chunk', {'audio_data': chunk_b64})
```

### Native WebSocket Client

```python
import asyncio
import websockets
import json
import base64
import numpy as np

async def websocket_client():
    uri = "ws://localhost:9000"
    
    async with websockets.connect(uri) as websocket:
        # Gửi stream info request
        await websocket.send(json.dumps({
            "type": "stream_info"
        }))
        
        # Nhận thông tin cấu hình
        response = await websocket.recv()
        info = json.loads(response)
        print(f"Stream info: {info}")
        
        # Gửi audio chunk
        audio_data = np.random.randint(-32768, 32767, 480, dtype=np.int16)
        chunk_b64 = base64.b64encode(audio_data.tobytes()).decode('utf-8')
        
        await websocket.send(json.dumps({
            "type": "audio_chunk",
            "data": chunk_b64
        }))
        
        # Nhận kết quả
        response = await websocket.recv()
        result = json.loads(response)
        
        if result["type"] == "denoised_chunk":
            denoised_bytes = base64.b64decode(result["data"])
            denoised_audio = np.frombuffer(denoised_bytes, dtype=np.int16)
            print(f"Received denoised audio: {len(denoised_audio)} samples")

# Chạy client
asyncio.run(websocket_client())
```

## 🧪 Testing

### Test REST API
```bash
python3 test_api.py
```

### Test Socket.IO WebSocket
```bash
python3 test_websocket.py
```

### Test Native WebSocket
```bash
python3 test_native_websocket.py
```

## ⚙️ Cấu hình Audio

### Yêu cầu Input
- **Sample Rate**: Bất kỳ (tự động convert về 48kHz)
- **Channels**: Bất kỳ (tự động convert về mono)
- **Bit Depth**: Bất kỳ (tự động convert về 16-bit)
- **Formats**: WAV, MP3, FLAC, OGG, M4A, AAC, raw PCM

### Output Format
- **Sample Rate**: 48000 Hz
- **Channels**: 1 (Mono)
- **Bit Depth**: 16-bit signed PCM
- **Format**: WAV (REST API), raw PCM (WebSocket)

### RNNoise Parameters
- **Frame Size**: 480 samples (10ms tại 48kHz)
- **Processing**: Frame-by-frame
- **Latency**: Minimum 10ms (1 frame)
- **Buffer**: Automatic management

## 🚀 Performance Tips

1. **Compilation**: Build với AVX2 support cho hiệu suất tốt nhất
   ```bash
   ./configure --enable-x86-rtcd CFLAGS="-march=native -O3"
   ```

2. **WebSocket Chunk Size**: Sử dụng bội số của frame size (480, 960, 1440...)

3. **Memory Management**: Server tự động quản lý buffer, sử dụng `clear_buffer` khi cần

4. **Real-time Processing**: Độ trễ tối thiểu là 10ms (1 frame)

## 🔧 Troubleshooting

### Common Issues

1. **Library not found**
   ```bash
   # Kiểm tra library đã được build
   ls -la librnnoise_wrapper.so
   
   # Rebuild nếu cần
   gcc -shared -fPIC -o librnnoise_wrapper.so api_wrapper.c -L.libs -lrnnoise -lm
   ```

2. **Permission denied**
   ```bash
   # Thay đổi port hoặc chạy với sudo
   sudo python3 rnnoise_api.py
   ```

3. **Audio format error**
   ```bash
   # Cài đặt FFmpeg
   sudo apt-get install ffmpeg  # Ubuntu/Debian
   brew install ffmpeg          # macOS
   ```

4. **WebSocket connection failed**
   ```bash
   # Kiểm tra server đang chạy
   netstat -tlnp | grep :5000
   netstat -tlnp | grep :9000
   ```

### Debug Mode

```bash
# Chạy với debug logging
FLASK_ENV=development python3 rnnoise_api.py

# Hoặc với Python logging
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('rnnoise_api.py').read())
"
```

## 📚 API Documentation

Chi tiết đầy đủ về API có thể tìm thấy trong:
- `API_README.md` - REST API documentation
- `ENHANCEMENT_SUMMARY.md` - Tính năng và cải tiến
- `HUONG_DAN_SU_DUNG.md` - Hướng dẫn sử dụng tiếng Việt

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Tạo Pull Request

## 📄 License

Dự án này dựa trên RNNoise library của Xiph.Org Foundation.
- RNNoise: BSD 3-Clause License
- API Extensions: MIT License

## 🔗 Links

- **Original RNNoise**: https://gitlab.xiph.org/xiph/rnnoise
- **Paper**: [A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement](https://arxiv.org/pdf/1709.08243.pdf)
- **Demo**: https://jmvalin.ca/demo/rnnoise/
- **Xiph.Org**: https://xiph.org/

## 📞 Support

Nếu gặp vấn đề hoặc có câu hỏi:
1. Kiểm tra [Troubleshooting](#-troubleshooting) section
2. Tạo issue trên repository
3. Tham khảo documentation trong thư mục `doc/`

---

**Phát triển bởi**: Dựa trên RNNoise của Jean-Marc Valin và Xiph.Org Foundation  
**Phiên bản**: 1.0.0  
**Cập nhật**: 2024