from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import numpy as np
from PIL import Image
import io
import base64
import os
from werkzeug.utils import secure_filename
import binascii
import tempfile
import uuid

app = Flask(__name__)
CORS(app)

# Konfigurasi
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

# Buat folder jika belum ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class RGBChannelSteganography:
    """
    Kelas untuk stenografi menggunakan RGB Channel Shifting
    Metode: Menyembunyikan pesan dengan menggeser bit terakhir dari setiap channel RGB
    """
    
    @staticmethod
    def string_to_binary(message):
        """Konversi string ke binary"""
        binary = ''.join(format(ord(char), '08b') for char in message)
        return binary + '1111111111111110'  # Delimiter untuk menandai akhir pesan
    
    @staticmethod
    def binary_to_string(binary):
        """Konversi binary ke string"""
        # Cari delimiter
        delimiter = '1111111111111110'
        if delimiter in binary:
            binary = binary[:binary.index(delimiter)]
        
        # Konversi ke string
        message = ''
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                message += chr(int(byte, 2))
        return message
    
    @staticmethod
    def encode_message(image_path, message, output_path, channel='R'):
        """
        Encode pesan ke dalam gambar menggunakan channel shifting
        
        Args:
            image_path: Path gambar asli
            message: Pesan yang akan disembunyikan
            output_path: Path output gambar hasil
            channel: Channel RGB yang akan digunakan ('R', 'G', 'B', atau 'ALL')
        """
        try:
            # Buka gambar
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img)
            
            # Konversi pesan ke binary
            binary_message = RGBChannelSteganography.string_to_binary(message)
            message_length = len(binary_message)
            
            # Hitung kapasitas maksimal
            height, width, channels = img_array.shape
            max_capacity = height * width * (3 if channel == 'ALL' else 1)
            
            if message_length > max_capacity:
                raise ValueError(f"Pesan terlalu panjang. Maksimal {max_capacity} bit, pesan membutuhkan {message_length} bit")
            
            # Pilih channel untuk encoding
            if channel == 'R':
                channel_indices = [0]
            elif channel == 'G':
                channel_indices = [1]
            elif channel == 'B':
                channel_indices = [2]
            else:  # ALL
                channel_indices = [0, 1, 2]
            
            # Encoding
            bit_index = 0
            for i in range(height):
                for j in range(width):
                    for c in channel_indices:
                        if bit_index < message_length:
                            # Ambil bit LSB dari pixel
                            pixel_value = img_array[i, j, c]
                            
                            # Ganti bit terakhir dengan bit pesan
                            message_bit = int(binary_message[bit_index])
                            new_pixel_value = (pixel_value & 0xFE) | message_bit
                            
                            img_array[i, j, c] = new_pixel_value
                            bit_index += 1
                        else:
                            break
                    if bit_index >= message_length:
                        break
                if bit_index >= message_length:
                    break
            
            # Simpan gambar hasil
            result_img = Image.fromarray(img_array.astype(np.uint8))
            result_img.save(output_path, 'PNG')
            
            return True, f"Pesan berhasil disembunyikan dalam channel {channel}"
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def decode_message(image_path, channel='R'):
        """
        Decode pesan dari gambar
        
        Args:
            image_path: Path gambar yang berisi pesan tersembunyi
            channel: Channel yang digunakan saat encoding
        """
        try:
            # Buka gambar
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img)
            
            height, width, channels = img_array.shape
            
            # Pilih channel untuk decoding
            if channel == 'R':
                channel_indices = [0]
            elif channel == 'G':
                channel_indices = [1]
            elif channel == 'B':
                channel_indices = [2]
            else:  # ALL
                channel_indices = [0, 1, 2]
            
            # Ekstrak bit
            binary_message = ''
            for i in range(height):
                for j in range(width):
                    for c in channel_indices:
                        # Ambil bit LSB
                        pixel_value = img_array[i, j, c]
                        binary_message += str(pixel_value & 1)
            
            # Konversi binary ke string
            decoded_message = RGBChannelSteganography.binary_to_string(binary_message)
            
            return True, decoded_message
            
        except Exception as e:
            return False, str(e)

