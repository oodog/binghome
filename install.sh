#!/bin/bash
# ============================================
# BingHome Complete Auto-Installer
# One script to install everything and auto-start
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/home/$USER/binghome"

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   BingHome Auto-Installer v2.2     ${NC}"
echo -e "${CYAN}=====================================${NC}"

# Clean previous installation
echo -e "\n${BLUE}Cleaning previous installation...${NC}"
sudo systemctl stop binghome 2>/dev/null || true
sudo systemctl disable binghome 2>/dev/null || true
[ -d "$INSTALL_DIR" ] && mv "$INSTALL_DIR" "$INSTALL_DIR.backup.$(date +%Y%m%d_%H%M%S)"

# Update system
echo -e "\n${BLUE}Updating system...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
echo -e "\n${BLUE}Installing dependencies...${NC}"
sudo apt-get install -y \
    python3-pip python3-venv python3-dev \
    git curl wget build-essential \
    portaudio19-dev python3-pyaudio \
    espeak ffmpeg \
    i2c-tools python3-rpi.gpio || true

# Create directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create virtual environment
echo -e "\n${BLUE}Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python packages
echo -e "\n${BLUE}Installing Python packages...${NC}"
pip install flask flask-cors flask-socketio
pip install python-socketio requests numpy
pip install pyttsx3 pygame
pip install SpeechRecognition vosk
pip install openai
pip install RPi.GPIO || echo "GPIO not available"
pip install adafruit-circuitpython-dht || echo "DHT not available"

# Download Vosk model
echo -e "\n${BLUE}Setting up Vosk model...${NC}"
if [ ! -d "/home/$USER/vosk-model-small-en-us-0.15" ]; then
    cd /home/$USER
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -q vosk-model-small-en-us-0.15.zip
    rm vosk-model-small-en-us-0.15.zip
fi
cd "$INSTALL_DIR"

# Create directories
mkdir -p templates static

# Create working app.py
echo -e "\n${BLUE}Creating application files...${NC}"
cat > app.py << 'APPEOF'
#!/usr/bin/env python3
"""BingHome Smart Home System - Simplified Working Version"""

import os
import json
import time
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Try to import hardware libraries
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    HARDWARE_AVAILABLE = True
    logger.info("Hardware libraries loaded")
except ImportError:
    HARDWARE_AVAILABLE = False
    logger.info("Running in simulation mode")

# Try voice libraries
try:
    import speech_recognition as sr
    import vosk
    import pyaudio
    VOICE_AVAILABLE = True
    logger.info("Voice libraries loaded")
except ImportError:
    VOICE_AVAILABLE = False
    logger.info("Voice recognition not available")

# Global data
sensor_data = {
    'temperature': 22.5,
    'humidity': 45.0,
    'gas_detected': False,
    'light_level': 'bright',
    'timestamp': None
}

settings = {
    'voice_mode': 'auto',
    'wake_words': ['hey bing', 'okay bing'],
    'openai_api_key': '',
    'bing_api_key': ''
}

class SensorManager:
    def __init__(self):
        self.dht = None
        if HARDWARE_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(17, GPIO.IN)  # Gas sensor
                GPIO.setup(27, GPIO.IN)  # Light sensor
                self.dht = adafruit_dht.DHT22(board.D4)
                logger.info("Hardware initialized")
            except Exception as e:
                logger.error(f"Hardware init error: {e}")
    
    def read_sensors(self):
        global sensor_data
        
        if HARDWARE_AVAILABLE and self.dht:
            try:
                sensor_data['temperature'] = self.dht.temperature
                sensor_data['humidity'] = self.dht.humidity
                sensor_data['gas_detected'] = GPIO.input(17) == GPIO.HIGH
                sensor_data['light_level'] = 'bright' if GPIO.input(27) == GPIO.HIGH else 'dark'
            except Exception as e:
                logger.debug(f"Sensor read error: {e}")
        else:
            # Simulate data
            sensor_data['temperature'] = round(20 + random.random() * 10, 1)
            sensor_data['humidity'] = round(40 + random.random() * 20, 1)
            sensor_data['gas_detected'] = random.random() > 0.95
            sensor_data['light_level'] = 'bright' if random.random() > 0.5 else 'dark'
        
        sensor_data['timestamp'] = datetime.now().isoformat()
        return sensor_data

