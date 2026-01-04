#!/usr/bin/env python3
"""Fix for Raspberry Pi 5 DHT22 sensor reading"""

import board
import adafruit_dht
import time
import json

# Read settings
with open('/home/rcook01/binghome/settings.json', 'r') as f:
    settings = json.load(f)

dht_pin = settings.get('gpio_pins', {}).get('dht22', 4)
pin = getattr(board, f'D{dht_pin}')

# Pi 5 requires use_pulseio=False
dht = adafruit_dht.DHT22(pin, use_pulseio=False)

print(f"Reading DHT22 on GPIO{dht_pin} (Pi 5 mode)...")

for attempt in range(10):
    try:
        temp = dht.temperature
        hum = dht.humidity
        
        if temp is not None and hum is not None:
            print(f"✓ SUCCESS: Temperature: {temp:.1f}°C, Humidity: {hum:.1f}%")
            print(f"\nYour sensor is working! Now update app.py with use_pulseio=False")
            break
    except RuntimeError as e:
        print(f"Attempt {attempt+1}: {e}")
    except Exception as e:
        print(f"Attempt {attempt+1}: Error - {e}")
    
    time.sleep(2.5)
else:
    print("\n❌ Sensor not responding - check wiring")

dht.exit()
