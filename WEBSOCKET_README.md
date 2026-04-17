# RNNoise WebSocket - Quick Integration Guide

## 🚀 Quick Start (3 bước)


### 2. Kết nối WebSocket
```javascript
const ws = new WebSocket('ws://localhost:9000');
```

### 3. Gửi Audio & Nhận Kết quả
```javascript
// Gửi audio chunk (PCM data)
ws.send(JSON.stringify({
    type: "audio_chunk", 
    data: base64AudioData
}));

// Nhận audio đã denoise
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "denoised_chunk") {
        const cleanAudio = atob(msg.data); // Decode base64
    }
};
```

## 📋 Message Format

### Gửi Audio (Client → Server)
```json
{"type": "audio_chunk", "data": "base64_pcm_data"}
```

### Nhận Audio Cleaned (Server → Client)  
```json
{"type": "denoised_chunk", "data": "base64_clean_data"}
```

### Xóa Buffer (Optional)
```json
{"type": "clear_buffer"}
```

## 🎵 Audio Requirements
- **Format**: PCM 16-bit, 48kHz, mono
- **Chunk Size**: 960 bytes
- **Encoding**: Base64

### WAV File → PCM
```javascript
// Bỏ qua WAV header (44 bytes đầu)
const pcmData = wavFile.slice(44);
```

## 💻 Complete Examples

### JavaScript/Node.js
```javascript
const WebSocket = require('ws');
const fs = require('fs');

const ws = new WebSocket('ws://localhost:9000');
let denoisedChunks = [];

ws.on('open', () => {
    console.log('✅ Connected');
    
    // Đọc file WAV và gửi
    const audioFile = fs.readFileSync('input.wav');
    const pcmData = audioFile.slice(44); // Bỏ header
    
    // Chia thành chunks 960 bytes
    for (let i = 0; i < pcmData.length; i += 960) {
        const chunk = pcmData.slice(i, i + 960);
        if (chunk.length === 960) {
            ws.send(JSON.stringify({
                type: 'audio_chunk',
                data: chunk.toString('base64')
            }));
        }
    }
});

ws.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'denoised_chunk') {
        denoisedChunks.push(Buffer.from(msg.data, 'base64'));
    }
});

ws.on('close', () => {
    // Lưu file output
    const output = Buffer.concat(denoisedChunks);
    fs.writeFileSync('output.wav', output);
    console.log('✅ Saved output.wav');
});
```

### Python
```python
import websocket, json, base64

chunks = []

def on_message(ws, message):
    data = json.loads(message)
    if data['type'] == 'denoised_chunk':
        chunks.append(base64.b64decode(data['data']))

def send_audio_file(ws, filename):
    with open(filename, 'rb') as f:
        audio_data = f.read()[44:]  # Bỏ WAV header
    
    # Gửi từng chunk 960 bytes
    for i in range(0, len(audio_data), 960):
        chunk = audio_data[i:i+960]
        if len(chunk) == 960:
            ws.send(json.dumps({
                'type': 'audio_chunk',
                'data': base64.b64encode(chunk).decode()
            }))

ws = websocket.WebSocketApp("ws://localhost:9000", on_message=on_message)
```