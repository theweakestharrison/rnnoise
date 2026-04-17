#!/usr/bin/env node

/**
 * Test script cho RNNoise WebSocket Client
 * Tạo audio test data và test client
 */

const fs = require('fs');
const path = require('path');
const RNNoiseWebSocketClient = require('./nodejs_websocket_client');

/**
 * Tạo test audio data (raw PCM 16-bit, 48kHz, mono)
 */
function createTestAudio(filename, durationSeconds = 2) {
    const sampleRate = 48000;
    const channels = 1;
    const bitsPerSample = 16;
    const totalSamples = sampleRate * durationSeconds * channels;
    
    console.log(`🎵 Tạo test audio: ${filename}`);
    console.log(`   Duration: ${durationSeconds}s`);
    console.log(`   Sample rate: ${sampleRate}Hz`);
    console.log(`   Channels: ${channels}`);
    console.log(`   Total samples: ${totalSamples}`);
    
    // Tạo buffer cho audio data (2 bytes per sample)
    const audioBuffer = Buffer.alloc(totalSamples * 2);
    
    // Tạo sine wave với noise
    for (let i = 0; i < totalSamples; i++) {
        const time = i / sampleRate;
        
        // Tạo sine wave (440Hz - note A4)
        const sineWave = Math.sin(2 * Math.PI * 440 * time) * 0.3;
        
        // Thêm noise
        const noise = (Math.random() - 0.5) * 0.2;
        
        // Combine signal + noise
        const sample = sineWave + noise;
        
        // Convert to 16-bit signed integer
        const sampleInt16 = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)));
        
        // Write to buffer (little-endian)
        audioBuffer.writeInt16LE(sampleInt16, i * 2);
    }
    
    // Lưu vào file
    fs.writeFileSync(filename, audioBuffer);
    console.log(`✅ Đã tạo test audio: ${audioBuffer.length} bytes`);
    
    return filename;
}

/**
 * Kiểm tra xem server có đang chạy không
 */
async function checkServer(url = 'ws://localhost:9000') {
    return new Promise((resolve) => {
        const WebSocket = require('ws');
        const ws = new WebSocket(url);
        
        const timeout = setTimeout(() => {
            ws.close();
            resolve(false);
        }, 3000);
        
        ws.on('open', () => {
            clearTimeout(timeout);
            ws.close();
            resolve(true);
        });
        
        ws.on('error', () => {
            clearTimeout(timeout);
            resolve(false);
        });
    });
}

/**
 * So sánh file input và output
 */
function compareAudioFiles(inputFile, outputFile) {
    try {
        const inputData = fs.readFileSync(inputFile);
        const outputData = fs.readFileSync(outputFile);
        
        console.log('\n📊 So sánh audio files:');
        console.log(`   Input size: ${inputData.length} bytes`);
        console.log(`   Output size: ${outputData.length} bytes`);
        console.log(`   Size difference: ${outputData.length - inputData.length} bytes`);
        
        // Tính RMS của input và output
        const inputSamples = inputData.length / 2;
        const outputSamples = outputData.length / 2;
        
        let inputRMS = 0;
        let outputRMS = 0;
        
        for (let i = 0; i < Math.min(inputSamples, outputSamples); i++) {
            const inputSample = inputData.readInt16LE(i * 2);
            const outputSample = outputData.readInt16LE(i * 2);
            
            inputRMS += inputSample * inputSample;
            outputRMS += outputSample * outputSample;
        }
        
        inputRMS = Math.sqrt(inputRMS / Math.min(inputSamples, outputSamples));
        outputRMS = Math.sqrt(outputRMS / Math.min(inputSamples, outputSamples));
        
        console.log(`   Input RMS: ${inputRMS.toFixed(2)}`);
        console.log(`   Output RMS: ${outputRMS.toFixed(2)}`);
        console.log(`   RMS reduction: ${((inputRMS - outputRMS) / inputRMS * 100).toFixed(1)}%`);
        
    } catch (error) {
        console.error('❌ Lỗi so sánh files:', error.message);
    }
}

/**
 * Main test function
 */
async function runTest() {
    console.log('🧪 RNNoise WebSocket Client Test');
    console.log('================================\n');
    
    // Kiểm tra server
    console.log('🔍 Kiểm tra WebSocket server...');
    const serverRunning = await checkServer();
    
    if (!serverRunning) {
        console.error('❌ WebSocket server không chạy tại ws://localhost:9000');
        console.log('💡 Hãy chạy server trước:');
        console.log('   python3 simple_websocket_api.py');
        process.exit(1);
    }
    
    console.log('✅ WebSocket server đang chạy\n');
    
    // Tạo test audio
    const testAudioFile = 'test_audio_nodejs.pcm';
    const outputFile = 'denoised_nodejs_output.pcm';
    
    createTestAudio(testAudioFile, 3); // 3 seconds
    
    console.log('\n🚀 Bắt đầu test WebSocket client...\n');
    
    // Tạo client và test
    const client = new RNNoiseWebSocketClient();
    
    try {
        // Kết nối
        await client.connect();
        
        // Đợi stream info
        await client.sleep(1000);
        
        // Xử lý audio
        await client.processAudioFile(testAudioFile);
        
        // Đợi nhận tất cả chunks
        console.log('\n⏳ Đang đợi nhận tất cả chunks...');
        await client.waitForAllChunks(15000); // 15 seconds timeout
        
        // Lưu kết quả
        client.saveDenoisedAudio(outputFile);
        
        // So sánh kết quả
        compareAudioFiles(testAudioFile, outputFile);
        
        console.log('\n🎉 Test hoàn thành thành công!');
        console.log(`📁 Files được tạo:`);
        console.log(`   Input: ${testAudioFile}`);
        console.log(`   Output: ${outputFile}`);
        
    } catch (error) {
        console.error('\n❌ Test thất bại:', error.message);
        process.exit(1);
    } finally {
        client.disconnect();
    }
}

/**
 * Cleanup function
 */
function cleanup() {
    const filesToClean = [
        'test_audio_nodejs.pcm',
        'denoised_nodejs_output.pcm'
    ];
    
    console.log('\n🧹 Dọn dẹp files...');
    filesToClean.forEach(file => {
        if (fs.existsSync(file)) {
            fs.unlinkSync(file);
            console.log(`   Đã xóa: ${file}`);
        }
    });
}

// Main execution
if (require.main === module) {
    // Handle cleanup on exit
    process.on('SIGINT', () => {
        console.log('\n\n⏹️  Test bị dừng bởi user');
        cleanup();
        process.exit(0);
    });
    
    process.on('exit', () => {
        // cleanup(); // Uncomment nếu muốn tự động xóa files
    });
    
    runTest().catch(error => {
        console.error('❌ Lỗi test:', error);
        process.exit(1);
    });
}