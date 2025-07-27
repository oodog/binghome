#!/usr/bin/env python3
"""
BingHome Smart Hub - Main Flask Application
GitHub: https://github.com/oodog/binghome

A modern smart home control interface for Raspberry Pi with:
- Xbox-style UI with touch navigation
- Home Assistant integration
- Voice assistant (ChatGPT)
- Real-time sensor monitoring
- Bing News integration
"""

import os
import logging
import requests
import atexit
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('binghome.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configuration from environment variables
CONFIG = {
    'HOME_ASSISTANT_URL': os.environ.get('HOME_ASSISTANT_URL', 'http://localhost:8123'),
    'HOME_ASSISTANT_TOKEN': os.environ.get('HOME_ASSISTANT_TOKEN', ''),
    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
    'BING_API_KEY': os.environ.get('BING_API_KEY', ''),
    'DEBUG': os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
}

# GPIO pin assignments for Raspberry Pi sensors
GPIO_PINS = {
    'DHT_PIN': 4,      # GPIO4 (physical pin 7) for DHT22 data line
    'GAS_PIN': 17,     # GPIO17 (physical pin 11) for digital gas sensor
    'LIGHT_PIN': 27,   # GPIO27 (physical pin 13) for digital light sensor
    'I2C_AUDIO_ADDRESS': 0x58  # TPA2016 I2C address
}

# Global state
gpio_initialized = False

def cleanup_gpio():
    """Cleanup GPIO on application exit"""
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        logger.info("GPIO cleanup completed")
    except ImportError:
        pass  # Not on Raspberry Pi
    except Exception as e:
        logger.error(f"GPIO cleanup error: {e}")

# Register cleanup function
atexit.register(cleanup_gpio)

def get_sensor_data():
    """Get sensor data from various sources with fallbacks"""
    global gpio_initialized
    data = {}
    
    # Temperature & humidity (DHT22)
    try:
        import Adafruit_DHT
        humidity, temperature = Adafruit_DHT.read_retry(
            Adafruit_DHT.DHT22, 
            GPIO_PINS['DHT_PIN']
        )
        if humidity is not None and temperature is not None:
            data['temperature'] = f"{temperature:.1f}"
            data['humidity'] = f"{humidity:.1f}"
        else:
            # Try Home Assistant fallback
            ha_temp = get_home_assistant_sensor('sensor.temperature')
            ha_humidity = get_home_assistant_sensor('sensor.humidity')
            data['temperature'] = ha_temp or "22.5"
            data['humidity'] = ha_humidity or "45"
    except ImportError:
        logger.warning("Adafruit_DHT not available, using fallback values")
        data['temperature'] = "22.5"
        data['humidity'] = "45"
    except Exception as e:
        logger.error(f"DHT sensor error: {e}")
        data['temperature'] = "22.5"
        data['humidity'] = "45"
    
    # Digital sensors (Gas and Light)
    try:
        import RPi.GPIO as GPIO
        
        # Initialize GPIO only once
        if not gpio_initialized:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(GPIO_PINS['GAS_PIN'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(GPIO_PINS['LIGHT_PIN'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            gpio_initialized = True
            logger.info("GPIO pins initialized")
        
        # Read digital sensors
        gas_detected = GPIO.input(GPIO_PINS['GAS_PIN'])
        data['gas'] = "Alert" if gas_detected else "Safe"
        
        light_detected = GPIO.input(GPIO_PINS['LIGHT_PIN'])
        data['light'] = "Bright" if light_detected else "Dark"
        
    except ImportError:
        logger.warning("RPi.GPIO not available, using fallback values")
        data['gas'] = "Safe"
        data['light'] = "Normal"
    except Exception as e:
        logger.error(f"Digital sensors error: {e}")
        data['gas'] = "Safe"
        data['light'] = "Normal"
    
    # Audio amplifier status (I2C)
    try:
        import smbus
        bus = smbus.SMBus(1)
        control_reg = bus.read_byte_data(GPIO_PINS['I2C_AUDIO_ADDRESS'], 0x01)
        data['audio'] = "Active" if control_reg & 0x80 else "Standby"
    except ImportError:
        logger.warning("smbus not available for audio amplifier")
        data['audio'] = "Unknown"
    except Exception as e:
        logger.error(f"Audio amplifier error: {e}")
        data['audio'] = "Offline"
    
    # Wi-Fi signal strength
    data['wifi'] = get_wifi_strength()
    
    return data

def get_home_assistant_sensor(entity_id):
    """Get sensor data from Home Assistant"""
    if not CONFIG['HOME_ASSISTANT_TOKEN'] or not CONFIG['HOME_ASSISTANT_URL']:
        return None
    
    try:
        headers = {
            'Authorization': f'Bearer {CONFIG["HOME_ASSISTANT_TOKEN"]}',
            'Content-Type': 'application/json'
        }
        url = f"{CONFIG['HOME_ASSISTANT_URL']}/api/states/{entity_id}"
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('state')
    except Exception as e:
        logger.error(f"Home Assistant API error for {entity_id}: {e}")
    
    return None

def get_wifi_strength():
    """Get Wi-Fi signal strength from system"""
    try:
        with open('/proc/net/wireless', 'r') as f:
            lines = f.readlines()
            if len(lines) >= 3:
                parts = lines[2].split()
                if len(parts) >= 5:
                    quality = float(parts[2].strip('.'))
                    wifi_percent = min(100, (quality / 70.0) * 100.0)
                    return f"{wifi_percent:.0f}"
    except Exception as e:
        logger.error(f"Wi-Fi strength read error: {e}")
    
    return "85"  # Fallback value

def get_news_headlines():
    """Fetch news headlines from Bing News API"""
    headlines = []
    
    if CONFIG['BING_API_KEY']:
        try:
            url = "https://api.bing.microsoft.com/v7.0/news"
            headers = {"Ocp-Apim-Subscription-Key": CONFIG['BING_API_KEY']}
            params = {
                "mkt": "en-US",
                "category": "ScienceAndTechnology",
                "count": 10
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for article in data.get('value', []):
                    title = article.get('name')
                    link = article.get('url')
                    published = article.get('datePublished', '')
                    
                    # Parse time for display
                    try:
                        pub_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        time_diff = datetime.now() - pub_time.replace(tzinfo=None)
                        hours_ago = int(time_diff.total_seconds() / 3600)
                        time_str = f"{hours_ago} hours ago" if hours_ago > 0 else "Just now"
                    except:
                        time_str = "Recently"
                    
                    if title and link:
                        headlines.append({
                            'title': title,
                            'link': link,
                            'time': time_str
                        })
        except Exception as e:
            logger.error(f"Bing News API error: {e}")
    
    # Fallback headlines if API fails
    if not headlines:
        headlines = [
            {
                'title': "BingHome Smart Hub is running successfully",
                'link': "https://github.com/oodog/binghome",
                'time': "Now"
            },
            {
                'title': "Raspberry Pi 5 announced with enhanced AI capabilities",
                'link': "#",
                'time': "2 hours ago"
            },
            {
                'title': "Smart home adoption reaches new heights in 2024",
                'link': "#",
                'time': "4 hours ago"
            },
            {
                'title': "New breakthrough in IoT security protocols",
                'link': "#",
                'time': "6 hours ago"
            },
            {
                'title': "Voice assistants becoming more privacy-focused",
                'link': "#",
                'time': "8 hours ago"
            }
        ]
    
    return headlines[:10]

# Flask Routes

@app.route('/')
def index():
    """Main dashboard page"""
    return send_from_directory('.', 'index.html')

@app.route('/api/sensor_data')
def api_sensor_data():
    """API endpoint for current sensor readings"""
    try:
        data = get_sensor_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Sensor data API error: {e}")
        return jsonify({"error": "Failed to get sensor data"}), 500

@app.route('/api/news')
def api_news():
    """API endpoint for news headlines"""
    try:
        headlines = get_news_headlines()
        return jsonify(headlines)
    except Exception as e:
        logger.error(f"News API error: {e}")
        return jsonify({"error": "Failed to get news"}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "BingHome Smart Hub is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/voice', methods=['POST'])
def voice_assistant():
    """Voice assistant endpoint using ChatGPT"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data['query']
        
        if not CONFIG['OPENAI_API_KEY']:
            return jsonify({"error": "Voice assistant not configured"}), 500
        
        import openai
        openai.api_key = CONFIG['OPENAI_API_KEY']
        
        # Create context-aware prompt for smart home
        system_prompt = """You are BingHome, a smart home assistant. You can help with:
        - Controlling smart home devices through Home Assistant
        - Answering questions about weather, news, and general topics
        - Managing entertainment systems
        - Providing information about the home's sensors and status
        
        Keep responses concise and helpful. Be friendly and conversational."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        answer = response['choices'][0]['message']['content']
        logger.info(f"Voice query: {user_query} | Response: {answer}")
        
        return jsonify({"answer": answer})
        
    except Exception as e:
        logger.error(f"Voice assistant error: {e}")
        return jsonify({"error": "Voice assistant failed"}), 500

@app.route('/api/wifi_scan')
def wifi_scan():
    """Scan for available Wi-Fi networks"""
    networks = []
    try:
        import subprocess
        result = subprocess.check_output(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
            timeout=10
        )
        for line in result.decode().splitlines():
            parts = line.split(":")
            if parts and parts[0]:
                ssid = parts[0]
                signal = parts[1] if len(parts) > 1 else "0"
                security = parts[2] if len(parts) > 2 else ""
                networks.append({
                    "ssid": ssid,
                    "signal": signal,
                    "security": security
                })
    except Exception as e:
        logger.error(f"Wi-Fi scan error: {e}")
        # Fallback networks for testing
        networks = [
            {"ssid": "BingHome_Network", "signal": "85", "security": "WPA2"},
            {"ssid": "Guest_Network", "signal": "72", "security": "WPA2"}
        ]
    
    return jsonify(networks)

@app.route('/api/wifi_connect', methods=['POST'])
def wifi_connect():
    """Connect to a Wi-Fi network"""
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid or not password:
            return jsonify({"error": "Missing SSID or password"}), 400
        
        import subprocess
        cmd = [
            "nmcli", "device", "wifi", "connect", ssid,
            "password", password
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"Successfully connected to Wi-Fi: {ssid}")
            return jsonify({"success": True, "message": f"Connected to {ssid}"})
        else:
            logger.error(f"Wi-Fi connection failed: {result.stderr}")
            return jsonify({"error": "Connection failed"}), 400
            
    except Exception as e:
        logger.error(f"Wi-Fi connection error: {e}")
        return jsonify({"error": "Connection failed"}), 500

@app.route('/api/system/info')
def system_info():
    """Get system information"""
    try:
        import psutil
        import platform
        
        info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "temperature": get_cpu_temperature(),
            "uptime": get_uptime(),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"System info error: {e}")
        return jsonify({"error": "System info unavailable"}), 500

def get_cpu_temperature():
    """Get CPU temperature (Raspberry Pi specific)"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            return f"{temp:.1f}°C"
    except:
        return "N/A"

def get_uptime():
    """Get system uptime"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_hours = int(uptime_seconds / 3600)
            return f"{uptime_hours}h"
    except:
        return "N/A"

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update application settings"""
    settings_file = 'settings.json'
    
    if request.method == 'GET':
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
        except FileNotFoundError:
            # Default settings
            default_settings = {
                "language": "en-US",
                "temperature_unit": "celsius",
                "news_refresh_rate": 300,
                "sensor_refresh_rate": 30,
                "theme": "dark"
            }
            return jsonify(default_settings)
    
    elif request.method == 'POST':
        try:
            settings = request.get_json()
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info("Settings updated")
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Settings update error: {e}")
            return jsonify({"error": "Failed to update settings"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("🏠 Starting BingHome Smart Hub...")
    logger.info(f"📱 Web interface will be available at http://localhost:5000")
    logger.info(f"🏠 Home Assistant URL: {CONFIG['HOME_ASSISTANT_URL']}")
    logger.info(f"🔧 Debug mode: {CONFIG['DEBUG']}")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=CONFIG['DEBUG'],
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("👋 BingHome Smart Hub stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start BingHome: {e}")
        raise