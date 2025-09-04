# ============================================
# core/weather.py - Weather Service Module
# ============================================
"""Weather service module for BingHome"""

import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = os.environ.get('WEATHER_API_KEY', '')
        self.location = os.environ.get('WEATHER_LOCATION', 'London')
        self.current_weather = {}
        self.forecast = []
        
    def get_current(self, location=None):
        """Get current weather"""
        location = location or self.location
        
        if not self.api_key:
            logger.warning("Weather API key not configured")
            return self.current_weather
        
        try:
            # Using OpenWeatherMap API as example
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.current_weather = {
                    'temp': round(data['main']['temp']),
                    'feels_like': round(data['main']['feels_like']),
                    'condition': data['weather'][0]['main'],
                    'description': data['weather'][0]['description'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'],
                    'location': data['name'],
                    'icon': data['weather'][0]['icon'],
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Weather updated for {location}")
                
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
        
        return self.current_weather
    
    def get_forecast(self, location=None, days=5):
        """Get weather forecast"""
        location = location or self.location
        
        if not self.api_key:
            return self.forecast
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/forecast"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.forecast = []
                
                # Group by day
                daily_forecasts = {}
                for item in data['list']:
                    date = item['dt_txt'].split(' ')[0]
                    if date not in daily_forecasts:
                        daily_forecasts[date] = {
                            'date': date,
                            'temps': [],
                            'conditions': [],
                            'descriptions': []
                        }
                    
                    daily_forecasts[date]['temps'].append(item['main']['temp'])
                    daily_forecasts[date]['conditions'].append(item['weather'][0]['main'])
                    daily_forecasts[date]['descriptions'].append(item['weather'][0]['description'])
                
                # Calculate daily summary
                for date, day_data in daily_forecasts.items():
                    self.forecast.append({
                        'date': date,
                        'temp_min': round(min(day_data['temps'])),
                        'temp_max': round(max(day_data['temps'])),
                        'condition': max(set(day_data['conditions']), key=day_data['conditions'].count),
                        'description': max(set(day_data['descriptions']), key=day_data['descriptions'].count)
                    })
                
                logger.info(f"Forecast updated for {location}")
                
        except Exception as e:
            logger.error(f"Forecast fetch error: {e}")
        
        return self.forecast[:days]
    
    def get_alerts(self, location=None):
        """Get weather alerts for location"""
        # This would connect to a weather alert service
        return []
