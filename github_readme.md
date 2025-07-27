# 🏠 BingHome Smart Hub

A modern smart home control interface designed for Raspberry Pi with touchscreen display. Features Xbox-style UI, voice assistant integration, Home Assistant compatibility, and comprehensive sensor support.

![BingHome Interface](https://img.shields.io/badge/Platform-Raspberry%20Pi%20OS-red) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

### 🎮 **Modern Interface**
- Xbox/iPhone-style dark theme with animated tiles
- Touch-optimized navigation with swipe gestures
- Auto-scrolling news feed with Bing News integration
- Real-time sensor data display in status bar

### 🏠 **Smart Home Integration**
- Full Home Assistant compatibility
- RESTful API for device control
- Sensor data monitoring and logging
- Custom automation support

### 🎤 **Voice Assistant**
- ChatGPT-powered voice commands
- Context-aware smart home control
- Natural language processing
- Hands-free operation

### 📱 **Media & Entertainment**
- YouTube, Netflix, Prime Video integration
- Xbox Cloud Gaming support
- Spotify music control
- Full-screen kiosk mode

### 🔧 **Hardware Support**
- DHT22 temperature/humidity sensor (GPIO4)
- Digital gas sensor (GPIO17)
- Digital light sensor (GPIO27)
- TPA2016 I2C audio amplifier
- Touch screen display (1024x600)

## 🚀 **One-Command Installation**

For Raspberry Pi OS, simply run:

```bash
curl -sSL https://raw.githubusercontent.com/oodog/binghome/main/install.sh | bash
```

Or download and run manually:

```bash
wget https://raw.githubusercontent.com/oodog/binghome/main/install.sh
chmod +x install.sh
./install.sh
```

## 📋 **What Gets Installed**

The installation script automatically:
- ✅ Updates Raspberry Pi OS packages
- ✅ Installs Python 3 and all dependencies
- ✅ Downloads BingHome from GitHub
- ✅ Configures GPIO, I2C, and SPI interfaces
- ✅ Installs and configures Home Assistant (Docker)
- ✅ Sets up systemd service for auto-start
- ✅ Configures kiosk mode for touchscreen
- ✅ Creates desktop autostart entries

## 🔌 **Hardware Setup**

### **Required Hardware**
- Raspberry Pi 4 (2GB+ recommended)
- 7-inch touchscreen display (1024x600)
- MicroSD card (32GB+ recommended)
- Power supply (official Raspberry Pi power supply)

### **Optional Sensors**
| Component | GPIO Pin | Physical Pin | Function |
|-----------|----------|--------------|----------|
| DHT22 Sensor | GPIO4 | Pin 7 | Temperature/Humidity |
| Gas Sensor | GPIO17 | Pin 11 | Digital gas detection |
| Light Sensor | GPIO27 | Pin 13 | Digital light level |
| TPA2016 Amp | GPIO2/3 | Pins 3/5 | I2C audio control |

### **Wiring Guide**

#### DHT22 Temperature/Humidity Sensor
```
DHT22 → Raspberry Pi
VCC   → Pin 1 (3.3V)
GND   → Pin 6 (Ground)  
DATA  → Pin 7 (GPIO4)
+ 10kΩ pull-up resistor between VCC and DATA
```

#### Digital Sensors
```
Gas Sensor → Pin 11 (GPIO17)
Light Sensor → Pin 13 (GPIO27)
Both sensors: VCC to 3.3V, GND to Ground
```

#### TPA2016 Audio Amplifier (I2C)
```
TPA2016 → Raspberry Pi
VCC     → Pin 1 (3.3V)
GND     → Pin 6 (Ground)
SDA     → Pin 3 (GPIO2)
SCL     → Pin 5 (GPIO3)
```

## 🎯 **Quick Start**

After installation:

1. **Access the interface**: Open `http://localhost:5000`
2. **Configure Home Assistant**: Visit `http://localhost:8123`
3. **Test sensors**: Check the status bar for real-time data
4. **Add API keys**: Configure OpenAI and Bing API keys
5. **Customize**: Modify settings through the web interface

## 🔧 **Manual Controls**

### **Start/Stop Commands**
```bash
# Manual start
cd /home/$USER/binghome && ./start.sh

# Kiosk mode
cd /home/$USER/binghome && ./start_kiosk.sh

# Service control
sudo systemctl start binghome
sudo systemctl stop binghome
sudo systemctl restart binghome

# View logs
journalctl -u binghome -f
```

### **Development Mode**
```bash
cd /home/$USER/binghome
source venv/bin/activate
export FLASK_DEBUG=1
python app.py
```

## ⚙️ **Configuration**

### **Environment Variables**
Set these in your environment or service file:

```bash
export HOME_ASSISTANT_URL="http://localhost:8123"
export HOME_ASSISTANT_TOKEN="your_long_lived_token"
export OPENAI_API_KEY="your_openai_api_key"
export BING_API_KEY="your_bing_news_api_key"
```

### **API Endpoints**
- `GET /` - Main interface
- `GET /api/sensor_data` - Current sensor readings
- `GET /api/health` - Health check
- `POST /api/voice` - Voice assistant queries
- `GET /api/wifi_scan` - WiFi network scan
- `POST /api/wifi_connect` - Connect to WiFi

## 🛠️ **Customization**

### **Adding New Sensors**
1. Modify `get_sensor_data()` in `app.py`
2. Update GPIO pin assignments
3. Add display elements to `index.html`

### **Changing the Interface**
- Edit `index.html` for layout changes
- Modify CSS for styling updates
- Add new app tiles for additional services

### **Extending Functionality**
- Add new Flask routes in `app.py`
- Integrate additional APIs
- Create custom Home Assistant automations

## 🐛 **Troubleshooting**

### **Common Issues**

**Service won't start:**
```bash
# Check service status
sudo systemctl status binghome

# View detailed logs
journalctl -u binghome -n 50

# Test manual start
cd /home/$USER/binghome
source venv/bin/activate
python app.py
```

**Sensors not working:**
```bash
# Check I2C devices
sudo i2cdetect -y 1

# Test GPIO permissions
groups $USER  # Should include 'gpio'

# Verify wiring with multimeter
```

**Browser issues:**
```bash
# Clear browser cache
rm -rf /tmp/binghome_kiosk

# Test in regular browser
firefox http://localhost:5000
```

### **Getting Help**

1. Check the [Issues](https://github.com/oodog/binghome/issues) page
2. Review system logs: `journalctl -f`
3. Test individual components manually
4. Verify hardware connections

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 **Contributing**

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🙏 **Acknowledgments**

- Home Assistant community for smart home integration
- OpenAI for ChatGPT API
- Microsoft for Bing News API
- Raspberry Pi Foundation for the hardware platform

---

**Made with ❤️ for the smart home community**