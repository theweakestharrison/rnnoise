# RNNoise API Server

Một API server đơn giản sử dụng RNNoise để khử tiếng ồn từ audio.

## Tính năng

- **Khử tiếng ồn audio**: Sử dụng RNNoise neural network để loại bỏ tiếng ồn nền
- **Hỗ trợ nhiều định dạng**: WAV files và raw PCM data
- **Tự động chuyển đổi**: Tự động convert audio về 48kHz mono 16-bit
- **RESTful API**: Dễ dàng tích hợp với các ứng dụng khác

## Cài đặt và Chạy

### 1. Build RNNoise library
```bash
./autogen.sh
./configure
make
```

### 2. Compile API wrapper
```bash
gcc -shared -fPIC -o librnnoise_wrapper.so api_wrapper.c -L.libs -lrnnoise -lm
```

### 3. Cài đặt Python dependencies
```bash
pip3 install flask numpy scipy
```

### 4. Chạy API server
```bash
python3 rnnoise_api.py
```

Server sẽ chạy tại `http://localhost:5000`

## API Endpoints

### GET `/`
Thông tin về API và các endpoints có sẵn.

**Response:**
```json
{
  "name": "RNNoise API",
  "version": "1.0.0",
  "description": "Audio denoising API using RNNoise",
  "frame_size": 480,
  "endpoints": {
    "/": "GET - API information",
    "/denoise": "POST - Denoise audio file",
    "/denoise/raw": "POST - Denoise raw PCM data",
    "/health": "GET - Health check"
  }
}
```

### GET `/health`
Kiểm tra trạng thái server.

**Response:**
```json
{
  "status": "healthy",
  "frame_size": 480
}
```

### POST `/denoise`
Khử tiếng ồn từ file audio (WAV).

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: File audio với key `audio`

**Response:**
- Content-Type: audio/wav
- Body: File audio đã được khử tiếng ồn

**Example với curl:**
```bash
curl -X POST -F "audio=@noisy_audio.wav" http://localhost:5000/denoise -o denoised_audio.wav
```

### POST `/denoise/raw`
Khử tiếng ồn từ raw PCM data.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: 
  - `audio`: Raw PCM data file
  - `sample_rate`: Sample rate (default: 48000)
  - `channels`: Number of channels (default: 1)

**Response:**
- Content-Type: application/octet-stream
- Body: Raw PCM data đã được khử tiếng ồn

**Example với curl:**
```bash
curl -X POST \
  -F "audio=@audio.pcm" \
  -F "sample_rate=48000" \
  -F "channels=1" \
  http://localhost:5000/denoise/raw \
  -o denoised_audio.pcm
```

### GET `/denoise/info`
Thông tin về quá trình xử lý RNNoise.

**Response:**
```json
{
  "frame_size": 480,
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 16,
  "supported_formats": ["WAV", "raw PCM"],
  "notes": [
    "Audio is automatically converted to 48kHz mono 16-bit",
    "Frame size is 480 samples (10ms at 48kHz)",
    "First frame is skipped in processing (RNNoise behavior)"
  ]
}
```

## Testing

Chạy script test để kiểm tra API:

```bash
python3 test_api.py
```

Script này sẽ:
1. Tạo file audio test với tiếng ồn
2. Test tất cả endpoints
3. Lưu kết quả đã được khử tiếng ồn

## Yêu cầu Audio

- **Input Formats**: 
  - WAV (PCM, IEEE_FLOAT, MULAW, ALAW)
  - MP3, FLAC, OGG, M4A, AAC
  - Raw PCM data
  - And many more formats via FFmpeg
- **Output Format**: WAV (16-bit PCM, 48kHz, mono)
- **Automatic Conversion**: All audio is converted to 48kHz mono 16-bit
- **Technology**: Uses pydub + FFmpeg for format conversion

## Lưu ý

1. **Frame Size**: RNNoise xử lý audio theo từng frame 480 samples (10ms tại 48kHz)
2. **First Frame**: Frame đầu tiên bị bỏ qua (behavior của RNNoise)
3. **Memory**: Server load toàn bộ audio vào memory, không phù hợp cho file rất lớn
4. **Performance**: Để có hiệu suất tốt nhất, compile với AVX2 support

