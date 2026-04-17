#!/usr/bin/env node

const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

class RNNoiseWebSocketClient {
    constructor(serverUrl = 'ws://localhost:9000') {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.isConnected = false;
        this.denoisedChunks = [];
        this.totalChunks = 0;
        this.processedChunks = 0;
    }

    connect() {
        return new Promise((resolve, reject) => {
            console.log(`🔗 Đang kết nối tới ${this.serverUrl}...`);
            
            this.ws = new WebSocket(this.serverUrl);
            
            this.ws.on('open', () => {
                console.log('✅ Kết nối WebSocket thành công!');
                this.isConnected = true;
                resolve();
            });

            this.ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleMessage(message);
                } catch (error) {
                    console.error('❌ Lỗi parse message:', error);
                }
            });

            this.ws.on('error', (error) => {
                console.error('❌ Lỗi WebSocket:', error);
                reject(error);
            });

            this.ws.on('close', () => {
                console.log('🔌 Kết nối WebSocket đã đóng');
                this.isConnected = false;
            });
        });
    }

    handleMessage(message) {
        switch (message.type) {
            case 'connection_confirmed':
                console.log('📡 Xác nhận kết nối từ server');
                break;
            
            case 'denoised_chunk':
                this.denoisedChunks.push(Buffer.from(message.data, 'base64'));
                this.processedChunks++;
                
                const progress = ((this.processedChunks / this.totalChunks) * 100).toFixed(1);
                process.stdout.write(`\r🎵 Đang xử lý: ${progress}% (${this.processedChunks}/${this.totalChunks})`);
                break;
            
            case 'error':
                console.error(`\n❌ Lỗi từ server: ${message.message}`);
                break;
            
            default:
                console.log('📨 Message từ server:', message);
        }
    }

    async processAudioFile(inputPath, outputPath) {
        if (!this.isConnected) {
            throw new Error('Chưa kết nối tới server');
        }

        if (!fs.existsSync(inputPath)) {
            throw new Error(`File không tồn tại: ${inputPath}`);
        }

        console.log(`\n📂 Đọc file audio: ${inputPath}`);
        const fileData = fs.readFileSync(inputPath);
        console.log(`📊 Kích thước file: ${fileData.length} bytes`);

        // Kiểm tra và bỏ qua WAV header nếu có
        let audioData = fileData;
        if (fileData.length > 44 && 
            fileData.toString('ascii', 0, 4) === 'RIFF' && 
            fileData.toString('ascii', 8, 12) === 'WAVE') {
            console.log('🎵 Phát hiện file WAV, bỏ qua header...');
            audioData = fileData.slice(44); // Bỏ qua 44 bytes WAV header
            console.log(`📊 Kích thước PCM data: ${audioData.length} bytes`);
        }

        // Reset counters
        this.denoisedChunks = [];
        this.processedChunks = 0;

        // Chia audio thành chunks 960 bytes (480 samples * 2 bytes)
        const chunkSize = 960;
        const chunks = [];
        
        for (let i = 0; i < audioData.length; i += chunkSize) {
            const chunk = audioData.slice(i, i + chunkSize);
            if (chunk.length === chunkSize) {
                chunks.push(chunk);
            }
        }

        this.totalChunks = chunks.length;
        console.log(`🔢 Tổng số chunks: ${this.totalChunks}`);

        // Gửi từng chunk
        console.log('🚀 Bắt đầu gửi audio chunks...');
        for (let i = 0; i < chunks.length; i++) {
            const chunk = chunks[i];
            const base64Data = chunk.toString('base64');
            
            const message = {
                type: 'audio_chunk',
                data: base64Data
            };

            this.ws.send(JSON.stringify(message));
            
            // Delay nhỏ để tránh overwhelm server
            await new Promise(resolve => setTimeout(resolve, 1));
        }

        // Đợi xử lý hoàn tất
        console.log('\n⏳ Đang đợi server xử lý...');
        await this.waitForProcessing();

        // Lưu kết quả
        if (this.denoisedChunks.length > 0) {
            const denoisedAudio = Buffer.concat(this.denoisedChunks);
            
            // Tạo WAV header cho file output
            const wavHeader = this.createWavHeader(denoisedAudio.length);
            const finalOutput = Buffer.concat([wavHeader, denoisedAudio]);
            
            fs.writeFileSync(outputPath, finalOutput);
            console.log(`\n✅ Đã lưu audio đã denoise: ${outputPath}`);
            console.log(`📊 Kích thước output: ${finalOutput.length} bytes (${denoisedAudio.length} bytes PCM + 44 bytes header)`);
        } else {
            console.log('\n⚠️  Không nhận được dữ liệu denoised từ server');
        }
    }

    waitForProcessing() {
        return new Promise((resolve) => {
            const checkInterval = setInterval(() => {
                if (this.processedChunks >= this.totalChunks) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 100);
        });
    }

    createWavHeader(dataLength) {
        const header = Buffer.alloc(44);
        
        // RIFF header
        header.write('RIFF', 0);
        header.writeUInt32LE(36 + dataLength, 4); // File size - 8
        header.write('WAVE', 8);
        
        // fmt chunk
        header.write('fmt ', 12);
        header.writeUInt32LE(16, 16); // fmt chunk size
        header.writeUInt16LE(1, 20);  // Audio format (PCM)
        header.writeUInt16LE(1, 22);  // Number of channels (mono)
        header.writeUInt32LE(48000, 24); // Sample rate (48kHz)
        header.writeUInt32LE(96000, 28); // Byte rate (48000 * 1 * 2)
        header.writeUInt16LE(2, 32);  // Block align (1 * 2)
        header.writeUInt16LE(16, 34); // Bits per sample
        
        // data chunk
        header.write('data', 36);
        header.writeUInt32LE(dataLength, 40); // Data size
        
        return header;
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Main function
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.log('📖 Cách sử dụng:');
        console.log('  node client.js <đường_dẫn_file_audio> [đường_dẫn_output] [server_url]');
        console.log('');
        console.log('Ví dụ:');
        console.log('  node client.js input.wav');
        console.log('  node client.js input.wav output.wav');
        console.log('  node client.js input.wav output.wav ws://localhost:9000');
        process.exit(1);
    }

    const inputPath = args[0];
    const outputPath = args[1] || `denoised_${path.basename(inputPath)}`;
    const serverUrl = args[2] || 'ws://localhost:9000';

    const client = new RNNoiseWebSocketClient(serverUrl);

    try {
        await client.connect();
        await client.processAudioFile(inputPath, outputPath);
        console.log('\n🎉 Hoàn thành!');
    } catch (error) {
        console.error('\n❌ Lỗi:', error.message);
        process.exit(1);
    } finally {
        client.disconnect();
    }
}

// Chạy chương trình
if (require.main === module) {
    main().catch(console.error);
}

module.exports = RNNoiseWebSocketClient;