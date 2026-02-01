# ============================================
# core/google_photos.py - Google Photos Integration
# ============================================
"""
Manages Google Photos OAuth and API access with automatic token refresh.
"""

import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GooglePhotosService:
    """Handles Google Photos OAuth and API access"""

    BASE_URL = 'https://photoslibrary.googleapis.com/v1'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'

    def __init__(self, settings_getter, settings_saver):
        """
        Initialize with callback functions to get/save settings.
        This avoids circular imports with the main app.
        
        Args:
            settings_getter: Function that returns current settings dict
            settings_saver: Function that saves settings dict
        """
        self.get_settings = settings_getter
        self.save_settings = settings_saver
        self._token_expiry = None

    def _get_credentials(self):
        """Get OAuth credentials from environment"""
        return {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', '')
        }

    def _get_access_token(self):
        """Get current access token from settings"""
        settings = self.get_settings()
        return settings.get('google_photos_access_token', '')

    def _get_refresh_token(self):
        """Get refresh token from settings"""
        settings = self.get_settings()
        return settings.get('google_photos_refresh_token', '')

    def is_connected(self):
        """Check if Google Photos is connected"""
        settings = self.get_settings()
        return settings.get('google_photos_connected', False) and bool(self._get_access_token())

    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token.
        Returns True if successful, False otherwise.
        """
        credentials = self._get_credentials()
        refresh_token = self._get_refresh_token()

        if not refresh_token:
            logger.error("No refresh token available")
            return False

        if not credentials['client_id'] or not credentials['client_secret']:
            logger.error("Google OAuth credentials not configured")
            return False

        try:
            response = requests.post(self.TOKEN_URL, data={
                'client_id': credentials['client_id'],
                'client_secret': credentials['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }, timeout=30)

            if response.status_code == 200:
                tokens = response.json()
                new_access_token = tokens.get('access_token', '')
                
                if new_access_token:
                    settings = self.get_settings().copy()
                    settings['google_photos_access_token'] = new_access_token
                    
                    # Update refresh token if a new one was provided
                    if tokens.get('refresh_token'):
                        settings['google_photos_refresh_token'] = tokens['refresh_token']
                    
                    self.save_settings(settings)
                    
                    # Set token expiry (tokens typically expire in 1 hour)
                    expires_in = tokens.get('expires_in', 3600)
                    self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
                    
                    logger.info("Google Photos access token refreshed successfully")
                    return True
                else:
                    logger.error("No access token in refresh response")
                    return False
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error_description', response.text[:200])
                logger.error(f"Token refresh failed: {response.status_code} - {error_msg}")
                
                # If refresh token is invalid, disconnect
                if response.status_code == 400 and 'invalid_grant' in str(error_data):
                    self._disconnect()
                
                return False

        except requests.Timeout:
            logger.error("Token refresh timed out")
            return False
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False

    def _disconnect(self):
        """Disconnect Google Photos (clear tokens)"""
        settings = self.get_settings().copy()
        settings['google_photos_connected'] = False
        settings['google_photos_access_token'] = ''
        settings['google_photos_refresh_token'] = ''
        settings['google_photos_album'] = ''
        self.save_settings(settings)
        logger.info("Google Photos disconnected due to invalid credentials")

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make an authenticated request to Google Photos API.
        Automatically refreshes token if needed.
        """
        access_token = self._get_access_token()
        
        if not access_token:
            return {'success': False, 'error': 'Not connected', 'status_code': 401}

        # Check if token needs refresh
        if self._token_expiry and datetime.now() >= self._token_expiry:
            if not self.refresh_access_token():
                return {'success': False, 'error': 'Token refresh failed', 'status_code': 401}
            access_token = self._get_access_token()

        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        
        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'

        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            
            # If unauthorized, try refreshing token once
            if response.status_code == 401:
                logger.info("Access token expired, attempting refresh...")
                if self.refresh_access_token():
                    access_token = self._get_access_token()
                    headers['Authorization'] = f'Bearer {access_token}'
                    response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
                else:
                    return {'success': False, 'error': 'Authentication failed', 'status_code': 401}

            if response.status_code == 200:
                return {'success': True, 'data': response.json(), 'status_code': 200}
            else:
                error_msg = response.text[:500] if response.text else 'Unknown error'
                return {'success': False, 'error': error_msg, 'status_code': response.status_code}

        except requests.Timeout:
            return {'success': False, 'error': 'Request timed out', 'status_code': 504}
        except Exception as e:
            logger.error(f"Google Photos API error: {e}")
            return {'success': False, 'error': str(e), 'status_code': 500}

    def get_albums(self, page_size=50):
        """Get list of albums"""
        result = self._make_request('GET', f'albums?pageSize={page_size}')
        
        if result['success']:
            return {
                'success': True,
                'albums': result['data'].get('albums', [])
            }
        return result

    def get_photos_from_album(self, album_id, page_size=100):
        """Get photos from a specific album"""
        if not album_id:
            return {'success': False, 'error': 'No album selected'}

        result = self._make_request('POST', 'mediaItems:search', json={
            'albumId': album_id,
            'pageSize': page_size
        })

        if result['success']:
            media_items = result['data'].get('mediaItems', [])
            photos = []
            for item in media_items:
                if item.get('mimeType', '').startswith('image/'):
                    photos.append({
                        'id': item['id'],
                        'url': item['baseUrl'] + '=w1920-h1080',
                        'filename': item.get('filename', ''),
                        'mimeType': item.get('mimeType', ''),
                        'description': item.get('description', ''),
                        'creationTime': item.get('mediaMetadata', {}).get('creationTime', '')
                    })
            return {'success': True, 'photos': photos}
        return result

    def get_recent_photos(self, page_size=50):
        """Get recent photos (not album-specific)"""
        result = self._make_request('POST', 'mediaItems:search', json={
            'pageSize': page_size
        })

        if result['success']:
            media_items = result['data'].get('mediaItems', [])
            photos = []
            for item in media_items:
                if item.get('mimeType', '').startswith('image/'):
                    photos.append({
                        'id': item['id'],
                        'url': item['baseUrl'] + '=w1920-h1080',
                        'filename': item.get('filename', ''),
                        'mimeType': item.get('mimeType', '')
                    })
            return {'success': True, 'photos': photos}
        return result

    def get_slideshow_photos(self):
        """Get photos for slideshow based on settings"""
        settings = self.get_settings()
        album_id = settings.get('google_photos_album', '')

        if album_id:
            return self.get_photos_from_album(album_id)
        else:
            return self.get_recent_photos()


