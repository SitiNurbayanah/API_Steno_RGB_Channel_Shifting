# RGB Channel Steganography API & Interface

A complete steganography solution that allows you to hide and reveal secret messages in images using RGB channel manipulation. This project includes both a Flask API backend and a modern web interface.

## 🌐 Live Demo

**API Endpoint:** `https://apistenorgbchannelshifting-production.up.railway.app/`

⚠️ **Important Notice:** The Flask API is deployed on Railway and will automatically stop working on **July 10, 2025** due to deployment limitations.

## 📋 Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [API Documentation](#api-documentation)
- [Web Interface](#web-interface)
- [Installation & Setup](#installation--setup)
- [Usage Examples](#usage-examples)
- [Technical Details](#technical-details)
- [Limitations](#limitations)
- [Contributing](#contributing)

## ✨ Features

### API Features
- **Hide messages** in RGB channels of images
- **Extract hidden messages** from encoded images
- **Multiple channel support** (R, G, B, or ALL channels)
- **Image capacity analysis** to determine storage limits
- **File format support** for PNG, JPG, JPEG, BMP
- **RESTful API** with JSON responses
- **CORS enabled** for web interface integration

### Web Interface Features
- **Modern, responsive design** with gradient backgrounds
- **Drag & drop file upload** with visual feedback
- **Real-time encoding/decoding** with loading indicators
- **Image preview** and direct download functionality
- **Capacity analysis** showing storage potential
- **Error handling** with user-friendly messages

## 🔬 How It Works

The steganography technique uses **Least Significant Bit (LSB)** modification in RGB channels:

1. **Encoding Process:**
   - Convert secret message to binary
   - Modify the least significant bit of selected RGB channel(s)
   - Add delimiter to mark message end
   - Save as new image file

2. **Decoding Process:**
   - Extract least significant bits from selected channel(s)
   - Convert binary back to text
   - Stop at delimiter to retrieve original message

3. **Channel Options:**
   - **R (Red):** Use only red channel
   - **G (Green):** Use only green channel  
   - **B (Blue):** Use only blue channel
   - **ALL:** Use all three channels for maximum capacity

## 📚 API Documentation

### Base URL
```
https://apistenorgbchannelshifting-production.up.railway.app
```

### Endpoints

#### 1. **GET /** - API Information
Returns API status and endpoint documentation.

**Response:**
```json
{
  "service": "Steganography API",
  "version": "1.1.0",
  "status": "running",
  "endpoints": { ... }
}
```

#### 2. **GET /health** - Health Check
Check if the API is running properly.

**Response:**
```json
{
  "status": "healthy",
  "service": "steganography-api"
}
```

#### 3. **POST /encode** - Encode Message
Hide a message in an image and return base64 encoded result.

**Parameters:**
- `image` (file): Image file (PNG, JPG, JPEG, BMP)
- `message` (string): Secret message to hide
- `channel` (string, optional): RGB channel to use (R/G/B/ALL, default: R)

**Response:**
```json
{
  "success": true,
  "message": "Message successfully encoded",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "metadata": {
    "original_filename": "image.jpg",
    "channel_used": "R",
    "message_length": 12,
    "output_format": "PNG"
  }
}
```

#### 4. **POST /encode-download** - Encode & Download
Same as `/encode` but returns the file directly for download.

#### 5. **POST /decode** - Decode Message
Extract hidden message from an encoded image.

**Parameters:**
- `image` (file): Encoded image file
- `channel` (string, optional): RGB channel used during encoding (R/G/B/ALL, default: R)

**Response:**
```json
{
  "success": true,
  "message": "Hello World!",
  "metadata": {
    "original_filename": "encoded_image.png",
    "channel_used": "R",
    "message_length": 12
  }
}
```

#### 6. **POST /info** - Image Analysis
Get capacity information for an image.

**Parameters:**
- `image` (file): Image file to analyze

**Response:**
```json
{
  "filename": "image.jpg",
  "dimensions": {
    "width": 1920,
    "height": 1080,
    "total_pixels": 2073600
  },
  "capacity": {
    "per_channel": {
      "bits": 2073600,
      "characters": 259200,
      "estimated_words": 51840
    },
    "all_channels": {
      "bits": 6220800,
      "characters": 777600,
      "estimated_words": 155520
    }
  }
}
```

## 🖥️ Web Interface

The web interface provides an easy-to-use frontend for the API with three main sections:

### 1. Encode Message
- Upload an image file
- Enter your secret message
- Select RGB channel (R/G/B/ALL)
- Download the encoded image

### 2. Decode Message
- Upload an encoded image
- Select the channel used during encoding
- View the hidden message

### 3. Image Info
- Upload any image
- See capacity analysis
- Get recommendations for optimal usage

### Interface Features
- **Modern Design:** Gradient backgrounds and smooth animations
- **Responsive Layout:** Works on desktop, tablet, and mobile
- **File Validation:** Automatic format checking
- **Real-time Feedback:** Loading states and error messages
- **Download Integration:** Direct download of encoded images

## 🚀 Installation & Setup

### Option 1: Use Live API (Recommended)
The API is already deployed and ready to use. Just save the web interface HTML file and open it in your browser.

### Option 2: Local Development

#### Prerequisites
- Python 3.7+
- pip (Python package manager)

#### Backend Setup
1. **Clone or download the Flask application code**

2. **Install dependencies:**
```bash
pip install flask flask-cors numpy pillow werkzeug
```

3. **Run the Flask application:**
```bash
python app.py
```

4. **API will be available at:** `http://localhost:5000`

#### Frontend Setup
1. **Save the web interface HTML file**
2. **Update the API_BASE URL in the JavaScript:**
```javascript
const API_BASE = 'http://localhost:5000';  // For local development
```
3. **Open the HTML file in your web browser**

## 🎯 Usage Examples

### Using cURL

#### Encode a message:
```bash
curl -X POST \
  https://apistenorgbchannelshifting-production.up.railway.app/encode \
  -F "image=@photo.jpg" \
  -F "message=Secret Message" \
  -F "channel=ALL"
```

#### Decode a message:
```bash
curl -X POST \
  https://apistenorgbchannelshifting-production.up.railway.app/decode \
  -F "image=@encoded_photo.png" \
  -F "channel=ALL"
```

#### Get image info:
```bash
curl -X POST \
  https://apistenorgbchannelshifting-production.up.railway.app/info \
  -F "image=@photo.jpg"
```

### Using Python

```python
import requests

# Encode a message
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'https://apistenorgbchannelshifting-production.up.railway.app/encode',
        files={'image': f},
        data={'message': 'Hello World!', 'channel': 'ALL'}
    )
    result = response.json()
    print(result['message'])

# Decode a message
with open('encoded_image.png', 'rb') as f:
    response = requests.post(
        'https://apistenorgbchannelshifting-production.up.railway.app/decode',
        files={'image': f},
        data={'channel': 'ALL'}
    )
    result = response.json()
    print(f"Hidden message: {result['message']}")
```

## ⚙️ Technical Details

### Steganography Algorithm
- **Method:** Least Significant Bit (LSB) modification
- **Channels:** RGB channels of image pixels
- **Delimiter:** `1111111111111110` (binary) marks message end
- **Encoding:** UTF-8 character encoding
- **Format:** Output images saved as PNG for lossless compression

### File Support
- **Input formats:** PNG, JPG, JPEG, BMP
- **Output format:** PNG (to preserve hidden data)
- **Max file size:** 16MB
- **Auto-conversion:** Non-RGB images converted automatically

### Capacity Calculation
- **Single channel:** 1 bit per pixel = width × height bits
- **All channels:** 3 bits per pixel = width × height × 3 bits
- **Character estimate:** Total bits ÷ 8 (8 bits per character)
- **Word estimate:** Characters ÷ 5 (average word length)

## ⚠️ Limitations

### Deployment Limitations
- **Railway hosting expires:** July 10, 2025
- **File size limit:** 16MB maximum
- **Temporary storage:** Files not permanently stored

### Technical Limitations
- **Lossy compression:** JPEG compression may damage hidden data
- **Visible changes:** Large messages may cause slight visual artifacts
- **Format dependency:** Best results with PNG format
- **Channel consistency:** Must use same channel for encode/decode

### Security Considerations
- **No encryption:** Messages stored as plain text in binary
- **Detectable:** Sophisticated analysis can detect LSB modification
- **No authentication:** No verification of message integrity
- **Public API:** All data processed on public server

## 🔧 Error Handling

The API provides comprehensive error messages for common issues:

- **File validation errors**
- **Message capacity exceeded**
- **Invalid channel selection**
- **Corrupted image files**
- **Network connectivity issues**

## 🤝 Contributing

This project is open for improvements! Areas for contribution:

1. **Security enhancements** (message encryption)
2. **Additional algorithms** (DCT-based steganography)
3. **Format support** (WebP, TIFF, etc.)
4. **Mobile optimization** for the web interface
5. **Batch processing** capabilities

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 📞 Support

For issues or questions:
1. Check the API health endpoint: `/health`
2. Verify file formats and sizes
3. Test with different RGB channels
4. Review error messages for specific guidance

---

**Last Updated:** June 28, 2025  
**API Status:** ✅ Active (until July 10, 2025)
