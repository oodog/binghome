#!/bin/bash
# ============================================
# DHT22 Sensor Test Script
# Tests temperature and humidity readings
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   DHT22 Sensor Test Utility        ${NC}"
echo -e "${CYAN}=====================================${NC}"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo -e "${YELLOW}Run the install script first: ./install.sh${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: Not running on Raspberry Pi${NC}"
    echo -e "${YELLOW}Sensor testing requires Raspberry Pi hardware${NC}"
    exit 1
fi

# Read GPIO pin from settings or use default
DHT_PIN=${1:-4}

echo -e "\n${BLUE}Testing DHT22 sensor on GPIO ${DHT_PIN}...${NC}"
echo -e "${YELLOW}Note: DHT22 sensors can be finicky. Multiple attempts may be needed.${NC}\n"

# Create Python test script
cat > /tmp/test_dht22.py << EOF
#!/usr/bin/env python3
"""
DHT22 Sensor Test Script
Reads temperature and humidity from DHT22 sensor
"""
import time
import sys

try:
    import board
    import adafruit_dht
except ImportError:
    print("Error: Required libraries not found")
    print("Install with: pip install adafruit-circuitpython-dht")
    sys.exit(1)

# Pin mapping
pin = ${DHT_PIN}
dht_pin = getattr(board, f'D{pin}')

print(f"Initializing DHT22 sensor on GPIO {pin} (D{pin})...")
dht = adafruit_dht.DHT22(dht_pin)

# Try multiple reads
max_attempts = 5
success_count = 0
failed_count = 0

print(f"\nAttempting {max_attempts} sensor reads...")
print("-" * 50)

for attempt in range(1, max_attempts + 1):
    try:
        print(f"\nAttempt {attempt}/{max_attempts}:")

        # Read sensor
        temperature = dht.temperature
        humidity = dht.humidity

        # Validate readings
        if temperature is not None and humidity is not None:
            print(f"  ✓ Temperature: {temperature:.1f}°C ({temperature * 9/5 + 32:.1f}°F)")
            print(f"  ✓ Humidity: {humidity:.1f}%")

            # Sanity check
            if -40 <= temperature <= 80 and 0 <= humidity <= 100:
                print("  ✓ Reading appears valid")
                success_count += 1
            else:
                print("  ⚠ Reading out of expected range")
                failed_count += 1
        else:
            print("  ✗ Sensor returned None values")
            failed_count += 1

    except RuntimeError as e:
        print(f"  ✗ RuntimeError: {e}")
        print("    (Common with DHT sensors - timing/checksum issues)")
        failed_count += 1

    except Exception as e:
        print(f"  ✗ Error: {e}")
        failed_count += 1

    # Wait before next read (DHT sensors need time between reads)
    if attempt < max_attempts:
        time.sleep(2)

# Cleanup
try:
    dht.exit()
except:
    pass

# Summary
print("\n" + "=" * 50)
print("TEST SUMMARY:")
print(f"  Successful reads: {success_count}/{max_attempts}")
print(f"  Failed reads: {failed_count}/{max_attempts}")

if success_count > 0:
    print("\n✓ Sensor is working!")
    sys.exit(0)
else:
    print("\n✗ Sensor test failed")
    print("\nTroubleshooting:")
    print("  1. Check wiring:")
    print("     • VCC (pin 1) -> 3.3V or 5V")
    print("     • DATA (pin 2) -> GPIO ${DHT_PIN}")
    print("     • GND (pin 4) -> GND")
    print("  2. Add 10kΩ pull-up resistor between VCC and DATA")
    print("  3. Ensure sensor has adequate power")
    print("  4. Try a different GPIO pin")
    print("  5. Test with a known working sensor")
    sys.exit(1)
EOF

# Run the test
python3 /tmp/test_dht22.py

# Cleanup
rm -f /tmp/test_dht22.py

echo -e "\n${GREEN}Test complete!${NC}"
