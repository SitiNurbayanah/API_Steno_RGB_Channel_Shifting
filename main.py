from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import numpy as np
from PIL import Image
import io
import base64
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class RGBChannelSteganography:
    """
    RGB Channel Steganography implementation
    Hides messages by modifying the least significant bit of RGB channels
    """
    
    @staticmethod
    def string_to_binary(message):
        """Convert string to binary with delimiter"""
        binary = ''.join(format(ord(char), '08b') for char in message)
        return binary + '1111111111111110'  # End delimiter
    
    @staticmethod
    def binary_to_string(binary):
        """Convert binary to string, stopping at delimiter"""
        delimiter = '1111111111111110'
        if delimiter in binary:
            binary = binary[:binary.index(delimiter)]
        
        message = ''
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                try:
                    message += chr(int(byte, 2))
                except ValueError:
                    continue
        return message
    
    @staticmethod
    def encode_message(image_data, message, channel='R'):
        """
        Encode message into image data
        
        Args:
            image_data: PIL Image object
            message: Message to hide
            channel: RGB channel to use ('R', 'G', 'B', or 'ALL')
        
        Returns:
            (success, result_image_data_or_error)
        """
        try:
            # Convert to RGB if needed
            if image_data.mode != 'RGB':
                image_data = image_data.convert('RGB')
            
            img_array = np.array(image_data)
            binary_message = RGBChannelSteganography.string_to_binary(message)
            message_length = len(binary_message)
            
            # Calculate capacity
            height, width, channels = img_array.shape
            max_capacity = height * width * (3 if channel == 'ALL' else 1)
            
            if message_length > max_capacity:
                return False, f"Message too long. Max: {max_capacity} bits, needed: {message_length} bits"
            
            # Select channels
            if channel == 'R':
                channel_indices = [0]
            elif channel == 'G':
                channel_indices = [1]
            elif channel == 'B':
                channel_indices = [2]
            else:  # ALL
                channel_indices = [0, 1, 2]
            
            # Encode message
            bit_index = 0
            for i in range(height):
                for j in range(width):
                    for c in channel_indices:
                        if bit_index < message_length:
                            pixel_value = img_array[i, j, c]
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
            
            # Convert back to PIL Image
            result_img = Image.fromarray(img_array.astype(np.uint8))
            return True, result_img
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def decode_message(image_data, channel='R'):
        """
        Decode message from image data
        
        Args:
            image_data: PIL Image object
            channel: RGB channel used during encoding
        
        Returns:
            (success, decoded_message_or_error)
        """
        try:
            # Convert to RGB if needed
            if image_data.mode != 'RGB':
                image_data = image_data.convert('RGB')
            
            img_array = np.array(image_data)
            height, width, channels = img_array.shape
            
            # Select channels
            if channel == 'R':
                channel_indices = [0]
            elif channel == 'G':
                channel_indices = [1]
            elif channel == 'B':
                channel_indices = [2]
            else:  # ALL
                channel_indices = [0, 1, 2]
            
            # Extract bits
            binary_message = ''
            for i in range(height):
                for j in range(width):
                    for c in channel_indices:
                        pixel_value = img_array[i, j, c]
                        binary_message += str(pixel_value & 1)
            
            # Convert to string
            decoded_message = RGBChannelSteganography.binary_to_string(binary_message)
            return True, decoded_message
            
        except Exception as e:
            return False, str(e)

# API Routes

@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        'service': 'Steganography API',
        'version': '1.1.0',
        'status': 'running',
        'description': 'RGB Channel Steganography API',
        'endpoints': {
            'GET /': 'API information',
            'GET /health': 'Health check',
            'POST /encode': 'Encode message into image (returns JSON with base64)',
            'POST /encode-download': 'Encode message into image (returns file for download)',
            'POST /decode': 'Decode message from image',
            'POST /info': 'Get image capacity information'
        },
        'usage': {
            'encode': 'Send multipart form with "image" file and "message" text, optional "channel" (R/G/B/ALL)',
            'encode-download': 'Same as encode but returns file directly for download',
            'decode': 'Send multipart form with "image" file and optional "channel" (R/G/B/ALL)',
            'info': 'Send multipart form with "image" file'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'steganography-api'
    })

