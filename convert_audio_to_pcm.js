#!/usr/bin/env node

/**
 * Audio Converter - Chuyển đổi audio files sang PCM format cho RNNoise
 * Sử dụng FFmpeg để convert các định dạng audio khác nhau
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class AudioConverter {
    constructor() {
        this.targetSampleRate = 48000;
        this.targetChannels = 1;
        this.targetFormat = 's16le'; // 16-bit signed little-endian
    }

    /**
     * Kiểm tra xem FFmpeg có được cài đặt không
     */
    async checkFFmpeg() {
        return new Promise((resolve) => {
            const ffmpeg = spawn('ffmpeg', ['-version']);
            
            ffmpeg.on('error', () => {
                resolve(false);
            });
            
            ffmpeg.on('close', (code) => {
                resolve(code === 0);
            });
        });
    }

    /**
     * Lấy thông tin audio file
     */
    async getAudioInfo(inputFile) {
        return new Promise((resolve, reject) => {
            const ffprobe = spawn('ffprobe', [
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                inputFile
            ]);

            let output = '';
            
            ffprobe.stdout.on('data', (data) => {
                output += data.toString();
            });

            ffprobe.on('error', (error) => {
                reject(new Error(`FFprobe error: ${error.message}`));
            });

            ffprobe.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`FFprobe exited with code ${code}`));
                    return;
                }

                try {
                    const info = JSON.parse(output);
                    const audioStream = info.streams.find(s => s.codec_type === 'audio');
                    
                    if (!audioStream) {
                        reject(new Error('Không tìm thấy audio stream'));
                        return;
                    }

                    resolve({
                        duration: parseFloat(info.format.duration),
                        sampleRate: parseInt(audioStream.sample_rate),
                        channels: audioStream.channels,
                        codec: audioStream.codec_name,
                        bitrate: parseInt(info.format.bit_rate) || 'unknown'
                    });
                } catch (error) {
                    reject(new Error(`Lỗi parse audio info: ${error.message}`));
                }
            });
        });
    }

    /**
     * Chuyển đổi audio file sang PCM format
     */
    async convertToPCM(inputFile, outputFile) {
        return new Promise((resolve, reject) => {
            console.log(`🔄 Đang chuyển đổi: ${inputFile} -> ${outputFile}`);
            
            const ffmpeg = spawn('ffmpeg', [
                '-i', inputFile,
                '-ar', this.targetSampleRate.toString(),
                '-ac', this.targetChannels.toString(),
                '-f', this.targetFormat,
                '-y', // Overwrite output file
                outputFile
            ]);

            let errorOutput = '';

            ffmpeg.stderr.on('data', (data) => {
                errorOutput += data.toString();
            });

            ffmpeg.on('error', (error) => {
                reject(new Error(`FFmpeg error: ${error.message}`));
            });

            ffmpeg.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`FFmpeg exited with code ${code}\nError: ${errorOutput}`));
                    return;
                }

                // Kiểm tra file output
                if (!fs.existsSync(outputFile)) {
                    reject(new Error('Output file không được tạo'));
                    return;
                }

                const stats = fs.statSync(outputFile);
                console.log(`✅ Chuyển đổi thành công: ${stats.size} bytes`);
                
                resolve({
                    outputFile,
                    size: stats.size,
                    samples: stats.size / 2, // 16-bit = 2 bytes per sample
                    duration: (stats.size / 2) / this.targetSampleRate
                });
            });
        });
    }

    /**
     * Xử lý file audio hoàn chỉnh
     */
    async processAudioFile(inputFile, outputFile = null) {
        try {
            // Tạo output filename nếu không được cung cấp
            if (!outputFile) {
                const ext = path.extname(inputFile);
                const basename = path.basename(inputFile, ext);
                outputFile = `${basename}_converted.pcm`;
            }

            // Kiểm tra input file
            if (!fs.existsSync(inputFile)) {
                throw new Error(`Input file không tồn tại: ${inputFile}`);
            }

            // Lấy thông tin audio
            console.log('📋 Đang lấy thông tin audio...');
            const audioInfo = await this.getAudioInfo(inputFile);
            
            console.log('🎵 Thông tin audio input:');
            console.log(`   Duration: ${audioInfo.duration.toFixed(2)}s`);
            console.log(`   Sample rate: ${audioInfo.sampleRate}Hz`);
            console.log(`   Channels: ${audioInfo.channels}`);
            console.log(`   Codec: ${audioInfo.codec}`);
            console.log(`   Bitrate: ${audioInfo.bitrate}`);

            // Chuyển đổi
            const result = await this.convertToPCM(inputFile, outputFile);
            
            console.log('\n📊 Kết quả chuyển đổi:');
            console.log(`   Output file: ${result.outputFile}`);
            console.log(`   Size: ${result.size} bytes`);
            console.log(`   Samples: ${result.samples}`);
            console.log(`   Duration: ${result.duration.toFixed(2)}s`);
            console.log(`   Format: PCM 16-bit, ${this.targetSampleRate}Hz, ${this.targetChannels} channel`);

            return result;

        } catch (error) {
            throw new Error(`Lỗi xử lý audio: ${error.message}`);
        }
    }
}

/**
 * Main function
 */
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.log('🎵 Audio Converter for RNNoise');
        console.log('Usage: node convert_audio_to_pcm.js <input_file> [output_file]');
        console.log('');
        console.log('Examples:');
        console.log('  node convert_audio_to_pcm.js audio.wav');
        console.log('  node convert_audio_to_pcm.js audio.mp3 converted.pcm');
        console.log('  node convert_audio_to_pcm.js audio.flac');
        console.log('');
        console.log('Supported formats: WAV, MP3, FLAC, OGG, M4A, AAC, và nhiều format khác');
        console.log('Output: PCM 16-bit, 48kHz, mono');
        process.exit(1);
    }
    
    const inputFile = args[0];
    const outputFile = args[1];
    
    console.log('🚀 Audio Converter for RNNoise');
    console.log(`📁 Input: ${inputFile}`);
    if (outputFile) {
        console.log(`💾 Output: ${outputFile}`);
    }
    console.log('');
    
    const converter = new AudioConverter();
    
    try {
        // Kiểm tra FFmpeg
        console.log('🔍 Kiểm tra FFmpeg...');
        const ffmpegAvailable = await converter.checkFFmpeg();
        
        if (!ffmpegAvailable) {
            throw new Error('FFmpeg không được cài đặt hoặc không có trong PATH');
        }
        
        console.log('✅ FFmpeg có sẵn\n');
        
        // Xử lý file
        const result = await converter.processAudioFile(inputFile, outputFile);
        
        console.log('\n🎉 Chuyển đổi hoàn thành!');
        console.log(`📁 File PCM: ${result.outputFile}`);
        console.log('\n💡 Bây giờ bạn có thể sử dụng file này với RNNoise WebSocket client:');
        console.log(`   node nodejs_websocket_client.js ${result.outputFile}`);
        
    } catch (error) {
        console.error('❌ Lỗi:', error.message);
        
        if (error.message.includes('FFmpeg')) {
            console.log('\n💡 Cài đặt FFmpeg:');
            console.log('   Ubuntu/Debian: sudo apt-get install ffmpeg');
            console.log('   macOS: brew install ffmpeg');
            console.log('   Windows: Download từ https://ffmpeg.org/download.html');
        }
        
        process.exit(1);
    }
}

// Chạy main function
if (require.main === module) {
    main().catch(console.error);
}

module.exports = AudioConverter;