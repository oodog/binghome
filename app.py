import os
import json
import time
import requests
import subprocess
from flask import Flask, render_template, request, jsonify, redirect, url_for
import RPi.GPIO as GPIO
import Adafruit_DHT
from smbus import SMBus
import threading

app = Flask(__name__)

# Hardware configuration
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4
GAS_PIN = 17
LIGHT_PIN = 27

# I2C configuration for TPA2016 audio amplifier
I2C_BUS = 1
TPA2016_ADDR = 0x58
TPA2016_AGC_CONTROL = 0x01
TPA2016_AGC_ATTACK = 0x02
TPA2016_AGC_RELEASE = 0x03
TPA2016_HOLD_TIME = 0x04
TPA2016_FIXED_GAIN = 0x05

# Initialize I2C bus
try:
    i2c_bus = SMBus(I2C_BUS)
    audio_available = True
except:
    audio_available = False
    print("Warning: I2C audio amplifier not available")

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(GAS_PIN, GPIO.IN)
GPIO.setup(LIGHT_PIN, GPIO.IN)

# Global variables
current_volume = 50  # Default volume (0-100)
navigation_stack = []  # For back navigation

class VolumeController:
    def __init__(self):
        self.current_volume = 50
        self.muted = False
        self.previous_volume = 50
        
    def set_volume(self, volume):
        """Set volume level (0-100) via I2C to TPA2016"""
        if not audio_available:
            return False
            
        try:
            # Clamp volume to valid range
            volume = max(0, min(100, volume))
            
            # Convert percentage to TPA2016 register value (0-30)
            register_value = int((volume / 100) * 30)
            
            # Write to TPA2016 fixed gain register
            i2c_bus.write_byte_data(TPA2016_ADDR, TPA2016_FIXED_GAIN, register_value)
            
            self.current_volume = volume
            self.muted = False
            return True
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def volume_up(self, step=5):
        """Increase volume by step amount"""
        new_volume = min(100, self.current_volume + step)
        return self.set_volume(new_volume)
    
    def volume_down(self, step=5):
        """Decrease volume by step amount"""
        new_volume = max(0, self.current_volume - step)
        return self.set_volume(new_volume)
    
    def mute_toggle(self):
        """Toggle mute state"""
        if self.muted:
            self.set_volume(self.previous_volume)
            self.muted = False
        else:
            self.previous_volume = self.current_volume
            self.set_volume(0)
            self.muted = True
        return self.muted

# Initialize volume controller
volume_controller = VolumeController()

def get_sensor_data():
    """Read all sensor data"""
    data = {
        'timestamp': time.time(),
        'temperature': None,
        'humidity': None,
        'gas_detected': False,
        'light_detected': False
    }
    
    try:
        # Read DHT22 sensor
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            data['temperature'] = round(temperature, 1)
            data['humidity'] = round(humidity, 1)
    except Exception as e:
        print(f"Error reading DHT22: {e}")
    
    try:
        # Read digital sensors
        data['gas_detected'] = GPIO.input(GAS_PIN) == GPIO.HIGH
        data['light_detected'] = GPIO.input(LIGHT_PIN) == GPIO.HIGH
    except Exception as e:
        print(f"Error reading digital sensors: {e}")
    
    return data

def get_wifi_networks():
    """Scan for available WiFi networks"""
    try:
        result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                              capture_output=True, text=True)
        networks = []
        
        for line in result.stdout.split('\n'):
            if 'ESSID:' in line:
                essid = line.split('ESSID:')[1].strip().strip('"')
                if essid and essid != '<hidden>':
                    networks.append(essid)
        
        return list(set(networks))  # Remove duplicates
    except Exception as e:
        print(f"Error scanning WiFi: {e}")
        return []

