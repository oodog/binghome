# ============================================
# core/weather.py - Enhanced Weather Service Module
# ============================================
"""Enhanced weather service module for BingHome with configurable sources"""

import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.api_key = self.settings.get('weather_api_key', os.environ.get('WEATHER_API_KEY', ''))
        self.location = self.settings.get('weather_location', 'Gold Coast, QLD')
        self.weather_source = self.settings.get('weather_source', 'openweather')
        self.current_weather = {}
        self.forecast = []
        
        # Weather source configurations
        self.sources = {
            'openweather': {
                'name': 'OpenWeatherMap',
                'requires_api_key': True,
                'supports_location': True
            },
            'qld_radar': {
                'name': 'Queensland Radar',
                'requires_api_key': False,
                'supports_location': False,
                'radar_url': 'https://data.theweather.com.au/access/animators/radar/?lt=wzstate&user=10545v3&lc=qld'
            },
            'bom_australia': {
                'name': 'Bureau of Meteorology',
                'requires_api_key': False,
                'supports_location': True,
                'base_url': 'http://www.bom.gov.au'
            }
        }
        
    def update_settings(self, settings):
        """Update weather service settings"""
        self.settings = settings
        self.api_key = settings.get('weather_api_key', self.api_key)
        self.location = settings.get('weather_location', self.location)
        self.weather_source = settings.get('weather_source', self.weather_source)
        
    def get_available_sources(self):
        """Get list of available weather sources"""
        return {
            source_id: {
                'name': config['name'],
                'requires_api_key': config['requires_api_key'],
                'supports_location': config['supports_location'],
                'configured': self._is_source_configured(source_id)
            }
            for source_id, config in self.sources.items()
        }
    
    def _is_source_configured(self, source_id):
        """Check if a weather source is properly configured"""
        config = self.sources.get(source_id, {})
        if config.get('requires_api_key') and not self.api_key:
            return False
        return True
    
    def get_current(self, location=None):
        """Get current weather data from configured source"""
        location = location or self.location
        
        if self.weather_source == 'openweather':
            return self._get_openweather_current(location)
        elif self.weather_source == 'qld_radar':
            return self._get_qld_default_weather(location)
        elif self.weather_source == 'bom_australia':
            return self._get_bom_weather(location)
        else:
            return self._get_default_weather(location)
    
    def _get_openweather_current(self, location):
        """Get current weather from OpenWeatherMap"""
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return self._get_default_weather(location)
        
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
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
                    'description': data['weather'][0]['description'].title(),
                    'humidity': data['main']['humidity'],
                    'pressure': data['main'].get('pressure', 0),
                    'wind_speed': round(data['wind'].get('speed', 0) * 3.6, 1),  # Convert m/s to km/h
                    'wind_direction': data['wind'].get('deg', 0),
                    'visibility': data.get('visibility', 0) / 1000 if data.get('visibility') else 0,  # Convert to km
                    'uv_index': 0,  # Not available in current weather API
                    'location': data['name'],
                    'country': data['sys']['country'],
                    'icon': data['weather'][0]['icon'],
                    'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                    'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'OpenWeatherMap',
                    'radar_available': False
                }
                logger.info(f"OpenWeather data updated for {location}")
                
        except Exception as e:
            logger.error(f"OpenWeather API error: {e}")
            return self._get_default_weather(location)
        
        return self.current_weather
    
    def _get_qld_default_weather(self, location):
        """Get Queensland weather with radar integration"""
        # Since Queensland radar doesn't provide current weather data,
        # we'll provide default values optimized for Queensland
        self.current_weather = {
            'temp': 24,
            'feels_like': 26,
            'condition': 'Partly Cloudy',
            'description': 'Partly Cloudy',
            'humidity': 68,
            'pressure': 1013,
            'wind_speed': 15.2,
            'wind_direction': 135,
            'visibility': 10,
            'uv_index': 8,
            'location': 'Gold Coast',
            'country': 'AU',
            'icon': '02d',
            'sunrise': '06:30',
            'sunset': '18:45',
            'timestamp': datetime.now().isoformat(),
            'source': 'Queensland Radar',
            'radar_available': True,
            'radar_url': self.sources['qld_radar']['radar_url'],
            'radar_description': 'Live weather radar showing precipitation and storm activity across Queensland'
        }
        
        return self.current_weather
    
    def _get_bom_weather(self, location):
        """Get weather from Bureau of Meteorology (placeholder)"""
        # This would require scraping BOM data or using their API if available
        return self._get_default_weather(location)
    
    def _get_default_weather(self, location):
        """Fallback default weather data"""
        return {
            'temp': 22,
            'feels_like': 23,
            'condition': 'Clear',
            'description': 'Clear Sky',
            'humidity': 60,
            'pressure': 1013,
            'wind_speed': 8.5,
            'wind_direction': 180,
            'visibility': 10,
            'uv_index': 5,
            'location': location,
            'country': 'AU',
            'icon': '01d',
            'sunrise': '06:45',
            'sunset': '18:30',
            'timestamp': datetime.now().isoformat(),
            'source': 'Default',
            'radar_available': False
        }
    
    def get_forecast(self, location=None, days=7):
        """Get weather forecast"""
        location = location or self.location
        
        if self.weather_source == 'openweather':
            return self._get_openweather_forecast(location, days)
        else:
            return self._get_default_forecast(days)
    
    def _get_openweather_forecast(self, location, days):
        """Get forecast from OpenWeatherMap"""
        if not self.api_key:
            return self._get_default_forecast(days)
        
        try:
            # Use 5-day forecast API
            url = "http://api.openweathermap.org/data/2.5/forecast"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Group by day and calculate daily summary
                daily_forecasts = {}
                for item in data['list']:
                    date_str = item['dt_txt'].split(' ')[0]
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    day_key = date_str
                    
                    if day_key not in daily_forecasts:
                        daily_forecasts[day_key] = {
                            'date': date_str,
                            'day_name': date.strftime('%A'),
                            'day_short': date.strftime('%a'),
                            'temps': [],
                            'conditions': [],
                            'descriptions': [],
                            'humidity': [],
                            'wind_speeds': [],
                            'pop': []  # Probability of precipitation
                        }
                    
                    daily_forecasts[day_key]['temps'].append(item['main']['temp'])
                    daily_forecasts[day_key]['conditions'].append(item['weather'][0]['main'])
                    daily_forecasts[day_key]['descriptions'].append(item['weather'][0]['description'])
                    daily_forecasts[day_key]['humidity'].append(item['main']['humidity'])
                    daily_forecasts[day_key]['wind_speeds'].append(item['wind'].get('speed', 0) * 3.6)
                    daily_forecasts[day_key]['pop'].append(item.get('pop', 0) * 100)
                
                # Calculate daily summary
                self.forecast = []
                for day_key in sorted(daily_forecasts.keys())[:days]:
                    day_data = daily_forecasts[day_key]
                    self.forecast.append({
                        'date': day_data['date'],
                        'day_name': day_data['day_name'],
                        'day_short': day_data['day_short'],
                        'temp_min': round(min(day_data['temps'])),
                        'temp_max': round(max(day_data['temps'])),
                        'temp_avg': round(sum(day_data['temps']) / len(day_data['temps'])),
                        'condition': max(set(day_data['conditions']), key=day_data['conditions'].count),
                        'description': max(set(day_data['descriptions']), key=day_data['descriptions'].count).title(),
                        'humidity_avg': round(sum(day_data['humidity']) / len(day_data['humidity'])),
                        'wind_speed_avg': round(sum(day_data['wind_speeds']) / len(day_data['wind_speeds']), 1),
                        'precipitation_chance': round(max(day_data['pop'])) if day_data['pop'] else 0,
                        'icon': '01d'  # Would need to determine from conditions
                    })
                
                logger.info(f"Forecast updated for {location}")
                
        except Exception as e:
            logger.error(f"Forecast API error: {e}")
            return self._get_default_forecast(days)
        
        return self.forecast
    
    def _get_default_forecast(self, days):
        """Generate default forecast data"""
        conditions = ['Sunny', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Clear', 'Scattered Clouds']
        descriptions = ['Sunny', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Clear Sky', 'Scattered Clouds']
        
        forecast = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            condition_idx = i % len(conditions)
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'day_name': date.strftime('%A'),
                'day_short': date.strftime('%a'),
                'temp_min': 18 + (i % 5),
                'temp_max': 26 + (i % 6),
                'temp_avg': 22 + (i % 4),
                'condition': conditions[condition_idx],
                'description': descriptions[condition_idx],
                'humidity_avg': 65 + (i % 20),
                'wind_speed_avg': 10.5 + (i % 8),
                'precipitation_chance': (i * 15) % 80,
                'icon': '01d'
            })
        
        return forecast
    
    def get_radar_info(self):
        """Get radar information for current source"""
        if self.weather_source == 'qld_radar':
            return {
                'available': True,
                'url': self.sources['qld_radar']['radar_url'],
                'title': 'Queensland Weather Radar',
                'description': 'Live weather radar showing precipitation and storm activity across Queensland',
                'update_frequency': 'Every 10 minutes',
                'coverage': 'Queensland state-wide',
                'type': 'precipitation_radar'
            }
        elif self.weather_source == 'openweather':
            # Use RainViewer for radar overlay
            return {
                'available': True,
                'url': 'https://www.rainviewer.com/map.html',
                'title': 'Weather Radar',
                'description': 'Live weather radar showing precipitation worldwide',
                'update_frequency': 'Every 10 minutes',
                'coverage': 'Global',
                'type': 'precipitation_radar'
            }
        else:
            return {
                'available': False,
                'message': f'Radar not available for {self.sources.get(self.weather_source, {}).get("name", "current source")}'
            }
    
    def get_weather_alerts(self, location=None):
        """Get weather alerts and warnings"""
        # This would integrate with weather alert APIs
        alerts = []
        
        current = self.get_current(location)
        
        # Generate example alerts based on conditions
        if current.get('wind_speed', 0) > 40:
            alerts.append({
                'type': 'wind',
                'severity': 'moderate',
                'title': 'Strong Wind Warning',
                'description': f"Winds exceeding {current['wind_speed']} km/h",
                'issued': datetime.now().isoformat(),
                'expires': (datetime.now() + timedelta(hours=6)).isoformat()
            })
        
        if current.get('condition', '').lower() in ['thunderstorm', 'storm']:
            alerts.append({
                'type': 'storm',
                'severity': 'high',
                'title': 'Severe Thunderstorm Warning',
                'description': 'Severe thunderstorms with heavy rain and strong winds possible',
                'issued': datetime.now().isoformat(),
                'expires': (datetime.now() + timedelta(hours=3)).isoformat()
            })
        
        return alerts
    
    def get_comprehensive_weather(self, location=None):
        """Get complete weather information"""
        current = self.get_current(location)
        forecast = self.get_forecast(location, 7)
        radar = self.get_radar_info()
        alerts = self.get_weather_alerts(location)
        
        return {
            'current': current,
            'forecast': forecast,
            'forecast_summary': {
                'next_24h': forecast[0] if forecast else None,
                'week_outlook': 'Variable conditions expected' if forecast else 'No forecast available'
            },
            'radar': radar,
            'alerts': alerts,
            'location': current.get('location', location or self.location),
            'source': current.get('source', self.weather_source),
            'last_updated': datetime.now().isoformat(),
            'settings': {
                'weather_source': self.weather_source,
                'location': self.location,
                'api_configured': bool(self.api_key)
            }
        }
    
    def get_weather_recommendations(self):
        """Get weather-based activity recommendations"""
        current = self.get_current()
        
        temp = current.get('temp', 20)
        condition = current.get('condition', '').lower()
        wind_speed = current.get('wind_speed', 0)
        uv_index = current.get('uv_index', 0)
        
        recommendations = []
        
        # Temperature recommendations
        if temp > 30:
            recommendations.append({
                'type': 'caution',
                'title': 'Hot Weather',
                'message': 'Stay hydrated and seek shade during outdoor activities'
            })
        elif temp < 10:
            recommendations.append({
                'type': 'caution',
                'title': 'Cold Weather',
                'message': 'Dress warmly for outdoor activities'
            })
        elif 18 <= temp <= 25:
            recommendations.append({
                'type': 'ideal',
                'title': 'Perfect Weather',
                'message': 'Ideal conditions for outdoor activities'
            })
        
        # UV recommendations
        if uv_index > 7:
            recommendations.append({
                'type': 'caution',
                'title': 'High UV',
                'message': 'Use sunscreen and wear protective clothing'
            })
        
        # Wind recommendations
        if wind_speed > 25:
            recommendations.append({
                'type': 'caution',
                'title': 'Windy Conditions',
                'message': 'Be cautious with outdoor activities'
            })
        
        # Condition-based recommendations
        if 'rain' in condition:
            recommendations.append({
                'type': 'info',
                'title': 'Rainy Weather',
                'message': 'Consider indoor activities or bring an umbrella'
            })
        elif condition in ['clear', 'sunny']:
            recommendations.append({
                'type': 'ideal',
                'title': 'Great Weather',
                'message': 'Perfect time for outdoor activities'
            })
        
        return recommendations
