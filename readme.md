# BingHome GitHub Repository Structure

## 📁 File Structure and Order

Create your GitHub repository with these files in this exact structure:

```
binghome/
├── README.md                 # Main documentation (file 1)
├── LICENSE                   # MIT License (file 2)
├── requirements.txt          # Python dependencies (file 3)
├── install.sh               # Installation script (file 4)
├── app.py                   # Main application (file 5)
├── templates/
│   └── index.html           # Web interface (file 6)
├── static/                  # Static files directory
│   └── .gitkeep            # Keep empty directory (file 7)
├── settings.json.example    # Example settings (file 8)
├── .env.example             # Environment example (file 9)
├── .gitignore              # Git ignore file (file 10)
├── systemd/
│   └── binghome.service    # Systemd service (file 11)
└── docs/
    ├── HARDWARE.md          # Hardware guide (file 12)
    ├── API.md               # API documentation (file 13)
    └── TROUBLESHOOTING.md   # Troubleshooting (file 14)
```

## File Contents

### File 1: README.md
```markdown
# BingHome - Smart Home Control System

[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](https://github.com/oodog/binghome)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)

A modern smart home control system with voice recognition, Google Photos integration, and sensor calibration, optimized for Raspberry Pi 5.

## ✨ Features

- 🎤 **Multiple Voice Engines**: Whisper, Vosk, or Google Speech
- 🤖 **ChatGPT Integration**: Natural language understanding
- 🔐 **OAuth Support**: Sign in with ChatGPT account
- 🌡️ **Sensor Monitoring**: Temperature, humidity, gas, light with calibration
- 📸 **Google Photos**: Rotating photo slideshow from your albums
- 🏠 **Home Assistant**: Full integration support
- 📱 **Responsive UI**: Works on any device
- 🔄 **Auto Fallback**: Switches between local and cloud voice

## 🚀 Quick Start

```bash
curl -sSL https://raw.githubusercontent.com/oodog/binghome/refs/heads/master/install.sh| bash
```

Or clone and install manually:

```bash
git clone https://github.com/oodog/binghome.git
cd binghome
chmod +x install.sh
./install.sh
```

## 📋 Requirements

- Raspberry Pi 4/5 (2GB+ RAM)
- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+
- USB microphone (optional)
- Speakers (optional)

## 🔧 Configuration

1. **Access the web interface**: `http://<your-pi-ip>:5000`
2. **Click the settings icon** (⚙️)
3. **Configure your settings**:
   - **Sensor Calibration**: Adjust temperature offset if readings are off
   - **Google Photos**: Connect your account for photo slideshow ([Setup Guide](GOOGLE_PHOTOS_SETUP.md))
   - **API Keys**: Add OpenAI, Bing News, Home Assistant tokens
   - **Voice Mode**: Choose between Auto, Vosk, Whisper, or Google
4. **Select voice mode**:
   - Auto: Tries local first, falls back to cloud
   - Vosk: Offline, lightweight (200MB RAM)
   - Whisper: Best quality (1GB RAM)
   - Google: Cloud-based, free tier available

## 🎤 Voice Commands

Say "Hey Bing" followed by:
- "What's the temperature?"
- "Turn on the lights"
- "Turn off the lights"
- "What's the humidity?"
- "Check the gas sensor"
- "Set temperature to 22 degrees"
🆕 New in Version 2.2.0

### Temperature Sensor Calibration
- Calibrate your DHT22 sensor readings in the Settings page
- Real-time preview showing raw vs calibrated temperature
- Perfect for sensors that run consistently high or low

### Google Photos Integration
- Display a rotating slideshow from your Google Photos albums
- Easy OAuth setup with step-by-step guide
- Configurable slideshow interval (5-300 seconds)
- Smooth fade transitions between photos
- Works with ngrok for easy HTTPS access

**Setup Instructions**: See [Google Photos Setup Guide](GOOGLE_PHOTOS_SETUP.md) and [ngrok Setup Guide](NGROK_SETUP.md)

## 📚 Documentation

- [Google Photos Setup](GOOGLE_PHOTOS_SETUP.md) - Complete OAuth configuration guide
- [ngrok Setup](NGROK_SETUP.md) - Quick HTTPS tunnel for Google OAuth## 📚 Documentation

