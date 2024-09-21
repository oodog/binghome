# web_server.py

import os
import subprocess
import logging
from flask import Flask, render_template, jsonify, session, redirect, url_for, flash, request
from flask_dance.contrib.google import make_google_blueprint, google
import feedparser
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object('config.Config')

# Setup Google OAuth Blueprint
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=[
        "https://www.googleapis.com/auth/photoslibrary.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    redirect_url="/home_menu_settings/google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

# In-memory user settings storage (for simplicity)
user_settings = {}

def get_wifi_strength():
    """
    Retrieves the current Wi-Fi signal strength using nmcli.
    Returns:
        int: Signal strength percentage (0-100).
    """
    try:
        # Run nmcli command to get Wi-Fi details
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SIGNAL', 'dev', 'wifi'],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 2 and parts[0].lower() == 'yes':
                signal = int(parts[1])
                logger.info(f"Connected Wi-Fi signal strength: {signal}%")
                return signal
        logger.warning("No active Wi-Fi connection found.")
        return 0  # If no active connection found
    except subprocess.CalledProcessError as e:
        logger.error(f"Error fetching Wi-Fi strength: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 0

def get_bing_wallpapers():
    """
    Fetches Bing's latest wallpapers.
    Returns:
        list: List of image URLs.
    """
    try:
        response = requests.get(
            "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US",
            timeout=5  # Timeout after 5 seconds
        )
        if response.status_code == 200:
            data = response.json()
            images = ["https://www.bing.com" + img['urlbase'] + "_UHD.jpg" for img in data.get('images', [])]
            logger.info(f"Fetched {len(images)} Bing wallpapers.")
            return images
        else:
            logger.error(f"Failed to fetch Bing wallpapers: Status code {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout occurred while fetching Bing wallpapers.")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception occurred: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching Bing wallpapers: {e}")
        return []

def get_google_photos_albums():
    """
    Fetches user's Google Photos albums.
    Returns:
        list: List of albums with 'id' and 'title'.
    """
    if not google.authorized:
        return []
    try:
        resp = google.get("https://photoslibrary.googleapis.com/v1/albums?pageSize=50")
        if resp.ok:
            data = resp.json()
            albums = [{'id': album['id'], 'title': album['title']} for album in data.get('albums', [])]
            logger.info(f"Fetched {len(albums)} Google Photos albums.")
            return albums
        else:
            logger.error(f"Failed to fetch Google Photos albums: {resp.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching Google Photos albums: {e}")
        return []

def get_google_photos_images(album_id):
    """
    Fetches images from a specific Google Photos album.
    Args:
        album_id (str): The ID of the Google Photos album.
    Returns:
        list: List of image URLs.
    """
    if not google.authorized:
        return []
    try:
        params = {
            "albumId": album_id,
            "pageSize": 50
        }
        resp = google.get("https://photoslibrary.googleapis.com/v1/mediaItems", params=params)
        if resp.ok:
            data = resp.json()
            images = [item['baseUrl'] + "=w800-h800" for item in data.get('mediaItems', [])]
            logger.info(f"Fetched {len(images)} images from Google Photos album ID {album_id}.")
            return images
        else:
            logger.error(f"Failed to fetch images from Google Photos: {resp.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching images from Google Photos: {e}")
        return []

def get_current_user():
    """
    Retrieves the current user. Placeholder for actual user management.
    Returns:
        str: User identifier.
    """
    # For simplicity, returning a static user. Implement proper user management as needed.
    return "admin"

@app.route('/')
def index():
    """
    Home page route. Renders the main interface with date, time, Wi-Fi strength, news, and images.
    """
    rss_url = "https://feeds.bbci.co.uk/news/rss.xml"  # Reliable RSS feed
    feed = feedparser.parse(rss_url)
    if feed.bozo:
        logger.error(f"Malformed RSS feed: {feed.bozo_exception}")
        news_items = []
    else:
        news_items = [{'title': entry.title, 'link': entry.link} for entry in feed.entries[:10]]  # Top 10 news

    wifi_strength = get_wifi_strength()

    # Get images to display (Google Photos or Bing Wallpapers)
    user = get_current_user()
    album_id = user_settings.get(user, {}).get('google_photos_album_id')
    if album_id:
        images = get_google_photos_images(album_id)
    else:
        images = get_bing_wallpapers()

    return render_template('index.html', news_items=news_items, wifi_strength=wifi_strength, images=images)

@app.route('/wifi_strength')
def wifi_strength_route():
    """
    API endpoint to fetch current Wi-Fi signal strength.
    Returns:
        JSON: Wi-Fi signal strength percentage.
    """
    try:
        strength = get_wifi_strength()
        return jsonify({'signal_strength': strength})
    except Exception as e:
        logger.error(f"Error in /wifi_strength: {e}")
        return jsonify({'signal_strength': 0}), 500

@app.route('/get_news')
def get_news():
    """
    API endpoint to fetch latest news.
    Returns:
        JSON: List of news items with 'title' and 'link'.
    """
    try:
        rss_url = "https://feeds.bbci.co.uk/news/rss.xml"  # Reliable RSS feed
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            logger.error(f"Malformed RSS feed: {feed.bozo_exception}")
            news_items = []
        else:
            news_items = [{'title': entry.title, 'link': entry.link} for entry in feed.entries[:10]]  # Top 10 news
        return jsonify({'news_items': news_items})
    except Exception as e:
        logger.error(f"Error in /get_news: {e}")
        return jsonify({'news_items': []}), 500

@app.route('/settings')
def settings():
    """
    Settings page route.
    """
    return render_template('settings.html')

@app.route('/wifi_settings')
def wifi_settings():
    """
    Wi-Fi Settings subpage.
    """
    # Fetch available Wi-Fi networks
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi'],
            capture_output=True,
            text=True,
            check=True
        )
        networks = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 3:
                ssid, signal, security = parts[0], parts[1], parts[2]
                networks.append({'ssid': ssid, 'signal': signal, 'security': security})
        logger.info(f"Found {len(networks)} Wi-Fi networks.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error fetching Wi-Fi networks: {e}")
        networks = []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        networks = []
    
    wifi_strength = get_wifi_strength()
    
    return render_template('wifi_settings.html', networks=networks, wifi_strength=wifi_strength)

@app.route('/language_settings')
def language_settings():
    """
    Language Settings subpage.
    """
    # Placeholder for language settings
    available_languages = ['English', 'Spanish', 'French', 'German', 'Chinese']
    current_language = 'English'  # Placeholder
    return render_template('language_settings.html', available_languages=available_languages, current_language=current_language)

@app.route('/home_menu_settings')
def home_menu_settings():
    """
    Home Menu Settings subpage.
    """
    authenticated = google.authorized
    albums = []
    if authenticated:
        albums = get_google_photos_albums()
    user = get_current_user()
    selected_album = user_settings.get(user, {}).get('google_photos_album_id')
    return render_template('home_menu_settings.html', authenticated=authenticated, albums=albums, selected_album=selected_album)

@app.route('/home_menu_settings/select_album', methods=['POST'])
def select_album():
    """
    Route to handle album selection from Home Menu Settings.
    """
    album_id = request.form.get('album_id')
    user = get_current_user()
    if user not in user_settings:
        user_settings[user] = {}
    user_settings[user]['google_photos_album_id'] = album_id
    logger.info(f"User {user} selected Google Photos album ID: {album_id}")
    flash('Album selected successfully!', 'success')
    return redirect(url_for('home_menu_settings'))

@app.route('/home_menu_settings/google_login')
def google_login():
    """
    Route to handle Google OAuth login.
    """
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('home_menu_settings'))