def fetch_shared_album_photos(shared_url):
    """
    Fetch photos from a shared Google Photos album link.
    Works with links like: https://photos.app.goo.gl/xxxxx

    This parses the shared album page to extract photo URLs.
    No authentication required - just needs the public share link.
    """
    import re

    if not shared_url:
        return {'success': False, 'error': 'No shared album URL provided', 'photos': []}

    try:
        # Follow redirects to get the actual album page
        response = requests.get(shared_url, timeout=15, allow_redirects=True)

        if response.status_code != 200:
            return {'success': False, 'error': f'Failed to access album: {response.status_code}', 'photos': []}

        html = response.text
        photos = []

        # Google Photos embeds photo data in the page as JSON
        # Look for photo URLs in the HTML - they follow patterns like:
        # https://lh3.googleusercontent.com/...

        # Pattern for Google Photos image URLs
        url_pattern = r'https://lh3\.googleusercontent\.com/[a-zA-Z0-9_\-/=]+(?=["\'>\s])'

        found_urls = set(re.findall(url_pattern, html))

        # Filter to get actual photo URLs (not thumbnails/icons)
        for url in found_urls:
            # Skip very short URLs (likely icons)
            if len(url) > 80:
                # Clean up the URL and add size parameters for high quality
                clean_url = url.split('=')[0]  # Remove any existing size params
                # Use moderate size for better Pi compatibility
                photo_url = clean_url + '=w1280-h720'

                photos.append({
                    'id': clean_url.split('/')[-1][:20],  # Use part of URL as ID
                    'url': photo_url,
                    'url_hd': clean_url + '=w1920-h1080',  # HD version for bigger screens
                    'url_sd': clean_url + '=w1024-h600',   # SD version for Pi
                    'thumbnail': clean_url + '=w320-h240',
                    'source': 'shared_album'
                })

        if photos:
            logger.info(f"Found {len(photos)} photos in shared album")
            return {'success': True, 'photos': photos, 'count': len(photos)}
        else:
            # Try alternative pattern - sometimes photos are in data arrays
            data_pattern = r'\["(https://lh3\.googleusercontent\.com/[^"]+)"'
            data_urls = set(re.findall(data_pattern, html))

            for url in data_urls:
                if len(url) > 80:
                    clean_url = url.split('=')[0]
                    photo_url = clean_url + '=w1280-h720'
                    photos.append({
                        'id': clean_url.split('/')[-1][:20],
                        'url': photo_url,
                        'url_hd': clean_url + '=w1920-h1080',
                        'url_sd': clean_url + '=w1024-h600',
                        'thumbnail': clean_url + '=w320-h240',
                        'source': 'shared_album'
                    })

            if photos:
                logger.info(f"Found {len(photos)} photos in shared album (alt method)")
                return {'success': True, 'photos': photos, 'count': len(photos)}

            return {'success': False, 'error': 'No photos found in album', 'photos': []}

    except requests.Timeout:
        return {'success': False, 'error': 'Connection timed out', 'photos': []}
    except Exception as e:
        logger.error(f"Error fetching shared album: {e}")
        return {'success': False, 'error': str(e), 'photos': []}