- [Hardware Setup Guide](docs/HARDWARE.md)
- [API Documentation](docs/API.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

## 📜 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Credits

- OpenAI for Whisper and ChatGPT
- Vosk for offline speech recognition
- Adafruit for sensor libraries
- Home Assistant community
```

### File 2: LICENSE
```
MIT License

Copyright (c) 2024 BingHome

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### File 3: requirements.txt
```
# Core
flask==2.3.3
flask-cors==4.0.0
flask-socketio==5.3.4
python-socketio==5.9.0
requests==2.31.0
numpy==1.24.3

# Hardware (Raspberry Pi)
RPi.GPIO==0.7.1
adafruit-circuitpython-dht==4.0.2
adafruit-circuitpython-tpa2016==1.1.10

# Audio
sounddevice==0.4.6
PyAudio==0.2.13

# TTS
pyttsx3==2.90
gTTS==2.4.0
pygame==2.5.2

# Voice Recognition
SpeechRecognition==3.10.1
vosk==0.3.45
openai-whisper==20231117  # Optional

# AI
openai==1.3.5

# Optional
torch==2.1.0  # For Whisper
torchaudio==2.1.0  # For Whisper
```

### File 4: install.sh
```bash
#!/bin/bash
# BingHome Installation Script
# See full script in the artifacts above
```

### File 5: app.py
```python
# Use the complete app.py from the artifact above
```

### File 6: templates/index.html
```html
<!-- Use the complete index.html from the artifact above -->
```

### File 7: static/.gitkeep
```
# This file keeps the static directory in git
```

### File 8: settings.json.example
```json
{
  "openai_api_key": "",
  "bing_api_key": "",
  "home_assistant_url": "http://localhost:8123",
  "home_assistant_token": "",
  "voice_mode": "auto",
  "wake_words": ["hey bing", "okay bing", "bing"],
  "tts_engine": "pyttsx3",
  "tts_rate": 150,
  "tts_volume": 0.9,
  "language": "en-US",
  "gpio_pins": {
    "dht22": 4,
    "gas_sensor": 17,
    "light_sensor": 27
  }
}
```

### File 9: .env.example
```env
# BingHome Environment Variables
# Copy to .env and fill in your values

# API Keys
OPENAI_API_KEY=
BING_API_KEY=

# OAuth (optional, for ChatGPT login)
OPENAI_CLIENT_ID=
OPENAI_CLIENT_SECRET=

# Server
PORT=5000
SECRET_KEY=your-secret-key-change-this

# Home Assistant
HOME_ASSISTANT_URL=http://localhost:8123
HOME_ASSISTANT_TOKEN=
```

### File 10: .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
env/
ENV/

# Settings
.env
settings.json
*.log

# System
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# IDE
.vscode/
.idea/
*.sublime-*

# Temporary
/tmp/
*.tmp
*.temp

# Models
*.pt
*.pth
vosk-model-*/
```

### File 11: systemd/binghome.service
```ini
[Unit]
Description=BingHome Smart Home System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/binghome
Environment="PATH=/home/pi/binghome/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/binghome/venv/bin/python /home/pi/binghome/app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/binghome.log
StandardError=append:/var/log/binghome.error.log

[Install]
WantedBy=multi-user.target
```

### File 12: docs/HARDWARE.md
```markdown
# Hardware Setup Guide

## Required Components

### Essential
- Raspberry Pi 4/5 (2GB+ RAM recommended)
- MicroSD card (32GB+ recommended)
- Power supply (official recommended)

### Optional but Recommended
- USB Microphone or ReSpeaker HAT
- Speakers (3.5mm jack or USB)
- DHT22 temperature/humidity sensor
- MQ-2/MQ-5 gas sensor
- Light sensor module
- 7" touchscreen display

## Wiring Diagrams

### DHT22 Temperature/Humidity Sensor
```
DHT22 Pin  →  Raspberry Pi Pin
─────────────────────────────
VCC        →  Pin 1 (3.3V)
GND        →  Pin 6 (Ground)
DATA       →  Pin 7 (GPIO4)
           →  10kΩ resistor to VCC
```

### Gas Sensor (MQ-2/MQ-5)
```
Sensor Pin →  Raspberry Pi Pin
─────────────────────────────
VCC        →  Pin 2 (5V)
GND        →  Pin 9 (Ground)
DO         →  Pin 11 (GPIO17)
AO         →  Not connected
```

### Light Sensor Module
```
Sensor Pin →  Raspberry Pi Pin
─────────────────────────────
VCC        →  Pin 1 (3.3V)
GND        →  Pin 14 (Ground)
DO         →  Pin 13 (GPIO27)
```

## Audio Setup

### USB Microphone
1. Plug in USB microphone
2. Check detection: `arecord -l`
3. Test: `arecord -d 5 test.wav && aplay test.wav`

### ReSpeaker Setup
```bash
git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot
```

## Enable Hardware Interfaces

```bash
# Enable I2C
sudo raspi-config nonint do_i2c 0

# Enable SPI
sudo raspi-config nonint do_spi 0

# Add user to groups
sudo usermod -a -G gpio,i2c,spi,audio $USER

# Reboot
sudo reboot
```

## Testing Hardware

### Test DHT22
```python
import adafruit_dht
import board

dht = adafruit_dht.DHT22(board.D4)
print(f"Temperature: {dht.temperature}°C")
print(f"Humidity: {dht.humidity}%")
```

### Test GPIO
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN)
print(f"Gas sensor: {GPIO.input(17)}")
```
```

