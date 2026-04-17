# Hướng Dẫn Sử Dụng Enhanced RNNoise API

## Tổng Quan

Enhanced RNNoise API là phiên bản cải tiến của RNNoise với khả năng điều chỉnh các thông số để giảm thiểu hiện tượng âm thanh như robot và cải thiện chất lượng âm thanh sau khi khử nhiễu.

## Khởi Động Server

```bash
cd /root/rnnoise
python3 enhanced_rnnoise_api.py
```

Server sẽ chạy trên: `http://localhost:5001`

## Các Tính Năng Mới

### 1. Voice Activity Detection (VAD)
- Phát hiện khi nào có giọng nói thực sự
- Chỉ áp dụng khử nhiễu khi cần thiết
- Giảm thiểu xử lý không cần thiết

### 2. Điều Chỉnh Cường Độ Khử Nhiễu
- Kiểm soát mức độ khử nhiễu
- Tránh xử lý quá mức gây ra âm thanh robot

### 3. Temporal Smoothing
- Làm mượt âm thanh giữa các frame
- Giảm thiểu hiện tượng nhảy cóc âm thanh

### 4. Gain Control
- Điều chỉnh âm lượng đầu ra
- Bù đắp mất mát âm lượng sau khử nhiễu

## Các Thông Số Có Thể Điều Chỉnh

### `vad_threshold` (0.0 - 1.0)
- **Mô tả**: Ngưỡng phát hiện giọng nói
- **Giá trị thấp**: Nhạy cảm hơn, phát hiện cả âm thanh nhỏ
- **Giá trị cao**: Chỉ phát hiện giọng nói rõ ràng
- **Khuyến nghị**: 0.02 - 0.05

### `denoise_strength` (0.0 - 1.0)
- **Mô tả**: Cường độ khử nhiễu
- **Giá trị thấp**: Khử nhiễu nhẹ, giữ nguyên âm thanh gốc
- **Giá trị cao**: Khử nhiễu mạnh, có thể gây robot
- **Khuyến nghị**: 0.5 - 0.8

### `smoothing_factor` (0.0 - 1.0)
- **Mô tả**: Mức độ làm mượt giữa các frame
- **Giá trị thấp**: Ít làm mượt, phản ứng nhanh
- **Giá trị cao**: Làm mượt nhiều, có thể làm mờ âm thanh
- **Khuyến nghị**: 0.3 - 0.5

### `gain_factor` (0.1 - 3.0)
- **Mô tả**: Hệ số khuếch đại âm lượng
- **1.0**: Không thay đổi âm lượng
- **> 1.0**: Tăng âm lượng
- **< 1.0**: Giảm âm lượng
- **Khuyến nghị**: 1.0 - 1.1

### `enable_vad` (true/false)
- **Mô tả**: Bật/tắt Voice Activity Detection
- **true**: Chỉ xử lý khi có giọng nói
- **false**: Xử lý tất cả âm thanh

### `enable_smoothing` (true/false)
- **Mô tả**: Bật/tắt temporal smoothing
- **true**: Làm mượt âm thanh
- **false**: Không làm mượt

## Các Preset Có Sẵn

### 1. Natural (Khuyến nghị)
```json
{
    "vad_threshold": 0.02,
    "denoise_strength": 0.7,
    "smoothing_factor": 0.3,
    "gain_factor": 1.0,
    "enable_vad": true,
    "enable_smoothing": true
}
```
- **Sử dụng**: Cho hầu hết các trường hợp
- **Đặc điểm**: Cân bằng giữa khử nhiễu và chất lượng âm thanh

### 2. Gentle (Nhẹ nhàng)
```json
{
    "vad_threshold": 0.05,
    "denoise_strength": 0.4,
    "smoothing_factor": 0.5,
    "gain_factor": 1.0,
    "enable_vad": true,
    "enable_smoothing": true
}
```
- **Sử dụng**: Khi muốn giữ nguyên âm thanh gốc
- **Đặc điểm**: Khử nhiễu nhẹ, ít thay đổi

### 3. Speech (Giọng nói)
```json
{
    "vad_threshold": 0.03,
    "denoise_strength": 0.8,
    "smoothing_factor": 0.4,
    "gain_factor": 1.05,
    "enable_vad": true,
    "enable_smoothing": true
}
```
- **Sử dụng**: Tối ưu cho ghi âm giọng nói
- **Đặc điểm**: Tăng cường độ khử nhiễu cho giọng nói

### 4. Aggressive (Mạnh mẽ)
```json
{
    "vad_threshold": 0.01,
    "denoise_strength": 0.95,
    "smoothing_factor": 0.1,
    "gain_factor": 1.1,
    "enable_vad": true,
    "enable_smoothing": true
}
```
- **Sử dụng**: Khi có nhiều nhiễu cần loại bỏ
- **Cảnh báo**: Có thể gây âm thanh robot

