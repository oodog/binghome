#!/usr/bin/env python3
"""
BingHome Hub - Enhanced with Weather Integration and App Management
"""

import os
import sys
import json
import time
import threading
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask imports
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Import core modules with fallback
sys.path.insert(0, str(Path(__file__).parent))
try:
    from core.media import MediaController
    from core.news import NewsManager
    from core.timers import TimerManager
    from core.weather import WeatherService
    from core.device_discovery import DeviceDiscovery
    from core.google_photos import GooglePhotosService
    from core.cameras import camera_service, security_camera_service
    import bluetooth_utils
    logger.info("Core modules imported successfully")
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    MediaController = None
    NewsManager = None
    TimerManager = None
    WeatherService = None
    DeviceDiscovery = None
    GooglePhotosService = None
    camera_service = None
    security_camera_service = None

# Hardware imports with fallback
try:
    import RPi.GPIO as GPIO
    import adafruit_dht
    import board
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    logger.info("Raspberry Pi libraries not available - running in simulation mode")

# Socket.IO import with fallback
try:
    from flask_socketio import SocketIO, emit
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logger.warning("SocketIO not available")

# Configuration
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create required directories
for dir_path in [TEMPLATES_DIR, BASE_DIR / "static", BASE_DIR / "core"]:
    dir_path.mkdir(exist_ok=True)

# Flask app setup
app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'binghome-hub-secret-key')

if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
else:
    socketio = None

# ============================================
# BingHome Hub Class
# ============================================