@app.route('/logout_google')
def logout_google():
    """
    Route to handle Google OAuth logout.
    """
    token = google_bp.token.get("access_token")
    if token:
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={'token': token},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )
        if resp.ok:
            del google_bp.token  # Delete OAuth token from storage
            logger.info("Google OAuth token revoked successfully.")
            flash('Logged out from Google successfully.', 'success')
        else:
            logger.error("Failed to revoke Google OAuth token.")
            flash('Failed to log out from Google.', 'error')
    else:
        flash('No active Google session found.', 'error')
    return redirect(url_for('home_menu_settings'))

@app.route('/connect_wifi', methods=['POST'])
def connect_wifi():
    """
    Route to handle connecting to a selected Wi-Fi network.
    Expects 'ssid' and 'password' in the form data.
    """
    ssid = request.form.get('ssid')
    password = request.form.get('password')
    if not ssid:
        flash('SSID is required to connect to Wi-Fi.', 'error')
        return redirect(url_for('wifi_settings'))
    
    # Attempt to connect to Wi-Fi
    try:
        if password:
            subprocess.run(
                ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
                check=True
            )
            flash(f'Successfully connected to {ssid}.', 'success')
        else:
            # Open network without password
            subprocess.run(
                ['nmcli', 'dev', 'wifi', 'connect', ssid],
                check=True
            )
            flash(f'Successfully connected to {ssid}.', 'success')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error connecting to Wi-Fi: {e}")
        flash(f"Failed to connect to {ssid}. Please check the password and try again.", 'error')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        flash(f"An unexpected error occurred while connecting to {ssid}.", 'error')
    
    return redirect(url_for('wifi_settings'))

@app.route('/logout')
def logout():
    """
    Logout function for the application. Clears session and redirects to home.
    """
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run()