## Ví dụ sử dụng với Python

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

## Ví dụ sử dụng với JavaScript

```javascript
const formData = new FormData();
formData.append('audio', audioFile);

fetch('http://localhost:5000/denoise', {
    method: 'POST',
    body: formData
})
.then(response => response.blob())
.then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'denoised_audio.wav';
    a.click();
});
```

## WebSocket Streaming API

RNNoise API hỗ trợ streaming real-time qua WebSocket để xử lý audio liên tục với độ trễ thấp.

### Kết nối WebSocket

**URL:** `ws://localhost:5000/socket.io/`

**Library:** Sử dụng Socket.IO client

### Events

#### `connect`
Kết nối đến server WebSocket.

**Response:**
```json
{
  "status": "connected",
  "session_id": "unique_session_id",
  "frame_size": 480,
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 16
}
```

#### `audio_chunk`
Gửi chunk audio để xử lý real-time.

**Request:**
```json
{
  "audio_data": "base64_encoded_pcm_data"
}
```

**Response:** `denoised_chunk` event

#### `denoised_chunk`
Nhận chunk audio đã được khử tiếng ồn.

**Data:**
```json
{
  "audio_data": "base64_encoded_denoised_pcm",
  "frame_size": 480,
  "timestamp": 1234567890.123
}
```

#### `stream_info`
Lấy thông tin cấu hình streaming.

**Response:**
```json
{
  "frame_size": 480,
  "sample_rate": 48000,
  "channels": 1,
  "bit_depth": 16,
  "format": "PCM signed 16-bit little-endian",
  "encoding": "base64"
}
```

#### `clear_buffer`
Xóa buffer audio của session.

**Response:**
```json
{
  "status": "success"
}
```

#### `error`
Thông báo lỗi từ server.

**Data:**
```json
{
  "error": "Error message"
}
```

### Example JavaScript Client

```javascript
// Kết nối WebSocket
const socket = io('http://localhost:5000');

// Lắng nghe kết nối
socket.on('connected', (data) => {
    console.log('Connected:', data);
    console.log('Frame size:', data.frame_size);
});

// Lắng nghe chunk đã được xử lý
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
    // Convert Int16Array to base64
    const bytes = new Uint8Array(audioData.buffer);
    const base64 = btoa(String.fromCharCode(...bytes));
    
    socket.emit('audio_chunk', {
        audio_data: base64
    });
}

// Lắng nghe lỗi
socket.on('error', (data) => {
    console.error('WebSocket error:', data.error);
});
```

### Example Python Client

```python
import socketio
import numpy as np
import base64

# Tạo client
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
    # Encode to base64
    chunk_b64 = base64.b64encode(audio_data.tobytes()).decode('utf-8')
    sio.emit('audio_chunk', {'audio_data': chunk_b64})

# Ngắt kết nối
sio.disconnect()
```

### Streaming Requirements

- **Sample Rate:** 48000 Hz
- **Channels:** 1 (Mono)
- **Bit Depth:** 16-bit signed PCM
- **Frame Size:** 480 samples (10ms tại 48kHz)
- **Encoding:** Base64 cho transmission
- **Optimal Chunk Size:** Bội số của frame size (480, 960, 1440, ...)

### Performance Tips

1. **Chunk Size:** Sử dụng chunk size là bội số của frame size để tối ưu hiệu suất
2. **Buffer Management:** Server tự động quản lý buffer, gửi `clear_buffer` khi cần reset
3. **Real-time Processing:** Độ trễ thấp nhất là 10ms (1 frame)
4. **Connection Management:** Mỗi client có session riêng với buffer độc lập

### Testing

Chạy test script để kiểm tra WebSocket streaming:

```bash
python3 test_websocket.py
```

## Troubleshooting

1. **Library not found**: Đảm bảo `librnnoise_wrapper.so` được build thành công
2. **Permission denied**: Chạy với quyền phù hợp hoặc thay đổi port
3. **Audio format error**: Đảm bảo file audio đúng định dạng
4. **Memory error**: Giảm kích thước file audio hoặc tăng RAM

## License

Dựa trên RNNoise library của Xiph.Org Foundation.