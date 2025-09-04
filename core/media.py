# ============================================
# core/media.py - Media Controller Module
# ============================================
"""Media control module for BingHome"""

import os
import logging
import subprocess
import threading

logger = logging.getLogger(__name__)

class MediaController:
    def __init__(self):
        self.is_playing = False
        self.current_source = None
        self.volume = 50
        
    def play(self, source=None):
        """Play media from source"""
        try:
            self.is_playing = True
            self.current_source = source or "default"
            logger.info(f"Playing from {self.current_source}")
            
            # Example: Use omxplayer on Raspberry Pi
            if os.path.exists('/usr/bin/omxplayer'):
                subprocess.Popen(['omxplayer', source]) if source else None
            
            return True
        except Exception as e:
            logger.error(f"Media play error: {e}")
            return False
    
    def pause(self):
        """Pause media playback"""
        self.is_playing = False
        logger.info("Media paused")
        return True
    
    def stop(self):
        """Stop media playback"""
        self.is_playing = False
        self.current_source = None
        logger.info("Media stopped")
        
        # Kill omxplayer if running
        try:
            subprocess.run(['killall', 'omxplayer.bin'], capture_output=True)
        except:
            pass
        
        return True
    
    def next(self):
        """Skip to next track"""
        logger.info("Next track")
        return True
    
    def previous(self):
        """Go to previous track"""
        logger.info("Previous track")
        return True
    
    def set_volume(self, level):
        """Set volume level (0-100)"""
        self.volume = max(0, min(100, level))
        
        # Set system volume
        try:
            # Use amixer on Raspberry Pi
            subprocess.run(['amixer', 'set', 'Master', f'{self.volume}%'])
        except:
            pass
        
        logger.info(f"Volume set to {self.volume}")
        return True