class BingHomeHub:
    def __init__(self):
        self.settings = self.load_settings()
        self.running = True
        
        # Initialize controllers with settings
        self.initialize_controllers()
        
        # Setup hardware if available
        if RPI_AVAILABLE:
            self.setup_hardware()
        
        self.startup_complete = False
        
    def initialize_controllers(self):
        """Initialize all controller modules"""
        try:
            self.media = MediaController() if MediaController else self.create_fallback_media()
            self.news = NewsManager() if NewsManager else self.create_fallback_news()
            self.timers = TimerManager() if TimerManager else self.create_fallback_timers()
            self.weather = WeatherService(self.settings) if WeatherService else self.create_fallback_weather()
            self.devices = DeviceDiscovery(self.settings) if DeviceDiscovery else self.create_fallback_devices()
            # Initialize Google Photos with settings callbacks
            if GooglePhotosService:
                self.google_photos = GooglePhotosService(
                    lambda: self.settings,
                    lambda s: self.save_settings(s)
                )
            else:
                self.google_photos = None
            logger.info("Controllers initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing controllers: {e}")
            self.media = self.create_fallback_media()
            self.news = self.create_fallback_news()
            self.timers = self.create_fallback_timers()
            self.weather = self.create_fallback_weather()
            self.devices = self.create_fallback_devices()
    
    def create_fallback_media(self):
        class FallbackMedia:
            def __init__(self): self.is_playing = False; self.volume = 50
            def play(self, source=None): self.is_playing = True; return True
            def pause(self): self.is_playing = False; return True
            def stop(self): self.is_playing = False; return True
            def set_volume(self, level): self.volume = level; return True
        return FallbackMedia()
    
    def create_fallback_news(self):
        class FallbackNews:
            def fetch_news(self, category='general', count=10):
                return [{'title': 'BingHome Hub Running', 'description': 'System operational', 'url': '#'}]
        return FallbackNews()
    
    def create_fallback_timers(self):
        class FallbackTimers:
            def __init__(self): self.timers = {}
            def create_timer(self, duration, name="Timer"): return "timer_001"
            def get_timers(self): return []
        return FallbackTimers()
    
    def create_fallback_weather(self):
        class FallbackWeather:
            def __init__(self, settings=None):
                self.settings = settings or {}
            def get_comprehensive_weather(self, location=None):
                return {
                    'current': {'temp': 24, 'humidity': 62, 'condition': 'Partly Cloudy',
                               'description': 'Partly Cloudy', 'wind_speed': 12, 'location': 'Gold Coast, QLD'},
                    'forecast': [{'date': '2024-01-01', 'temp_min': 18, 'temp_max': 26, 'condition': 'Sunny', 'day_name': 'Today'}],
                    'radar': {'available': True, 'url': 'https://data.theweather.com.au/access/animators/radar/?lt=wzstate&user=10545v3&lc=qld'}
                }
            def get_current(self, location=None):
                return self.get_comprehensive_weather(location)['current']
            def update_settings(self, settings): pass
        return FallbackWeather()

    def create_fallback_devices(self):
        class FallbackDevices:
            def __init__(self, settings=None):
                self.settings = settings or {}
            def scan_all_devices(self):
                return {'devices': {'wifi': [], 'bluetooth': [], 'home_assistant': []}, 'summary': {'total': 0}}
            def get_all_devices(self):
                return {'devices': {'wifi': [], 'bluetooth': [], 'home_assistant': []}, 'summary': {'total': 0}}
            def control_device(self, device_type, device_id, action, **kwargs):
                return {'success': False, 'error': 'Device control not available'}
            def update_settings(self, settings): pass
        return FallbackDevices()
        
    def load_settings(self):
        """Load settings from JSON file"""
        default_settings = {
            "temp_offset": 0,
            "google_photos_connected": False,
            "google_photos_access_token": "",
            "google_photos_refresh_token": "",
            "google_photos_album": "",
            "google_photos_interval": 10,
            "voice_provider": "local",
            "voice_enabled": True,
            "wake_words": ["hey bing", "okay bing"],
            "weather_source": "openweather",
            "weather_location": "Gold Coast, QLD",
            "weather_api_key": "",
            "openai_api_key": "",
            "bing_api_key": "",
            "home_assistant_url": "http://localhost:8123",
            "home_assistant_token": "",
            "kiosk_mode": False,
            "auto_start_browser": False,
            "display_timeout": 0,
            "apps": {
                "netflix": {"enabled": True, "url": "https://www.netflix.com"},
                "prime_video": {"enabled": True, "url": "https://www.primevideo.com"},
                "youtube": {"enabled": True, "url": "https://www.youtube.com/tv"},
                "disney_plus": {"enabled": True, "url": "https://www.disneyplus.com"},
                "xbox_cloud": {"enabled": True, "url": "https://www.xbox.com/play"},
                "steam": {"enabled": True, "url": "https://store.steampowered.com"},
                "spotify": {"enabled": True, "url": "https://open.spotify.com"},
                "apple_music": {"enabled": True, "url": "https://music.apple.com"},
                "google_photos": {"enabled": True, "url": "https://photos.google.com"}
            },
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
                # Merge with defaults
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
            
            # Update weather service with new settings
            if hasattr(self.weather, 'update_settings'):
                self.weather.update_settings(settings)
            
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def setup_hardware(self):
        """Initialize hardware components"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            self.sensors = {}
            
            # DHT22 sensor
            dht_pin = self.settings["gpio_pins"]["dht22"]
            self.sensors['dht22'] = adafruit_dht.DHT22(getattr(board, f'D{dht_pin}'), use_pulseio=False)
            
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
            self.sensors = {}
    
    def read_sensors(self):
        """Read all sensor data"""
        import random

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
            if hasattr(self, 'sensors'):
                # Read DHT22 with retry logic
                if 'dht22' in self.sensors:
                    dht = self.sensors['dht22']
                    max_retries = 3
                    retry_delay = 2

                    for attempt in range(max_retries):
                        try:
                            # DHT sensors need time between reads
                            temperature = dht.temperature
                            humidity = dht.humidity

                            # Validate readings
                            if temperature is not None and humidity is not None:
                                # Apply calibration offset
                                temp_offset = self.settings.get('temp_offset', 0)
                                data['temperature'] = round(temperature + temp_offset, 1)
                                data['humidity'] = round(humidity, 1)
                                logger.debug(f"DHT22 read successful: {temperature}°C (raw) -> {data['temperature']}°C (calibrated), {humidity}%")
                                break
                            else:
                                logger.warning(f"DHT22 returned None values (attempt {attempt + 1}/{max_retries})")

                        except RuntimeError as e:
                            # DHT sensors often throw RuntimeError for checksum/timing issues
                            logger.warning(f"DHT22 read failed (attempt {attempt + 1}/{max_retries}): {e}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                        except Exception as e:
                            logger.error(f"DHT22 unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)

                    # If all retries failed, log final error
                    if data['temperature'] is None or data['humidity'] is None:
                        logger.error("DHT22 sensor failed to read after all retries. Check wiring and power.")

                # Read gas sensor
                if 'gas_pin' in self.sensors:
                    try:
                        gas_state = GPIO.input(self.sensors['gas_pin'])
                        data['gas_detected'] = bool(gas_state)
                        data['air_quality'] = 'poor' if gas_state else 'good'
                    except Exception as e:
                        logger.error(f"Gas sensor read error: {e}")

                # Read light sensor
                if 'light_pin' in self.sensors:
                    try:
                        light_state = GPIO.input(self.sensors['light_pin'])
                        data['light_level'] = 'bright' if light_state else 'dark'
                    except Exception as e:
                        logger.error(f"Light sensor read error: {e}")

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
            result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                                  capture_output=True, text=True)
            if 'inet ' in result.stdout:
                status['ethernet']['connected'] = True
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        status['ethernet']['ip'] = line.split()[1].split('/')[0]
                        break
                status['primary'] = 'ethernet'
            else:
                # Check WiFi as fallback
                try:
                    result = subprocess.run(['iwconfig', 'wlan0'], 
                                          capture_output=True, text=True)
                    if 'ESSID:' in result.stdout and 'off/any' not in result.stdout:
                        status['wifi']['connected'] = True
                        status['primary'] = 'wifi'
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Network status error: {e}")
        
        return status

# Initialize the system
binghome = BingHomeHub()

# ============================================
# Flask Routes
# ============================================

@app.route('/')
def index():
    """Main hub interface - customizable dashboard"""
    try:
        return render_template('dashboard.html', settings=binghome.settings)
    except:
        try:
            return render_template('hub_v3.html', settings=binghome.settings)
        except:
            try:
                return render_template('hub_enhanced.html', settings=binghome.settings)
            except:
                try:
                    return render_template('hub.html', settings=binghome.settings)
                except:
                    try:
                        return render_template('index.html', settings=binghome.settings)
                    except:
                        # Fallback HTML if no templates exist
                        return f'''
                        <!DOCTYPE html>
                        <html><head><title>BingHome Hub</title>
                        <style>body{{background:#000;color:#fff;font-family:Arial;text-align:center;padding:50px;}}
                        h1{{color:#00ff88;}}</style></head>
                        <body><h1>BingHome Hub</h1><p>System Running</p><a href="/settings">Settings</a></body></html>
                        '''

@app.route('/settings')
def settings_page():
    """Settings page"""
    try:
        return render_template('settings.html', settings=binghome.settings)
    except Exception as e:
        logger.error(f"Settings template error: {e}")
        return f"<h1>Settings</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/bluetooth')
def bluetooth_page():
    """Bluetooth settings page"""
    return render_template('bluetooth_settings.html')

@app.route('/system')
def system_page():
    """System status page"""
    try:
        sensor_data = binghome.read_sensors()
        system_info = {
            'cpu_temp': 45.0,
            'memory_used_percent': 35,
            'disk_used_percent': 42,
            'uptime': '2 days, 5 hours'
        }
        return render_template('system_status.html', 
                             sensor_data=sensor_data,
                             system_info=system_info)
    except Exception as e:
        logger.error(f"System template error: {e}")
        return f"<h1>System Status</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/wifi')
def wifi_page():
    """WiFi settings page"""
    try:
        return render_template('wifi_settings.html')
    except Exception as e:
        return f"<h1>WiFi Settings</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/devices')
def devices_page():
    """Devices management page"""
    try:
        return render_template('devices.html')
    except Exception as e:
        logger.error(f"Devices template error: {e}")
        return f"<h1>Devices</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/routines')
def routines_page():
    """Routines/Automations page"""
    try:
        return render_template('routines.html')
    except Exception as e:
        logger.error(f"Routines template error: {e}")
        return f"<h1>Routines</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/shopping')
def shopping_page():
    """Shopping list page"""
    try:
        return render_template('shopping.html')
    except Exception as e:
        logger.error(f"Shopping template error: {e}")
        return f"<h1>Shopping List</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/calendar')
def calendar_page():
    """Calendar page"""
    try:
        return render_template('calendar.html')
    except Exception as e:
        logger.error(f"Calendar template error: {e}")
        return f"<h1>Calendar</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/intercom')
def intercom_page():
    """Intercom/Broadcast page"""
    try:
        return render_template('intercom.html')
    except Exception as e:
        logger.error(f"Intercom template error: {e}")
        return f"<h1>Intercom</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route("/app/<app_name>")
def app_viewer(app_name):
    """View external apps in iframe with navigation overlay"""
    apps = {
        "youtube": {"name": "YouTube", "url": "https://www.youtube.com/tv"},
        "netflix": {"name": "Netflix", "url": "https://www.netflix.com/browse"},
        "spotify": {"name": "Spotify", "url": "https://open.spotify.com"},
        "prime": {"name": "Prime Video", "url": "https://www.primevideo.com"},
        "xbox": {"name": "Xbox Cloud", "url": "https://www.xbox.com/play"},
        "disney_plus": {"name": "Disney+", "url": "https://www.disneyplus.com"}
    }
    if app_name in apps:
        return render_template("app_viewer.html", app_name=apps[app_name]["name"], app_url=apps[app_name]["url"])
    return redirect("/")

@app.route('/hub')
def hub_v3_page():
    """Enhanced hub page"""
    try:
        return render_template('hub_v3.html')
    except Exception as e:
        logger.error(f"Hub v3 template error: {e}")
        return redirect('/')

@app.route('/timers')
def timers_page():
    """Timers, Alarms, and Stopwatch page"""
    try:
        return render_template('timers.html')
    except Exception as e:
        logger.error(f"Timers template error: {e}")
        return f"<h1>Timers</h1><p>Template error: {e}</p><a href='/'>Back</a>"

@app.route('/dashboard')
def dashboard_page():
    """Customizable dashboard page"""
    try:
        return render_template('dashboard.html', settings=binghome.settings)
    except Exception as e:
        logger.error(f"Dashboard template error: {e}")
        return redirect('/')

@app.route('/camera-settings')
def camera_settings_page():
    """Camera settings page for Pi/USB cameras"""
    try:
        return render_template('camera_settings.html')
    except Exception as e:
        logger.error(f"Camera settings template error: {e}")
        return f"<h1>Camera Settings</h1><p>Template error: {e}</p><a href='/settings'>Back</a>"

@app.route('/security-cameras')
def security_cameras_page():
    """Security cameras page for RTSP streams"""
    try:
        return render_template('security_cameras.html')
    except Exception as e:
        logger.error(f"Security cameras template error: {e}")
        return f"<h1>Security Cameras</h1><p>Template error: {e}</p><a href='/settings'>Back</a>"

# ============================================
# API Routes
# ============================================

@app.route('/api/sensor_data')
def api_sensor_data():
    """Get current sensor readings"""
    try:
        data = binghome.read_sensors()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Sensor API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network_status')
def api_network_status():
    """Get network connection status"""
    try:
        status = binghome.get_network_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Network API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather')
def api_weather():
    """Get basic weather information (legacy endpoint)"""
    try:
        current = binghome.weather.get_current()
        forecast = binghome.weather.get_forecast() if hasattr(binghome.weather, 'get_forecast') else []
        return jsonify({
            'current': current,
            'forecast': forecast
        })
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/comprehensive')
def api_weather_comprehensive():
    """Get comprehensive weather information"""
    try:
        if hasattr(binghome.weather, 'get_comprehensive_weather'):
            data = binghome.weather.get_comprehensive_weather()
            return jsonify(data)
        else:
            # Fallback to basic weather
            return api_weather()
    except Exception as e:
        logger.error(f"Comprehensive weather API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/test', methods=['POST'])
def api_weather_test():
    """Test weather configuration"""
    try:
        test_settings = request.get_json() or {}
        
        # Create temporary weather service with test settings
        if WeatherService:
            temp_weather = WeatherService(test_settings)
            current = temp_weather.get_current()
            radar = temp_weather.get_radar_info() if hasattr(temp_weather, 'get_radar_info') else {'available': False}
            
            return jsonify({
                'success': True,
                'current': current,
                'radar': radar
            })
        else:
            # Fallback test
            return jsonify({
                'success': True,
                'current': {
                    'temp': 24,
                    'humidity': 62,
                    'condition': 'Partly Cloudy',
                    'description': 'Test Weather Data',
                    'wind_speed': 12,
                    'location': test_settings.get('weather_location', 'Test Location'),
                    'radar_available': test_settings.get('weather_source') == 'qld_radar'
                }
            })
    except Exception as e:
        logger.error(f"Weather test API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if request.method == 'GET':
        try:
            # Hide sensitive keys in response
            safe_settings = binghome.settings.copy()
            for key in ['openai_api_key', 'weather_api_key', 'bing_api_key', 'home_assistant_token', 
                       'google_photos_access_token', 'google_photos_refresh_token']:
                if key in safe_settings and safe_settings[key]:
                    safe_settings[key + '_configured'] = True
                    safe_settings[key] = ''
            return jsonify(safe_settings)
        except Exception as e:
            logger.error(f"Settings GET error: {e}")
            return jsonify({'error': str(e)}), 500
    
    try:
        new_settings = request.get_json() or {}
        
        # Merge with existing settings
        merged_settings = binghome.settings.copy()
        for key, value in new_settings.items():
            if value or key not in merged_settings:
                merged_settings[key] = value
        
        if binghome.save_settings(merged_settings):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500
    except Exception as e:
        logger.error(f"Settings POST error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    """Get news feed"""
    try:
        news = binghome.news.fetch_news()
        return jsonify(news)
    except Exception as e:
        logger.error(f"News API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/timers')
def api_timers():
    """Get active timers"""
    try:
        timers = binghome.timers.get_timers()
        return jsonify(timers)
    except Exception as e:
        logger.error(f"Timers API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/timer', methods=['POST'])
def api_timer():
    """Create a timer"""
    try:
        data = request.get_json() or {}
        duration = data.get('duration', 60)
        name = data.get('name', 'Timer')
        
        timer_id = binghome.timers.create_timer(duration, name)
        
        return jsonify({
            'success': True,
            'timer_id': timer_id
        })
    except Exception as e:
        logger.error(f"Timer creation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        elif action == 'volume':
            data = request.get_json() or {}
            level = data.get('level', 50)
            binghome.media.set_volume(level)
        else:
            return jsonify({'success': False, 'error': 'Unknown action'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Media control error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/google_photos/auth')
def google_photos_auth():
    """Initiate Google Photos OAuth flow"""
    try:
        # Google OAuth configuration
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        
        # Build redirect URI - ensure HTTPS for ngrok
        host = request.host
        scheme = 'https' if 'ngrok' in host else request.scheme
        redirect_uri = f'{scheme}://{host}/api/google_photos/callback'
        
        logger.info(f"OAuth initiated - Host: {host}, Scheme: {scheme}, Redirect URI: {redirect_uri}")
        
        # Check if accessing via IP address (which Google doesn't allow)
        import re
        if re.match(r'^https?://\d+\.\d+\.\d+\.\d+', request.host_url):
            return """<html><body style='font-family: sans-serif; padding: 20px;'>
            <h2>⚠️ Cannot Use IP Address</h2>
            <p>Google OAuth requires a domain name, not an IP address.</p>
            <h3>Please access BingHome using one of these instead:</h3>
            <ul>
                <li><strong>Hostname:</strong> <a href='http://raspberrypi.local:5000/settings'>http://raspberrypi.local:5000</a></li>
                <li><strong>Localhost:</strong> <a href='http://localhost:5000/settings'>http://localhost:5000</a> (if local)</li>
                <li><strong>Custom domain:</strong> Set up a free domain at <a href='https://www.duckdns.org' target='_blank'>duckdns.org</a></li>
            </ul>
            <p>See <a href='https://github.com/oodog/binghome/blob/master/GOOGLE_PHOTOS_SETUP.md' target='_blank'>GOOGLE_PHOTOS_SETUP.md</a> for details.</p>
            <button onclick='window.close()'>Close</button>
            </body></html>"""
        
        if not client_id:
            return """<html><body style='font-family: sans-serif; padding: 20px;'>
            <h2>Google Photos Setup Required</h2>
            <p>Please set up Google OAuth credentials:</p>
            <ol>
                <li>Go to <a href='https://console.cloud.google.com/apis/credentials' target='_blank'>Google Cloud Console</a></li>
                <li>Create OAuth 2.0 Client ID</li>
                <li>Add this redirect URI: <code>""" + redirect_uri + """</code></li>
                <li>Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file</li>
            </ol>
            <p><strong>Note:</strong> Make sure you're accessing BingHome via hostname (not IP address)!</p>
            <button onclick='window.close()'>Close</button>
            </body></html>"""
        
        auth_url = (
            'https://accounts.google.com/o/oauth2/v2/auth?'
            f'client_id={client_id}&'
            f'redirect_uri={redirect_uri}&'
            'response_type=code&'
            'scope=https://www.googleapis.com/auth/photoslibrary.readonly&'
            'access_type=offline&'
            'prompt=consent'
        )
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Google Photos auth error: {e}")
        return f"<html><body><h2>Error</h2><p>{str(e)}</p><button onclick='window.close()'>Close</button></body></html>"

@app.route('/api/google_photos/callback')
def google_photos_callback():
    """Handle Google Photos OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return "<html><body><h2>Authorization Failed</h2><p>No code received</p><button onclick='window.close()'>Close</button></body></html>"
        
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
        
        # Build redirect URI - must match exactly what was used in auth request
        host = request.host
        scheme = 'https' if 'ngrok' in host else request.scheme
        redirect_uri = f'{scheme}://{host}/api/google_photos/callback'
        
        logger.info(f"OAuth callback - Host: {host}, Scheme: {scheme}, Redirect URI: {redirect_uri}")
        
        # Exchange code for tokens
        import requests
        token_response = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        })
        
        if token_response.status_code == 200:
            tokens = token_response.json()
            settings = binghome.settings.copy()
            settings['google_photos_connected'] = True
            settings['google_photos_access_token'] = tokens.get('access_token', '')
            settings['google_photos_refresh_token'] = tokens.get('refresh_token', '')
            binghome.save_settings(settings)
            
            return """<html><body>
            <h2>✅ Successfully Connected to Google Photos!</h2>
            <p>You can now close this window and return to settings.</p>
            <script>setTimeout(() => window.close(), 2000);</script>
            </body></html>"""
        else:
            return f"<html><body><h2>Token Exchange Failed</h2><p>{token_response.text}</p><button onclick='window.close()'>Close</button></body></html>"
    except Exception as e:
        logger.error(f"Google Photos callback error: {e}")
        return f"<html><body><h2>Error</h2><p>{str(e)}</p><button onclick='window.close()'>Close</button></body></html>"

