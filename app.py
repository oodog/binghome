#!/usr/bin/env python3
"""
BingHome Hub - Complete Smart Home Control System
Full version with all services and features
"""

import os
import sys
import json
import time
import threading
import subprocess
import socket
import random
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask and web framework imports
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Try to import optional packages
try:
    from flask_socketio import SocketIO, emit
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logger.warning("SocketIO not available - real-time features disabled")

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logger.warning("CORS not available")

# Hardware and sensor imports
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    logger.info("Raspberry Pi libraries not available - running in simulation mode")

# Audio and speech imports
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.warning("Speech recognition not available")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("TTS not available")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("Pygame not available")

# AI and language processing
try:
    import vosk
    import json as vosk_json
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk not available - local voice recognition disabled")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
ENV_FILE = BASE_DIR / ".env"
MODELS_DIR = BASE_DIR / "models"

# Create required directories
for dir_path in [BASE_DIR / "templates", BASE_DIR / "static", BASE_DIR / "logs", MODELS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Flask app setup
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'binghome-hub-secret-key-change-me')

if CORS_AVAILABLE:
    CORS(app)

if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
else:
    socketio = None

# ============================================
# Core Module Classes
# ============================================

class MediaController:
    """Media control module"""
    def __init__(self):
        self.is_playing = False
        self.current_source = None
        self.volume = 50
        
    def play(self, source=None):
        self.is_playing = True
        self.current_source = source or "default"
        logger.info(f"Playing from {self.current_source}")
        return True
    
    def pause(self):
        self.is_playing = False
        logger.info("Media paused")
        return True
    
    def stop(self):
        self.is_playing = False
        self.current_source = None
        logger.info("Media stopped")
        return True
    
    def next(self):
        logger.info("Next track")
        return True
    
    def previous(self):
        logger.info("Previous track")
        return True
    
    def set_volume(self, level):
        self.volume = max(0, min(100, level))
        logger.info(f"Volume set to {self.volume}")
        return True

