# core/weather.py
from typing import Dict, Any
import requests

def get_weather(lat: float, lon: float, tz: str = "auto") -> Dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&hourly=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        f"&timezone={tz}"
    )
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json()
