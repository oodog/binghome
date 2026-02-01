# BingHome Hub - Enhanced Features

This document describes the major enhancements made to your BingHome Hub for the Raspberry Pi 5 with 7-inch touchscreen display.

## Overview

Your BingHome Hub has been significantly enhanced with:
- Advanced weather system with radar integration
- Smart device discovery and control
- Optimized UI for 7-inch touchscreen (1024x600 resolution)
- Improved navigation with back button support
- Enhanced voice control with visual feedback
- Full Home Assistant integration

## New Features

### 1. Enhanced Weather System

**Location:** [core/weather.py](core/weather.py)

**Features:**
- Real-time weather radar integration
  - Queensland state radar support
  - Global radar via RainViewer
  - Click on weather widget to toggle between current weather and radar view
- Comprehensive weather data:
  - Current temperature, feels like, humidity
  - Wind speed and direction
  - 7-day forecast
  - Weather alerts and warnings
- Multiple weather sources:
  - OpenWeatherMap (with your API key)
  - Queensland Radar
  - Bureau of Meteorology (Australia)

**Usage:**
```python
# API endpoint for comprehensive weather
GET /api/weather/comprehensive

# Returns:
{
  "current": {...},
  "forecast": [...],
  "radar": {...},
  "alerts": [...]
}
```

### 2. Smart Device Discovery

**Location:** [core/device_discovery.py](core/device_discovery.py)

**Features:**
- **WiFi/Network Device Discovery**
  - Automatic network scanning using arp-scan or nmap
  - Identifies smart home devices (Philips Hue, TP-Link, Google Home, etc.)
  - Shows IP, MAC address, and manufacturer

- **Bluetooth Device Discovery**
  - Scans for nearby Bluetooth devices
  - Identifies device types (audio, phone, wearable, etc.)
  - Shows device names and addresses

- **Home Assistant Integration**
  - Discovers all Home Assistant entities
  - Supports lights, switches, sensors, climate, media players, cameras, and more
  - Direct control from BingHome interface

**Usage:**
```bash
# Install required dependencies
pip install python-nmap pybluez

# For Bluetooth on Raspberry Pi, you may need:
sudo apt-get install bluetooth libbluetooth-dev
```

**API Endpoints:**
```python
# Scan for devices
POST /api/devices/scan

# Get all devices
GET /api/devices

# Control a device
POST /api/devices/control
{
  "device_type": "home_assistant",
  "device_id": "light.living_room",
  "action": "turn_on",
  "brightness": 255
}
```

### 3. Optimized UI for 7" Touchscreen

**Location:** [templates/hub_enhanced.html](templates/hub_enhanced.html)