class NewsManager:
    """News fetching module"""
    def __init__(self):
        self.api_key = os.environ.get('BING_API_KEY', '')
        self.news_cache = []
        self.last_fetch = None
        
    def fetch_news(self, category='general', count=10):
        if not self.api_key:
            # Return mock news for testing
            return [
                {'title': 'BingHome Hub Successfully Installed', 'description': 'Your smart home system is running', 'url': '#'},
                {'title': 'Voice Control Ready', 'description': 'Say "Hey Bing" to activate', 'url': '#'},
                {'title': 'Home Automation Connected', 'description': 'Control your devices with voice', 'url': '#'}
            ]
        
        try:
            import requests
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {'mkt': 'en-US', 'count': count, 'category': category}
            
            response = requests.get(
                'https://api.bing.microsoft.com/v7.0/news',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.news_cache = data.get('value', [])
                self.last_fetch = datetime.now()
                
        except Exception as e:
            logger.error(f"News fetch error: {e}")
        
        return self.news_cache

class TimerManager:
    """Timer and routine management"""
    def __init__(self):
        self.timers = {}
        self.routines = []
        
    def create_timer(self, duration, name="Timer", callback=None):
        timer_id = str(uuid.uuid4())[:8]
        
        def timer_thread():
            time.sleep(duration)
            if timer_id in self.timers:
                logger.info(f"Timer '{name}' completed")
                if callback:
                    callback()
                del self.timers[timer_id]
        
        timer = {
            'id': timer_id,
            'name': name,
            'duration': duration,
            'started': datetime.now(),
            'ends': datetime.now() + timedelta(seconds=duration),
            'thread': threading.Thread(target=timer_thread, daemon=True)
        }
        
        self.timers[timer_id] = timer
        timer['thread'].start()
        
        logger.info(f"Timer '{name}' created for {duration} seconds")
        return timer_id
    
    def cancel_timer(self, timer_id):
        if timer_id in self.timers:
            del self.timers[timer_id]
            logger.info(f"Timer {timer_id} cancelled")
            return True
        return False
    
    def get_timers(self):
        active_timers = []
        for timer_id, timer in self.timers.items():
            remaining = (timer['ends'] - datetime.now()).total_seconds()
            if remaining > 0:
                active_timers.append({
                    'id': timer_id,
                    'name': timer['name'],
                    'remaining': int(remaining),
                    'duration': timer['duration']
                })
        return active_timers
    
    def check_routines(self):
        """Check if any routine should run"""
        current_time = datetime.now().strftime('%H:%M')
        current_day = datetime.now().strftime('%A').lower()
        
        for routine in self.routines:
            if routine.get('enabled') and routine.get('time') == current_time:
                if 'everyday' in routine.get('days', []) or current_day in routine.get('days', []):
                    logger.info(f"Executing routine: {routine.get('name')}")

class WeatherService:
    """Weather service module"""
    def __init__(self):
        self.api_key = os.environ.get('WEATHER_API_KEY', '')
        self.location = os.environ.get('WEATHER_LOCATION', 'London')
        self.current_weather = {}
        self.forecast = []
        
    def get_current(self, location=None):
        location = location or self.location
        
        if not self.api_key:
            # Return mock weather
            return {
                'temp': 22,
                'feels_like': 21,
                'condition': 'Clear',
                'description': 'clear sky',
                'humidity': 65,
                'wind_speed': 5.2,
                'location': location
            }
        
        try:
            import requests
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.current_weather = {
                    'temp': round(data['main']['temp']),
                    'feels_like': round(data['main']['feels_like']),
                    'condition': data['weather'][0]['main'],
                    'description': data['weather'][0]['description'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'],
                    'location': data['name']
                }
                
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
        
        return self.current_weather
    
    def get_forecast(self, days=5):
        # Return mock forecast
        return [
            {'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
             'temp_min': 18 + i, 'temp_max': 25 + i,
             'condition': 'Clear', 'description': 'sunny'}
            for i in range(days)
        ]

# ============================================
# Main BingHome Hub Class
# ============================================

class BingHomeHub:
    def __init__(self):
        self.settings = self.load_settings()
        self.setup_hardware()
        self.setup_audio()
        self.setup_ai()
        self.running = True
        self.startup_complete = False
        
        # Initialize controllers
        self.media = MediaController()
        self.news = NewsManager()
        self.timers = TimerManager()
        self.weather = WeatherService()
        
        # Voice state
        self.voice_active = False
        self.last_wake_time = None
        self.voice_model = None
        self.recognizer = None
        self.microphone = None
        self.tts_engine = None
        
        # Device state
        self.devices = {}
        self.scenes = []
        self.automations = []
        
        # Background threads
        self.sensor_thread = None
        self.voice_thread = None
        self.automation_thread = None
        
    def load_settings(self):
        """Load settings from JSON file or create defaults"""
        default_settings = {
            "voice_provider": "local",
            "voice_model": "vosk",
            "openai_api_key": "",
            "azure_speech_key": "",
            "google_cloud_key": "",
            "amazon_polly_key": "",
            "bing_api_key": "",
            "weather_api_key": "",
            "home_assistant_url": "http://localhost:8123",
            "home_assistant_token": "",
            "wake_words": ["hey bing", "okay bing", "bing"],
            "tts_engine": "pyttsx3",
            "tts_rate": 150,
            "tts_volume": 0.9,
            "language": "en-US",
            "kiosk_mode": False,
            "auto_start_browser": False,
            "network_interface": "auto",
            "gpio_pins": {
                "dht22": 4,
                "gas_sensor": 17,
                "light_sensor": 27
            },
            "apps": {
                "netflix": {"enabled": True, "url": "https://www.netflix.com"},
                "prime_video": {"enabled": True, "url": "https://www.primevideo.com"},
                "youtube": {"enabled": True, "url": "https://www.youtube.com/tv"},
                "xbox_cloud": {"enabled": True, "url": "https://www.xbox.com/play"},
                "spotify": {"enabled": True, "url": "https://open.spotify.com"},
                "google_photos": {"enabled": True, "url": "https://photos.google.com"}
            }
        }
        
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    settings = json.load(f)
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self, settings):
        """Save settings to JSON file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            self.settings = settings
            # Reinitialize components with new settings
            self.setup_ai()
            self.setup_audio()
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def setup_hardware(self):
        """Initialize hardware components"""
        self.sensors = {}
        
        if not RPI_AVAILABLE:
            logger.info("Hardware simulation mode - no GPIO access")
            return
        
        try:
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
            
            logger.info("Hardware sensors initialized")
            
        except Exception as e:
            logger.error(f"Hardware setup error: {e}")
    
    def setup_audio(self):
        """Initialize audio system"""
        if not TTS_AVAILABLE:
            logger.warning("TTS not available")
            return
        
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', self.settings['tts_rate'])
            self.tts_engine.setProperty('volume', self.settings['tts_volume'])
            logger.info("TTS engine initialized")
        except Exception as e:
            logger.error(f"TTS setup error: {e}")
        
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                logger.info("Speech recognition initialized")
            except Exception as e:
                logger.error(f"Speech recognition setup error: {e}")
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                logger.info("Audio mixer initialized")
            except Exception as e:
                logger.error(f"Pygame audio setup error: {e}")
    
    def setup_ai(self):
        """Initialize AI services"""
        voice_provider = self.settings.get('voice_provider', 'local')
        
        if voice_provider == 'local':
            if VOSK_AVAILABLE:
                self.setup_vosk()
            elif WHISPER_AVAILABLE:
                self.setup_whisper()
        elif voice_provider == 'openai' and OPENAI_AVAILABLE:
            if self.settings.get('openai_api_key'):
                openai.api_key = self.settings['openai_api_key']
                logger.info("OpenAI API configured")
    
    def setup_vosk(self):
        """Setup Vosk for local speech recognition"""
        try:
            model_path = MODELS_DIR / "vosk-model-small-en-us-0.15"
            if model_path.exists():
                self.voice_model = vosk.Model(str(model_path))
                logger.info("Vosk model loaded")
            else:
                logger.warning(f"Vosk model not found at {model_path}")
        except Exception as e:
            logger.error(f"Vosk setup error: {e}")
    
    def setup_whisper(self):
        """Setup Whisper for local speech recognition"""
        try:
            self.voice_model = whisper.load_model("base")
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error(f"Whisper setup error: {e}")
    
    def read_sensors(self):
        """Read all sensor data"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'temperature': None,
            'humidity': None,
            'gas_detected': False,
            'light_level': 'unknown',
            'air_quality': 'good'
        }
        
        if not RPI_AVAILABLE:
            # Simulate sensor data
            data.update({
                'temperature': round(20 + random.uniform(-5, 15), 1),
                'humidity': round(40 + random.uniform(-10, 30), 1),
                'gas_detected': random.choice([False, False, False, True]),
                'light_level': random.choice(['dark', 'dim', 'bright']),
                'air_quality': random.choice(['excellent', 'good', 'moderate'])
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
                data['air_quality'] = 'poor' if gas_state else 'good'
            
            # Read light sensor
            if 'light_pin' in self.sensors:
                light_state = GPIO.input(self.sensors['light_pin'])
                data['light_level'] = 'bright' if light_state else 'dark'
                
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
        
        return data
    
    def get_network_status(self):
        """Get network connection status"""
        status = {
            'wifi': {'connected': False, 'ssid': '', 'signal': 0},
            'ethernet': {'connected': False, 'ip': ''},
            'primary': 'none'
        }
        
        try:
            # Check ethernet
            result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                                  capture_output=True, text=True)
            if 'inet ' in result.stdout:
                status['ethernet']['connected'] = True
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        status['ethernet']['ip'] = line.split()[1].split('/')[0]
                        break
                status['primary'] = 'ethernet'
            
            # Check WiFi
            if not status['ethernet']['connected']:
                try:
                    result = subprocess.run(['iwconfig', 'wlan0'], 
                                          capture_output=True, text=True)
                    if 'ESSID:' in result.stdout and 'off/any' not in result.stdout:
                        status['wifi']['connected'] = True
                        for line in result.stdout.split('\n'):
                            if 'ESSID:' in line:
                                status['wifi']['ssid'] = line.split('ESSID:')[1].strip('"')
                        status['primary'] = 'wifi'
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Network status error: {e}")
        
        return status
    
    def scan_wifi_networks(self):
        """Scan for WiFi networks"""
        networks = []
        try:
            result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                                  capture_output=True, text=True)
            
            current_network = {}
            for line in result.stdout.split('\n'):
                if 'Cell ' in line:
                    if current_network and 'ssid' in current_network:
                        networks.append(current_network)
                    current_network = {}
                elif 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    if ssid:
                        current_network['ssid'] = ssid
                elif 'Quality=' in line:
                    try:
                        quality = line.split('Quality=')[1].split()[0]
                        if '/' in quality:
                            current, max_val = quality.split('/')
                            current_network['signal'] = int((int(current) / int(max_val)) * 100)
                    except:
                        current_network['signal'] = 0
            
            if current_network and 'ssid' in current_network:
                networks.append(current_network)
                
        except Exception as e:
            logger.error(f"WiFi scan error: {e}")
        
        return networks
    
    def connect_wifi(self, ssid, password):
        """Connect to WiFi network"""
        try:
            config = f'''country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            config_path = '/tmp/wpa_temp.conf'
            with open(config_path, 'w') as f:
                f.write(config)
            
            subprocess.run(['sudo', 'cp', config_path, 
                          '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=True)
            
            return True
            
        except Exception as e:
            logger.error(f"WiFi connection error: {e}")
            return False
    
    def process_voice_command(self, command):
        """Process voice command"""
        command = command.lower().strip()
        response = ""
        actions = []
        
        # Temperature query
        if 'temperature' in command:
            data = self.read_sensors()
            if data['temperature']:
                response = f"The temperature is {data['temperature']:.1f} degrees"
            else:
                response = "Temperature sensor not available"
        
        # Humidity query
        elif 'humidity' in command:
            data = self.read_sensors()
            if data['humidity']:
                response = f"The humidity is {data['humidity']:.1f} percent"
            else:
                response = "Humidity sensor not available"
        
        # Timer commands
        elif 'timer' in command:
            # Simple timer for X minutes
            import re
            match = re.search(r'(\d+)\s*(minute|second|hour)', command)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                duration = value * (1 if 'second' in unit else 60 if 'minute' in unit else 3600)
                timer_id = self.timers.create_timer(duration, f"{value} {unit} timer")
                response = f"Timer set for {value} {unit}"
                actions.append({'type': 'timer_created', 'id': timer_id})
            else:
                response = "Please specify timer duration"
        
        # Light control
        elif 'light' in command:
            if 'on' in command:
                response = "Turning on the lights"
                actions.append({'type': 'lights', 'action': 'on'})
            elif 'off' in command:
                response = "Turning off the lights"
                actions.append({'type': 'lights', 'action': 'off'})
            else:
                response = "Please say turn on or turn off"
        
        # Weather
        elif 'weather' in command:
            weather = self.weather.get_current()
            if weather:
                response = f"It's {weather.get('temp', 'unknown')} degrees with {weather.get('description', 'unknown conditions')}"
            else:
                response = "Weather information not available"
        
        # Media control
        elif 'play' in command:
            self.media.play()
            response = "Playing media"
            actions.append({'type': 'media', 'action': 'play'})
        elif 'pause' in command:
            self.media.pause()
            response = "Media paused"
            actions.append({'type': 'media', 'action': 'pause'})
        elif 'stop' in command:
            self.media.stop()
            response = "Media stopped"
            actions.append({'type': 'media', 'action': 'stop'})
        
        # Default
        else:
            response = "I can help with temperature, humidity, timers, lights, weather, and media control"
        
        return response, actions
    
    def speak(self, text):
        """Text-to-speech output"""
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
        else:
            logger.info(f"TTS: {text}")
    
    def listen_for_wake_word(self):
        """Listen for wake word"""
        if not SPEECH_RECOGNITION_AVAILABLE or not self.recognizer or not self.microphone:
            logger.warning("Voice recognition not available")
            return
        
        wake_words = self.settings.get('wake_words', ['hey bing'])
        
        while self.running:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        
                        for wake_word in wake_words:
                            if wake_word in text:
                                self.on_wake_word_detected()
                                break
                                
                    except sr.UnknownValueError:
                        pass
                        
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                logger.error(f"Wake word detection error: {e}")
                time.sleep(1)
    
    def on_wake_word_detected(self):
        """Handle wake word detection"""
        self.voice_active = True
        self.last_wake_time = datetime.now()
        
        logger.info("Wake word detected")
        self.speak("Yes?")
        
        if socketio and SOCKETIO_AVAILABLE:
            socketio.emit('wake_word_detected', {
                'timestamp': self.last_wake_time.isoformat()
            })
        
        # Listen for command
        self.listen_for_command()
    
    def listen_for_command(self):
        """Listen for voice command after wake word"""
        if not SPEECH_RECOGNITION_AVAILABLE or not self.recognizer or not self.microphone:
            return
        
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                try:
                    command = self.recognizer.recognize_google(audio)
                    
                    # Process command
                    response, actions = self.process_voice_command(command)
                    self.speak(response)
                    
                    if socketio and SOCKETIO_AVAILABLE:
                        socketio.emit('voice_response', {
                            'command': command,
                            'response': response,
                            'actions': actions,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except sr.UnknownValueError:
                    self.speak("I didn't understand that")
                    
        except sr.WaitTimeoutError:
            self.speak("I didn't hear anything")
        except Exception as e:
            logger.error(f"Command recognition error: {e}")
            self.speak("Sorry, there was an error")
        
        finally:
            self.voice_active = False
    
    def sensor_monitor_loop(self):
        """Background sensor monitoring"""
        while self.running:
            try:
                data = self.read_sensors()
                if socketio and SOCKETIO_AVAILABLE:
                    socketio.emit('sensor_update', data)
                time.sleep(5)
            except Exception as e:
                logger.error(f"Sensor monitor error: {e}")
                time.sleep(10)
    
    def automation_loop(self):
        """Background automation processing"""
        while self.running:
            try:
                self.timers.check_routines()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Automation error: {e}")
                time.sleep(60)
    
    def start_background_tasks(self):
        """Start all background tasks"""
        # Sensor monitoring
        if self.sensor_thread is None or not self.sensor_thread.is_alive():
            self.sensor_thread = threading.Thread(target=self.sensor_monitor_loop, daemon=True)
            self.sensor_thread.start()
            logger.info("Sensor monitoring started")
        
        # Voice detection
        if SPEECH_RECOGNITION_AVAILABLE and (self.voice_thread is None or not self.voice_thread.is_alive()):
            self.voice_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)
            self.voice_thread.start()
            logger.info("Voice detection started")
        
        # Automation processing
        if self.automation_thread is None or not self.automation_thread.is_alive():
            self.automation_thread = threading.Thread(target=self.automation_loop, daemon=True)
            self.automation_thread.start()
            logger.info("Automation processing started")
    
    def get_system_status(self):
        """Get comprehensive system status"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'hardware': RPI_AVAILABLE,
            'audio': TTS_AVAILABLE and SPEECH_RECOGNITION_AVAILABLE,
            'ai': VOSK_AVAILABLE or WHISPER_AVAILABLE or OPENAI_AVAILABLE,
            'voice_provider': self.settings.get('voice_provider', 'local'),
            'voice_model': self.settings.get('voice_model', 'vosk'),
            'network': self.get_network_status(),
            'sensors': self.read_sensors(),
            'startup_complete': self.startup_complete,
            'timestamp': datetime.now().isoformat(),
            'version': '3.0.0'
        }

# ============================================
# Initialize the system
# ============================================
binghome = BingHomeHub()

# ============================================
# Flask Routes
# ============================================

@app.route('/')
def index():
    """Main hub interface"""
    return render_template('hub.html', settings=binghome.settings)

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html', settings=binghome.settings)

@app.route('/wifi')
def wifi_page():
    """WiFi settings page"""
    return render_template('wifi_settings.html')

@app.route('/system')
def system_page():
    """System status page"""
    sensor_data = binghome.read_sensors()
    
    # Get system info
    try:
        import psutil
        cpu_temp = 45.0  # Would need specific method for Pi
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.now() - boot_time).split('.')[0]
    except:
        cpu_temp = 45.0
        memory_percent = 35
        disk_percent = 42
        uptime = '2 days, 5 hours'
    
    system_info = {
        'cpu_temp': cpu_temp,
        'memory_used_percent': memory_percent,
        'disk_used_percent': disk_percent,
        'uptime': uptime
    }
    
    return render_template('system_status.html', 
                         sensor_data=sensor_data,
                         system_info=system_info)

# ============================================
# API Routes
# ============================================

@app.route('/api/sensor_data')
def api_sensor_data():
    """Get current sensor readings"""
    data = binghome.read_sensors()
    return jsonify(data)

@app.route('/api/network_status')
def api_network_status():
    """Get network connection status"""
    status = binghome.get_network_status()
    return jsonify(status)

@app.route('/api/weather')
def api_weather():
    """Get weather information"""
    current = binghome.weather.get_current()
    forecast = binghome.weather.get_forecast()
    return jsonify({
        'current': current,
        'forecast': forecast
    })

@app.route('/api/news')
def api_news():
    """Get news feed"""
    news = binghome.news.fetch_news()
    return jsonify(news)

@app.route('/api/timers')
def api_timers():
    """Get active timers"""
    timers = binghome.timers.get_timers()
    return jsonify(timers)

@app.route('/api/timer', methods=['POST'])
def api_timer():
    """Create a timer"""
    try:
        data = request.get_json()
        duration = data.get('duration', 60)
        name = data.get('name', 'Timer')
        
        timer_id = binghome.timers.create_timer(duration, name)
        
        return jsonify({
            'success': True,
            'timer_id': timer_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/timer/<timer_id>', methods=['DELETE'])
def api_cancel_timer(timer_id):
    """Cancel a timer"""
    if binghome.timers.cancel_timer(timer_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Timer not found'})

@app.route('/api/wifi_scan')
def api_wifi_scan():
    """Scan for WiFi networks"""
    networks = binghome.scan_wifi_networks()
    return jsonify({'networks': networks})

@app.route('/api/wifi_connect', methods=['POST'])
def api_wifi_connect():
    """Connect to WiFi network"""
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if binghome.connect_wifi(ssid, password):
            return jsonify({'success': True, 'message': 'Connecting to ' + ssid})
        else:
            return jsonify({'success': False, 'error': 'Connection failed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if request.method == 'GET':
        # Hide sensitive keys
        safe_settings = binghome.settings.copy()
        for key in ['openai_api_key', 'azure_speech_key', 'google_cloud_key', 
                   'amazon_polly_key', 'home_assistant_token', 'bing_api_key', 'weather_api_key']:
            if key in safe_settings and safe_settings[key]:
                safe_settings[key + '_configured'] = True
                safe_settings[key] = ''
        return jsonify(safe_settings)
    
    try:
        new_settings = request.get_json()
        
        # Merge with existing settings
        merged_settings = binghome.settings.copy()
        for key, value in new_settings.items():
            if value or key not in merged_settings:
                merged_settings[key] = value
        
        if binghome.save_settings(merged_settings):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voice', methods=['POST'])
def api_voice():
    """Process voice command"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if command:
            response, actions = binghome.process_voice_command(command)
            binghome.speak(response)
            
            return jsonify({
                'success': True,
                'command': command,
                'response': response,
                'actions': actions
            })
        else:
            return jsonify({'success': False, 'error': 'No command provided'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/media/<action>', methods=['POST'])
def api_media(action):
    """Media control"""
    try:
        if action == 'play':
            binghome.media.play()
        elif action == 'pause':
            binghome.media.pause()
        elif action == 'stop':
            binghome.media.stop()
        elif action == 'next':
            binghome.media.next()
        elif action == 'previous':
            binghome.media.previous()
        elif action == 'volume':
            data = request.get_json()
            level = data.get('level', 50)
            binghome.media.set_volume(level)
        else:
            return jsonify({'success': False, 'error': 'Unknown action'})
        
        return jsonify({'success': True})
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
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'binghome'])
        return jsonify({'success': True, 'message': 'Restarting...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# WebSocket Events (if available)
# ============================================

if SOCKETIO_AVAILABLE and socketio:
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info(f"Client connected: {request.sid}")
        emit('status', binghome.get_system_status())
        
        # Send initial data
        sensor_data = binghome.read_sensors()
        emit('sensor_update', sensor_data)
        
        network_status = binghome.get_network_status()
        emit('network_update', network_status)

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {request.sid}")

    @socketio.on('voice_command')
    def handle_voice_command(data):
        """Handle voice command via WebSocket"""
        try:
            command = data.get('command', '')
            if command:
                response, actions = binghome.process_voice_command(command)
                binghome.speak(response)
                
                emit('voice_response', {
                    'command': command,
                    'response': response,
                    'actions': actions,
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
            
            response = f"Controlling {device}: {action}"
            binghome.speak(response)
            
            emit('device_response', {
                'device': device,
                'action': action,
                'response': response
            })
        except Exception as e:
            emit('error', {'message': str(e)})

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ============================================
# Startup Function
# ============================================

def startup_tasks():
    """Perform startup tasks"""
    logger.info("BingHome Hub starting up...")
    
    # Start background monitoring
    binghome.start_background_tasks()
    
    # Mark startup as complete
    binghome.startup_complete = True
    
    logger.info("BingHome Hub startup complete")

# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    try:
        # Perform startup tasks in background thread
        startup_thread = threading.Thread(target=startup_tasks, daemon=True)
        startup_thread.start()
        
        # Get host and port from environment or defaults
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        logger.info(f"Starting BingHome Hub on {host}:{port}")
        
        # Run the Flask app with or without SocketIO
        if SOCKETIO_AVAILABLE and socketio:
            socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        else:
            app.run(host=host, port=port, debug=debug)
            
    except KeyboardInterrupt:
        logger.info("BingHome Hub shutting down...")
        binghome.running = False
        
        # Cleanup GPIO if available
        if RPI_AVAILABLE:
            GPIO.cleanup()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)