### 5. Music (Âm nhạc)
```json
{
    "vad_threshold": 0.01,
    "denoise_strength": 0.5,
    "smoothing_factor": 0.6,
    "gain_factor": 1.0,
    "enable_vad": false,
    "enable_smoothing": true
}
```
- **Sử dụng**: Cho file âm nhạc
- **Đặc điểm**: Tắt VAD, giữ nguyên dynamics

## Cách Sử Dụng API

### 1. Kiểm Tra Thông Tin API
```bash
curl http://localhost:5001/
```

### 2. Xem Thông Số Hiện Tại
```bash
curl http://localhost:5001/denoise/params
```

### 3. Thay Đổi Thông Số
```bash
curl -X POST http://localhost:5001/denoise/params \
  -H "Content-Type: application/json" \
  -d '{
    "vad_threshold": 0.03,
    "denoise_strength": 0.6,
    "smoothing_factor": 0.4
  }'
```

### 4. Áp Dụng Preset
```bash
# Áp dụng preset "natural"
curl -X POST http://localhost:5001/denoise/presets/natural

# Áp dụng preset "speech"
curl -X POST http://localhost:5001/denoise/presets/speech
```

### 5. Xử Lý File Âm Thanh
```bash
curl -X POST http://localhost:5001/denoise \
  -F "audio=@input.wav" \
  -o output.wav
```

### 6. Xem Danh Sách Preset
```bash
curl http://localhost:5001/denoise/presets
```

## Ví Dụ Sử Dụng Python

```python
import requests

# Áp dụng preset natural
response = requests.post('http://localhost:5001/denoise/presets/natural')
print(response.json())

# Điều chỉnh thông số tùy chỉnh
params = {
    'vad_threshold': 0.025,
    'denoise_strength': 0.75,
    'smoothing_factor': 0.35,
    'gain_factor': 1.05
}
response = requests.post('http://localhost:5001/denoise/params', json=params)
print(response.json())

# Xử lý file âm thanh
with open('input.wav', 'rb') as f:
    files = {'audio': f}
    response = requests.post('http://localhost:5001/denoise', files=files)
    
    if response.status_code == 200:
        with open('output.wav', 'wb') as out_f:
            out_f.write(response.content)
        print("Đã xử lý thành công!")
```

## Khuyến Nghị Sử Dụng

### Cho Giọng Nói Rõ Ràng
1. Bắt đầu với preset **"natural"**
2. Nếu vẫn có nhiễu: tăng `denoise_strength` lên 0.8
3. Nếu âm thanh robot: giảm `denoise_strength` xuống 0.6

### Cho Giọng Nói Có Nhiều Nhiễu
1. Sử dụng preset **"speech"**
2. Điều chỉnh `vad_threshold` theo môi trường:
   - Môi trường yên tĩnh: 0.05
   - Môi trường ồn: 0.02

### Cho Âm Nhạc
1. Sử dụng preset **"music"**
2. Tắt VAD: `"enable_vad": false`
3. Tăng smoothing: `"smoothing_factor": 0.6`

### Khi Âm Thanh Bị Robot
1. Giảm `denoise_strength` (0.4 - 0.6)
2. Tăng `smoothing_factor` (0.4 - 0.6)
3. Bật VAD: `"enable_vad": true`
4. Điều chỉnh `vad_threshold` phù hợp

## Định Dạng Âm Thanh Hỗ Trợ

- **WAV**: PCM, IEEE_FLOAT, MULAW, ALAW
- **MP3**: Tất cả bitrate
- **FLAC**: Lossless
- **OGG**: Vorbis
- **M4A/AAC**: Advanced Audio Codec
- **Raw PCM**: 16-bit
- **Và nhiều định dạng khác** qua FFmpeg

## Lưu Ý Quan Trọng

1. **Thử nghiệm với preset trước**: Bắt đầu với các preset có sẵn
2. **Điều chỉnh từ từ**: Thay đổi một thông số một lúc
3. **Kiểm tra kết quả**: Nghe thử sau mỗi lần điều chỉnh
4. **Backup cài đặt**: Lưu lại thông số hoạt động tốt
5. **Môi trường khác nhau**: Cần thông số khác nhau

## Khắc Phục Sự Cố

### Âm Thanh Vẫn Như Robot
- Giảm `denoise_strength` xuống 0.5-0.6
- Tăng `smoothing_factor` lên 0.4-0.5
- Đảm bảo `enable_smoothing` = true

### Không Khử Được Nhiễu
- Tăng `denoise_strength` lên 0.8-0.9
- Giảm `vad_threshold` xuống 0.01-0.02
- Kiểm tra `enable_vad` = true

### Âm Lượng Quá Nhỏ
- Tăng `gain_factor` lên 1.1-1.2
- Kiểm tra file đầu vào có bị nhỏ không

### API Không Phản Hồi
- Kiểm tra server đang chạy: `curl http://localhost:5001/health`
- Khởi động lại server nếu cần

## Liên Hệ và Hỗ Trợ

Nếu gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng kiểm tra:
1. Log của server
2. Định dạng file đầu vào
3. Thông số đã cài đặt
4. Kết quả test với file mẫu