@app.route('/api/google_photos/status')
def google_photos_status():
    """Check Google Photos connection status"""
    try:
        connected = binghome.settings.get('google_photos_connected', False)
        return jsonify({'connected': connected})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/google_photos/albums')
def google_photos_albums():
    """Get list of Google Photos albums"""
    try:
        # Use the GooglePhotosService with automatic token refresh
        if binghome.google_photos:
            result = binghome.google_photos.get_albums()
            if result['success']:
                logger.info(f"Found {len(result.get('albums', []))} albums")
                return jsonify(result)
            else:
                status_code = result.get('status_code', 500)
                return jsonify(result), status_code
        else:
            # Fallback to direct API call
            import requests
            access_token = binghome.settings.get('google_photos_access_token', '')
            
            if not access_token:
                return jsonify({'success': False, 'error': 'Not connected'}), 401
            
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get('https://photoslibrary.googleapis.com/v1/albums', headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                albums = data.get('albums', [])
                return jsonify({'success': True, 'albums': albums})
            else:
                return jsonify({'success': False, 'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        logger.error(f"Google Photos albums error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/google_photos/photos')
def google_photos_photos():
    """Get photos from selected album"""
    try:
        album_id = binghome.settings.get('google_photos_album', '')
        
        # Use the GooglePhotosService with automatic token refresh
        if binghome.google_photos:
            if album_id:
                result = binghome.google_photos.get_photos_from_album(album_id)
            else:
                result = binghome.google_photos.get_recent_photos()
            
            if result['success']:
                return jsonify(result)
            else:
                status_code = result.get('status_code', 500)
                return jsonify(result), status_code
        else:
            # Fallback to direct API call
            import requests
            access_token = binghome.settings.get('google_photos_access_token', '')
            
            if not access_token:
                return jsonify({'success': False, 'error': 'Not connected'}), 401
            
            if not album_id:
                return jsonify({'success': False, 'error': 'No album selected'}), 400
            
            headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
            response = requests.post(
                'https://photoslibrary.googleapis.com/v1/mediaItems:search',
                headers=headers,
                json={'albumId': album_id, 'pageSize': 100}
            )
            
            if response.status_code == 200:
                data = response.json()
                media_items = data.get('mediaItems', [])
                photos = [{
                    'id': item['id'],
                    'url': item['baseUrl'] + '=w1920-h1080',
                    'filename': item.get('filename', ''),
                    'mimeType': item.get('mimeType', '')
                } for item in media_items if item.get('mimeType', '').startswith('image/')]
                return jsonify({'success': True, 'photos': photos})
            else:
                return jsonify({'success': False, 'error': 'Failed to fetch photos'}), response.status_code
    except Exception as e:
        logger.error(f"Google Photos photos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/google_photos/disconnect', methods=['POST'])
def google_photos_disconnect():
    """Disconnect Google Photos"""
    try:
        settings = binghome.settings.copy()
        settings['google_photos_connected'] = False
        settings['google_photos_access_token'] = ''
        settings['google_photos_refresh_token'] = ''
        settings['google_photos_album'] = ''
        binghome.save_settings(settings)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Google Photos disconnect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/google_photos/shared')
def google_photos_shared():
    """Get photos from a shared Google Photos album link"""
    try:
        from core.google_photos import fetch_shared_album_photos

        # Get shared URL from settings or query param
        shared_url = request.args.get('url') or binghome.settings.get('google_photos_shared_url', '')

        if not shared_url:
            return jsonify({'success': False, 'error': 'No shared album URL configured', 'photos': []})

        result = fetch_shared_album_photos(shared_url)
        return jsonify(result)
    except ImportError:
        return jsonify({'success': False, 'error': 'Google Photos module not available', 'photos': []})
    except Exception as e:
        logger.error(f"Shared album error: {e}")
        return jsonify({'success': False, 'error': str(e), 'photos': []}), 500

@app.route('/api/google_photos/shared/test', methods=['POST'])
def google_photos_shared_test():
    """Test a shared album URL"""
    try:
        from core.google_photos import fetch_shared_album_photos

        data = request.get_json() or {}
        shared_url = data.get('url', '')

        if not shared_url:
            return jsonify({'success': False, 'error': 'No URL provided'})

        result = fetch_shared_album_photos(shared_url)

        if result['success']:
            return jsonify({
                'success': True,
                'count': result.get('count', len(result.get('photos', []))),
                'message': f"Found {result.get('count', 0)} photos"
            })
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f"Shared album test error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices')
def api_devices():
    """Get all discovered devices"""
    try:
        devices_data = binghome.devices.get_all_devices()
        return jsonify(devices_data)
    except Exception as e:
        logger.error(f"Devices API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/scan', methods=['POST'])
def api_devices_scan():
    """Scan for all devices"""
    try:
        devices_data = binghome.devices.scan_all_devices()
        return jsonify(devices_data)
    except Exception as e:
        logger.error(f"Device scan error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/control', methods=['POST'])
def api_devices_control():
    """Control a device"""
    try:
        data = request.get_json() or {}
        device_type = data.get('device_type')
        device_id = data.get('device_id')
        action = data.get('action')

        if not all([device_type, device_id, action]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Pass additional parameters
        kwargs = {k: v for k, v in data.items() if k not in ['device_type', 'device_id', 'action']}

        result = binghome.devices.control_device(device_type, device_id, action, **kwargs)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Device control error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/shopping', methods=['GET', 'POST'])
def api_shopping():
    """Shopping list API"""
    shopping_file = BASE_DIR / 'data' / 'shopping.json'
    shopping_file.parent.mkdir(exist_ok=True)

    if request.method == 'GET':
        try:
            if shopping_file.exists():
                with open(shopping_file) as f:
                    data = json.load(f)
                return jsonify(data)
            return jsonify({'items': []})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            with open(shopping_file, 'w') as f:
                json.dump(data, f)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/routines', methods=['GET', 'POST'])
def api_routines():
    """Routines/Automations API"""
    routines_file = BASE_DIR / 'data' / 'routines.json'
    routines_file.parent.mkdir(exist_ok=True)

    if request.method == 'GET':
        try:
            if routines_file.exists():
                with open(routines_file) as f:
                    data = json.load(f)
                return jsonify(data)
            return jsonify({'routines': []})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            # Load existing routines
            routines = []
            if routines_file.exists():
                with open(routines_file) as f:
                    routines = json.load(f).get('routines', [])

            # Add new routine
            data['id'] = f"routine_{int(time.time())}"
            data['created'] = datetime.now().isoformat()
            routines.append(data)

            with open(routines_file, 'w') as f:
                json.dump({'routines': routines}, f)
            return jsonify({'success': True, 'id': data['id']})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/list')
def api_photos_list():
    """List local photos for slideshow"""
    photos_dir = BASE_DIR / 'static' / 'photos'
    photos_dir.mkdir(parents=True, exist_ok=True)

    photos = []
    supported = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    try:
        for file_path in photos_dir.rglob('*'):
            if file_path.suffix.lower() in supported:
                photos.append({
                    'url': f'/static/photos/{file_path.relative_to(photos_dir)}',
                    'name': file_path.name
                })
        return jsonify({'photos': photos})
    except Exception as e:
        return jsonify({'photos': [], 'error': str(e)})

@app.route('/api/intercom/announce', methods=['POST'])
def api_intercom_announce():
    """Text-to-speech announcement"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '')
        devices = data.get('devices', ['all'])

        if not message:
            return jsonify({'success': False, 'error': 'No message provided'})

        # Use TTS to speak the message
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', binghome.settings.get('tts_rate', 150))
            engine.setProperty('volume', binghome.settings.get('tts_volume', 0.9))
            engine.say(message)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            # Fallback to espeak
            subprocess.run(['espeak', message], capture_output=True)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/intercom/broadcast', methods=['POST'])
def api_intercom_broadcast():
    """Audio broadcast to devices"""
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file'})

        audio = request.files['audio']
        devices = json.loads(request.form.get('devices', '["all"]'))

        # Save audio temporarily
        audio_path = BASE_DIR / 'data' / 'broadcast.wav'
        audio_path.parent.mkdir(exist_ok=True)
        audio.save(str(audio_path))

        # Play audio
        try:
            subprocess.run(['aplay', str(audio_path)], capture_output=True)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/events')
def api_calendar_events():
    """Get calendar events"""
    # Placeholder - would integrate with Google Calendar or iCloud
    return jsonify({'events': []})

@app.route('/api/health')
def api_health():
    """System health check"""
    try:
        return jsonify({
            'status': 'healthy' if binghome.running else 'stopped',
            'hardware': RPI_AVAILABLE,
            'weather_source': binghome.settings.get('weather_source', 'openweather'),
            'apps_configured': len(binghome.settings.get('apps', {})),
            'startup_complete': binghome.startup_complete,
            'timestamp': datetime.now().isoformat(),
            'version': '3.0.0'
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """Restart the system"""
    try:
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'binghome'])
        return jsonify({'success': True, 'message': 'Restarting BingHome...'})
    except Exception as e:
        logger.error(f"Restart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# Bluetooth API Routes
# ============================================

@app.route('/api/bluetooth/paired')
def api_bluetooth_paired():
    """Get list of paired Bluetooth devices"""
    try:
        devices = bluetooth_utils.get_paired_devices()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logger.error(f"Bluetooth paired error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bluetooth/scan', methods=['POST'])
def api_bluetooth_scan():
    """Scan for nearby Bluetooth devices"""
    try:
        devices = bluetooth_utils.scan_for_devices()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logger.error(f"Bluetooth scan error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bluetooth/pair', methods=['POST'])
def api_bluetooth_pair():
    """Pair with a Bluetooth device"""
    try:
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'success': False, 'error': 'MAC address required'}), 400
        
        success, message = bluetooth_utils.pair_device(mac)
        return jsonify({'success': success, 'message': message if success else None, 'error': message if not success else None})
    except Exception as e:
        logger.error(f"Bluetooth pair error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bluetooth/connect', methods=['POST'])
def api_bluetooth_connect():
    """Connect to a paired Bluetooth device"""
    try:
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'success': False, 'error': 'MAC address required'}), 400
        
        success, message = bluetooth_utils.connect_device(mac)
        return jsonify({'success': success, 'message': message if success else None, 'error': message if not success else None})
    except Exception as e:
        logger.error(f"Bluetooth connect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bluetooth/disconnect', methods=['POST'])
def api_bluetooth_disconnect():
    """Disconnect a Bluetooth device"""
    try:
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'success': False, 'error': 'MAC address required'}), 400
        
        success, message = bluetooth_utils.disconnect_device(mac)
        return jsonify({'success': success, 'message': message if success else None, 'error': message if not success else None})
    except Exception as e:
        logger.error(f"Bluetooth disconnect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bluetooth/remove', methods=['POST'])
def api_bluetooth_remove():
    """Remove/unpair a Bluetooth device"""
    try:
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'success': False, 'error': 'MAC address required'}), 400

        success, message = bluetooth_utils.remove_device(mac)
        return jsonify({'success': success, 'message': message if success else None, 'error': message if not success else None})
    except Exception as e:
        logger.error(f"Bluetooth remove error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# Camera API Routes
# ============================================

@app.route('/api/cameras/detect')
def api_cameras_detect():
    """Detect local cameras (Pi Camera, USB)"""
    try:
        if camera_service:
            cameras = camera_service.detect_cameras()
            return jsonify({'cameras': cameras})
        return jsonify({'cameras': [], 'error': 'Camera service not available'})
    except Exception as e:
        logger.error(f"Camera detect error: {e}")
        return jsonify({'cameras': [], 'error': str(e)}), 500

@app.route('/api/cameras/snapshot')
def api_cameras_snapshot():
    """Capture snapshot from a camera"""
    try:
        camera_id = request.args.get('camera_id')
        if camera_service:
            snapshot_path, error = camera_service.get_camera_snapshot(camera_id)
            if snapshot_path:
                # Copy to static folder for web access
                import shutil
                static_path = BASE_DIR / 'static' / 'snapshots'
                static_path.mkdir(parents=True, exist_ok=True)
                dest_path = static_path / 'camera_snapshot.jpg'
                shutil.copy(snapshot_path, dest_path)
                return jsonify({'success': True, 'url': '/static/snapshots/camera_snapshot.jpg'})
            return jsonify({'success': False, 'error': error or 'Failed to capture'})
        return jsonify({'success': False, 'error': 'Camera service not available'})
    except Exception as e:
        logger.error(f"Camera snapshot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cameras/stream/start', methods=['POST'])
def api_cameras_stream_start():
    """Start camera stream"""
    try:
        camera_id = request.args.get('camera_id')
        if camera_service:
            success, message = camera_service.start_mjpeg_stream(camera_id)
            return jsonify({'success': success, 'message': message})
        return jsonify({'success': False, 'error': 'Camera service not available'})
    except Exception as e:
        logger.error(f"Camera stream start error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cameras/stream/stop', methods=['POST'])
def api_cameras_stream_stop():
    """Stop camera stream"""
    try:
        if camera_service:
            success, message = camera_service.stop_stream()
            return jsonify({'success': success, 'message': message})
        return jsonify({'success': False, 'error': 'Camera service not available'})
    except Exception as e:
        logger.error(f"Camera stream stop error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/security-cameras', methods=['GET', 'POST'])
def api_security_cameras():
    """Get or add security cameras"""
    if request.method == 'GET':
        try:
            if security_camera_service:
                cameras = security_camera_service.get_cameras()
                return jsonify({'cameras': cameras})
            return jsonify({'cameras': []})
        except Exception as e:
            logger.error(f"Security cameras GET error: {e}")
            return jsonify({'cameras': [], 'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            name = data.get('name')
            rtsp_url = data.get('rtsp_url')
            vendor = data.get('vendor', 'generic')

            if not name or not rtsp_url:
                return jsonify({'success': False, 'error': 'Name and RTSP URL required'}), 400

            if security_camera_service:
                camera = security_camera_service.add_camera(name, rtsp_url, vendor)
                return jsonify({'success': True, 'camera': camera})
            return jsonify({'success': False, 'error': 'Security camera service not available'})
        except Exception as e:
            logger.error(f"Security cameras POST error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/security-cameras/<camera_id>', methods=['GET', 'DELETE', 'PUT'])
def api_security_camera(camera_id):
    """Get, update, or delete a specific security camera"""
    if request.method == 'GET':
        try:
            if security_camera_service:
                camera = security_camera_service.get_camera(camera_id)
                if camera:
                    return jsonify({'success': True, 'camera': camera})
                return jsonify({'success': False, 'error': 'Camera not found'}), 404
            return jsonify({'success': False, 'error': 'Service not available'})
        except Exception as e:
            logger.error(f"Security camera GET error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            if security_camera_service:
                security_camera_service.remove_camera(camera_id)
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Service not available'})
        except Exception as e:
            logger.error(f"Security camera DELETE error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'PUT':
        try:
            data = request.get_json() or {}
            if security_camera_service:
                camera = security_camera_service.update_camera(camera_id, **data)
                if camera:
                    return jsonify({'success': True, 'camera': camera})
                return jsonify({'success': False, 'error': 'Camera not found'}), 404
            return jsonify({'success': False, 'error': 'Service not available'})
        except Exception as e:
            logger.error(f"Security camera PUT error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/security-cameras/<camera_id>/snapshot')
def api_security_camera_snapshot(camera_id):
    """Capture snapshot from security camera"""
    try:
        if security_camera_service:
            camera = security_camera_service.get_camera(camera_id)
            if camera:
                # Capture thumbnail from RTSP stream
                static_path = BASE_DIR / 'static' / 'snapshots'
                static_path.mkdir(parents=True, exist_ok=True)
                output_path = str(static_path / f'security_{camera_id}.jpg')

                result = security_camera_service.capture_thumbnail(camera['rtsp_url'], output_path)
                if result:
                    return jsonify({'success': True, 'url': f'/static/snapshots/security_{camera_id}.jpg'})
                return jsonify({'success': False, 'error': 'Failed to capture snapshot'})
            return jsonify({'success': False, 'error': 'Camera not found'}), 404
        return jsonify({'success': False, 'error': 'Service not available'})
    except Exception as e:
        logger.error(f"Security camera snapshot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/security-cameras/test', methods=['POST'])
def api_security_cameras_test():
    """Test RTSP stream connection"""
    try:
        data = request.get_json() or {}
        rtsp_url = data.get('rtsp_url')

        if not rtsp_url:
            return jsonify({'success': False, 'error': 'RTSP URL required'}), 400

        if security_camera_service:
            success, message = security_camera_service.test_rtsp_stream(rtsp_url)
            return jsonify({'success': success, 'message': message if success else None, 'error': message if not success else None})
        return jsonify({'success': False, 'error': 'Service not available'})
    except Exception as e:
        logger.error(f"Security camera test error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/security-cameras/discover')
def api_security_cameras_discover():
    """Discover cameras on the network"""
    try:
        if security_camera_service:
            cameras = security_camera_service.discover_cameras()
            return jsonify({'cameras': cameras})
        return jsonify({'cameras': [], 'error': 'Service not available'})
    except Exception as e:
        logger.error(f"Security camera discover error: {e}")
        return jsonify({'cameras': [], 'error': str(e)}), 500

# ============================================
# WebSocket Events (if available)
# ============================================

if SOCKETIO_AVAILABLE and socketio:
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"Client connected: {request.sid}")
        try:
            emit('status', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Socket connect error: {e}")

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")

    @socketio.on('voice_command')
    def handle_voice_command(data):
        try:
            command = data.get('command', '')
            if command:
                # Process voice command (basic implementation)
                response = f"Received command: {command}"
                
                emit('voice_response', {
                    'command': command,
                    'response': response,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Voice command error: {e}")
            emit('error', {'message': str(e)})

    @socketio.on('request_sensor_data')
    def handle_sensor_request():
        try:
            data = binghome.read_sensors()
            emit('sensor_update', data)
        except Exception as e:
            logger.error(f"Sensor request error: {e}")

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    try:
        return render_template('404.html'), 404
    except:
        return "<h1>404 - Page Not Found</h1><a href='/'>Home</a>", 404

@app.errorhandler(500)
def server_error(e):
    try:
        return render_template('500.html'), 500
    except:
        return "<h1>500 - Server Error</h1><a href='/'>Home</a>", 500

# ============================================
# Background Tasks
# ============================================

def background_tasks():
    """Background monitoring and updates"""
    while binghome.running:
        try:
            # Update sensor data and emit to connected clients
            if SOCKETIO_AVAILABLE and socketio:
                sensor_data = binghome.read_sensors()
                socketio.emit('sensor_update', sensor_data)
            
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Background task error: {e}")
            time.sleep(10)

# ============================================
# Startup Function
# ============================================

def startup_tasks():
    """Perform startup initialization"""
    logger.info("BingHome Hub starting up...")
    
    try:
        # Start background monitoring
        if not binghome.startup_complete:
            bg_thread = threading.Thread(target=background_tasks, daemon=True)
            bg_thread.start()
            logger.info("Background tasks started")
        
        binghome.startup_complete = True
        logger.info("BingHome Hub startup complete")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    try:
        # Perform startup tasks
        startup_tasks()
        
        # Get configuration
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        logger.info(f"Starting BingHome Hub on {host}:{port}")
        logger.info(f"Weather source: {binghome.settings.get('weather_source', 'openweather')}")
        logger.info(f"Apps configured: {len(binghome.settings.get('apps', {}))}")
        
        # Start the server
        if SOCKETIO_AVAILABLE and socketio:
            socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        else:
            app.run(host=host, port=port, debug=debug)
            
    except KeyboardInterrupt:
        logger.info("BingHome Hub shutting down...")
        binghome.running = False
        
        if RPI_AVAILABLE:
            try:
                GPIO.cleanup()
            except:
                pass
                
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
