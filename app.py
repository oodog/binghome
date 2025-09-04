#!/usr/bin/env python3
"""
BingHome Smart Hub - Main Application
Modular design with core components
"""

import os
import sys
import json
import time
import threading
import logging
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, session, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

# Import core modules
try:
    from core.media import MediaController
    from core.news import NewsManager
    from core.timers import TimerManager
    from core.weather import WeatherService
except ImportError as e:
    print(f"Warning: Could not import core modules: {e}")
    # Define placeholder classes if modules don't exist
    class MediaController:
        def __init__(self): pass
        def play(self): pass
        def pause(self): pass
        def stop(self): pass
        
    class NewsManager:
        def __init__(self): pass
        def fetch_news(self): return []
        
    class TimerManager:
        def __init__(self): pass
        def create_timer(self, duration): pass
        def cancel_timer(self, timer_id): pass
        
    class WeatherService:
        def __init__(self): pass
        def get_current(self): return {}
        def get_forecast(self): return []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Try to import hardware libraries
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    HARDWARE_AVAILABLE = True
    logger.info("Hardware libraries loaded")
except ImportError:
    HARDWARE_AVAILABLE = False
    logger.warning("Hardware not available - simulation mode")

# Try voice libraries
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# Configuration
class Config:
    # API Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    BING_API_KEY = os.environ.get('BING_API_KEY', '')
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')
    HOME_ASSISTANT_URL = os.environ.get('HOME_ASSISTANT_URL', 'http://localhost:8123')
    HOME_ASSISTANT_TOKEN = os.environ.get('HOME_ASSISTANT_TOKEN', '')
    
    # GPIO Pins
    DHT22_PIN = 4
    GAS_SENSOR_PIN = 17
    LIGHT_SENSOR_PIN = 27
    MOTION_SENSOR_PIN = 22
    
    # Server
    PORT = int(os.environ.get('PORT', 5000))
    
    # Settings file
    SETTINGS_FILE = 'settings.json'
    
    @classmethod
    def load_settings(cls):
        """Load settings from file"""
        if os.path.exists(cls.SETTINGS_FILE):
            try:
                with open(cls.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    for key, value in settings.items():
                        if hasattr(cls, key.upper()):
                            setattr(cls, key.upper(), value)
                    logger.info("Settings loaded from file")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
    
    @classmethod
    def save_settings(cls, settings):
        """Save settings to file"""
        try:
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            
            # Update config
            for key, value in settings.items():
                if hasattr(cls, key.upper()):
                    setattr(cls, key.upper(), value)
            
            logger.info("Settings saved")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

# Load settings on startup
Config.load_settings()

# Initialize core modules
media_controller = MediaController()
news_manager = NewsManager()
timer_manager = TimerManager()
weather_service = WeatherService()

# Global data
sensor_data = {
    'temperature': 22.5,
    'humidity': 45.0,
    'gas_detected': False,
    'light_level': 'bright',
    'motion_detected': False,
    'timestamp': None
}

devices = {
    'lights': {},
    'switches': {},
    'thermostats': {},
    'cameras': {},
    'speakers': {}
}

routines = []
notifications = []

# Sensor Manager
class SensorManager:
    def __init__(self):
        self.dht = None
        self.setup_hardware()
    
    def setup_hardware(self):
        if not HARDWARE_AVAILABLE:
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(Config.GAS_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(Config.LIGHT_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(Config.MOTION_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            self.dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            logger.info("Hardware initialized")
        except Exception as e:
            logger.error(f"Hardware init error: {e}")
    
    def read_sensors(self):
        global sensor_data
        
        if HARDWARE_AVAILABLE and self.dht:
            try:
                temp = self.dht.temperature
                hum = self.dht.humidity
                if temp and hum:
                    sensor_data['temperature'] = round(temp, 1)
                    sensor_data['humidity'] = round(hum, 1)
                
                sensor_data['gas_detected'] = GPIO.input(Config.GAS_SENSOR_PIN) == GPIO.HIGH
                sensor_data['light_level'] = 'bright' if GPIO.input(Config.LIGHT_SENSOR_PIN) == GPIO.HIGH else 'dark'
                sensor_data['motion_detected'] = GPIO.input(Config.MOTION_SENSOR_PIN) == GPIO.HIGH
            except:
                pass
        else:
            # Simulation
            import random
            sensor_data['temperature'] = round(20 + random.random() * 10, 1)
            sensor_data['humidity'] = round(40 + random.random() * 20, 1)
            sensor_data['gas_detected'] = random.random() > 0.95
            sensor_data['light_level'] = 'bright' if random.random() > 0.5 else 'dark'
            sensor_data['motion_detected'] = random.random() > 0.8
        
        sensor_data['timestamp'] = datetime.now().isoformat()
        return sensor_data

# Voice Assistant
class VoiceAssistant:
    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        self.setup_voice()
    
    def setup_voice(self):
        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                logger.info("Voice recognition ready")
            except:
                pass
        
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                logger.info("TTS ready")
            except:
                pass
    
    def process_command(self, command):
        """Process voice command"""
        command = command.lower()
        
        # Media controls
        if 'play music' in command:
            media_controller.play()
            return "Playing music"
        elif 'stop music' in command:
            media_controller.stop()
            return "Music stopped"
        
        # Weather
        elif 'weather' in command:
            weather = weather_service.get_current()
            if weather:
                return f"Currently {weather.get('temp')}° and {weather.get('condition')}"
            return "Weather data unavailable"
        
        # Timer
        elif 'set timer' in command:
            # Extract duration from command
            import re
            match = re.search(r'(\d+)\s*(minute|hour|second)', command)
            if match:
                duration = int(match.group(1))
                unit = match.group(2)
                if unit == 'hour':
                    duration *= 3600
                elif unit == 'minute':
                    duration *= 60
                timer_manager.create_timer(duration)
                return f"Timer set for {match.group(1)} {unit}s"
        
        # Sensors
        elif 'temperature' in command:
            return f"The temperature is {sensor_data['temperature']} degrees"
        elif 'humidity' in command:
            return f"The humidity is {sensor_data['humidity']} percent"
        
        return "How can I help you?"

# Background threads
def sensor_update_loop():
    sensor_manager = SensorManager()
    while True:
        try:
            data = sensor_manager.read_sensors()
            socketio.emit('sensor_update', data)
            
            if data['gas_detected']:
                socketio.emit('alert', {
                    'type': 'danger',
                    'message': 'Gas detected!'
                })
            
            time.sleep(5)
        except Exception as e:
            logger.error(f"Sensor loop error: {e}")
            time.sleep(5)

def news_update_loop():
    while True:
        try:
            if Config.BING_API_KEY:
                news = news_manager.fetch_news()
                if news:
                    socketio.emit('news_update', news)
            time.sleep(300)  # 5 minutes
        except:
            time.sleep(60)

def weather_update_loop():
    while True:
        try:
            if Config.WEATHER_API_KEY:
                current = weather_service.get_current()
                if current:
                    socketio.emit('weather_update', current)
            time.sleep(600)  # 10 minutes
        except:
            time.sleep(60)

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.route('/wifi')
def wifi_settings():
    return render_template('wifi_settings.html')

@app.route('/system')
def system_status():
    return render_template('system_status.html')

# API Routes
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'hardware': HARDWARE_AVAILABLE,
        'voice': VOICE_AVAILABLE,
        'modules': {
            'media': hasattr(media_controller, 'play'),
            'news': hasattr(news_manager, 'fetch_news'),
            'weather': hasattr(weather_service, 'get_current'),
            'timers': hasattr(timer_manager, 'create_timer')
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sensor_data')
def get_sensor_data():
    return jsonify(sensor_data)

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        # Return settings without sensitive keys
        safe_settings = {
            'has_openai_key': bool(Config.OPENAI_API_KEY),
            'has_bing_key': bool(Config.BING_API_KEY),
            'has_weather_key': bool(Config.WEATHER_API_KEY),
            'has_ha_token': bool(Config.HOME_ASSISTANT_TOKEN),
            'home_assistant_url': Config.HOME_ASSISTANT_URL
        }
        return jsonify(safe_settings)
    
    else:  # POST
        try:
            settings = request.json
            if Config.save_settings(settings):
                return jsonify({'success': True})
            return jsonify({'success': False}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/voice', methods=['POST'])
def voice_command():
    try:
        command = request.json.get('command', '')
        voice_assistant = VoiceAssistant()
        response = voice_assistant.process_command(command)
        return jsonify({
            'success': True,
            'command': command,
            'response': response
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/media/<action>', methods=['POST'])
def media_control(action):
    try:
        if action == 'play':
            media_controller.play()
        elif action == 'pause':
            media_controller.pause()
        elif action == 'stop':
            media_controller.stop()
        elif action == 'next':
            media_controller.next()
        elif action == 'previous':
            media_controller.previous()
        
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/weather')
def get_weather():
    try:
        current = weather_service.get_current()
        forecast = weather_service.get_forecast()
        return jsonify({
            'current': current,
            'forecast': forecast
        })
    except:
        return jsonify({'error': 'Weather unavailable'}), 503

@app.route('/api/news')
def get_news():
    try:
        news = news_manager.fetch_news()
        return jsonify(news)
    except:
        return jsonify([])

@app.route('/api/timer', methods=['POST'])
def create_timer():
    try:
        duration = request.json.get('duration', 60)
        name = request.json.get('name', 'Timer')
        timer_id = timer_manager.create_timer(duration, name)
        return jsonify({'success': True, 'timer_id': timer_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system')
def system_info():
    try:
        import psutil
        return jsonify({
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'temperature': psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else None,
            'uptime': time.time() - psutil.boot_time()
        })
    except:
        return jsonify({'error': 'System info unavailable'}), 503

@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        import subprocess
        result = subprocess.run(
            ['sudo', 'iwlist', 'wlan0', 'scan'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        networks = []
        lines = result.stdout.split('\n')
        current = {}
        
        for line in lines:
            if 'Cell' in line:
                if current and 'ssid' in current:
                    networks.append(current)
                current = {}
            elif 'ESSID:' in line:
                ssid = line.split('"')[1] if '"' in line else ''
                if ssid:
                    current['ssid'] = ssid
            elif 'Signal level=' in line:
                try:
                    signal = line.split('Signal level=')[1].split(' ')[0]
                    current['signal'] = signal
                except:
                    pass
            elif 'Encryption key:on' in line:
                current['encrypted'] = True
        
        if current and 'ssid' in current:
            networks.append(current)
        
        return jsonify(networks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    try:
        ssid = request.json.get('ssid')
        password = request.json.get('password')
        
        if not ssid:
            return jsonify({'error': 'SSID required'}), 400
        
        config = f'''
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    {"psk=\"" + password + "\"" if password else "key_mgmt=NONE"}
}}
'''
        
        with open('/tmp/wpa_supplicant.conf', 'w') as f:
            f.write(config)
        
        import subprocess
        subprocess.run(['sudo', 'cp', '/tmp/wpa_supplicant.conf', '/etc/wpa_supplicant/wpa_supplicant.conf'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to BingHome'})
    emit('sensor_update', sensor_data)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_update_request(data):
    update_type = data.get('type')
    
    if update_type == 'sensors':
        emit('sensor_update', sensor_data)
    elif update_type == 'weather':
        emit('weather_update', weather_service.get_current())
    elif update_type == 'news':
        emit('news_update', news_manager.fetch_news())

# Main
def main():
    logger.info("=" * 50)
    logger.info("BingHome Smart Hub Starting")
    logger.info(f"Port: {Config.PORT}")
    logger.info(f"Hardware: {'Available' if HARDWARE_AVAILABLE else 'Simulated'}")
    logger.info("=" * 50)
    
    # Start background threads
    threading.Thread(target=sensor_update_loop, daemon=True).start()
    threading.Thread(target=news_update_loop, daemon=True).start()
    threading.Thread(target=weather_update_loop, daemon=True).start()
    
    # Start server
    try:
        socketio.run(app, host='0.0.0.0', port=Config.PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
