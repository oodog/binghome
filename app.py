#!/usr/bin/env python3
"""
BingHome - Smart Home Control System
Auto-start optimized version with kiosk mode support
"""

import os
import sys
import json
import time
import threading
import subprocess
import socket
from datetime import datetime
from pathlib import Path

# Flask and web framework imports
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Hardware and sensor imports
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    print("⚠️  Raspberry Pi libraries not available - running in development mode")

# Audio and speech imports
import requests
import numpy as np
try:
    import speech_recognition as sr
    import pyttsx3
    import pygame
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  Audio libraries not available - speech features disabled")

# AI and language processing
try:
    import openai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  OpenAI library not available - ChatGPT features disabled")

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
ENV_FILE = BASE_DIR / ".env"

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'binghome-secret-key-change-me')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app)

class BingHomeSystem:
    def __init__(self):
        self.settings = self.load_settings()
        self.setup_hardware()
        self.setup_audio()
        self.setup_ai()
        self.running = True
        self.sensor_thread = None
        self.voice_thread = None
        self.startup_complete = False
        
    def load_settings(self):
        """Load settings from JSON file or create defaults"""
        default_settings = {
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
            "kiosk_mode": True,
            "auto_start_browser": True,
            "gpio_pins": {
                "dht22": 4,
                "gas_sensor": 17,
                "light_sensor": 27
            }
        }
        
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    settings = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self, settings):
        """Save settings to JSON file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            self.settings = settings
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def setup_hardware(self):
        """Initialize hardware components"""
        self.sensors = {}
        
        if not RPI_AVAILABLE:
            print("🔧 Hardware simulation mode - no GPIO access")
            return
        
        try:
            # GPIO setup
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # DHT22 temperature/humidity sensor
            dht_pin = self.settings["gpio_pins"]["dht22"]
            self.sensors['dht22'] = adafruit_dht.DHT22(getattr(board, f'D{dht_pin}'))
            
            # Gas sensor
            gas_pin = self.settings["gpio_pins"]["gas_sensor"]
            GPIO.setup(gas_pin, GPIO.IN)
            self.sensors['gas_pin'] = gas_pin
            
            # Light sensor
            light_pin = self.settings["gpio_pins"]["light_sensor"]
            GPIO.setup(light_pin, GPIO.IN)
            self.sensors['light_pin'] = light_pin
            
            print("✅ Hardware sensors initialized")
            
        except Exception as e:
            print(f"⚠️  Hardware setup error: {e}")
    
    def setup_audio(self):
        """Initialize audio system"""
        if not AUDIO_AVAILABLE:
            print("🔇 Audio simulation mode")
            return
        
        try:
            # Text-to-speech setup
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', self.settings['tts_rate'])
            self.tts_engine.setProperty('volume', self.settings['tts_volume'])
            
            # Speech recognition setup
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Audio output setup
            pygame.mixer.init()
            
            print("✅ Audio system initialized")
            
        except Exception as e:
            print(f"⚠️  Audio setup error: {e}")
    
    def setup_ai(self):
        """Initialize AI services"""
        if not AI_AVAILABLE:
            print("🤖 AI simulation mode")
            return
        
        try:
            if self.settings.get('openai_api_key'):
                openai.api_key = self.settings['openai_api_key']
                print("✅ OpenAI API configured")
            else:
                print("⚠️  OpenAI API key not configured")
                
        except Exception as e:
            print(f"⚠️  AI setup error: {e}")
    
    def read_sensors(self):
        """Read all sensor data"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'temperature': None,
            'humidity': None,
            'gas_detected': False,
            'light_level': 'unknown'
        }
        
        if not RPI_AVAILABLE:
            # Simulate sensor data for development
            import random
            data.update({
                'temperature': round(20 + random.uniform(-5, 15), 1),
                'humidity': round(40 + random.uniform(-10, 30), 1),
                'gas_detected': random.choice([True, False]),
                'light_level': random.choice(['dark', 'dim', 'bright'])
            })
            return data
        
        try:
            # Read DHT22 sensor
            if 'dht22' in self.sensors:
                dht = self.sensors['dht22']
                data['temperature'] = dht.temperature
                data['humidity'] = dht.humidity
            
            # Read gas sensor
            if 'gas_pin' in self.sensors:
                gas_state = GPIO.input(self.sensors['gas_pin'])
                data['gas_detected'] = bool(gas_state)
            
            # Read light sensor
            if 'light_pin' in self.sensors:
                light_state = GPIO.input(self.sensors['light_pin'])
                data['light_level'] = 'bright' if light_state else 'dark'
                
        except Exception as e:
            print(f"Sensor read error: {e}")
        
        return data
    
    def speak(self, text):
        """Text-to-speech output"""
        if not AUDIO_AVAILABLE:
            print(f"🔊 TTS: {text}")
            return
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    def process_voice_command(self, command):
        """Process voice command and return response"""
        command = command.lower().strip()
        
        # Temperature query
        if 'temperature' in command:
            data = self.read_sensors()
            if data['temperature']:
                temp = data['temperature']
                return f"The current temperature is {temp:.1f} degrees Celsius"
            return "Temperature sensor not available"
        
        # Humidity query
        if 'humidity' in command:
            data = self.read_sensors()
            if data['humidity']:
                humidity = data['humidity']
                return f"The current humidity is {humidity:.1f} percent"
            return "Humidity sensor not available"
        
        # Gas sensor query
        if 'gas' in command:
            data = self.read_sensors()
            gas = "detected" if data['gas_detected'] else "not detected"
            return f"Gas is {gas}"
        
        # Light control
        if 'lights' in command:
            if 'on' in command or 'turn on' in command:
                return "Turning on the lights"
            elif 'off' in command or 'turn off' in command:
                return "Turning off the lights"
            return "Light status: unknown"
        
        # Default AI response
        if AI_AVAILABLE and self.settings.get('openai_api_key'):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are BingHome, a helpful smart home assistant. Keep responses brief and friendly."},
                        {"role": "user", "content": command}
                    ],
                    max_tokens=100
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI API error: {e}")
        
        return "I'm sorry, I didn't understand that command."
    
    def start_browser_kiosk(self):
        """Start browser in kiosk mode after service is ready"""
        if not self.settings.get('auto_start_browser', True):
            return
        
        def launch_browser():
            # Wait for web service to be ready
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get('http://localhost:5000', timeout=2)
                    if response.status_code == 200:
                        break
                except:
                    pass
                time.sleep(2)
            else:
                print("⚠️  Web service not ready for browser launch")
                return
            
            # Check if running in graphical environment
            if os.environ.get('DISPLAY'):
                try:
                    # Launch Chromium in kiosk mode
                    subprocess.Popen([
                        'chromium-browser',
                        '--kiosk',
                        '--incognito',
                        '--disable-infobars',
                        '--disable-web-security',
                        '--disable-features=TranslateUI',
                        '--autoplay-policy=no-user-gesture-required',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--no-default-browser-check',
                        'http://localhost:5000'
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("✅ Browser launched in kiosk mode")
                except Exception as e:
                    print(f"Browser launch error: {e}")
            else:
                print("ℹ️  No display available - browser auto-start disabled")
        
        # Launch browser in separate thread
        browser_thread = threading.Thread(target=launch_browser, daemon=True)
        browser_thread.start()
    
    def sensor_monitor_loop(self):
        """Background sensor monitoring"""
        while self.running:
            try:
                data = self.read_sensors()
                socketio.emit('sensor_update', data)
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                print(f"Sensor monitor error: {e}")
                time.sleep(10)
    
    def start_background_tasks(self):
        """Start background monitoring tasks"""
        if self.sensor_thread is None or not self.sensor_thread.is_alive():
            self.sensor_thread = threading.Thread(target=self.sensor_monitor_loop, daemon=True)
            self.sensor_thread.start()
            print("✅ Background sensor monitoring started")
    
    def get_system_status(self):
        """Get system health status"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'hardware': RPI_AVAILABLE,
            'audio': AUDIO_AVAILABLE,
            'ai': AI_AVAILABLE and bool(self.settings.get('openai_api_key')),
            'voice_mode': self.settings.get('voice_mode', 'auto'),
            'startup_complete': self.startup_complete,
            'timestamp': datetime.now().isoformat()
        }

# Initialize the system
binghome = BingHomeSystem()

# Flask routes
@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('index.html', settings=binghome.settings)

@app.route('/api/sensor_data')
def api_sensor_data():
    """Get current sensor readings"""
    data = binghome.read_sensors()
    return jsonify(data)

@app.route('/api/voice', methods=['POST'])
def api_voice():
    """Process voice command"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if command:
            response = binghome.process_voice_command(command)
            binghome.speak(response)
            
            return jsonify({
                'success': True,
                'response': response,
                'command': command
            })
        else:
            return jsonify({'success': False, 'error': 'No command provided'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if request.method == 'GET':
        return jsonify(binghome.settings)
    
    try:
        new_settings = request.get_json()
        if binghome.save_settings(new_settings):
            # Restart relevant services if needed
            binghome.setup_ai()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/health')
def api_health():
    """System health check"""
    return jsonify(binghome.get_system_status())

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """Restart the system"""
    try:
        import subprocess
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'binghome'])
        return jsonify({'success': True, 'message': 'Restarting...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('status', binghome.get_system_status())
    
    # Send initial sensor data
    sensor_data = binghome.read_sensors()
    emit('sensor_update', sensor_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice command via WebSocket"""
    try:
        command = data.get('command', '')
        if command:
            response = binghome.process_voice_command(command)
            binghome.speak(response)
            
            emit('voice_response', {
                'command': command,
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('request_sensor_data')
def handle_sensor_request():
    """Handle sensor data request"""
    data = binghome.read_sensors()
    emit('sensor_update', data)

@socketio.on('control_device')
def handle_device_control(data):
    """Handle device control commands"""
    try:
        device = data.get('device')
        action = data.get('action')
        
        if device == 'lights':
            if action == 'on':
                response = "Turning on the lights"
            elif action == 'off':
                response = "Turning off the lights"
            else:
                response = f"Unknown action: {action}"
        else:
            response = f"Unknown device: {device}"
        
        binghome.speak(response)
        emit('device_response', {
            'device': device,
            'action': action,
            'response': response
        })
        
    except Exception as e:
        emit('error', {'message': str(e)})

# Startup function
def startup_tasks():
    """Perform startup tasks"""
    print("🏠 BingHome starting up...")
    
    # Start background monitoring
    binghome.start_background_tasks()
    
    # Mark startup as complete
    binghome.startup_complete = True
    
    # Auto-launch browser if enabled and in graphical environment
    if binghome.settings.get('auto_start_browser', True):
        time.sleep(5)  # Wait for web server to be ready
        binghome.start_browser_kiosk()
    
    print("✅ BingHome startup complete")

if __name__ == '__main__':
    try:
        # Perform startup tasks in background thread
        startup_thread = threading.Thread(target=startup_tasks, daemon=True)
        startup_thread.start()
        
        # Get host and port from environment or defaults
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        print(f"🚀 Starting BingHome on {host}:{port}")
        
        # Run the Flask-SocketIO app
        socketio.run(app, 
                    host=host, 
                    port=port, 
                    debug=debug,
                    allow_unsafe_werkzeug=True)
                    
    except KeyboardInterrupt:
        print("\n🛑 BingHome shutting down...")
        binghome.running = False
        
        # Cleanup GPIO if available
        if RPI_AVAILABLE:
            GPIO.cleanup()
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
