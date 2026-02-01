# ============================================
# core/photos.py - Photo Slideshow Manager
# ============================================
"""Manages local and cloud photo slideshows"""

import os
import logging
import random
import time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class PhotoManager:
    """Manages photo slideshows from multiple sources"""

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self, settings=None):
        self.settings = settings or {}
        self.photos_dir = Path('/home/rcook01/binghome/static/photos')
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.cached_photos = []
        self.last_scan = None

    def scan_local_photos(self):
        """Scan local photos directory"""
        photos = []

        try:
            for file_path in self.photos_dir.rglob('*'):
                if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                    photos.append({
                        'path': str(file_path),
                        'url': f'/static/photos/{file_path.relative_to(self.photos_dir)}',
                        'name': file_path.name,
                        'modified': file_path.stat().st_mtime,
                        'source': 'local'
                    })

            # Sort by modification time (newest first)
            photos.sort(key=lambda x: x['modified'], reverse=True)
            self.cached_photos = photos
            self.last_scan = datetime.now().isoformat()

            logger.info(f"Found {len(photos)} local photos")

        except Exception as e:
            logger.error(f"Error scanning photos: {e}")

        return photos

    def get_photos(self, limit=100, shuffle=False):
        """Get photos for slideshow"""
        if not self.cached_photos or not self.last_scan:
            self.scan_local_photos()

        photos = self.cached_photos[:limit]

        if shuffle:
            random.shuffle(photos)

        return photos

    def get_random_photo(self):
        """Get a random photo"""
        photos = self.get_photos()
        if photos:
            return random.choice(photos)
        return None

    def get_photo_urls(self, limit=100):
        """Get just the URLs for slideshow"""
        photos = self.get_photos(limit)
        return [p['url'] for p in photos]

    def add_photo_from_url(self, url, name=None):
        """Download and add a photo from URL"""
        import requests

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Generate filename
            if not name:
                name = f"photo_{int(time.time())}.jpg"

            file_path = self.photos_dir / name

            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Refresh cache
            self.scan_local_photos()

            return {'success': True, 'path': str(file_path)}

        except Exception as e:
            logger.error(f"Error adding photo: {e}")
            return {'success': False, 'error': str(e)}

    def delete_photo(self, filename):
        """Delete a photo"""
        try:
            file_path = self.photos_dir / filename
            if file_path.exists():
                file_path.unlink()
                self.scan_local_photos()
                return {'success': True}
            return {'success': False, 'error': 'File not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_unsplash_photos(self, query='nature', count=10):
        """Get random photos from Unsplash (free, no API key needed for small usage)"""
        photos = []

        # Unsplash source URLs (free tier)
        for i in range(count):
            photos.append({
                'url': f'https://source.unsplash.com/random/1920x1080/?{query}&sig={i}',
                'source': 'unsplash'
            })

        return photos

    def update_settings(self, settings):
        """Update settings"""
        self.settings = settings