# API Endpoints

@app.route('/', methods=['GET'])
def home():
    """Endpoint untuk informasi API"""
    return jsonify({
        'message': 'Flask Steganography API - RGB Channel Shifting',
        'version': '1.0',
        'endpoints': {
            'POST /encode': 'Encode pesan ke dalam gambar (auto download)',
            'POST /decode': 'Decode pesan dari gambar',
            'GET /info': 'Informasi tentang gambar'
        }
    })

@app.route('/encode', methods=['POST'])
def encode():
    """Endpoint untuk encode pesan ke dalam gambar dengan auto download"""
    
    try:
        # Validasi request
        if 'image' not in request.files:
            return jsonify({'error': 'File gambar tidak ditemukan'}), 400
        
        if 'message' not in request.form:
            return jsonify({'error': 'Pesan tidak ditemukan'}), 400
        
        file = request.files['image']
        message = request.form['message']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Format file tidak didukung'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel harus R, G, B, atau ALL'}), 400
        
        # Generate unique filename untuk menghindari collision
        unique_id = str(uuid.uuid4())[:8]
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        
        # Path file input dan output
        input_filename = f"{unique_id}_{filename}"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        
        output_filename = f"{name}_encoded_{channel.lower()}_{unique_id}.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Simpan file upload
        file.save(input_path)
        
        try:
            # Encode pesan
            success, result = RGBChannelSteganography.encode_message(
                input_path, message, output_path, channel
            )
            
            if success:
                # Kirim file untuk didownload langsung
                def cleanup_files():
                    """Bersihkan file setelah download"""
                    try:
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    except:
                        pass
                
                # Set header untuk download
                return send_file(
                    output_path,
                    as_attachment=True,
                    download_name=f"{name}_encoded_{channel.lower()}.png",
                    mimetype='image/png'
                )
            else:
                # Bersihkan file jika gagal
                if os.path.exists(input_path):
                    os.remove(input_path)
                return jsonify({'error': result}), 400
                
        except Exception as e:
            # Bersihkan file jika terjadi error
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/encode-form', methods=['GET', 'POST'])
def encode_form():
    """Endpoint untuk form HTML encode"""
    if request.method == 'GET':
        # Form HTML untuk testing
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Steganography Encoder</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="file"], input[type="text"], textarea, select { 
                    width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; 
                }
                textarea { height: 100px; resize: vertical; }
                button { 
                    background-color: #007bff; color: white; padding: 10px 20px; 
                    border: none; border-radius: 4px; cursor: pointer; font-size: 16px; 
                }
                button:hover { background-color: #0056b3; }
                .info { background-color: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <h1>🔐 Steganography Encoder</h1>
            <div class="info">
                <strong>Info:</strong> Upload gambar dan pesan untuk disembunyikan. 
                File hasil akan otomatis terdownload.
            </div>
            
            <form action="/encode" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="image">Pilih Gambar:</label>
                    <input type="file" name="image" id="image" accept=".png,.jpg,.jpeg,.bmp" required>
                </div>
                
                <div class="form-group">
                    <label for="message">Pesan yang akan disembunyikan:</label>
                    <textarea name="message" id="message" placeholder="Masukkan pesan rahasia..." required></textarea>
                </div>
                
                <div class="form-group">
                    <label for="channel">Channel RGB:</label>
                    <select name="channel" id="channel">
                        <option value="R">Red Channel</option>
                        <option value="G">Green Channel</option>
                        <option value="B">Blue Channel</option>
                        <option value="ALL">All Channels</option>
                    </select>
                </div>
                
                <button type="submit">🔒 Encode & Download</button>
            </form>
        </body>
        </html>
        '''
    else:
        # Redirect ke endpoint encode
        return encode()
def encode_json():
    """Endpoint untuk encode dengan response JSON (untuk API)"""
    try:
        # Validasi request
        if 'image' not in request.files:
            return jsonify({'error': 'File gambar tidak ditemukan'}), 400
        
        if 'message' not in request.form:
            return jsonify({'error': 'Pesan tidak ditemukan'}), 400
        
        file = request.files['image']
        message = request.form['message']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Format file tidak didukung'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel harus R, G, B, atau ALL'}), 400
        
        # Simpan file upload
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Generate output filename
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_encoded_{channel.lower()}.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Encode pesan
        success, result = RGBChannelSteganography.encode_message(
            input_path, message, output_path, channel
        )
        
        if success:
            # Baca file hasil dan konversi ke base64
            with open(output_path, 'rb') as f:
                img_data = f.read()
            
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Bersihkan file temporary
            os.remove(input_path)
            
            return jsonify({
                'success': True,
                'message': result,
                'filename': output_filename,
                'image_base64': img_base64,
                'channel_used': channel,
                'message_length': len(message),
                'download_url': f'/download/{output_filename}'
            })
        else:
            os.remove(input_path)
            return jsonify({'error': result}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    """Endpoint untuk decode pesan dari gambar"""
    if request.method == 'GET':
        # Form HTML untuk testing
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Steganography Decoder</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="file"], select { 
                    width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; 
                }
                button { 
                    background-color: #28a745; color: white; padding: 10px 20px; 
                    border: none; border-radius: 4px; cursor: pointer; font-size: 16px; 
                }
                button:hover { background-color: #218838; }
                .result { 
                    background-color: #f8f9fa; padding: 15px; border-radius: 4px; 
                    margin-top: 20px; border-left: 4px solid #28a745; 
                }
                .info { background-color: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <h1>🔓 Steganography Decoder</h1>
            <div class="info">
                <strong>Info:</strong> Upload gambar yang berisi pesan tersembunyi untuk mengekstrak pesannya.
            </div>
            
            <form method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="image">Pilih Gambar:</label>
                    <input type="file" name="image" id="image" accept=".png,.jpg,.jpeg,.bmp" required>
                </div>
                
                <div class="form-group">
                    <label for="channel">Channel RGB yang digunakan saat encode:</label>
                    <select name="channel" id="channel">
                        <option value="R">Red Channel</option>
                        <option value="G">Green Channel</option>
                        <option value="B">Blue Channel</option>
                        <option value="ALL">All Channels</option>
                    </select>
                </div>
                
                <button type="submit">🔍 Decode Message</button>
            </form>
        </body>
        </html>
        '''
    
    try:
        # Validasi request
        if 'image' not in request.files:
            return jsonify({'error': 'File gambar tidak ditemukan'}), 400
        
        file = request.files['image']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Format file tidak didukung'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel harus R, G, B, atau ALL'}), 400
        
        # Simpan file upload
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Decode pesan
        success, result = RGBChannelSteganography.decode_message(input_path, channel)
        
        # Bersihkan file temporary
        os.remove(input_path)
        
        if success:
            # Jika request dari browser (form), tampilkan HTML
            if 'text/html' in request.headers.get('Accept', ''):
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Decode Result</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                        .result {{ 
                            background-color: #d4edda; padding: 20px; border-radius: 4px; 
                            border-left: 4px solid #28a745; margin-bottom: 20px; 
                        }}
                        .back-btn {{ 
                            background-color: #6c757d; color: white; padding: 10px 20px; 
                            text-decoration: none; border-radius: 4px; display: inline-block; 
                        }}
                        .back-btn:hover {{ background-color: #545b62; }}
                        .message-box {{ 
                            background-color: white; padding: 15px; border-radius: 4px; 
                            border: 1px solid #ddd; word-wrap: break-word; 
                        }}
                    </style>
                </head>
                <body>
                    <h1>✅ Pesan Berhasil Didecode</h1>
                    <div class="result">
                        <h3>Hasil Decode:</h3>
                        <div class="message-box">
                            <strong>Pesan:</strong><br>
                            {result.replace('<', '&lt;').replace('>', '&gt;')}
                        </div>
                        <br>
                        <strong>Channel yang digunakan:</strong> {channel}<br>
                        <strong>Panjang pesan:</strong> {len(result)} karakter
                    </div>
                    <a href="/decode" class="back-btn">← Decode Lagi</a>
                </body>
                </html>
                '''
            else:
                # Response JSON untuk API
                return jsonify({
                    'success': True,
                    'message': result,
                    'channel_used': channel,
                    'message_length': len(result)
                })
        else:
            if 'text/html' in request.headers.get('Accept', ''):
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Decode Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                        .error {{ 
                            background-color: #f8d7da; padding: 20px; border-radius: 4px; 
                            border-left: 4px solid #dc3545; margin-bottom: 20px; 
                        }}
                        .back-btn {{ 
                            background-color: #6c757d; color: white; padding: 10px 20px; 
                            text-decoration: none; border-radius: 4px; display: inline-block; 
                        }}
                        .back-btn:hover {{ background-color: #545b62; }}
                    </style>
                </head>
                <body>
                    <h1>❌ Error Decode</h1>
                    <div class="error">
                        <strong>Error:</strong> {result}
                    </div>
                    <a href="/decode" class="back-btn">← Coba Lagi</a>
                </body>
                </html>
                '''
            else:
                return jsonify({'error': result}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/info', methods=['POST'])
def get_image_info():
    """Endpoint untuk mendapatkan informasi gambar"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'File gambar tidak ditemukan'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Format file tidak didukung'}), 400
        
        # Simpan file sementara
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Analisis gambar
        img = Image.open(input_path)
        img_array = np.array(img)
        
        if len(img_array.shape) == 3:
            height, width, channels = img_array.shape
        else:
            height, width = img_array.shape
            channels = 1
        
        # Hitung kapasitas maksimal untuk setiap channel
        capacity_per_channel = height * width
        total_capacity = capacity_per_channel * (3 if channels >= 3 else channels)
        
        # Bersihkan file temporary
        os.remove(input_path)
        
        return jsonify({
            'filename': file.filename,
            'dimensions': f"{width}x{height}",
            'channels': channels,
            'format': img.format,
            'mode': img.mode,
            'capacity': {
                'per_channel_bits': capacity_per_channel,
                'per_channel_chars': capacity_per_channel // 8,
                'total_bits': total_capacity,
                'total_chars': total_capacity // 8
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint untuk download file hasil encoding"""
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File tidak ditemukan'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File terlalu besar. Maksimal 16MB'}), 413

# Cleanup function untuk menghapus file lama
def cleanup_old_files():
    """Bersihkan file lama dari folder upload dan output"""
    import time
    current_time = time.time()
    
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                # Hapus file yang lebih dari 1 jam
                if current_time - os.path.getctime(file_path) > 3600:
                    try:
                        os.remove(file_path)
                    except:
                        pass

if __name__ == '__main__':
    print("🔐 Flask Steganography API - RGB Channel Shifting")
    print("=" * 50)
    print("Endpoints tersedia:")
    print("- POST /encode        - Encode pesan (auto download)")
    print("- POST /encode-json   - Encode dengan response JSON")
    print("- GET  /encode-form   - Form encode")
    print("- GET  /decode        - Form decode")
    print("- POST /decode        - Decode pesan dari gambar") 
    print("- POST /info          - Info kapasitas gambar")
    print("- GET  /download/<filename> - Download hasil")
    print("=" * 50)
    print("🌐 Server berjalan di: http://localhost:5000")
    print("📝 Form encode: http://localhost:5000/encode-form")
    print("🔍 Form decode: http://localhost:5000/decode")
    
    # Cleanup file lama saat startup
    cleanup_old_files()
    
    app.run(debug=True, host='0.0.0.0', port=5000)