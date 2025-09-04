# ============================================
# core/timers.py - Timer Manager Module
# ============================================
"""Timer and routine management for BingHome"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class TimerManager:
    def __init__(self):
        self.timers = {}
        self.routines = []
        
    def create_timer(self, duration, name="Timer", callback=None):
        """Create a new timer"""
        timer_id = str(uuid.uuid4())[:8]
        
        def timer_thread():
            time.sleep(duration)
            if timer_id in self.timers:
                logger.info(f"Timer '{name}' completed")
                if callback:
                    callback()
                del self.timers[timer_id]
        
        timer = {
            'id': timer_id,
            'name': name,
            'duration': duration,
            'started': datetime.now(),
            'ends': datetime.now() + timedelta(seconds=duration),
            'thread': threading.Thread(target=timer_thread, daemon=True)
        }
        
        self.timers[timer_id] = timer
        timer['thread'].start()
        
        logger.info(f"Timer '{name}' created for {duration} seconds")
        return timer_id
    
    def cancel_timer(self, timer_id):
        """Cancel a timer"""
        if timer_id in self.timers:
            # Thread will check if timer still exists
            del self.timers[timer_id]
            logger.info(f"Timer {timer_id} cancelled")
            return True
        return False
    
    def get_timers(self):
        """Get all active timers"""
        active_timers = []
        for timer_id, timer in self.timers.items():
            remaining = (timer['ends'] - datetime.now()).total_seconds()
            if remaining > 0:
                active_timers.append({
                    'id': timer_id,
                    'name': timer['name'],
                    'remaining': int(remaining),
                    'duration': timer['duration']
                })
        return active_timers
    
    def create_routine(self, name, time_str, actions, days=None):
        """Create a routine"""
        routine = {
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'time': time_str,  # "HH:MM" format
            'actions': actions,
            'days': days or ['everyday'],  # ['monday', 'tuesday', ...] or ['everyday']
            'enabled': True
        }
        
        self.routines.append(routine)
        logger.info(f"Routine '{name}' created")
        return routine['id']
    
    def check_routines(self):
        """Check if any routine should run"""
        current_time = datetime.now().strftime('%H:%M')
        current_day = datetime.now().strftime('%A').lower()
        
        for routine in self.routines:
            if not routine['enabled']:
                continue
                
            if routine['time'] == current_time:
                if 'everyday' in routine['days'] or current_day in routine['days']:
                    self.execute_routine(routine)
    
    def execute_routine(self, routine):
        """Execute a routine's actions"""
        logger.info(f"Executing routine: {routine['name']}")
        for action in routine['actions']:
            # Actions would be executed here
            logger.info(f"  Action: {action}")
