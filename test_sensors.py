#!/usr/bin/env python3
"""
BingHome Sensor Testing Script
Tests DHT22 and other sensors to diagnose issues
"""

import sys
import time
import json
from pathlib import Path

print("=" * 60)
print("BingHome Sensor Diagnostic Tool")
print("=" * 60)
print()

# Test 1: Check if running on Raspberry Pi
print("Test 1: Checking platform...")
try:
    with open('/proc/device-tree/model', 'r') as f:
        model = f.read()
        print(f"✓ Running on: {model.strip()}")
except:
    print("✗ Not running on Raspberry Pi or cannot detect model")
    print("  Sensors require Raspberry Pi hardware")
    sys.exit(1)

print()

# Test 2: Check GPIO availability
print("Test 2: Checking GPIO library...")
try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO installed and available")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
except ImportError:
    print("✗ RPi.GPIO not installed")
    print("  Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)
except Exception as e:
    print(f"✗ GPIO error: {e}")
    sys.exit(1)

print()

# Test 3: Check Adafruit libraries
print("Test 3: Checking Adafruit DHT library...")
try:
    import adafruit_dht
    import board
    print("✓ adafruit-circuitpython-dht installed")
except ImportError:
    print("✗ Adafruit DHT library not installed")
    print("  Install with: pip3 install adafruit-circuitpython-dht")
    print("  Or: sudo apt-get install python3-libgpiod")
    sys.exit(1)

print()

# Test 4: Load settings to get GPIO pin
print("Test 4: Loading settings...")
settings_file = Path(__file__).parent / "settings.json"
dht_pin = 4  # Default

if settings_file.exists():
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            dht_pin = settings.get('gpio_pins', {}).get('dht22', 4)
            print(f"✓ Settings loaded - DHT22 pin: GPIO{dht_pin}")
    except Exception as e:
        print(f"⚠ Settings load error: {e}")
        print(f"  Using default pin: GPIO{dht_pin}")
else:
    print(f"⚠ No settings.json found")
    print(f"  Using default pin: GPIO{dht_pin}")

print()

# Test 5: Check I2C (if using I2C sensors)
print("Test 5: Checking I2C interface...")
try:
    import smbus
    bus = smbus.SMBus(1)
    print("✓ I2C interface available")
except ImportError:
    print("⚠ smbus not installed (only needed for I2C sensors)")
except Exception as e:
    print(f"⚠ I2C error: {e}")

print()

# Test 6: Initialize DHT22 sensor
print("Test 6: Initializing DHT22 sensor...")
try:
    # Create DHT22 instance
    dht_device = adafruit_dht.DHT22(getattr(board, f'D{dht_pin}'))
    print(f"✓ DHT22 initialized on GPIO{dht_pin}")
except AttributeError:
    print(f"✗ Invalid pin: D{dht_pin}")
    print(f"  Valid pins: D4, D17, D18, D27, D22, D23, D24, D25")
    sys.exit(1)
except Exception as e:
    print(f"✗ DHT22 initialization error: {e}")
    sys.exit(1)

print()

# Test 7: Read sensor data
print("Test 7: Reading sensor data (this may take a few attempts)...")
print("DHT22 sensors can be slow and may need multiple reads...")
print()

successful_reads = 0
failed_reads = 0
max_attempts = 10

for attempt in range(1, max_attempts + 1):
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        
        if temperature is not None and humidity is not None:
            print(f"Attempt {attempt}: ✓ Success!")
            print(f"  Temperature: {temperature:.1f}°C")
            print(f"  Humidity: {humidity:.1f}%")
            successful_reads += 1
        else:
            print(f"Attempt {attempt}: ✗ Read returned None")
            failed_reads += 1
            
    except RuntimeError as error:
        print(f"Attempt {attempt}: ✗ RuntimeError - {error.args[0]}")
        failed_reads += 1
    except Exception as error:
        print(f"Attempt {attempt}: ✗ Unexpected error - {error}")
        failed_reads += 1
    
    # Wait before next read (DHT22 needs 2+ seconds between reads)
    if attempt < max_attempts:
        time.sleep(2.5)

print()
print("=" * 60)
print("Test Summary:")
print("=" * 60)
print(f"Successful reads: {successful_reads}/{max_attempts}")
print(f"Failed reads: {failed_reads}/{max_attempts}")
print()

if successful_reads == 0:
    print("❌ DIAGNOSIS: Sensor not working")
    print()
    print("Possible issues:")
    print("  1. Wiring problem - check connections:")
    print(f"     - DHT22 VCC → Raspberry Pi Pin 1 (3.3V)")
    print(f"     - DHT22 GND → Raspberry Pi Pin 6 (Ground)")
    print(f"     - DHT22 DATA → Raspberry Pi Pin {7 if dht_pin == 4 else 'check your pin'} (GPIO{dht_pin})")
    print(f"     - 10kΩ pull-up resistor between DATA and VCC")
    print()
    print("  2. Wrong GPIO pin configured")
    print(f"     - Currently using GPIO{dht_pin}")
    print(f"     - Check your physical wiring")
    print()
    print("  3. Defective sensor")
    print(f"     - Try a different DHT22 sensor")
    print()
    print("  4. Power supply issue")
    print(f"     - Ensure 3.3V is stable")
    
elif successful_reads < 5:
    print("⚠️  DIAGNOSIS: Sensor working but unstable")
    print()
    print("Recommendations:")
    print("  1. Add or check 10kΩ pull-up resistor")
    print("  2. Check wire connections (loose wires)")
    print("  3. Try shorter wires if using long cables")
    print("  4. Move sensor away from interference sources")
    
else:
    print("✅ DIAGNOSIS: Sensor working correctly!")
    print()
    print("Next steps:")
    print("  1. Check if BingHome service is running:")
    print("     sudo systemctl status binghome")
    print()
    print("  2. Check BingHome logs:")
    print("     sudo journalctl -u binghome -f")
    print()
    print("  3. Verify API endpoint:")
    print("     curl http://localhost:5000/api/sensor_data")
    print()
    print("  4. Check browser console for errors:")
    print("     Open browser DevTools (F12) on your hub page")

print()
print("=" * 60)

# Cleanup
try:
    dht_device.exit()
except:
    pass

GPIO.cleanup()
print("GPIO cleanup complete")
print()
