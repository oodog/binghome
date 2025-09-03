#!/usr/bin/env python3
"""
BingHome - Smart Home Control System
Version 2.1.0 - Enhanced with OAuth and automatic voice fallback
"""

import os
import sys
import json
import time
import threading
import logging
import queue
import numpy as np
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, session, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
from functools import wraps

# Hardware libraries - will be installed on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    import busio
    import adafruit_tpa2016
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: Hardware libraries not available. Running in simulation mode.")

# Voice recognition libraries
try:
    import sounddevice as sd
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import vosk
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# Text-to-speech
try:
    import pyttsx3
    TTS_ENGINE = 'pyttsx3'
except ImportError:
    try:
        from gtts import gTTS
        import pygame
        TTS_ENGINE = 'gtts'
    except ImportError:
        TTS_ENGINE = None

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings.json')

# Configuration class
class Config:
    def __init__(self):
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        default_settings = {
            'openai_api_key': '',
            'bing_api_key': '',
            'home_assistant_url': 'http://localhost:8123',
            'home_assistant_token': '',
            'voice_mode': 'auto',  # auto, vosk, whisper, speech_recognition
            'wake_words': ["hey bing", "okay bing", "bing"],
            'tts_engine': 'pyttsx3',
            'tts_rate': 150,
            'tts_volume': 0.9,
            'language': 'en-US',
            'gpio_pins': {
                'dht22': 4,
                'gas_sensor': 17,
                'light_sensor': 27
            }
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        
        # Update attributes
        for key, value in default_settings.items():
            setattr(self, key.upper(), value)
        
        # Additional computed properties
        self.SENSOR_UPDATE_INTERVAL = 5
        self.NEWS_UPDATE_INTERVAL = 300
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.CHUNK_SIZE = 1024
        
    def save_settings(self, settings):
        """Save settings to file"""
        try:
            # Update current config
            for key, value in settings.items():
                setattr(self, key.upper(), value)
            
            # Save to file
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

# Global instances
config = Config()
sensor_data = {
    'temperature': 0,
    'humidity': 0,
    'gas_detected': False,
    'light_level': 'dark',
    'timestamp': None
}
news_data = []
voice_assistant = None

# OAuth Configuration
OAUTH_CONFIG = {
    'client_id': os.environ.get('OPENAI_CLIENT_ID', ''),
    'client_secret': os.environ.get('OPENAI_CLIENT_SECRET', ''),
    'redirect_uri': 'http://localhost:5000/auth/callback',
    'authorize_url': 'https://auth.openai.com/authorize',
    'token_url': 'https://auth.openai.com/oauth/token',
    'scope': 'openai.api'
}

class SensorManager:
    """Manages all sensor operations"""
    
    def __init__(self):
        self.dht = None
        self.i2c = None
        self.tpa2016 = None
        self.setup_hardware()
    
    def setup_hardware(self):
        """Initialize hardware components"""
        if not HARDWARE_AVAILABLE:
            logger.info("Hardware not available, using simulated values")
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.GPIO_PINS['gas_sensor'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(config.GPIO_PINS['light_sensor'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            self.dht = adafruit_dht.DHT22(getattr(board, f"D{config.GPIO_PINS['dht22']}"), use_pulseio=False)
            
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.tpa2016 = adafruit_tpa2016.TPA2016(self.i2c)
            self.tpa2016.amplifier_gain = 10
            
            logger.info("Hardware initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
    
    def read_sensors(self):
        """Read all sensor values"""
        global sensor_data
        
        if not HARDWARE_AVAILABLE:
            import random
            sensor_data = {
                'temperature': round(20 + random.random() * 10, 1),
                'humidity': round(40 + random.random() * 20, 1),
                'gas_detected': random.random() > 0.95,
                'light_level': 'bright' if random.random() > 0.5 else 'dark',
                'timestamp': datetime.now().isoformat()
            }
            return sensor_data
        
        try:
            if self.dht:
                try:
                    temperature = self.dht.temperature
                    humidity = self.dht.humidity
                    if temperature and humidity:
                        sensor_data['temperature'] = round(temperature, 1)
                        sensor_data['humidity'] = round(humidity, 1)
                except RuntimeError:
                    pass  # Normal for DHT22 to occasionally fail
            
            sensor_data['gas_detected'] = GPIO.input(config.GPIO_PINS['gas_sensor']) == GPIO.HIGH
            sensor_data['light_level'] = 'bright' if GPIO.input(config.GPIO_PINS['light_sensor']) == GPIO.HIGH else 'dark'
            sensor_data['timestamp'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
        
        return sensor_data

class VoiceAssistant:
    """Enhanced voice assistant with automatic fallback"""
    
    def __init__(self):
        self.listening = False
        self.processing = False
        self.audio_queue = queue.Queue()
        self.whisper_model = None
        self.vosk_model = None
        self.speech_recognizer = None
        self.openai_client = None
        self.tts_engine = None
        self.current_mode = None
        self.setup_voice()
    
    def setup_voice(self):
        """Initialize voice components with fallback"""
        # Setup OpenAI if available
        if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except:
                pass
        
        # Determine voice mode
        mode = config.VOICE_MODE
        
        if mode == 'auto':
            # Try local first, then cloud
            if self.setup_vosk():
                self.current_mode = 'vosk'
            elif self.setup_speech_recognition():
                self.current_mode = 'speech_recognition'
            elif self.setup_whisper():
                self.current_mode = 'whisper'
            else:
                logger.error("No voice recognition available")
                self.current_mode = None
        elif mode == 'vosk':
            if not self.setup_vosk():
                self.setup_fallback()
        elif mode == 'whisper':
            if not self.setup_whisper():
                self.setup_fallback()
        elif mode == 'speech_recognition':
            if not self.setup_speech_recognition():
                self.setup_fallback()
        
        # Setup TTS
        self.setup_tts()
        
        logger.info(f"Voice assistant initialized with mode: {self.current_mode}")
    
    def setup_vosk(self):
        """Setup Vosk for offline recognition"""
        if not VOSK_AVAILABLE:
            return False
        
        try:
            model_path = os.path.expanduser("~/vosk-model-small-en-us-0.15")
            if os.path.exists(model_path):
                self.vosk_model = vosk.Model(model_path)
                logger.info("Vosk model loaded")
                return True
        except Exception as e:
            logger.error(f"Vosk setup failed: {e}")
        return False
    
    def setup_whisper(self):
        """Setup Whisper for high-quality recognition"""
        if not WHISPER_AVAILABLE:
            return False
        
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.whisper_model = whisper.load_model("tiny", device=device)
            if device == "cpu":
                self.whisper_model = self.whisper_model.half()
            logger.info("Whisper model loaded")
            return True
        except Exception as e:
            logger.error(f"Whisper setup failed: {e}")
        return False
    
    def setup_speech_recognition(self):
        """Setup speech_recognition for cloud-based recognition"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return False
        
        try:
            self.speech_recognizer = sr.Recognizer()
            self.speech_microphone = sr.Microphone()
            with self.speech_microphone as source:
                self.speech_recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Speech recognition initialized")
            return True
        except Exception as e:
            logger.error(f"Speech recognition setup failed: {e}")
        return False
    
    def setup_fallback(self):
        """Setup fallback voice recognition"""
        logger.info("Setting up fallback voice recognition...")
        
        # Try alternatives in order
        if self.setup_speech_recognition():
            self.current_mode = 'speech_recognition'
        elif self.setup_whisper():
            self.current_mode = 'whisper'
        elif self.setup_vosk():
            self.current_mode = 'vosk'
        else:
            self.current_mode = None
            logger.error("No fallback voice recognition available")
    
    def setup_tts(self):
        """Initialize text-to-speech"""
        if TTS_ENGINE == 'pyttsx3':
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', config.TTS_RATE)
                self.tts_engine.setProperty('volume', config.TTS_VOLUME)
                logger.info("TTS initialized")
            except:
                self.tts_engine = None
        elif TTS_ENGINE == 'gtts':
            pygame.mixer.init()
    
    def listen_continuous(self):
        """Main listening loop with automatic fallback"""
        self.listening = True
        logger.info(f"Listening with {self.current_mode}")
        
        while self.listening and self.current_mode:
            try:
                if self.current_mode == 'vosk':
                    self.listen_with_vosk()
                elif self.current_mode == 'whisper':
                    self.listen_with_whisper()
                elif self.current_mode == 'speech_recognition':
                    self.listen_with_speech_recognition()
            except Exception as e:
                logger.error(f"Voice recognition error: {e}")
                logger.info("Attempting fallback...")
                self.setup_fallback()
                time.sleep(2)
    
    def listen_with_vosk(self):
        """Vosk listening implementation"""
        if not self.vosk_model:
            raise Exception("Vosk not available")
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config.CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=config.CHUNK_SIZE
        )
        
        rec = vosk.KaldiRecognizer(self.vosk_model, config.SAMPLE_RATE)
        
        try:
            while self.listening:
                data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '').lower()
                    
                    if text:
                        self.process_speech(text)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
    
    def listen_with_whisper(self):
        """Whisper listening implementation"""
        if not self.whisper_model:
            raise Exception("Whisper not available")
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            self.audio_queue.put(indata.copy())
        
        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            callback=audio_callback,
            blocksize=config.CHUNK_SIZE
        ):
            while self.listening:
                audio_chunks = []
                silence_counter = 0
                recording = False
                
                while True:
                    if not self.audio_queue.empty():
                        chunk = self.audio_queue.get()
                        volume = np.sqrt(np.mean(chunk**2))
                        
                        if volume > 0.01:
                            recording = True
                            silence_counter = 0
                            audio_chunks.append(chunk)
                        elif recording:
                            audio_chunks.append(chunk)
                            silence_counter += 1
                            if silence_counter > 30:
                                break
                    
                    time.sleep(0.01)
                
                if audio_chunks and len(audio_chunks) > 10:
                    audio_data = np.concatenate(audio_chunks).flatten()
                    audio_data = audio_data.astype(np.float32)
                    if audio_data.max() > 1.0:
                        audio_data = audio_data / np.max(np.abs(audio_data))
                    
                    result = self.whisper_model.transcribe(audio_data, language='en', fp16=False)
                    text = result["text"].lower().strip()
                    
                    if text:
                        self.process_speech(text)
    
    def listen_with_speech_recognition(self):
        """Speech recognition (Google) listening implementation"""
        if not self.speech_recognizer:
            raise Exception("Speech recognition not available")
        
        with self.speech_microphone as source:
            while self.listening:
                try:
                    audio = self.speech_recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    try:
                        # Try Google first (free)
                        text = self.speech_recognizer.recognize_google(audio).lower()
                        if text:
                            self.process_speech(text)
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        # If Google fails, try Whisper API if available
                        if config.OPENAI_API_KEY:
                            try:
                                text = self.speech_recognizer.recognize_whisper_api(
                                    audio,
                                    api_key=config.OPENAI_API_KEY
                                ).lower()
                                if text:
                                    self.process_speech(text)
                            except:
                                raise e
                        else:
                            raise e
                            
                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    logger.error(f"Recognition error: {e}")
                    raise
    
    def process_speech(self, text):
        """Process recognized speech"""
        logger.info(f"Heard: {text}")
        
        # Check for wake word
        for wake_word in config.WAKE_WORDS:
            if wake_word in text:
                logger.info("Wake word detected!")
                self.handle_command_mode()
                return
        
        # If already in command mode, process as command
        if self.processing:
            self.process_command(text)
    
    def handle_command_mode(self):
        """Enter command mode"""
        try:
            self.processing = True
            self.speak("Yes, I'm listening")
            socketio.emit('voice_status', {'status': 'listening'})
            
            # Record command with appropriate method
            command = None
            
            if self.current_mode == 'vosk':
                command = self.record_command_vosk()
            elif self.current_mode == 'whisper':
                command = self.record_command_whisper()
            elif self.current_mode == 'speech_recognition':
                command = self.record_command_speech_recognition()
            
            if command:
                self.process_command(command)
            else:
                self.speak("I didn't catch that. Please try again.")
                
        except Exception as e:
            logger.error(f"Command mode error: {e}")
            self.speak("Sorry, there was an error")
        finally:
            self.processing = False
            socketio.emit('voice_status', {'status': 'ready'})
    
    def record_command_vosk(self):
        """Record command using Vosk"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config.CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=config.CHUNK_SIZE
        )
        
        rec = vosk.KaldiRecognizer(self.vosk_model, config.SAMPLE_RATE)
        command_text = ""
        
        try:
            start_time = time.time()
            while time.time() - start_time < 10:
                data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    if text:
                        command_text = text
                        break
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
        
        return command_text.lower()
    
    def record_command_whisper(self):
        """Record command using Whisper"""
        audio_chunks = []
        
        def callback(indata, frames, time, status):
            audio_chunks.append(indata.copy())
        
        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            callback=callback,
            blocksize=config.CHUNK_SIZE
        ):
            time.sleep(5)  # Record for 5 seconds
        
        if audio_chunks:
            audio_data = np.concatenate(audio_chunks).flatten()
            audio_data = audio_data.astype(np.float32)
            if audio_data.max() > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            result = self.whisper_model.transcribe(audio_data, language='en', fp16=False)
            return result["text"].lower().strip()
        
        return None
    
    def record_command_speech_recognition(self):
        """Record command using speech recognition"""
        with self.speech_microphone as source:
            try:
                audio = self.speech_recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                try:
                    return self.speech_recognizer.recognize_google(audio).lower()
                except:
                    if config.OPENAI_API_KEY:
                        return self.speech_recognizer.recognize_whisper_api(
                            audio,
                            api_key=config.OPENAI_API_KEY
                        ).lower()
            except:
                pass
        
        return None
    
    def process_command(self, command):
        """Process voice command"""
        logger.info(f"Processing: {command}")
        
        # Get response
        if self.openai_client:
            response = self.process_with_chatgpt(command)
        else:
            response = self.process_locally(command)
        
        # Extract and execute actions
        actions = self.extract_actions(response)
        if actions:
            self.execute_actions(actions)
        
        # Speak response
        self.speak(response)
        
        # Send to frontend
        socketio.emit('voice_command', {
            'command': command,
            'response': response,
            'actions': actions
        })
    
    def process_with_chatgpt(self, command):
        """Process with ChatGPT"""
        try:
            context = f"""
            You are BingHome, a helpful smart home assistant.
            
            Current conditions:
            - Temperature: {sensor_data['temperature']}°C
            - Humidity: {sensor_data['humidity']}%
            - Gas: {'DETECTED - WARNING!' if sensor_data['gas_detected'] else 'Clear'}
            - Light: {sensor_data['light_level']}
            - Time: {datetime.now().strftime('%H:%M')}
            
            User said: "{command}"
            
            Respond concisely. For device control, include tags like:
            [ACTION:LIGHTS_ON] or [ACTION:TEMPERATURE_SET:22]
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are BingHome, a friendly smart home assistant. Be concise."},
                    {"role": "user", "content": context}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"ChatGPT error: {e}")
            return self.process_locally(command)
    
    def process_locally(self, command):
        """Process command locally without AI"""
        command = command.lower()
        
        if 'temperature' in command or 'temp' in command:
            return f"The temperature is {sensor_data['temperature']} degrees."
        elif 'humidity' in command:
            return f"The humidity is {sensor_data['humidity']} percent."
        elif 'light' in command:
            if 'on' in command:
                return "Turning on the lights. [ACTION:LIGHTS_ON]"
            elif 'off' in command:
                return "Turning off the lights. [ACTION:LIGHTS_OFF]"
            else:
                return f"It's {sensor_data['light_level']} according to the sensor."
        elif 'gas' in command or 'smoke' in command:
            if sensor_data['gas_detected']:
                return "Warning! Gas detected. Check immediately!"
            else:
                return "No gas detected. Air is clear."
        elif 'time' in command:
            return f"The time is {datetime.now().strftime('%I:%M %p')}."
        else:
            return "I can help with lights, temperature, humidity, and sensors. What would you like?"
    
    def extract_actions(self, response):
        """Extract action tags from response"""
        import re
        actions = []
        pattern = r'\[ACTION:([^\]]+)\]'
        matches = re.findall(pattern, response)
        
        for match in matches:
            parts = match.split(':')
            actions.append({
                'type': parts[0],
                'value': parts[1] if len(parts) > 1 else None
            })
        
        return actions
    
    def execute_actions(self, actions):
        """Execute smart home actions"""
        for action in actions:
            try:
                action_type = action['type']
                value = action.get('value')
                
                if action_type == 'LIGHTS_ON':
                    self.control_lights(True)
                elif action_type == 'LIGHTS_OFF':
                    self.control_lights(False)
                elif action_type == 'TEMPERATURE_SET' and value:
                    self.set_temperature(float(value))
                
                logger.info(f"Executed: {action}")
            except Exception as e:
                logger.error(f"Action error: {e}")
    
    def control_lights(self, state):
        """Control lights"""
        if config.HOME_ASSISTANT_URL and config.HOME_ASSISTANT_TOKEN:
            try:
                headers = {
                    'Authorization': f'Bearer {config.HOME_ASSISTANT_TOKEN}',
                    'Content-Type': 'application/json'
                }
                service = 'turn_on' if state else 'turn_off'
                url = f"{config.HOME_ASSISTANT_URL}/api/services/light/{service}"
                response = requests.post(url, headers=headers, json={'entity_id': 'light.living_room'}, timeout=5)
                
                if response.status_code == 200:
                    logger.info(f"Lights {'on' if state else 'off'}")
            except:
                pass
        
        socketio.emit('device_status', {'device': 'lights', 'state': 'on' if state else 'off'})
    
    def set_temperature(self, temp):
        """Set temperature"""
        logger.info(f"Setting temperature to {temp}°C")
        socketio.emit('device_status', {'device': 'thermostat', 'temperature': temp})
    
    def speak(self, text):
        """Text to speech"""
        try:
            import re
            clean_text = re.sub(r'\[ACTION:[^\]]+\]', '', text).strip()
            
            if not clean_text:
                return
            
            if TTS_ENGINE == 'pyttsx3' and self.tts_engine:
                self.tts_engine.say(clean_text)
                self.tts_engine.runAndWait()
            elif TTS_ENGINE == 'gtts':
                tts = gTTS(text=clean_text, lang='en', slow=False)
                tts.save("/tmp/response.mp3")
                pygame.mixer.music.load("/tmp/response.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                os.system(f'espeak "{clean_text}" 2>/dev/null')
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    def stop(self):
        """Stop voice assistant"""
        self.listening = False
        self.processing = False

# Background threads
def sensor_update_loop():
    """Sensor monitoring thread"""
    sensor_manager = SensorManager()
    
    while True:
        try:
            data = sensor_manager.read_sensors()
            socketio.emit('sensor_update', data)
            
            if data['gas_detected']:
                socketio.emit('alert', {
                    'type': 'danger',
                    'message': 'Gas detected! Check immediately!'
                })
            
            time.sleep(config.SENSOR_UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Sensor error: {e}")
            time.sleep(5)

def news_update_loop():
    """News fetching thread"""
    while True:
        try:
            if config.BING_API_KEY:
                headers = {'Ocp-Apim-Subscription-Key': config.BING_API_KEY}
                params = {'mkt': 'en-US', 'count': 10, 'freshness': 'Day'}
                
                response = requests.get(
                    'https://api.bing.microsoft.com/v7.0/news',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    global news_data
                    data = response.json()
                    news_data = [{
                        'title': article['name'],
                        'description': article.get('description', ''),
                        'url': article['url'],
                        'provider': article['provider'][0]['name'] if article.get('provider') else '',
                        'published': article.get('datePublished', '')
                    } for article in data.get('value', [])]
                    
                    socketio.emit('news_update', news_data)
            
            time.sleep(config.NEWS_UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"News error: {e}")
            time.sleep(60)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Flask routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/sensor_data')
def get_sensor_data():
    """Get current sensor readings"""
    return jsonify(sensor_data)

@app.route('/api/news')
def get_news():
    """Get latest news"""
    return jsonify(news_data)

@app.route('/api/health')
def health_check():
    """System health check"""
    return jsonify({
        'status': 'healthy',
        'hardware': HARDWARE_AVAILABLE,
        'voice_mode': voice_assistant.current_mode if voice_assistant else None,
        'whisper': WHISPER_AVAILABLE,
        'vosk': VOSK_AVAILABLE,
        'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
        'tts': TTS_ENGINE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/voice', methods=['POST'])
def voice_command():
    """Process voice command via API"""
    try:
        data = request.json
        command = data.get('command', '')
        
        if voice_assistant and command:
            if voice_assistant.openai_client:
                response = voice_assistant.process_with_chatgpt(command)
            else:
                response = voice_assistant.process_locally(command)
            
            actions = voice_assistant.extract_actions(response)
            if actions:
                voice_assistant.execute_actions(actions)
            
            return jsonify({
                'success': True,
                'response': response,
                'actions': actions
            })
        
        return jsonify({'success': False, 'error': 'Voice assistant not available'}), 503
            
    except Exception as e:
        logger.error(f"Voice API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings"""
    if request.method == 'GET':
        # Don't send API keys to frontend
        safe_settings = {
            'voice_mode': config.VOICE_MODE,
            'wake_words': config.WAKE_WORDS,
            'language': config.LANGUAGE,
            'tts_engine': config.TTS_ENGINE,
            'tts_rate': config.TTS_RATE,
            'tts_volume': config.TTS_VOLUME,
            'home_assistant_url': config.HOME_ASSISTANT_URL,
            'gpio_pins': config.GPIO_PINS,
            'has_openai_key': bool(config.OPENAI_API_KEY),
            'has_bing_key': bool(config.BING_API_KEY),
            'has_ha_token': bool(config.HOME_ASSISTANT_TOKEN)
        }
        return jsonify(safe_settings)
    
    else:  # POST
        try:
            new_settings = request.json
            
            # Save settings
            if config.save_settings(new_settings):
                # Restart voice assistant if needed
                global voice_assistant
                if voice_assistant:
                    voice_assistant.stop()
                    voice_assistant = VoiceAssistant()
                    threading.Thread(
                        target=voice_assistant.listen_continuous,
                        daemon=True
                    ).start()
                
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500
            
        except Exception as e:
            logger.error(f"Settings error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/auth/login')
def auth_login():
    """Initiate OAuth login with OpenAI"""
    # Generate state for security
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Build authorization URL
    params = {
        'client_id': OAUTH_CONFIG['client_id'],
        'redirect_uri': OAUTH_CONFIG['redirect_uri'],
        'response_type': 'code',
        'scope': OAUTH_CONFIG['scope'],
        'state': state
    }
    
    auth_url = OAUTH_CONFIG['authorize_url'] + '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
    
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback"""
    try:
        # Verify state
        if request.args.get('state') != session.get('oauth_state'):
            return jsonify({'error': 'Invalid state'}), 400
        
        # Exchange code for token
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        # Get access token
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': OAUTH_CONFIG['redirect_uri'],
            'client_id': OAUTH_CONFIG['client_id'],
            'client_secret': OAUTH_CONFIG['client_secret']
        }
        
        response = requests.post(OAUTH_CONFIG['token_url'], data=token_data)
        
        if response.status_code == 200:
            token_info = response.json()
            
            # Save token and user info
            session['user'] = {
                'access_token': token_info['access_token'],
                'authenticated_at': datetime.now().isoformat()
            }
            
            # Update OpenAI API key
            config.OPENAI_API_KEY = token_info['access_token']
            config.save_settings({'openai_api_key': token_info['access_token']})
            
            # Reinitialize voice assistant
            global voice_assistant
            if voice_assistant:
                voice_assistant.setup_voice()
            
            return redirect('/?auth=success')
        else:
            return redirect('/?auth=failed')
            
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        return redirect('/?auth=error')

@app.route('/auth/logout')
def auth_logout():
    """Logout user"""
    session.pop('user', None)
    session.pop('oauth_state', None)
    return redirect('/')

@app.route('/api/wifi_scan')
def wifi_scan():
    """Scan for WiFi networks"""
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
        current_network = {}
        
        for line in lines:
            if 'Cell' in line:
                if current_network and 'ssid' in current_network:
                    networks.append(current_network)
                current_network = {}
            elif 'ESSID:' in line:
                ssid = line.split('"')[1] if '"' in line else ''
                if ssid:
                    current_network['ssid'] = ssid
            elif 'Signal level=' in line:
                try:
                    signal = line.split('Signal level=')[1].split(' ')[0]
                    current_network['signal'] = signal
                except:
                    pass
            elif 'Encryption key:on' in line:
                current_network['encrypted'] = True
        
        if current_network and 'ssid' in current_network:
            networks.append(current_network)
        
        return jsonify(networks)
        
    except Exception as e:
        logger.error(f"WiFi scan error: {e}")
        return jsonify([])

@app.route('/api/wifi_connect', methods=['POST'])
def wifi_connect():
    """Connect to WiFi network"""
    try:
        data = request.json
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid:
            return jsonify({'success': False, 'error': 'SSID required'}), 400
        
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
        logger.error(f"WiFi connect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'data': 'Connected to BingHome'})
    
    # Send initial data
    emit('sensor_update', sensor_data)
    emit('news_update', news_data)
    
    # Send voice status
    if voice_assistant:
        emit('voice_status', {
            'available': True,
            'mode': voice_assistant.current_mode,
            'listening': voice_assistant.listening
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_sensor_data')
def handle_sensor_request():
    """Handle sensor data request"""
    emit('sensor_update', sensor_data)

@socketio.on('control_device')
def handle_device_control(data):
    """Handle device control commands"""
    device = data.get('device')
    action = data.get('action')
    value = data.get('value')
    
    logger.info(f"Device control: {device} - {action} - {value}")
    
    if voice_assistant:
        if device == 'lights':
            voice_assistant.control_lights(action == 'on')
        elif device == 'thermostat' and value:
            voice_assistant.set_temperature(float(value))
    
    emit('device_status', {
        'device': device,
        'status': 'success',
        'action': action
    })

# Main execution
def main():
    """Main application entry point"""
    global voice_assistant
    
    logger.info("=" * 50)
    logger.info("BingHome Smart Home System v2.1.0")
    logger.info(f"Hardware: {'Available' if HARDWARE_AVAILABLE else 'Simulated'}")
    logger.info("=" * 50)
    
    # Start sensor monitoring
    sensor_thread = threading.Thread(target=sensor_update_loop, daemon=True)
    sensor_thread.start()
    logger.info("✓ Sensor monitoring started")
    
    # Start news fetching
    if config.BING_API_KEY:
        news_thread = threading.Thread(target=news_update_loop, daemon=True)
        news_thread.start()
        logger.info("✓ News fetching started")
    
    # Initialize voice assistant
    try:
        voice_assistant = VoiceAssistant()
        if voice_assistant.current_mode:
            voice_thread = threading.Thread(
                target=voice_assistant.listen_continuous,
                daemon=True
            )
            voice_thread.start()
            logger.info(f"✓ Voice assistant started ({voice_assistant.current_mode})")
        else:
            logger.warning("⚠ Voice assistant not available")
    except Exception as e:
        logger.error(f"Voice assistant error: {e}")
    
    # Start Flask app
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting web server on http://0.0.0.0:{port}")
        logger.info("Press Ctrl+C to stop")
        
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        if voice_assistant:
            voice_assistant.stop()
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()
        logger.info("Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
