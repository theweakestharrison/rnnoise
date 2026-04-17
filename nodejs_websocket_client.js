#!/usr/bin/env node

/**
 * RNNoise WebSocket Client - Node.js
 * Kết nối với RNNoise WebSocket server để khử tiếng ồn real-time
 * 
 * Usage: node nodejs_websocket_client.js <input_audio_file> [output_file]
 */

const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

class RNNoiseWebSocketClient {
    constructor(serverUrl = 'ws://localhost:9000') {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.isConnected = false;
        this.frameSize = 480;
        this.sampleRate = 48000;
        this.channels = 1;
        this.denoisedChunks = [];
        this.totalChunksSent = 0;
        this.totalChunksReceived = 0;
    }

    /**
     * Kết nối đến WebSocket server
     */
    async connect() {
        return new Promise((resolve, reject) => {
            console.log(`Đang kết nối đến ${this.serverUrl}...`);
            
            this.ws = new WebSocket(this.serverUrl);
            
            this.ws.on('open', () => {
                console.log('✅ Kết nối WebSocket thành công!');
                this.isConnected = true;
                
                // Gửi yêu cầu thông tin stream
                this.sendMessage({
                    type: 'stream_info'
                });
                
                resolve();
            });
            
            this.ws.on('message', (data) => {
                this.handleMessage(data);
            });
            
            this.ws.on('error', (error) => {
                console.error('❌ Lỗi WebSocket:', error);
                reject(error);
            });
            
            this.ws.on('close', () => {
                console.log('🔌 WebSocket đã đóng kết nối');
                this.isConnected = false;
            });
        });
    }

    /**
     * Xử lý message từ server
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data.toString());
            
            switch (message.type) {
                case 'connected':
                    console.log(`📡 Đã kết nối với client ID: ${message.client_id}`);
                    console.log(`🎵 Frame size: ${message.frame_size}, Sample rate: ${message.sample_rate}Hz`);
                    this.frameSize = message.frame_size;
                    this.sampleRate = message.sample_rate;
                    break;
                    
                case 'stream_info':
                    console.log('📋 Thông tin stream:', {
                        sample_rate: message.sample_rate,
                        channels: message.channels,
                        frame_size: message.frame_size,
                        bit_depth: message.bit_depth
                    });
                    break;
                    
                case 'denoised_chunk':
                    this.handleDenoisedChunk(message.data);
                    break;
                    
                case 'buffer_cleared':
                    console.log('🧹 Buffer đã được xóa');
                    break;
                    
                case 'error':
                    console.error('❌ Lỗi từ server:', message.error);
                    break;
                    
                default:
                    console.log('📨 Message không xác định:', message);
            }
        } catch (error) {
            console.error('❌ Lỗi parse message:', error);
        }
    }

    /**
     * Xử lý chunk audio đã được khử tiếng ồn
     */
    handleDenoisedChunk(base64Data) {
        try {
            // Decode base64 thành buffer
            const audioBuffer = Buffer.from(base64Data, 'base64');
            this.denoisedChunks.push(audioBuffer);
            this.totalChunksReceived++;
            
            console.log(`🎧 Nhận chunk ${this.totalChunksReceived}/${this.totalChunksSent} (${audioBuffer.length} bytes)`);
        } catch (error) {
            console.error('❌ Lỗi xử lý denoised chunk:', error);
        }
    }

