# BingHome Hub - Quick Start Guide

## What's New?

Your BingHome Hub has been upgraded with professional smart home features:

✅ **Advanced Weather** - Live radar, 7-day forecast, weather alerts
✅ **Smart Device Discovery** - Find and control WiFi, Bluetooth, and Home Assistant devices
✅ **Optimized UI** - Perfect for your 7-inch touchscreen (1024x600)
✅ **Back Navigation** - Swipe from left edge or use back button
✅ **Voice Feedback** - Visual indicator shows when voice control is listening
✅ **Device Control** - Turn lights on/off, control switches, view sensors
✅ **Home Assistant** - Full integration with your Home Assistant setup

## Quick Installation

```bash
cd /home/rcook01/binghome
./install_enhancements.sh
```

The script will guide you through:
1. Installing network scanning tools (nmap, arp-scan)
2. Installing Bluetooth support (optional)
3. Installing Python dependencies
4. Setting up permissions
5. Testing the installation
6. Configuring autostart (optional)

## Manual Installation

If you prefer manual setup:

```bash
# 1. Install system packages
sudo apt-get update
sudo apt-get install nmap arp-scan bluetooth libbluetooth-dev

# 2. Install Python packages
cd /home/rcook01/binghome
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart BingHome
sudo systemctl restart binghome
# or
./start.sh
```

## Configuration

### 1. Weather Setup

**Option A: OpenWeatherMap (Recommended)**
1. Get free API key from https://openweathermap.org/api
2. Open BingHome Settings
3. Enter API key in "Weather API Key" field
4. Set location to "Gold Coast, QLD" (or your location)
5. Select "OpenWeatherMap" as weather source
6. Save settings

**Option B: Queensland Radar (No API key needed)**
1. Open BingHome Settings
2. Select "Queensland Radar" as weather source
3. Save settings

### 2. Home Assistant Setup

1. **Generate Token in Home Assistant:**
   - Open Home Assistant
   - Click your profile (bottom left)
   - Scroll to "Long-Lived Access Tokens"
   - Click "Create Token"
   - Give it a name like "BingHome"
   - Copy the token (you won't see it again!)

2. **Configure BingHome:**
   - Open BingHome Settings
   - Enter Home Assistant URL: `http://homeassistant.local:8123`
   - Paste the access token
   - Save settings

3. **Test It:**
   - Click "Devices" app on home screen
   - Click "🔍 Scan Devices"
   - You should see your Home Assistant devices!

### 3. Display Optimization

For your 7-inch display:

1. **Set Resolution:**
   ```bash
   sudo raspi-config
   # Navigate to: Display Options → Resolution → 1024x600
   ```

2. **Auto-start Browser (Optional):**
   ```bash
   # Edit autostart
   mkdir -p ~/.config/lxsession/LXDE-pi/
   nano ~/.config/lxsession/LXDE-pi/autostart

   # Add this line:
   @chromium-browser --kiosk --noerrors --disable-session-crashed-bubble http://localhost:5000
   ```

3. **Disable Screen Blanking:**
   ```bash
   sudo raspi-config
   # Navigate to: Display Options → Screen Blanking → No
   ```

## Using Your New Features

### Weather Radar
- **Tap** on the weather widget to see live radar
- **Tap again** to return to current weather
- Updates automatically every 10 minutes

### Device Discovery
1. Click **"Devices"** app tile
2. Click **"🔍 Scan Devices"**
3. Wait 30-60 seconds for scan to complete
4. See all discovered devices organized by type
5. Tap **"Turn On/Off"** to control lights and switches

### Voice Control
- Look for the **microphone icon** (🎤) in the top right corner
- Icon pulses when voice control is active
- Say: **"Hey Bing"** or **"Okay Bing"**
- Full-screen overlay appears when listening
- Give your command: "show weather", "open Netflix", "show devices"

### Navigation
- **Swipe from left edge** to go back (like a phone)
- **◀ Back button** on all sub-pages
- **🏠 Home button** when in apps
- **⚙️ Settings** button in bottom right corner

## Troubleshooting

### "No devices found" when scanning
```bash
# Test network scanning
sudo arp-scan -l

# Test nmap
nmap -sn 192.168.1.0/24

# Check Home Assistant token in settings
```

### Weather not loading
1. Check internet connection
2. Verify API key in settings
3. Try switching to "Queensland Radar" (no API needed)

### Voice control not working
1. Open browser console (F12)
2. Check for microphone permission prompt
3. Use Chromium/Chrome browser (best compatibility)
4. Check wake words in settings

### UI doesn't fit screen
1. Set display resolution to 1024x600
2. Press F11 for fullscreen mode
3. Use `--kiosk` flag when starting browser

### Can't control Home Assistant devices
1. Verify Home Assistant URL is correct
2. Check access token hasn't expired
3. Make sure devices are online in Home Assistant
4. Check logs: `tail -f /home/rcook01/binghome/logs/binghome.log`

## File Locations

```
/home/rcook01/binghome/
├── app.py                      - Main application
├── settings.json               - Your settings
├── start.sh                    - Start script
├── install_enhancements.sh     - NEW: Installation script
├── ENHANCEMENTS.md             - NEW: Full documentation
├── QUICK_START.md              - NEW: This file
├── core/
│   ├── weather.py              - Weather service
│   └── device_discovery.py     - NEW: Device discovery
├── templates/
│   ├── hub_enhanced.html       - NEW: Main UI
│   └── devices.html            - NEW: Devices page
└── logs/
    └── binghome.log            - Application logs
```

## Quick Commands

```bash
# Start BingHome
cd /home/rcook01/binghome
./start.sh

# Restart service
sudo systemctl restart binghome

# View logs
tail -f /home/rcook01/binghome/logs/binghome.log

# Check status
sudo systemctl status binghome

# Stop service
sudo systemctl stop binghome

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt
```

## Tips & Tricks

1. **First-time Setup:**
   - Run device scan when devices are on and active
   - Start with Home Assistant integration first
   - Test voice control with simple commands

2. **Performance:**
   - Device scanning runs in background (doesn't block UI)
   - Weather updates every 10 minutes
   - Sensors update every 5 seconds

3. **Touchscreen:**
   - All buttons are touch-optimized (large tap targets)
   - Swipe gestures work like smartphones
   - No need for mouse/keyboard

4. **Voice Commands:**
   - Keep commands short and clear
   - Wait for overlay before speaking command
   - Say wake word clearly: "Hey Bing" or "Okay Bing"

5. **Weather Radar:**
   - Queensland users get state-wide radar
   - Others get global radar via RainViewer
   - Click weather widget to toggle views

## Support & Resources

- **Full Documentation:** [ENHANCEMENTS.md](ENHANCEMENTS.md)
- **Original README:** [readme.md](readme.md)
- **GitHub Issues:** https://github.com/oodog/binghome/issues
- **Home Assistant:** https://www.home-assistant.io/
- **OpenWeatherMap:** https://openweathermap.org/

## Next Steps

1. ✅ Run installation script
2. ✅ Configure weather API
3. ✅ Connect Home Assistant
4. ✅ Scan for devices
5. ✅ Test voice control
6. ✅ Set up auto-start (optional)
7. ✅ Configure display settings
8. 🎉 Enjoy your smart home hub!

---

Need help? Check the logs first:
```bash
tail -f /home/rcook01/binghome/logs/binghome.log
```

Happy smart home automation! 🏠✨
