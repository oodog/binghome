# BingHome - Smart Home Hub for Raspberry Pi

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/oodog/binghome)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%205-red.svg)](https://www.raspberrypi.org/)

A modern smart home control system optimized for Raspberry Pi 5 with a 7-inch touchscreen (1024x600). Features voice control, Google Photos slideshow, security cameras, sensor monitoring, and more.

![BingHome Dashboard](docs/images/dashboard-preview.png)

## Features

### Core Features
- **Touchscreen Optimized UI** - Designed for 7" 1024x600 displays with large touch targets
- **Voice Control** - Multiple voice engines: Whisper, Vosk, or Google Speech
- **AI Assistant** - ChatGPT/OpenAI integration for natural language understanding
- **Real-time Updates** - WebSocket-based live sensor data and notifications

### Photo Slideshow
- **Google Photos Shared Albums** - Just paste a shared album link (no OAuth required!)
- **Google Photos OAuth** - Full album access with OAuth authentication
- **Configurable Intervals** - 2s, 5s, 10s, 15s, 20s, 30s, 45s, or 60s between photos
- **Pi-Optimized Loading** - Smaller image sizes for smooth performance

### Camera System
- **Pi Camera Support** - Raspberry Pi Camera Module v2/v3
- **USB Cameras** - Auto-detection and streaming
- **Security Cameras** - RTSP streaming with vendor presets:
  - Hikvision
  - Reolink
  - TP-Link Tapo
  - Generic RTSP
- **Network Discovery** - Automatic camera detection on your network
- **Live Snapshots** - Capture and view camera snapshots

### Sensors & Monitoring
- **Temperature & Humidity** - DHT22 sensor with calibration offset
- **Gas Detection** - MQ-2/MQ-5 gas sensor support
- **Light Sensor** - Ambient light level detection
- **Weather Integration** - OpenWeatherMap, WeatherAPI, or BOM (Australia)

### Smart Home Integration
- **Home Assistant** - Full integration with your HA instance
- **Device Discovery** - Network scanning for smart devices
- **Bluetooth** - Device pairing and management

### Dashboard & Widgets
- **Customizable Dashboard** - Drag and drop widget layout
- **Available Widgets**:
  - Clock & Date
  - Weather
  - Photo Slideshow
  - Calendar
  - Security Cameras
  - Quick Actions
  - Sensor Data

### Additional Features
- **Calendar Integration** - View your schedule
- **Shopping Lists** - Create and manage lists
- **Timers** - Countdown and stopwatch
- **Routines** - Automated actions
- **Intercom** - Audio communication between devices

## Quick Start

### One-Line Install
```bash
curl -sSL https://raw.githubusercontent.com/oodog/binghome/master/install.sh | bash
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/oodog/binghome.git
cd binghome

# Run installer
chmod +x install.sh
./install.sh

# Or install manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the application
python app.py
```

### Access the Interface
Open your browser to: `http://<raspberry-pi-ip>:5000`

## Requirements

### Hardware
- Raspberry Pi 4/5 (2GB+ RAM recommended)
- 7" Touchscreen Display (1024x600 optimal)
- MicroSD card (32GB+ recommended)
- USB Microphone (optional, for voice control)
- Speakers (optional, for TTS)

### Optional Sensors
- DHT22 Temperature/Humidity Sensor
- MQ-2/MQ-5 Gas Sensor
- Light Sensor Module
- Raspberry Pi Camera Module

### Software
- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+

## Configuration

### Settings Page
Access settings at `http://<pi-ip>:5000/settings`

### Google Photos (Easiest Method)
1. Create a shared album in Google Photos
2. Set sharing to "Anyone with the link can view"
3. Copy the share link (e.g., `https://photos.app.goo.gl/xxxxx`)
4. Paste into Settings > Google Photos > Shared Album Link
5. Click "Test Shared Album" to verify
6. Save settings

### Security Cameras
1. Go to Settings > Quick Access > Security Cameras
2. Click "Add Camera"
3. Select your camera vendor for auto-filled RTSP patterns
4. Enter camera IP, username, and password
5. Test the stream before saving

### Sensor Calibration
If your DHT22 sensor reads high/low:
1. Go to Settings > Sensor Calibration
2. Adjust the temperature offset (e.g., -2.5 if reading 2.5 degrees high)
3. Save settings

## Project Structure

```
binghome/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── settings.json            # User settings (auto-created)
├── core/
│   ├── cameras.py           # Camera management (Pi, USB, RTSP)
│   ├── device_discovery.py  # Network device discovery
│   ├── google_photos.py     # Google Photos integration
│   ├── media.py             # Media playback
│   ├── news.py              # News aggregation
│   ├── timers.py            # Timer management
│   └── weather.py           # Weather services
├── templates/
│   ├── index.html           # Main hub interface
│   ├── hub.html             # Alternative hub layout
│   ├── dashboard.html       # Customizable dashboard
│   ├── settings.html        # Settings page
│   ├── camera_settings.html # Local camera settings
│   ├── security_cameras.html# RTSP camera management
│   ├── bluetooth_settings.html
│   ├── wifi_settings.html
│   ├── calendar.html
│   ├── timers.html
│   ├── routines.html
│   ├── shopping.html
│   └── ...
├── static/
│   ├── js/
│   │   └── hub_enhanced.js  # Enhanced UI interactions
│   ├── icons/
│   │   └── icons.svg        # SVG icon set
│   └── snapshots/           # Camera snapshots (auto-created)
└── data/
    └── security_cameras.json # Saved camera configurations
```

## API Reference

### Sensor Data
```http
GET /api/sensor_data
```
Returns temperature, humidity, gas detection, and light levels.

### Google Photos
```http
GET /api/google_photos/shared?url=<optional-url>
```
Fetch photos from shared album.

```http
POST /api/google_photos/shared/test
Content-Type: application/json
{"url": "https://photos.app.goo.gl/xxxxx"}
```
Test a shared album URL.

### Cameras
```http
GET /api/cameras/detect
```
Detect local Pi/USB cameras.

```http
GET /api/security-cameras
POST /api/security-cameras
```
List or add security cameras.

```http
POST /api/security-cameras/test
Content-Type: application/json
{"rtsp_url": "rtsp://..."}
```
Test RTSP stream connection.

### Settings
```http
GET /api/settings
POST /api/settings
```
Get or update application settings.

### Health Check
```http
GET /api/health
```
System health status.

## GPIO Pinout

### DHT22 Temperature/Humidity Sensor
| DHT22 Pin | Raspberry Pi |
|-----------|--------------|
| VCC       | Pin 1 (3.3V) |
| GND       | Pin 6 (GND)  |
| DATA      | Pin 7 (GPIO4)|

*Add a 10kΩ pull-up resistor between VCC and DATA*

### Gas Sensor (MQ-2/MQ-5)
| Sensor Pin | Raspberry Pi  |
|------------|---------------|
| VCC        | Pin 2 (5V)    |
| GND        | Pin 9 (GND)   |
| DO         | Pin 11 (GPIO17)|

### Light Sensor
| Sensor Pin | Raspberry Pi   |
|------------|----------------|
| VCC        | Pin 1 (3.3V)   |
| GND        | Pin 14 (GND)   |
| DO         | Pin 13 (GPIO27)|

## Running as a Service

```bash
# Create systemd service
sudo nano /etc/systemd/system/binghome.service
```

```ini
[Unit]
Description=BingHome Smart Home Hub
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/binghome
Environment="PATH=/home/pi/binghome/venv/bin"
ExecStart=/home/pi/binghome/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable binghome
sudo systemctl start binghome

# Check status
sudo systemctl status binghome
```

## Kiosk Mode

For a dedicated touchscreen display:

```bash
# Install dependencies
sudo apt install chromium-browser unclutter

# Auto-start in kiosk mode
nano ~/.config/lxsession/LXDE-pi/autostart
```

Add:
```
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.5 -root
@chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:5000
```

## Troubleshooting

### Photos Not Loading on Pi
- Images are automatically resized for Pi (1024x600)
- Check your network connection
- Try the "Test Shared Album" button in settings

### Settings Page Shows Error
- Clear browser cache and reload
- Check browser console for specific errors
- Ensure all required DOM elements exist

### Camera Stream Not Working
- Verify RTSP URL is correct
- Check camera is on same network
- Test with VLC: `vlc rtsp://...`
- Ensure ffmpeg is installed: `sudo apt install ffmpeg`

### DHT22 Sensor Errors
- Check wiring and pull-up resistor
- Add delay between reads (included in code)
- Try different GPIO pin

### Service Won't Start
```bash
# Check logs
sudo journalctl -u binghome -f

# Run manually to see errors
cd /home/pi/binghome
source venv/bin/activate
python app.py
```

## Documentation

- [Google Photos Setup Guide](GOOGLE_PHOTOS_SETUP.md) - OAuth configuration
- [ngrok Setup Guide](NGROK_SETUP.md) - HTTPS for OAuth callbacks
- [Quick Start Guide](QUICK_START.md) - Getting started fast
- [Enhancements](ENHANCEMENTS.md) - Feature roadmap

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Credits

- OpenAI for Whisper and ChatGPT
- Vosk for offline speech recognition
- Adafruit for sensor libraries
- Flask and Flask-SocketIO
- Home Assistant community

---

**BingHome** - Your smart home, your way.