def sensor_loop():
    """Background thread for sensors"""
    sensor_manager = SensorManager()
    while True:
        try:
            data = sensor_manager.read_sensors()
            socketio.emit('sensor_update', data)
            time.sleep(5)
        except Exception as e:
            logger.error(f"Sensor loop error: {e}")
            time.sleep(5)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sensor_data')
def get_sensor_data():
    return jsonify(sensor_data)

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'hardware': HARDWARE_AVAILABLE,
        'voice': VOICE_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global settings
    if request.method == 'POST':
        settings.update(request.json)
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        return jsonify({'success': True})
    return jsonify(settings)

@app.route('/api/voice', methods=['POST'])
def voice_command():
    command = request.json.get('command', '')
    response = f"Processing: {command}"
    return jsonify({'success': True, 'response': response})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('sensor_update', sensor_data)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('control_device')
def handle_device_control(data):
    device = data.get('device')
    action = data.get('action')
    logger.info(f"Control: {device} - {action}")
    emit('device_status', {'device': device, 'status': 'success'})

# Main
if __name__ == '__main__':
    logger.info("Starting BingHome...")
    
    # Start sensor thread
    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()
    
    # Start web server
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()
APPEOF

# Create HTML template
cat > templates/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BingHome - Smart Home Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #1a1a1a;
            --accent: #00ff88;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --glass: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .header {
            background: var(--glass);
            backdrop-filter: blur(10px);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }
        
        .logo {
            font-size: 28px;
            font-weight: bold;
            background: linear-gradient(135deg, var(--accent) 0%, #00ffff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
        }
        
        .status-item {
            padding: 8px 15px;
            background: var(--glass);
            border-radius: 20px;
            border: 1px solid var(--border);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .tile {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 25px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .tile:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
        }
        
        .tile-icon {
            font-size: 40px;
            margin-bottom: 15px;
        }
        
        .tile-title {
            font-size: 20px;
            margin-bottom: 10px;
        }
        
        .tile-value {
            font-size: 32px;
            color: var(--accent);
            font-weight: bold;
        }
        
        .voice-button {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), #00cc66);
            border: none;
            color: #000;
            font-size: 32px;
            cursor: pointer;
            margin: 20px auto;
            display: block;
            transition: all 0.3s ease;
        }
        
        .voice-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 30px var(--accent);
        }
        
        .settings-button {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--glass);
            border: 1px solid var(--border);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 20px;
            transition: all 0.3s ease;
        }
        
        .settings-button:hover {
            background: var(--accent);
            transform: rotate(90deg);
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
        }
        
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: var(--bg-secondary);
            padding: 30px;
            border-radius: 20px;
            max-width: 500px;
            width: 90%;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-secondary);
        }
        
        .form-input {
            width: 100%;
            padding: 12px;
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
        }
        
        .button {
            padding: 12px 24px;
            background: var(--accent);
            border: none;
            border-radius: 10px;
            color: #000;
            font-weight: 600;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">🏠 BingHome</div>
        <div class="status-bar">
            <div class="status-item">
                <span id="temp">--</span>°C
            </div>
            <div class="status-item">
                <span id="humidity">--</span>%
            </div>
            <div class="status-item">
                <span id="gas">Safe</span>
            </div>
            <button class="settings-button" onclick="openSettings()">⚙️</button>
        </div>
    </header>
    
    <div class="container">
        <div class="dashboard-grid">
            <div class="tile">
                <div class="tile-icon">🎤</div>
                <div class="tile-title">Voice Control</div>
                <button class="voice-button" onclick="toggleVoice()">🎙️</button>
                <div id="voiceStatus">Ready</div>
            </div>
            
            <div class="tile">
                <div class="tile-icon">🌡️</div>
                <div class="tile-title">Temperature</div>
                <div class="tile-value" id="tempValue">--°C</div>
            </div>
            
            <div class="tile">
                <div class="tile-icon">💧</div>
                <div class="tile-title">Humidity</div>
                <div class="tile-value" id="humidityValue">--%</div>
            </div>
            
            <div class="tile" onclick="toggleLights()">
                <div class="tile-icon">💡</div>
                <div class="tile-title">Lights</div>
                <div class="tile-value" id="lightStatus">ON</div>
            </div>
        </div>
    </div>
    
    <div class="modal" id="settingsModal">
        <div class="modal-content">
            <h2>Settings</h2>
            <div class="form-group">
                <label class="form-label">OpenAI API Key</label>
                <input type="password" class="form-input" id="openaiKey">
            </div>
            <div class="form-group">
                <label class="form-label">Voice Mode</label>
                <select class="form-input" id="voiceMode">
                    <option value="auto">Auto</option>
                    <option value="vosk">Vosk (Offline)</option>
                    <option value="whisper">Whisper</option>
                </select>
            </div>
            <button class="button" onclick="saveSettings()">Save</button>
            <button class="button" onclick="closeSettings()">Close</button>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('sensor_update', function(data) {
            document.getElementById('temp').textContent = data.temperature || '--';
            document.getElementById('tempValue').textContent = (data.temperature || '--') + '°C';
            document.getElementById('humidity').textContent = data.humidity || '--';
            document.getElementById('humidityValue').textContent = (data.humidity || '--') + '%';
            document.getElementById('gas').textContent = data.gas_detected ? 'Warning!' : 'Safe';
            document.getElementById('gas').style.color = data.gas_detected ? '#ff4444' : '#00ff88';
        });
        
        function toggleLights() {
            const status = document.getElementById('lightStatus');
            const newStatus = status.textContent === 'ON' ? 'OFF' : 'ON';
            status.textContent = newStatus;
            socket.emit('control_device', {device: 'lights', action: newStatus.toLowerCase()});
        }
        
        function toggleVoice() {
            document.getElementById('voiceStatus').textContent = 'Listening...';
            setTimeout(() => {
                document.getElementById('voiceStatus').textContent = 'Ready';
            }, 3000);
        }
        
        function openSettings() {
            document.getElementById('settingsModal').classList.add('active');
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }
        
        function saveSettings() {
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    openai_api_key: document.getElementById('openaiKey').value,
                    voice_mode: document.getElementById('voiceMode').value
                })
            });
            closeSettings();
        }
    </script>