def connect_wifi(ssid, password):
    """Connect to a WiFi network"""
    try:
        # Create wpa_supplicant configuration
        config = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
}}
"""
        with open('/tmp/wpa_temp.conf', 'w') as f:
            f.write(config)
        
        # Connect using wpa_supplicant
        result = subprocess.run([
            'sudo', 'wpa_supplicant', '-B', '-i', 'wlan0', 
            '-c', '/tmp/wpa_temp.conf'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Request IP address
            subprocess.run(['sudo', 'dhclient', 'wlan0'])
            return True
        return False
    except Exception as e:
        print(f"Error connecting to WiFi: {e}")
        return False

# Routes
@app.route('/')
def index():
    """Main interface"""
    navigation_stack.clear()  # Reset navigation on home
    return render_template('index.html')

@app.route('/settings')
def settings():
    """Settings page"""
    navigation_stack.append('/')
    sensor_data = get_sensor_data()
    return render_template('settings.html', 
                         sensor_data=sensor_data,
                         current_volume=volume_controller.current_volume,
                         audio_available=audio_available)

@app.route('/settings/system_status')
def system_status():
    """System status page"""
    navigation_stack.append('/settings')
    
    # Get system information
    try:
        # CPU temperature
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            cpu_temp = float(f.read()) / 1000.0
        
        # Memory usage
        mem_info = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith(('MemTotal:', 'MemAvailable:')):
                    key, value = line.split(':')
                    mem_info[key.strip()] = int(value.split()[0])
        
        mem_used_percent = ((mem_info['MemTotal'] - mem_info['MemAvailable']) 
                           / mem_info['MemTotal']) * 100
        
        # Disk usage
        disk_result = subprocess.run(['df', '-h', '/'], 
                                   capture_output=True, text=True)
        disk_info = disk_result.stdout.split('\n')[1].split()
        disk_used_percent = int(disk_info[4].strip('%'))
        
        system_info = {
            'cpu_temp': round(cpu_temp, 1),
            'memory_used_percent': round(mem_used_percent, 1),
            'disk_used_percent': disk_used_percent,
            'uptime': subprocess.run(['uptime', '-p'], 
                                   capture_output=True, text=True).stdout.strip()
        }
    except Exception as e:
        print(f"Error getting system info: {e}")
        system_info = {}
    
    sensor_data = get_sensor_data()
    return render_template('system_status.html', 
                         system_info=system_info,
                         sensor_data=sensor_data)

@app.route('/settings/wifi')
def wifi_settings():
    """WiFi settings page"""
    navigation_stack.append('/settings')
    networks = get_wifi_networks()
    return render_template('wifi_settings.html', networks=networks)

@app.route('/back')
def go_back():
    """Navigate back to previous page"""
    if navigation_stack:
        previous_page = navigation_stack.pop()
        return redirect(previous_page)
    return redirect('/')

# API Routes
@app.route('/api/sensor_data')
def api_sensor_data():
    """API endpoint for current sensor readings"""
    return jsonify(get_sensor_data())

@app.route('/api/volume/up', methods=['POST'])
def api_volume_up():
    """Increase volume"""
    step = request.json.get('step', 5) if request.is_json else 5
    success = volume_controller.volume_up(step)
    return jsonify({
        'success': success,
        'volume': volume_controller.current_volume,
        'muted': volume_controller.muted
    })

@app.route('/api/volume/down', methods=['POST'])
def api_volume_down():
    """Decrease volume"""
    step = request.json.get('step', 5) if request.is_json else 5
    success = volume_controller.volume_down(step)
    return jsonify({
        'success': success,
        'volume': volume_controller.current_volume,
        'muted': volume_controller.muted
    })

@app.route('/api/volume/set', methods=['POST'])
def api_volume_set():
    """Set specific volume level"""
    volume = request.json.get('volume', 50) if request.is_json else 50
    success = volume_controller.set_volume(volume)
    return jsonify({
        'success': success,
        'volume': volume_controller.current_volume,
        'muted': volume_controller.muted
    })

@app.route('/api/volume/mute', methods=['POST'])
def api_volume_mute():
    """Toggle mute"""
    muted = volume_controller.mute_toggle()
    return jsonify({
        'success': True,
        'volume': volume_controller.current_volume,
        'muted': muted
    })

@app.route('/api/wifi_scan')
def api_wifi_scan():
    """WiFi network scan"""
    networks = get_wifi_networks()
    return jsonify({'networks': networks})

@app.route('/api/wifi_connect', methods=['POST'])
def api_wifi_connect():
    """Connect to WiFi"""
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    
    if not ssid:
        return jsonify({'success': False, 'error': 'SSID required'}), 400
    
    success = connect_wifi(ssid, password)
    return jsonify({'success': success})

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'audio_available': audio_available
    })

if __name__ == '__main__':
    try:
        # Initialize TPA2016 audio amplifier
        if audio_available:
            # Set initial configuration
            i2c_bus.write_byte_data(TPA2016_ADDR, TPA2016_AGC_CONTROL, 0x05)
            volume_controller.set_volume(50)  # Set initial volume to 50%
        
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()