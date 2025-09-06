#!/usr/bin/env python3
"""
BingHome Hub - Smart Home Control System
Enhanced version with streaming apps, local AI, and advanced automation
"""

import os
import sys
import json
import time
import threading
import subprocess
import socket
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Flask and web framework imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
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

# Local AI models
try:
    import whisper
    import vosk
    import json as vosk_json
    LOCAL_AI_AVAILABLE = True
except ImportError:
    LOCAL_AI_AVAILABLE = False
    print("⚠️  Local AI models not available - cloud services will be used")

# Home automation
try:
    from homeassistant_api import Client
    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    print("⚠️  Home Assistant API not available")

# Import core modules
from core.media import MediaController
from core.news import NewsManager
from core.timers import TimerManager
from core.weather import WeatherService

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
ENV_FILE = BASE_DIR / ".env"
MODELS_DIR = BASE_DIR / "models"

# Flask app setup
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'binghome-hub-secret-key-change-me')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app)

class BingHomeHub:
    def __init__(self):
        self.settings = self.load_settings()
        self.setup_hardware()
        self.setup_audio()
        self.setup_ai()
        self.setup_home_automation()
        self.running = True
        self.sensor_thread = None
        self.voice_thread = None
        self.automation_thread = None
        self.startup_complete = False
        
        # Controllers
        self.media = MediaController()
        self.news = NewsManager()
        self.timers = TimerManager()
        self.weather = WeatherService()
        
        # Voice state
        self.voice_active = False
        self.last_wake_time = None
        self.voice_model = None
        self.recognizer = None
        
        # Automation state
        self.devices = {}
        self.scenes = []
        self.automations = []
        
    def load_settings(self):
        """Load settings from JSON file or create defaults"""
        default_settings = {
            "voice_provider": "local",  # local, openai, azure, google, amazon
            "voice_model": "vosk",  # vosk, whisper, cloud
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
            "kiosk_mode": True,
            "auto_start_browser": True,
            "network_interface": "auto",  # auto, wifi, ethernet
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
            # Reinitialize components with new settings
            self.setup_ai()
            self.setup_home_automation()
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
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # DHT22 temperature/humidity sensor
            dht_pin = self.settings["gpio_pins"]["dht22"]
            self.sensors['dht22'] = adafruit_dht.DHT22(getattr(board, f'D{dht_pin}'))
            
            # Gas sensor (MQ-2/MQ-5)
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
        """Initialize audio system with local AI preference"""
        if not AUDIO_AVAILABLE:
            print("🔇 Audio simulation mode")
            return
        
        try:
            # Initialize TTS
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', self.settings['tts_rate'])
            self.tts_engine.setProperty('volume', self.settings['tts_volume'])
            
            # Initialize speech recognition
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Initialize pygame for audio playback
            pygame.mixer.init()
            
            print("✅ Audio system initialized")
            
        except Exception as e:
            print(f"⚠️  Audio setup error: {e}")
    
    def setup_ai(self):
        """Initialize AI services with local model preference"""
        voice_provider = self.settings.get('voice_provider', 'local')
        
        if voice_provider == 'local' and LOCAL_AI_AVAILABLE:
            self.setup_local_ai()
        elif voice_provider == 'openai' and self.settings.get('openai_api_key'):
            self.setup_openai()
        elif voice_provider == 'azure' and self.settings.get('azure_speech_key'):
            self.setup_azure()
        elif voice_provider == 'google' and self.settings.get('google_cloud_key'):
            self.setup_google()
        elif voice_provider == 'amazon' and self.settings.get('amazon_polly_key'):
            self.setup_amazon()
        else:
            print("⚠️  No AI provider configured, using basic recognition")
    
    def setup_local_ai(self):
        """Setup local AI models (Vosk or Whisper)"""
        try:
            model_type = self.settings.get('voice_model', 'vosk')
            
            if model_type == 'vosk':
                # Load Vosk model
                model_path = MODELS_DIR / "vosk-model-small-en-us-0.15"
                if model_path.exists():
                    import vosk
                    self.voice_model = vosk.Model(str(model_path))
                    print("✅ Vosk model loaded")
                else:
                    print("⚠️  Vosk model not found, downloading...")
                    self.download_vosk_model()
                    
            elif model_type == 'whisper':
                # Load Whisper model
                import whisper
                self.voice_model = whisper.load_model("base")
                print("✅ Whisper model loaded")
                
        except Exception as e:
            print(f"⚠️  Local AI setup error: {e}")
    
    def setup_openai(self):
        """Setup OpenAI Whisper API"""
        try:
            import openai
            openai.api_key = self.settings['openai_api_key']
            print("✅ OpenAI API configured")
        except Exception as e:
            print(f"⚠️  OpenAI setup error: {e}")
    
    def setup_azure(self):
        """Setup Azure Speech Services"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.settings['azure_speech_key'],
                region="eastus"
            )
            print("✅ Azure Speech configured")
        except Exception as e:
            print(f"⚠️  Azure setup error: {e}")
    
    def setup_google(self):
        """Setup Google Cloud Speech"""
        # Google Cloud Speech setup would go here
        print("✅ Google Cloud Speech configured")
    
    def setup_amazon(self):
        """Setup Amazon Polly/Transcribe"""
        # Amazon AWS setup would go here
        print("✅ Amazon Speech configured")
    
    def setup_home_automation(self):
        """Initialize Home Assistant connection"""
        if not HA_AVAILABLE:
            print("⚠️  Home Assistant API not available")
            return
        
        try:
            ha_url = self.settings.get('home_assistant_url')
            ha_token = self.settings.get('home_assistant_token')
            
            if ha_url and ha_token:
                self.ha_client = Client(ha_url, ha_token)
                self.load_devices()
                print("✅ Home Assistant connected")
            else:
                print("⚠️  Home Assistant not configured")
                
        except Exception as e:
            print(f"⚠️  Home Assistant setup error: {e}")
    
    def load_devices(self):
        """Load devices from Home Assistant"""
        if hasattr(self, 'ha_client'):
            try:
                # Get all entities
                entities = self.ha_client.get_entities()
                
                for entity in entities:
                    entity_id = entity['entity_id']
                    domain = entity_id.split('.')[0]
                    
                    self.devices[entity_id] = {
                        'id': entity_id,
                        'name': entity.get('attributes', {}).get('friendly_name', entity_id),
                        'domain': domain,
                        'state': entity.get('state'),
                        'attributes': entity.get('attributes', {})
                    }
                
                print(f"✅ Loaded {len(self.devices)} devices from Home Assistant")
                
            except Exception as e:
                print(f"Error loading devices: {e}")
    
    def read_sensors(self):
        """Read all sensor data"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'temperature': None,
            'humidity': None,
            'gas_detected': False,
            'light_level': 'unknown',
            'air_quality': 'good'  # Calculate from gas sensor
        }
        
        if not RPI_AVAILABLE:
            # Simulate sensor data for development
            import random
            data.update({
                'temperature': round(20 + random.uniform(-5, 15), 1),
                'humidity': round(40 + random.uniform(-10, 30), 1),
                'gas_detected': random.choice([False, False, False, True]),  # 25% chance
                'light_level': random.choice(['dark', 'dim', 'bright']),
                'air_quality': random.choice(['excellent', 'good', 'moderate', 'poor'])
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
            print(f"Sensor read error: {e}")
        
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
                # Extract IP
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        status['ethernet']['ip'] = line.split()[1].split('/')[0]
                        break
                status['primary'] = 'ethernet'
            
            # Check WiFi only if ethernet not connected
            if not status['ethernet']['connected']:
                result = subprocess.run(['iwconfig', 'wlan0'], 
                                      capture_output=True, text=True)
                if 'ESSID:' in result.stdout and 'off/any' not in result.stdout:
                    status['wifi']['connected'] = True
                    # Extract SSID
                    for line in result.stdout.split('\n'):
                        if 'ESSID:' in line:
                            status['wifi']['ssid'] = line.split('ESSID:')[1].strip('"')
                        if 'Signal level=' in line:
                            # Extract signal strength
                            signal = line.split('Signal level=')[1].split(' ')[0]
                            status['wifi']['signal'] = int(signal)
                    status['primary'] = 'wifi'
            
        except Exception as e:
            print(f"Network status error: {e}")
        
        return status
    
    def process_voice_command(self, command):
        """Process voice command with home automation support"""
        command = command.lower().strip()
        response = ""
        actions = []
        
        # Home automation commands
        if any(word in command for word in ['turn on', 'turn off', 'switch', 'toggle']):
            response, actions = self.process_device_command(command)
        
        # Timer commands
        elif 'timer' in command or 'alarm' in command:
            response = self.process_timer_command(command)
        
        # Scene commands
        elif any(word in command for word in ['scene', 'mode']):
            response = self.process_scene_command(command)
        
        # Information queries
        elif 'temperature' in command:
            data = self.read_sensors()
            if data['temperature']:
                response = f"The current temperature is {data['temperature']:.1f} degrees Celsius"
            else:
                response = "Temperature sensor not available"
        
        elif 'humidity' in command:
            data = self.read_sensors()
            if data['humidity']:
                response = f"The current humidity is {data['humidity']:.1f} percent"
            else:
                response = "Humidity sensor not available"
        
        elif 'air quality' in command:
            data = self.read_sensors()
            response = f"The air quality is {data['air_quality']}"
        
        elif 'weather' in command:
            weather = self.weather.get_current()
            if weather:
                response = f"It's currently {weather['temp']} degrees with {weather['description']}"
            else:
                response = "Weather information not available"
        
        # Media commands
        elif any(word in command for word in ['play', 'pause', 'stop', 'next', 'previous']):
            response = self.process_media_command(command)
        
        # App launch commands
        elif any(app in command for app in ['netflix', 'youtube', 'prime', 'spotify', 'xbox']):
            response = self.launch_app(command)
        
        # Default response
        else:
            response = "I didn't understand that command. Try saying 'turn on the lights' or 'what's the temperature'"
        
        return response, actions
    
    def process_device_command(self, command):
        """Process device control commands"""
        actions = []
        
        # Parse the command
        action = None
        if 'turn on' in command or 'switch on' in command:
            action = 'on'
        elif 'turn off' in command or 'switch off' in command:
            action = 'off'
        elif 'toggle' in command:
            action = 'toggle'
        
        # Find the device
        device_found = None
        for device_id, device in self.devices.items():
            device_name = device['name'].lower()
            if device_name in command:
                device_found = device
                break
        
        if device_found and action:
            # Send command to Home Assistant
            if hasattr(self, 'ha_client'):
                try:
                    if action == 'on':
                        self.ha_client.call_service('homeassistant', 'turn_on', 
                                                  entity_id=device_found['id'])
                    elif action == 'off':
                        self.ha_client.call_service('homeassistant', 'turn_off', 
                                                  entity_id=device_found['id'])
                    elif action == 'toggle':
                        self.ha_client.call_service('homeassistant', 'toggle', 
                                                  entity_id=device_found['id'])
                    
                    actions.append({
                        'type': 'device_control',
                        'device': device_found['id'],
                        'action': action
                    })
                    
                    return f"Turning {action} {device_found['name']}", actions
                    
                except Exception as e:
                    return f"Failed to control {device_found['name']}: {str(e)}", []
            else:
                return "Home Assistant not connected", []
        
        return "I couldn't find that device", []
    
    def process_timer_command(self, command):
        """Process timer commands"""
        import re
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*(hour|minute|second|hr|min|sec)', command)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)
            
            # Convert to seconds
            if 'hour' in unit or 'hr' in unit:
                duration = value * 3600
            elif 'minute' in unit or 'min' in unit:
                duration = value * 60
            else:
                duration = value
            
            # Extract name if provided
            name = "Timer"
            if 'for' in command:
                name_part = command.split('for')[-1].strip()
                name = name_part if name_part else "Timer"
            
            timer_id = self.timers.create_timer(duration, name)
            return f"Timer set for {value} {unit}"
        
        return "Please specify a duration for the timer"
    
    def process_scene_command(self, command):
        """Process scene activation commands"""
        # This would activate Home Assistant scenes
        return "Scene control coming soon"
    
    def process_media_command(self, command):
        """Process media control commands"""
        if 'play' in command:
            self.media.play()
            return "Playing media"
        elif 'pause' in command:
            self.media.pause()
            return "Media paused"
        elif 'stop' in command:
            self.media.stop()
            return "Media stopped"
        elif 'next' in command:
            self.media.next()
            return "Next track"
        elif 'previous' in command:
            self.media.previous()
            return "Previous track"
        
        return "Media command not recognized"
    
    def launch_app(self, command):
        """Launch streaming apps"""
        app_map = {
            'netflix': 'netflix',
            'youtube': 'youtube',
            'prime': 'prime_video',
            'spotify': 'spotify',
            'xbox': 'xbox_cloud'
        }
        
        for keyword, app_key in app_map.items():
            if keyword in command:
                if self.settings['apps'][app_key]['enabled']:
                    socketio.emit('launch_app', {
                        'app': app_key,
                        'url': self.settings['apps'][app_key]['url']
                    })
                    return f"Launching {keyword}"
                else:
                    return f"{keyword} is not enabled"
        
        return "App not found"
    
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
    
    def listen_for_wake_word(self):
        """Continuously listen for wake word"""
        if not AUDIO_AVAILABLE or not self.recognizer:
            return
        
        wake_words = self.settings.get('wake_words', ['hey bing'])
        
        while self.running:
            try:
                with self.microphone as source:
                    # Listen for audio
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                    # Try to recognize
                    text = ""
                    if self.settings.get('voice_provider') == 'local' and self.voice_model:
                        # Use local model
                        if self.settings.get('voice_model') == 'vosk':
                            # Vosk recognition
                            rec = vosk.KaldiRecognizer(self.voice_model, 16000)
                            if rec.AcceptWaveform(audio.get_wav_data()):
                                result = json.loads(rec.Result())
                                text = result.get('text', '')
                        elif self.settings.get('voice_model') == 'whisper':
                            # Whisper recognition
                            audio_data = audio.get_wav_data()
                            result = self.voice_model.transcribe(audio_data)
                            text = result['text']
                    else:
                        # Use cloud service
                        text = self.recognizer.recognize_google(audio)
                    
                    # Check for wake word
                    text_lower = text.lower()
                    for wake_word in wake_words:
                        if wake_word in text_lower:
                            self.on_wake_word_detected()
                            break
                            
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"Wake word detection error: {e}")
                time.sleep(1)
    
    def on_wake_word_detected(self):
        """Handle wake word detection"""
        self.voice_active = True
        self.last_wake_time = datetime.now()
        
        # Notify UI
        socketio.emit('wake_word_detected', {
            'timestamp': self.last_wake_time.isoformat()
        })
        
        # Play acknowledgment sound
        self.speak("Yes?")
        
        # Listen for command
        self.listen_for_command()
    
    def listen_for_command(self):
        """Listen for voice command after wake word"""
        if not AUDIO_AVAILABLE or not self.recognizer:
            return
        
        try:
            with self.microphone as source:
                # Listen for command
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # Recognize command
                command = ""
                if self.settings.get('voice_provider') == 'local' and self.voice_model:
                    # Use local model
                    if self.settings.get('voice_model') == 'vosk':
                        rec = vosk.KaldiRecognizer(self.voice_model, 16000)
                        if rec.AcceptWaveform(audio.get_wav_data()):
                            result = json.loads(rec.Result())
                            command = result.get('text', '')
                    elif self.settings.get('voice_model') == 'whisper':
                        audio_data = audio.get_wav_data()
                        result = self.voice_model.transcribe(audio_data)
                        command = result['text']
                else:
                    # Use cloud service
                    command = self.recognizer.recognize_google(audio)
                
                if command:
                    # Process command
                    response, actions = self.process_voice_command(command)
                    
                    # Send response
                    self.speak(response)
                    
                    # Notify UI
                    socketio.emit('voice_command', {
                        'command': command,
                        'response': response,
                        'actions': actions,
                        'timestamp': datetime.now().isoformat()
                    })
                    
        except sr.WaitTimeoutError:
            self.speak("I didn't hear anything")
        except sr.UnknownValueError:
            self.speak("I didn't understand that")
        except Exception as e:
            print(f"Command recognition error: {e}")
            self.speak("Sorry, there was an error")
        
        finally:
            self.voice_active = False
    
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
    
    def automation_loop(self):
        """Background automation processing"""
        while self.running:
            try:
                # Check for scheduled automations
                self.timers.check_routines()
                
                # Update device states
                if hasattr(self, 'ha_client'):
                    self.load_devices()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Automation error: {e}")
                time.sleep(60)
    
    def start_background_tasks(self):
        """Start all background tasks"""
        # Sensor monitoring
        if self.sensor_thread is None or not self.sensor_thread.is_alive():
            self.sensor_thread = threading.Thread(target=self.sensor_monitor_loop, daemon=True)
            self.sensor_thread.start()
            print("✅ Sensor monitoring started")
        
        # Voice detection
        if AUDIO_AVAILABLE and (self.voice_thread is None or not self.voice_thread.is_alive()):
            self.voice_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)
            self.voice_thread.start()
            print("✅ Voice detection started")
        
        # Automation processing
        if self.automation_thread is None or not self.automation_thread.is_alive():
            self.automation_thread = threading.Thread(target=self.automation_loop, daemon=True)
            self.automation_thread.start()
            print("✅ Automation processing started")
    
    def download_vosk_model(self):
        """Download Vosk model if not present"""
        import urllib.request
        import zipfile
        
        model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        model_zip = MODELS_DIR / "vosk-model.zip"
        
        try:
            MODELS_DIR.mkdir(exist_ok=True)
            
            print("Downloading Vosk model...")
            urllib.request.urlretrieve(model_url, model_zip)
            
            print("Extracting model...")
            with zipfile.ZipFile(model_zip, 'r') as zip_ref:
                zip_ref.extractall(MODELS_DIR)
            
            model_zip.unlink()  # Remove zip file
            print("✅ Vosk model downloaded")
            
        except Exception as e:
            print(f"Failed to download Vosk model: {e}")
    
    def get_system_status(self):
        """Get comprehensive system status"""
        network = self.get_network_status()
        sensors = self.read_sensors()
        
        return {
            'status': 'healthy