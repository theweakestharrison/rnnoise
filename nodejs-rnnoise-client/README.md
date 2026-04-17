# RNNoise WebSocket Client (Node.js)

Client Node.js đơn giản để kết nối với RNNoise WebSocket server và xử lý audio denoising.

## Cài đặt

```bash
# Cài đặt dependencies
npm install
```

## Sử dụng

### Cú pháp cơ bản
```bash
node client.js <đường_dẫn_file_audio> [đường_dẫn_output] [server_url]
```

### Ví dụ

1. **Sử dụng cơ bản** (output tự động tạo):
```bash
node client.js input.wav
# Tạo file: denoised_input.wav
```

2. **Chỉ định file output**:
```bash
node client.js input.wav clean_audio.wav
```

3. **Chỉ định server URL**:
```bash
node client.js input.wav output.wav ws://192.168.1.100:9000
```

## Yêu cầu

- **Node.js**: >= 14.0.0
- **Audio format**: PCM 16-bit, 48kHz, mono
- **RNNoise server**: Phải chạy trước khi sử dụng client

## Tính năng

- ✅ Kết nối WebSocket tự động
- ✅ Chia file audio thành chunks phù hợp
- ✅ Hiển thị progress real-time
- ✅ Xử lý lỗi và thông báo rõ ràng
- ✅ Tự động tạo tên file output
- ✅ Hỗ trợ custom server URL

## Cách hoạt động

1. **Kết nối**: Client kết nối tới RNNoise WebSocket server
2. **Đọc file**: Đọc file audio từ đường dẫn được chỉ định
3. **Chia chunks**: Chia audio thành chunks 960 bytes (480 samples)
4. **Gửi dữ liệu**: Gửi từng chunk tới server qua WebSocket
5. **Nhận kết quả**: Nhận chunks đã denoised từ server
6. **Lưu file**: Ghép các chunks và lưu thành file output

## Thông báo

- 🔗 **Kết nối**: Hiển thị trạng thái kết nối WebSocket
- 📊 **Thông tin file**: Kích thước và số chunks
- 🎵 **Progress**: Tiến độ xử lý real-time
- ✅ **Hoàn thành**: Thông báo kết quả và đường dẫn file

## Lỗi thường gặp

### "File không tồn tại"
- Kiểm tra đường dẫn file input
- Đảm bảo file tồn tại và có quyền đọc

### "Chưa kết nối tới server"
- Kiểm tra RNNoise server đã chạy chưa
- Kiểm tra URL server (mặc định: ws://localhost:9000)

### "Lỗi WebSocket"
- Kiểm tra network connection
- Đảm bảo server đang chạy và accessible

## Server mặc định

Client mặc định kết nối tới:
- **URL**: `ws://localhost:9000`
- **Protocol**: Native WebSocket (không phải Socket.IO)

Để chạy server, sử dụng:
```bash
# Trong thư mục rnnoise chính
python3 simple_websocket_api.py
```