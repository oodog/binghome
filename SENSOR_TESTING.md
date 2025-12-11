# DHT22 Sensor Testing Guide

This guide explains how to test the DHT22 temperature and humidity sensor from the command line on your Raspberry Pi.

## Quick Test

The easiest way to test the sensor is using the provided test script:

```bash
cd /home/$USER/binghome
./test-dht22.sh
```

This will automatically test the DHT22 sensor on GPIO pin 4 (default) with multiple read attempts.

### Test with a Different GPIO Pin

If your sensor is connected to a different GPIO pin:

```bash
./test-dht22.sh 17   # Tests sensor on GPIO 17
```

## Manual Testing from Python CLI

You can also test the sensor directly from the Python REPL:

### 1. Activate the Virtual Environment

```bash
cd /home/$USER/binghome
source venv/bin/activate
```

### 2. Start Python and Test the Sensor

```python
python3
```

Then in the Python interpreter:

```python
import time
import board
import adafruit_dht

# Initialize sensor (change D4 to match your GPIO pin)
dht = adafruit_dht.DHT22(board.D4)

# Read sensor (may need multiple attempts)
for i in range(5):
    try:
        temperature = dht.temperature
        humidity = dht.humidity

        if temperature is not None and humidity is not None:
            print(f"Temperature: {temperature:.1f}°C ({temperature * 9/5 + 32:.1f}°F)")
            print(f"Humidity: {humidity:.1f}%")
            break
        else:
            print(f"Attempt {i+1}: No data")
    except RuntimeError as e:
        print(f"Attempt {i+1}: {e}")

    time.sleep(2)

# Cleanup
dht.exit()
```

### 3. Exit Python

```python
exit()
```

## Command Line One-Liner

For a quick single test:

```bash
cd /home/$USER/binghome
source venv/bin/activate
python3 -c "
import board, adafruit_dht, time
dht = adafruit_dht.DHT22(board.D4)
try:
    for _ in range(3):
        try:
            t, h = dht.temperature, dht.humidity
            if t and h: print(f'Temp: {t:.1f}°C, Humidity: {h:.1f}%'); break
        except: time.sleep(2)
finally: dht.exit()
"
```

## Checking BingHome Hub Sensor Readings

You can also check sensor readings through the BingHome Hub API:

```bash
curl http://localhost:5000/api/sensor_data
```

This will return JSON with current sensor readings:

```json
{
  "temperature": 24.5,
  "humidity": 62.3,
  "gas_detected": false,
  "light_level": "bright",
  "air_quality": "good",
  "timestamp": "2024-01-15T10:30:00"
}
```

## GPIO Pin Reference

Common GPIO pins on Raspberry Pi (BCM numbering):

| Physical Pin | GPIO (BCM) | Board Pin Name |
|--------------|------------|----------------|
| 7            | 4          | D4             |
| 11           | 17         | D17            |
| 12           | 18         | D18            |
| 13           | 27         | D27            |
| 15           | 22         | D22            |
| 16           | 23         | D23            |

The DHT22 sensor should be connected as follows:
- **VCC (pin 1)** → 3.3V or 5V power
- **DATA (pin 2)** → GPIO pin (e.g., GPIO 4)
- **NC (pin 3)** → Not connected
- **GND (pin 4)** → Ground

**Important:** Add a 10kΩ pull-up resistor between VCC and DATA for reliable readings.

## Troubleshooting

### "RuntimeError" or checksum errors

This is common with DHT sensors due to timing issues. Solutions:
1. Run the test multiple times
2. Increase delay between reads (minimum 2 seconds)
3. Check the pull-up resistor (10kΩ)
4. Verify power supply is stable

### "No module named 'board'" or "'adafruit_dht'"

Install the required packages:

```bash
cd /home/$USER/binghome
source venv/bin/activate
pip install adafruit-circuitpython-dht
```

### Sensor always returns None

1. Check physical connections
2. Verify the correct GPIO pin number
3. Ensure the sensor has adequate power
4. Test with a known working sensor
5. Try a different GPIO pin

### Permission denied

Add your user to the GPIO group:

```bash
sudo usermod -a -G gpio $USER
```

Then log out and back in.

## Testing from the Web Interface

1. Open BingHome Hub: `http://localhost:5000`
2. The dashboard should display current temperature and humidity
3. Click on the system status page for detailed sensor information
4. Sensor data updates automatically every 5 seconds

## Viewing Sensor Logs

Check BingHome Hub logs for sensor-related messages:

```bash
# Real-time logs
binghome logs

# Or directly:
sudo journalctl -u binghome -f | grep -i sensor
```

## Alternative: Testing with Raspberry Pi GPIO Library

If the Adafruit library doesn't work, you can try the alternative DHT library:

```bash
pip install Adafruit_DHT
```

Then test:

```python
import Adafruit_DHT

sensor = Adafruit_DHT.DHT22
pin = 4

humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

if humidity is not None and temperature is not None:
    print(f'Temp={temperature:.1f}°C  Humidity={humidity:.1f}%')
else:
    print('Failed to get reading')
```

## Support

For issues or questions:
- Check wiring diagram in the hardware documentation
- Review logs: `binghome logs`
- Create an issue on GitHub: https://github.com/oodog/binghome/issues