### File 13: docs/API.md
```markdown
# API Documentation

## Base URL
```
http://<raspberry-pi-ip>:5000
```

## Endpoints

### Sensor Data
```http
GET /api/sensor_data
```

Response:
```json
{
  "temperature": 22.5,
  "humidity": 45.2,
  "gas_detected": false,
  "light_level": "bright",
  "timestamp": "2024-01-20T10:30:00"
}
```

### Voice Command
```http
POST /api/voice
Content-Type: application/json

{
  "command": "turn on the lights"
}
```

Response:
```json
{
  "success": true,
  "response": "Turning on the lights",
  "actions": [
    {"type": "LIGHTS_ON", "value": null}
  ]
}
```

### Settings
```http
GET /api/settings
```

```http
POST /api/settings
Content-Type: application/json

{
  "openai_api_key": "sk-...",
  "voice_mode": "auto",
  "wake_words": ["hey bing"],
  ...
}
```

### Health Check
```http
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "hardware": true,
  "voice_mode": "vosk",
  "timestamp": "2024-01-20T10:30:00"
}
```

### WiFi Management
```http
GET /api/wifi_scan
```

```http
POST /api/wifi_connect
Content-Type: application/json

{
  "ssid": "NetworkName",
  "password": "password123"
}
```

## WebSocket Events

### Client → Server

#### request_sensor_data
Request current sensor readings
```javascript
socket.emit('request_sensor_data');
```

#### control_device
Control a device
```javascript
socket.emit('control_device', {
  device: 'lights',
  action: 'on'
});
```

### Server → Client

#### sensor_update
Sensor data update
```javascript
socket.on('sensor_update', function(data) {
  console.log('Temperature:', data.temperature);
});
```

#### voice_status
Voice assistant status
```javascript
socket.on('voice_status', function(data) {
  console.log('Voice mode:', data.mode);
});
```

#### alert
System alerts
```javascript
socket.on('alert', function(data) {
  console.log('Alert:', data.message);
});
```
```

### File 14: docs/TROUBLESHOOTING.md
```markdown
# Troubleshooting Guide

## Common Issues and Solutions

### Voice Recognition Not Working

#### Issue: No voice input detected
```bash
# Check microphone
arecord -l

# Test recording
arecord -d 5 test.wav
aplay test.wav

# Check permissions
groups $USER  # Should include 'audio'
```

#### Issue: Whisper model not loading
```bash
# Install Whisper with CPU support
pip install openai-whisper

# Download tiny model
python3 -c "import whisper; whisper.load_model('tiny')"
```

#### Issue: Vosk not working
```bash
# Download model
cd ~
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### Sensor Issues

#### Issue: DHT22 timeout
- Check wiring and pull-up resistor
- Try different GPIO pin
- Add delays between reads

#### Issue: Permission denied on GPIO
```bash
sudo usermod -a -G gpio $USER
# Logout and login again
```

### Service Issues

#### Issue: Service won't start
```bash
# Check status
sudo systemctl status binghome

# View logs
journalctl -u binghome -f

# Test manually
cd ~/binghome
source venv/bin/activate
python app.py
```

#### Issue: Port already in use
```bash
# Find process
sudo lsof -i :5000

# Kill process
sudo kill -9 <PID>
```

### Performance Issues

#### High CPU with Whisper
- Use whisper-tiny model
- Switch to Vosk
- Reduce sample rate

#### Out of memory
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Getting Help

1. Check the [GitHub Issues](https://github.com/oodog/binghome/issues)
2. Join our [Discord Community](https://discord.gg/binghome)
3. Read the [Wiki](https://github.com/oodog/binghome/wiki)
```
