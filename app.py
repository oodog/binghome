#!/usr/bin/env python3
"""
BingHome - Fixed Smart Home Control Interface
A modern smart home dashboard for Raspberry Pi with touchscreen
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import sys
import logging
from datetime import datetime
import subprocess
import requests
from threading import Thread
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Global variables for sensor data
sensor_data = {
    'temperature': 22.5,
    'humidity': 45.0,
    'gas_detected': False,
    'light_level': True,
    'last_update': datetime.now().isoformat()
}

# Configuration
CONFIG = {
    'HOME_ASSISTANT_URL': os.getenv('HOME_ASSISTANT_URL', 'http://localhost:8123'),
    'HOME_ASSISTANT_TOKEN': os.getenv('HOME_ASSISTANT_TOKEN', ''),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
    'BING_API_KEY': os.getenv('BING_API_KEY', ''),
    'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
}

def init_gpio():
    """Initialize GPIO pins for sensors (mock implementation for testing)"""
    try:
        logger.info("Initializing GPIO pins...")
        # In a real implementation, this would set up actual GPIO
        return True
    except Exception as e:
        logger.error(f"GPIO initialization failed: {e}")
        return False

def read_sensors():
    """Read sensor data (mock implementation for testing)"""
    global sensor_data
    try:
        # Mock sensor readings - replace with actual GPIO reads
        import random
        sensor_data.update({
            'temperature': round(20 + random.uniform(-5, 15), 1),
            'humidity': round(40 + random.uniform(-10, 30), 1),
            'gas_detected': random.choice([True, False, False, False]),  # Usually false
            'light_level': random.choice([True, False]),
            'last_update': datetime.now().isoformat()
        })
        logger.debug(f"Sensor data updated: {sensor_data}")
    except Exception as e:
        logger.error(f"Error reading sensors: {e}")

def sensor_thread():
    """Background thread to continuously read sensors"""
    while True:
        read_sensors()
        time.sleep(30)  # Update every 30 seconds

@app.route('/')
def index():
    """Main dashboard route"""
    try:
        logger.info("Serving main dashboard")
        return render_template('index.html', 
                             sensor_data=sensor_data,
                             config=CONFIG)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        # Return a simple HTML page if template fails
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>BingHome - Smart Home Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; }
                .error { color: #ff6b6b; }
                .container { max-width: 800px; margin: 0 auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>BingHome Dashboard</h1>
                <p class="error">Template loading error. Using fallback page.</p>
                <p>Current time: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                <p>Sensor data: """ + json.dumps(sensor_data, indent=2) + """</p>
                <p><a href="/api/sensor_data">View API Data</a></p>
            </div>
        </body>
        </html>
        """

@app.route('/api/sensor_data')
def api_sensor_data():
    """API endpoint for sensor data"""
    try:
        return jsonify({
            'success': True,
            'data': sensor_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in sensor_data API: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'sensors_active': True
    })

@app.route('/api/voice', methods=['POST'])
def api_voice():
    """Voice assistant endpoint"""
    try:
        data = request.get_json()
        query = data.get('query', '') if data else ''
        
        # Mock response - replace with actual OpenAI integration
        response = {
            'success': True,
            'query': query,
            'response': f"I heard you say: '{query}'. Voice assistant is working!",
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in voice API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wifi_scan')
def api_wifi_scan():
    """WiFi network scan endpoint with signal strength"""
    try:
        # Get current WiFi signal strength (mock implementation)
        import random
        current_strength = random.randint(60, 100)
        
        # Mock WiFi networks with realistic signal strengths
        networks = [
            {'ssid': 'HomeNetwork_5G', 'signal': -35, 'security': 'WPA3', 'frequency': '5GHz'},
            {'ssid': 'HomeNetwork_2.4G', 'signal': -45, 'security': 'WPA3', 'frequency': '2.4GHz'},
            {'ssid': 'GuestWiFi', 'signal': -65, 'security': 'WPA2', 'frequency': '2.4GHz'},
            {'ssid': 'NeighborNet', 'signal': -80, 'security': 'WPA2', 'frequency': '2.4GHz'},
            {'ssid': 'CoffeeShop_Free', 'signal': -85, 'security': 'Open', 'frequency': '2.4GHz'},
            {'ssid': 'Hidden_Network', 'signal': -75, 'security': 'WPA2', 'frequency': '5GHz'}
        ]
        
        # Sort by signal strength (higher is better, so closer to 0)
        networks.sort(key=lambda x: x['signal'], reverse=True)
        
        return jsonify({
            'success': True,
            'networks': networks,
            'current_strength': current_strength,
            'connected_ssid': 'HomeNetwork_5G',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in WiFi scan: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wifi_connect', methods=['POST'])
def api_wifi_connect():
    """WiFi connection endpoint"""
    try:
        data = request.get_json()
        ssid = data.get('ssid', '') if data else ''
        password = data.get('password', '') if data else ''
        
        # Mock connection - replace with actual WiFi connection logic
        return jsonify({
            'success': True,
            'message': f'Connected to {ssid}',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in WiFi connect: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Custom 404 page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BingHome - Page Not Found</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; text-align: center; }
            .container { max-width: 600px; margin: 50px auto; }
            a { color: #4CAF50; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404 - Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def server_error(error):
    """Custom 500 page"""
    logger.error(f"Server error: {error}")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BingHome - Server Error</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; text-align: center; }
            .container { max-width: 600px; margin: 50px auto; }
            .error { color: #ff6b6b; }
            a { color: #4CAF50; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="error">500 - Server Error</h1>
            <p>Something went wrong on our end.</p>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    """, 500

def main():
    """Main application entry point"""
    try:
        logger.info("Starting BingHome application...")
        
        # Initialize GPIO
        if not init_gpio():
            logger.warning("GPIO initialization failed, continuing without hardware sensors")
        
        # Start sensor reading thread
        sensor_thread_instance = Thread(target=sensor_thread, daemon=True)
        sensor_thread_instance.start()
        logger.info("Sensor thread started")
        
        # Check if running on Raspberry Pi
        is_pi = os.path.exists('/proc/device-tree/model')
        host = '0.0.0.0' if is_pi else '127.0.0.1'
        port = int(os.getenv('PORT', 5000))
        
        logger.info(f"Starting Flask app on {host}:{port}")
        logger.info(f"Debug mode: {CONFIG['DEBUG']}")
        
        app.run(
            host=host,
            port=port,
            debug=CONFIG['DEBUG'],
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()