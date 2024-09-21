# web_server.py

import os
import subprocess
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import feedparser
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Setup Basic Authentication
auth = HTTPBasicAuth()

# In-memory user store (for demonstration purposes)
users = {
    os.getenv('AUTH_USERNAME', 'admin'): generate_password_hash(os.getenv('AUTH_PASSWORD', 'password'))
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to nmcli
NMCLI_PATH = '/usr/bin/nmcli'  # Update this path if different

# Verify password for authentication
@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# Decorator to protect routes without requiring auth
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    rss_url = "https://feeds.bbci.co.uk/news/rss.xml"  # Reliable RSS feed
    feed = feedparser.parse(rss_url)
    if feed.bozo:
        logger.error(f"Malformed RSS feed: {feed.bozo_exception}")
        news_items = []
    else:
        news_items = [{'title': entry.title, 'link': entry.link} for entry in feed.entries[:10]]  # Top 10 news
    wifi_strength = get_wifi_strength()
    return render_template('index.html', news_items=news_items, wifi_strength=wifi_strength)

@app.route('/wifi_strength')
def wifi_strength():
    try:
        strength = get_wifi_strength()
        return jsonify({'signal_strength': strength})
    except Exception as e:
        logger.error(f"Error in /wifi_strength: {e}")
        return jsonify({'signal_strength': 0}), 500

@app.route('/get_news')
def get_news():
    try:
        rss_url = "https://feeds.bbci.co.uk/news/rss.xml"  # Reliable RSS feed
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            logger.error(f"Malformed RSS feed: {feed.bozo_exception}")
            return jsonify({'news_items': []}), 500
        news_items = [{'title': entry.title, 'link': entry.link} for entry in feed.entries[:10]]
        logger.info(f"Fetched {len(news_items)} news items.")
        return jsonify({'news_items': news_items})
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({'news_items': []}), 500

@app.route('/settings')
@auth.login_required
def settings():
    return render_template('settings.html')

@app.route('/settings/wifi')
@auth.login_required
def wifi_settings():
    networks = scan_wifi()
    return render_template('wifi_settings.html', networks=networks)

@app.route('/connect_wifi', methods=['POST'])
@auth.login_required
def connect_wifi_route():
    ssid = request.form.get('ssid')
    password = request.form.get('password')

    if not ssid or not password:
        flash('SSID and password are required!', 'danger')
        return redirect(url_for('wifi_settings'))

    # Create a temporary password file
    temp_password_file = '/tmp/wifi_password.txt'
    try:
        with open(temp_password_file, 'w') as f:
            f.write(password)

        # Call the connect_wifi.py script
        subprocess.run(['python3', 'connect_wifi.py', ssid, temp_password_file, NMCLI_PATH], check=True)
        flash(f'Successfully connected to {ssid}.', 'success')
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to connect to Wi-Fi: {e}")
        flash('Failed to connect to Wi-Fi. Please check the credentials and try again.', 'danger')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        flash('An unexpected error occurred.', 'danger')
    finally:
        # Ensure the temporary password file is deleted
        if os.path.exists(temp_password_file):
            os.remove(temp_password_file)

    return redirect(url_for('wifi_settings'))

def get_wifi_strength():
    try:
        # Use nmcli to get the signal strength of the current connection
        result = subprocess.run(
            [NMCLI_PATH, '-t', '-f', 'ACTIVE,SSID,SIGNAL', 'dev', 'wifi'],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) < 3:
                continue
            active, ssid, signal = parts[0], parts[1], parts[2]
            if active.lower() == 'yes':
                logger.info(f"Connected to {ssid} with signal strength {signal}%")
                return int(signal)
        logger.warning("No active Wi-Fi connection found.")
        return 0  # If no active connection found
    except subprocess.CalledProcessError as e:
        logger.error(f"Error fetching Wi-Fi strength: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 0

def scan_wifi():
    try:
        # Use nmcli to scan for available Wi-Fi networks
        result = subprocess.run(
            [NMCLI_PATH, '-t', '-f', 'SSID,SIGNAL', 'dev', 'wifi', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        networks = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) < 2:
                continue
            ssid, signal = parts[0], parts[1]
            networks.append({'ssid': ssid, 'signal': int(signal)})
        logger.info(f"Scanned {len(networks)} Wi-Fi networks.")
        return networks
    except subprocess.CalledProcessError as e:
        logger.error(f"Error scanning Wi-Fi networks: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
