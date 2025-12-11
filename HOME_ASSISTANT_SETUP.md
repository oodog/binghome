# Home Assistant Setup Guide

This guide explains how Home Assistant is installed with BingHome Hub and how to integrate them.

## Installation

Home Assistant is automatically installed by the `install.sh` script using Docker. The installation includes:

- Docker and Docker Compose
- Home Assistant container running on port 8123
- Systemd service for automatic startup
- Configuration directory at `~/homeassistant/config`

## Quick Start

### 1. Complete Initial Setup

After running the install script, access Home Assistant:

```
http://localhost:8123
```

Or from another device on your network:

```
http://YOUR_RASPBERRY_PI_IP:8123
```

**Note:** First startup takes 2-5 minutes to initialize.

### 2. Create Your Account

1. Open Home Assistant in your browser
2. Create your admin account
3. Set your location and timezone
4. Follow the onboarding wizard
5. Add any discovered devices

### 3. Generate Access Token

To connect BingHome Hub to Home Assistant:

1. Click your profile icon (bottom left)
2. Scroll to "Long-Lived Access Tokens"
3. Click "Create Token"
4. Name it "BingHome Hub"
5. Copy the token (you won't see it again!)

### 4. Configure BingHome Hub

1. Open BingHome Hub: `http://localhost:5000`
2. Click the Settings button (⚙️)
3. Find "Home Assistant" section
4. Enter:
   - **URL:** `http://localhost:8123`
   - **Token:** Paste your long-lived access token
5. Click "Save Settings"

## Manual Installation (if not using install.sh)

If you need to install Home Assistant manually:

### Using Docker

```bash
# Create directory
mkdir -p ~/homeassistant

# Create docker-compose.yml
cat > ~/homeassistant/docker-compose.yml << 'EOF'
version: '3'
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
    environment:
      - TZ=Australia/Brisbane
EOF

# Start Home Assistant
cd ~/homeassistant
docker-compose up -d
```

### Check Status

```bash
# View logs
docker logs -f homeassistant

# Check if running
docker ps | grep homeassistant

# Restart
cd ~/homeassistant
docker-compose restart
```

## Managing Home Assistant

### Control via Systemd

```bash
# Start
sudo systemctl start homeassistant-docker

# Stop
sudo systemctl stop homeassistant-docker

# Restart
sudo systemctl restart homeassistant-docker

# Check status
sudo systemctl status homeassistant-docker

# View logs
journalctl -u homeassistant-docker -f
```

### Control via Docker Compose

```bash
cd ~/homeassistant

# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f
```

### Control via Docker Directly

```bash
# Start
docker start homeassistant

# Stop
docker stop homeassistant

# Restart
docker restart homeassistant

# View logs
docker logs -f homeassistant
```

## Configuration

### Configuration Files

Home Assistant configuration is stored in:
```
~/homeassistant/config/
```

Key files:
- `configuration.yaml` - Main configuration
- `automations.yaml` - Automation rules
- `scripts.yaml` - Custom scripts
- `secrets.yaml` - Sensitive data (tokens, passwords)

### Editing Configuration

```bash
# Open configuration file
nano ~/homeassistant/config/configuration.yaml

# After editing, check configuration
docker exec homeassistant hass --script check_config

# Restart to apply changes
docker restart homeassistant
```

## Integrating Devices

### Adding Smart Devices

1. **Automatic Discovery:**
   - Many devices are discovered automatically
   - Check "Notifications" for discovered devices
   - Click "Configure" to add them

2. **Manual Integration:**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for your device/service
   - Follow the setup wizard

### Common Integrations

- **MQTT:** For IoT devices
- **Zigbee/Z-Wave:** Smart home protocols
- **Wi-Fi Devices:** Smart plugs, lights, etc.
- **Voice Assistants:** Alexa, Google Home
- **Weather:** Various weather services
- **Media Players:** Spotify, Chromecast, Kodi

## Integrating with BingHome Hub

BingHome Hub can control Home Assistant devices through the API:

### Example: Control a Light

From BingHome Hub voice commands:
- "Hey Bing, turn on kitchen light"
- "Hey Bing, set bedroom lights to 50%"
- "Hey Bing, turn off all lights"

### Example: Get Sensor Data

BingHome Hub can read Home Assistant sensors:
- "Hey Bing, what's the temperature?"
- "Hey Bing, is the front door locked?"

### Automation Ideas

1. **Temperature Sync:**
   - Send DHT22 readings from BingHome to Home Assistant
   - Create automations based on temperature

2. **Voice Control:**
   - Control Home Assistant scenes via BingHome voice
   - Trigger scripts and automations

3. **Presence Detection:**
   - Use BingHome as a presence sensor
   - Trigger automations when BingHome detects activity

## Updating Home Assistant

### Update Container

```bash
cd ~/homeassistant

# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

### Backup Before Updating

```bash
# Backup configuration
tar -czf ~/ha-backup-$(date +%Y%m%d).tar.gz ~/homeassistant/config/
```

### Restore from Backup

```bash
# Stop Home Assistant
docker-compose down

# Restore configuration
tar -xzf ~/ha-backup-YYYYMMDD.tar.gz -C ~

# Start Home Assistant
docker-compose up -d
```

## Troubleshooting

### Home Assistant Won't Start

Check logs:
```bash
docker logs homeassistant
```

Common issues:
- Invalid `configuration.yaml` (check syntax)
- Port 8123 already in use
- Insufficient disk space
- Corrupted database

### Can't Connect from BingHome Hub

1. **Verify Home Assistant is running:**
   ```bash
   curl http://localhost:8123
   ```

2. **Check token is valid:**
   - Log into Home Assistant web interface
   - Check Long-Lived Access Tokens section
   - Generate a new token if needed

3. **Test API access:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8123/api/
   ```

### Permission Issues

If you get permission errors with Docker:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker ps
```

### Home Assistant Not Discovering Devices

1. Ensure devices are on the same network
2. Check device compatibility
3. Manually add integration (Settings → Devices & Services)
4. Check firewall settings
5. Review Home Assistant logs for errors

## Performance Optimization

### For Raspberry Pi

1. **Increase swap:**
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

2. **Disable unused integrations**
3. **Use recorder purge to limit database size**
4. **Move database to USB/SSD if possible**

### Database Maintenance

Add to `configuration.yaml`:

```yaml
recorder:
  purge_keep_days: 7
  commit_interval: 30
  db_url: sqlite:////config/home-assistant_v2.db
```

## Useful Commands

```bash
# Access Home Assistant CLI
docker exec -it homeassistant bash

# Check configuration
docker exec homeassistant hass --script check_config

# View real-time logs
docker logs -f homeassistant

# Restart Home Assistant
docker restart homeassistant

# Full system restart
sudo systemctl restart homeassistant-docker

# Check Docker resource usage
docker stats homeassistant
```

## Additional Resources

- **Official Documentation:** https://www.home-assistant.io/docs/
- **Community Forum:** https://community.home-assistant.io/
- **Integration List:** https://www.home-assistant.io/integrations/
- **GitHub Repository:** https://github.com/home-assistant/core

## Support

For issues specific to the BingHome + Home Assistant integration:
- Check logs: `binghome logs` and `docker logs homeassistant`
- Verify API token in BingHome settings
- Create an issue: https://github.com/oodog/binghome/issues