    /**
     * Gửi message đến server
     */
    sendMessage(message) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('❌ WebSocket chưa kết nối');
        }
    }

    /**
     * Đọc file audio và chuyển đổi thành PCM 16-bit
     */
    readAudioFile(filePath) {
        try {
            console.log(`📁 Đang đọc file: ${filePath}`);
            
            if (!fs.existsSync(filePath)) {
                throw new Error(`File không tồn tại: ${filePath}`);
            }
            
            // Đọc file audio (giả sử là raw PCM 16-bit)
            const audioData = fs.readFileSync(filePath);
            console.log(`📊 Đã đọc ${audioData.length} bytes từ file`);
            
            return audioData;
        } catch (error) {
            console.error('❌ Lỗi đọc file audio:', error);
            throw error;
        }
    }

    /**
     * Chuyển đổi audio data thành chunks và gửi đến server
     */
    async processAudioFile(filePath) {
        try {
            const audioData = this.readAudioFile(filePath);
            
            // Tính toán số lượng samples (16-bit = 2 bytes per sample)
            const totalSamples = audioData.length / 2;
            const totalChunks = Math.ceil(totalSamples / this.frameSize);
            
            console.log(`🔢 Tổng samples: ${totalSamples}, Chunks: ${totalChunks}, Frame size: ${this.frameSize}`);
            
            // Chia audio thành chunks và gửi
            for (let i = 0; i < totalChunks; i++) {
                const startByte = i * this.frameSize * 2; // 2 bytes per sample
                const endByte = Math.min(startByte + (this.frameSize * 2), audioData.length);
                const chunk = audioData.slice(startByte, endByte);
                
                // Nếu chunk cuối cùng nhỏ hơn frame size, pad với zeros
                let paddedChunk = chunk;
                if (chunk.length < this.frameSize * 2) {
                    paddedChunk = Buffer.alloc(this.frameSize * 2);
                    chunk.copy(paddedChunk);
                    console.log(`⚠️  Chunk cuối được pad từ ${chunk.length} đến ${paddedChunk.length} bytes`);
                }
                
                // Encode thành base64 và gửi
                const base64Chunk = paddedChunk.toString('base64');
                this.sendMessage({
                    type: 'audio_chunk',
                    data: base64Chunk
                });
                
                this.totalChunksSent++;
                console.log(`📤 Gửi chunk ${this.totalChunksSent}/${totalChunks} (${paddedChunk.length} bytes)`);
                
                // Delay nhỏ để tránh overwhelm server
                await this.sleep(10);
            }
            
            console.log(`✅ Đã gửi xong ${this.totalChunksSent} chunks`);
        } catch (error) {
            console.error('❌ Lỗi xử lý file audio:', error);
            throw error;
        }
    }

    /**
     * Lưu audio đã được khử tiếng ồn vào file
     */
    saveDenoisedAudio(outputPath) {
        try {
            if (this.denoisedChunks.length === 0) {
                console.warn('⚠️  Không có audio data để lưu');
                return;
            }
            
            // Ghép tất cả chunks lại
            const totalLength = this.denoisedChunks.reduce((sum, chunk) => sum + chunk.length, 0);
            const combinedAudio = Buffer.alloc(totalLength);
            
            let offset = 0;
            for (const chunk of this.denoisedChunks) {
                chunk.copy(combinedAudio, offset);
                offset += chunk.length;
            }
            
            // Lưu vào file
            fs.writeFileSync(outputPath, combinedAudio);
            console.log(`💾 Đã lưu ${combinedAudio.length} bytes vào ${outputPath}`);
            console.log(`🎵 Audio specs: ${combinedAudio.length / 2} samples, ${(combinedAudio.length / 2 / this.sampleRate).toFixed(2)}s`);
            
        } catch (error) {
            console.error('❌ Lỗi lưu file:', error);
            throw error;
        }
    }

    /**
     * Đóng kết nối WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }

    /**
     * Utility function để sleep
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Chờ đến khi nhận đủ tất cả chunks
     */
    async waitForAllChunks(timeoutMs = 30000) {
        const startTime = Date.now();
        
        while (this.totalChunksReceived < this.totalChunksSent) {
            if (Date.now() - startTime > timeoutMs) {
                console.warn(`⏰ Timeout: Chỉ nhận được ${this.totalChunksReceived}/${this.totalChunksSent} chunks`);
                break;
            }
            await this.sleep(100);
        }
        
        console.log(`✅ Đã nhận đủ ${this.totalChunksReceived} chunks`);
    }
}

/**
 * Main function
 */
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.log('Usage: node nodejs_websocket_client.js <input_audio_file> [output_file]');
        console.log('');
        console.log('Examples:');
        console.log('  node nodejs_websocket_client.js input.pcm');
        console.log('  node nodejs_websocket_client.js input.pcm denoised_output.pcm');
        console.log('');
        console.log('Note: Input file phải là raw PCM 16-bit, 48kHz, mono');
        process.exit(1);
    }
    
    const inputFile = args[0];
    const outputFile = args[1] || `denoised_${path.basename(inputFile)}`;
    
    console.log('🚀 RNNoise WebSocket Client');
    console.log(`📁 Input file: ${inputFile}`);
    console.log(`💾 Output file: ${outputFile}`);
    console.log('');
    
    const client = new RNNoiseWebSocketClient();
    
    try {
        // Kết nối đến server
        await client.connect();
        
        // Đợi một chút để nhận stream info
        await client.sleep(1000);
        
        // Xử lý file audio
        await client.processAudioFile(inputFile);
        
        // Đợi nhận tất cả chunks
        console.log('⏳ Đang đợi nhận tất cả chunks...');
        await client.waitForAllChunks();
        
        // Lưu kết quả
        client.saveDenoisedAudio(outputFile);
        
        console.log('🎉 Hoàn thành!');
        
    } catch (error) {
        console.error('❌ Lỗi:', error.message);
        process.exit(1);
    } finally {
        client.disconnect();
    }
}

// Chạy main function
if (require.main === module) {
    main().catch(console.error);
}

module.exports = RNNoiseWebSocketClient;