@app.route('/encode', methods=['POST'])
def encode():
    """Encode message into image - returns JSON with base64"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        if 'message' not in request.form:
            return jsonify({'error': 'No message provided'}), 400
        
        file = request.files['image']
        message = request.form['message']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel must be R, G, B, or ALL'}), 400
        
        if not message.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Load image
        try:
            image = Image.open(file.stream)
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Encode message
        success, result = RGBChannelSteganography.encode_message(image, message, channel)
        
        if not success:
            return jsonify({'error': result}), 400
        
        # Convert result image to base64
        img_buffer = io.BytesIO()
        result.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Return base64 encoded image
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'Message successfully encoded',
            'image_base64': img_base64,
            'metadata': {
                'original_filename': file.filename,
                'channel_used': channel,
                'message_length': len(message),
                'output_format': 'PNG'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/encode-download', methods=['POST'])
def encode_download():
    """Encode message into image - returns file directly for download"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        if 'message' not in request.form:
            return jsonify({'error': 'No message provided'}), 400
        
        file = request.files['image']
        message = request.form['message']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel must be R, G, B, or ALL'}), 400
        
        if not message.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Load image
        try:
            image = Image.open(file.stream)
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Encode message
        success, result = RGBChannelSteganography.encode_message(image, message, channel)
        
        if not success:
            return jsonify({'error': result}), 400
        
        # Create file buffer
        img_buffer = io.BytesIO()
        result.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Generate download filename
        original_name = secure_filename(file.filename)
        name_without_ext = os.path.splitext(original_name)[0]
        download_filename = f"encoded_{name_without_ext}_{channel}.png"
        
        # Return file for download
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/decode', methods=['POST'])
def decode():
    """Decode message from image"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        channel = request.form.get('channel', 'R').upper()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        if channel not in ['R', 'G', 'B', 'ALL']:
            return jsonify({'error': 'Channel must be R, G, B, or ALL'}), 400
        
        # Load image
        try:
            image = Image.open(file.stream)
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Decode message
        success, result = RGBChannelSteganography.decode_message(image, channel)
        
        if not success:
            return jsonify({'error': result}), 400
        
        if not result.strip():
            return jsonify({'error': 'No hidden message found or wrong channel'}), 400
        
        return jsonify({
            'success': True,
            'message': result,
            'metadata': {
                'original_filename': file.filename,
                'channel_used': channel,
                'message_length': len(result)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/info', methods=['POST'])
def get_image_info():
    """Get image capacity information"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Load and analyze image
        try:
            image = Image.open(file.stream)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            width, height = image.size
            img_array = np.array(image)
            
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Calculate capacity
        total_pixels = width * height
        capacity_per_channel = total_pixels  # 1 bit per pixel per channel
        total_capacity_all = total_pixels * 3  # All 3 channels
        
        return jsonify({
            'filename': file.filename,
            'dimensions': {
                'width': width,
                'height': height,
                'total_pixels': total_pixels
            },
            'format': image.format,
            'mode': image.mode,
            'capacity': {
                'per_channel': {
                    'bits': capacity_per_channel,
                    'characters': capacity_per_channel // 8,
                    'estimated_words': (capacity_per_channel // 8) // 5
                },
                'all_channels': {
                    'bits': total_capacity_all,
                    'characters': total_capacity_all // 8,
                    'estimated_words': (total_capacity_all // 8) // 5
                }
            },
            'recommendations': {
                'single_channel': f"Up to {capacity_per_channel // 8} characters",
                'all_channels': f"Up to {total_capacity_all // 8} characters",
                'best_practice': "Use 'ALL' channels for longer messages"
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle not found error"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    """Handle method not allowed error"""
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    return jsonify({'error': 'Internal server error'}), 500

# Get port from environment variable (Railway sets PORT)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)