</body>
</html>
HTMLEOF

# Create settings.json
cat > settings.json << 'EOF'
{
  "voice_mode": "auto",
  "wake_words": ["hey bing", "okay bing"],
  "tts_engine": "pyttsx3"
}
EOF

# Create systemd service
echo -e "\n${BLUE}Setting up auto-start service...${NC}"
sudo tee /etc/systemd/system/binghome.service > /dev/null << EOF
[Unit]
Description=BingHome Smart Home System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable binghome
sudo systemctl start binghome

# Enable hardware interfaces if on Pi
if [ -f /proc/device-tree/model ]; then
    echo -e "\n${BLUE}Enabling hardware interfaces...${NC}"
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_spi 0
    sudo usermod -a -G gpio,i2c,spi,audio $USER
fi

# Get IP
IP=$(hostname -I | awk '{print $1}')

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}   Installation Complete! 🎉         ${NC}"
echo -e "${GREEN}=====================================${NC}"

echo -e "\n${CYAN}BingHome is now running!${NC}"
echo -e "Access at: ${GREEN}http://$IP:5000${NC}"

echo -e "\n${CYAN}Service Status:${NC}"
sudo systemctl status binghome --no-pager

echo -e "\n${CYAN}Commands:${NC}"
echo -e "  View logs:  ${GREEN}journalctl -u binghome -f${NC}"
echo -e "  Restart:    ${GREEN}sudo systemctl restart binghome${NC}"
echo -e "  Stop:       ${GREEN}sudo systemctl stop binghome${NC}"

echo -e "\n${YELLOW}The service will auto-start on reboot!${NC}"