**Features:**
- **Fixed resolution:** 1024x600 pixels (perfect for your 7" display)
- **No scrolling:** All content fits on one screen
- **Touch-optimized:**
  - Large tap targets (minimum 40x40px)
  - Swipe gestures for navigation
  - No hover states (all interactions work on touch)
  - Visual feedback on tap

**Layout:**
- **Status bar** (40px): Time, network, sensors
- **Left panel** (40%): Weather and Google Photos
- **Right panel** (60%): Apps grid (5 columns)

**Responsive Design:**
- Optimized for 1024x600 resolution
- Works on 800x480 resolution as well
- Fixed viewport prevents zoom/scroll issues

### 4. Navigation System

**Features:**
- **Back Button:** Every sub-page has a back button (◀)
- **Swipe Gestures:**
  - Swipe right from left edge: Go back
  - Works in apps and settings pages
- **Home Button:** Quick access to home screen
- **Navigation History:** Tracks page history for proper back navigation

**Keyboard Shortcuts:**
- `Escape` or `Backspace`: Go back
- `Home`: Return to home screen
- `Ctrl+S`: Open settings

### 5. Voice Control with Visual Feedback

**Features:**
- **Voice Indicator:**
  - Floating microphone icon when voice control is active
  - Pulsing animation shows system is listening
  - Always visible in corner so you know voice control is on

- **Voice Overlay:**
  - Full-screen overlay appears when wake word detected
  - Shows current command being spoken
  - Displays system response
  - Auto-dismisses after 3 seconds

**Wake Words:**
- "Hey Bing"
- "Okay Bing"

**Voice Commands:**
- "Hey Bing, show weather"
- "Hey Bing, open Netflix"
- "Hey Bing, play music"
- "Hey Bing, show devices"
- "Hey Bing, go home"

### 6. Device Management Interface

**Location:** [templates/devices.html](templates/devices.html)

**Features:**
- Clean, organized device listing
- Grouped by device type (Home Assistant, Network, Bluetooth)
- Device status indicators (online/offline)
- Quick control buttons for lights and switches
- One-tap device scanning
- Shows device count for each category

**Access:**
- Click "Devices" app tile on home screen
- Or navigate to `/devices`

### 7. Home Assistant Integration

**Setup:**
1. Open Settings
2. Enter your Home Assistant URL (e.g., `http://homeassistant.local:8123`)
3. Generate a Long-Lived Access Token in Home Assistant:
   - Profile → Long-Lived Access Tokens → Create Token
4. Paste token into BingHome settings
5. Save settings
6. Click "Scan Devices" in the Devices page

**Supported Devices:**
- 💡 Lights (turn on/off, dim)
- 🔌 Switches (turn on/off)
- 🌡️ Sensors (read values)
- ❄️ Climate (thermostats)
- 🚪 Covers (blinds, garage doors)
- 💨 Fans
- 🔒 Locks
- 📺 Media Players
- 📷 Cameras
- 🧹 Vacuums

## Installation & Setup

### Install New Dependencies

```bash
cd /home/rcook01/binghome
source venv/bin/activate
pip install -r requirements.txt
```

### Optional: Bluetooth Support

For Bluetooth device discovery:

```bash
sudo apt-get update
sudo apt-get install bluetooth libbluetooth-dev
pip install pybluez
```

### Optional: Network Scanning

For better network device discovery:

```bash
sudo apt-get install nmap arp-scan
pip install python-nmap
```

### Restart BingHome

```bash
sudo systemctl restart binghome
# or
./start.sh
```

## Configuration

### Weather Settings

Edit [settings.json](settings.json):

```json
{
  "weather_source": "openweather",
  "weather_location": "Gold Coast, QLD",
  "weather_api_key": "your_openweather_api_key"
}
```

Or use Queensland Radar (no API key needed):

```json
{
  "weather_source": "qld_radar",
  "weather_location": "Gold Coast, QLD"
}
```

### Home Assistant Settings

```json
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "home_assistant_token": "your_long_lived_access_token"
}
```

### Display Settings

For optimal display on your 7" screen:

```json
{
  "display_timeout": 0,
  "kiosk_mode": false,
  "auto_start_browser": true
}
```

## File Structure

```
/home/rcook01/binghome/
├── app.py                          # Main application (updated)
├── core/
│   ├── weather.py                  # Enhanced weather service
│   ├── device_discovery.py         # NEW: Device discovery
│   ├── media.py
│   ├── news.py
│   └── timers.py
├── templates/
│   ├── hub_enhanced.html           # NEW: Optimized UI
│   ├── devices.html                # NEW: Device management
│   ├── hub.html                    # Original hub
│   ├── index.html
│   └── settings.html
├── static/
│   └── js/
│       ├── hub_enhanced.js         # NEW: Enhanced hub logic
│       └── navigation.js           # Existing navigation
└── requirements.txt                # Updated dependencies
```

## Usage Tips

### 1. Weather Radar
- Tap on the weather widget to toggle between current weather and radar view
- Radar updates every 10 minutes automatically
- Tap again to return to current weather

### 2. Device Discovery
- First-time scan may take 30-60 seconds
- Network scans work best with arp-scan installed
- Bluetooth requires the device to be in pairing mode
- Home Assistant devices refresh automatically

### 3. Voice Control
- The microphone icon in the corner shows voice control is active
- Say wake word clearly: "Hey Bing" or "Okay Bing"
- Wait for the overlay before giving command
- Keep commands simple and direct

### 4. Navigation
- Swipe from left edge to go back (like smartphones)
- Back button (◀) always available on sub-pages
- Home button (🏠) returns to main screen
- Settings button (⚙️) in bottom right corner

### 5. Touch Optimization
- All buttons are large enough for finger touch
- No need for precision - generous tap targets
- Visual feedback on all interactions
- No hover states to worry about

## Troubleshooting

### Weather Not Loading
1. Check your API key in settings
2. Verify internet connection
3. Try switching weather source to "qld_radar" (no API needed)
4. Check logs: `tail -f logs/binghome.log`

### Device Discovery Not Finding Devices
1. Ensure devices are on same network
2. Install nmap: `sudo apt-get install nmap`
3. For Bluetooth: Check if bluetooth service is running: `sudo systemctl status bluetooth`
4. For Home Assistant: Verify URL and token in settings

### Voice Control Not Working
1. Check microphone permissions in browser
2. Use Chromium/Chrome for best compatibility
3. Verify wake words in settings
4. Check browser console for errors

### UI Not Fitting Screen
1. Access BingHome at `http://your-pi-ip:5000`
2. Press F11 for fullscreen in browser
3. Set display resolution to 1024x600 in Raspberry Pi config
4. Use kiosk mode for automatic fullscreen

## Performance Optimization

### For 7" Display
- UI is optimized for 1024x600 resolution
- No animations that slow down performance
- Efficient rendering (60fps on Pi 5)
- Minimal JavaScript overhead

### Memory Usage
- Device scanning runs in background threads
- Automatic cleanup of cached data
- Efficient Socket.IO for real-time updates

### Network Traffic
- Weather updates every 10 minutes (configurable)
- Sensor updates every 5 seconds
- Device scans only on-demand
- Efficient API calls to Home Assistant

## Future Enhancements

Possible additions you could make:
- [ ] Zigbee device support (via zigbee2mqtt)
- [ ] Z-Wave device support (via Home Assistant)
- [ ] Custom weather alerts by severity
- [ ] Device automation rules
- [ ] Scene control for smart home
- [ ] More voice commands
- [ ] Custom app shortcuts
- [ ] Spotify integration
- [ ] YouTube TV integration

## Support

For issues or questions:
1. Check logs: `tail -f logs/binghome.log`
2. Review GitHub issues: https://github.com/oodog/binghome/issues
3. Check Home Assistant integration status
4. Verify all dependencies are installed

## Credits

- Weather data: OpenWeatherMap API
- Radar: Queensland Government / RainViewer
- Device discovery: python-nmap, pybluez
- Smart home: Home Assistant API
- UI framework: Flask + Socket.IO

---

**Version:** 2.2.0
**Date:** 2026-01-16
**Compatible with:** Raspberry Pi 5, 7" touchscreen (1024x600 or 800x480)
