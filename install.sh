#!/bin/bash
# ============================================
# BingHome Installation Script - Auto-Start Fixed
# Includes browser kiosk mode and proper startup
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
GITHUB_REPO="https://github.com/oodog/binghome.git"
INSTALL_DIR="/home/$USER/binghome"
SERVICE_NAME="binghome"

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   BingHome Smart Hub Installer     ${NC}"
echo -e "${CYAN}   With Auto-Start Browser Fix      ${NC}"
echo -e "${CYAN}=====================================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as regular user (not root)${NC}"
    exit 1
fi

# Check Python version
check_python() {
    echo -e "\n${BLUE}Checking Python version...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        exit 1
    fi
}

# Update system
update_system() {
    echo -e "\n${BLUE}Updating system packages...${NC}"
    sudo apt-get update
    sudo apt-get upgrade -y
}

# Install dependencies with browser support
install_dependencies() {
    echo -e "\n${BLUE}Installing system dependencies...${NC}"
    
    sudo apt-get install -y \
        python3-pip python3-venv python3-dev \
        git curl wget build-essential \
        portaudio19-dev python3-pyaudio \
        espeak ffmpeg libsndfile1 \
        i2c-tools \
        chromium-browser \
        xdotool \
        unclutter \
        x11-xserver-utils \
        xinit \
        openbox \
        lxde-core \
        lightdm \
        xserver-xorg \
        matchbox-window-manager \
        xautomation \
        screen || true
    
    # Raspberry Pi specific
    if [ -f /proc/device-tree/model ]; then
        echo -e "${BLUE}Configuring Raspberry Pi...${NC}"
        sudo apt-get install -y python3-rpi.gpio || true
        
        # Enable interfaces
        sudo raspi-config nonint do_i2c 0 2>/dev/null || true
        sudo raspi-config nonint do_spi 0 2>/dev/null || true
        
        # Enable auto-login to desktop
        sudo raspi-config nonint do_boot_behaviour B4 2>/dev/null || true
        
        # Add user to groups
        sudo usermod -a -G gpio,i2c,spi,audio,dialout,video $USER || true
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Setup project
setup_project() {
    echo -e "\n${BLUE}Setting up project...${NC}"
    
    # Clone or update repository
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Updating existing installation...${NC}"
        cd "$INSTALL_DIR"
        git stash
        git pull || true
    else
        echo -e "${BLUE}Cloning repository...${NC}"
        git clone "$GITHUB_REPO" "$INSTALL_DIR" || {
            echo -e "${YELLOW}Creating local installation...${NC}"
            mkdir -p "$INSTALL_DIR"
        }
    fi
    
    cd "$INSTALL_DIR"
    
    # Create required directories
    mkdir -p core templates static/js
    
    # Fix any file issues
    if [ -f "gitignore.txt" ]; then
        mv gitignore.txt .gitignore
    fi
    
    # Remove redundant files if app.py exists
    if [ -f "app.py" ] && [ -f "binghome.py" ]; then
        echo -e "${YELLOW}Removing redundant binghome.py...${NC}"
        mv binghome.py binghome.py.backup 2>/dev/null || true
    fi
}

# Create core modules if missing
create_core_modules() {
    echo -e "\n${BLUE}Checking core modules...${NC}"
    
    # Create media.py if missing
    if [ ! -f "core/media.py" ]; then
        echo -e "${YELLOW}Creating core/media.py...${NC}"
        cat > core/media.py << 'EOF'
"""Media control module for BingHome"""
import logging

logger = logging.getLogger(__name__)

class MediaController:
    def __init__(self):
        self.is_playing = False
        
    def play(self, source=None):
        self.is_playing = True
        logger.info(f"Playing media")
        return True
    
    def pause(self):
        self.is_playing = False
        return True
    
    def stop(self):
        self.is_playing = False
        return True
    
    def next(self):
        return True
    
    def previous(self):
        return True
EOF
    fi
    
    # Create news.py if missing
    if [ ! -f "core/news.py" ]; then
        echo -e "${YELLOW}Creating core/news.py...${NC}"
        cat > core/news.py << 'EOF'
"""News fetching module for BingHome"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(self):
        self.api_key = os.environ.get('BING_API_KEY', '')
        
    def fetch_news(self, category='general', count=10):
        if not self.api_key:
            return []
        
        try:
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {'mkt': 'en-US', 'count': count}
            
            response = requests.get(
                'https://api.bing.microsoft.com/v7.0/news',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('value', [])
        except Exception as e:
            logger.error(f"News error: {e}")
        
        return []
EOF
    fi
    
    # Create timers.py if missing
    if [ ! -f "core/timers.py" ]; then
        echo -e "${YELLOW}Creating core/timers.py...${NC}"
        cat > core/timers.py << 'EOF'
"""Timer management for BingHome"""
import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)

class TimerManager:
    def __init__(self):
        self.timers = {}
        
    def create_timer(self, duration, name="Timer"):
        timer_id = str(uuid.uuid4())[:8]
        
        def timer_thread():
            time.sleep(duration)
            if timer_id in self.timers:
                logger.info(f"Timer {name} completed")
                del self.timers[timer_id]
        
        self.timers[timer_id] = {
            'name': name,
            'duration': duration,
            'thread': threading.Thread(target=timer_thread, daemon=True)
        }
        self.timers[timer_id]['thread'].start()
        return timer_id
    
    def cancel_timer(self, timer_id):
        if timer_id in self.timers:
            del self.timers[timer_id]
            return True
        return False
EOF
    fi
    
    # Create weather.py if missing
    if [ ! -f "core/weather.py" ]; then
        echo -e "${YELLOW}Creating core/weather.py...${NC}"
        cat > core/weather.py << 'EOF'
"""Weather service module for BingHome"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = os.environ.get('WEATHER_API_KEY', '')
        
    def get_current(self, location='London'):
        if not self.api_key:
            return {}
        
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'temp': round(data['main']['temp']),
                    'condition': data['weather'][0]['main'],
                    'description': data['weather'][0]['description']
                }
        except Exception as e:
            logger.error(f"Weather error: {e}")
        
        return {}
    
    def get_forecast(self):
        return []
EOF
    fi
    
    echo -e "${GREEN}✓ Core modules ready${NC}"
}

# Setup Python environment
setup_python_env() {
    echo -e "\n${BLUE}Setting up Python environment...${NC}"
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}Installing from requirements.txt...${NC}"
        pip install -r requirements.txt
    else
        echo -e "${BLUE}Installing packages manually...${NC}"
        
        # Core packages
        pip install flask flask-cors flask-socketio
        pip install requests python-dotenv psutil
        
        # Voice/Audio
        pip install SpeechRecognition pyttsx3 pyaudio || true
        
        # Hardware (Raspberry Pi)
        pip install RPi.GPIO adafruit-circuitpython-dht || true
    fi
    
    echo -e "${GREEN}✓ Python environment ready${NC}"
}

# Setup auto-start browser configuration
setup_autostart() {
    echo -e "\n${BLUE}Setting up browser auto-start...${NC}"
    
    # Create autostart directories
    mkdir -p "$HOME/.config/lxsession/LXDE-pi"
    mkdir -p "$HOME/.config/openbox"
    
    # Create browser launch script
    cat > "$INSTALL_DIR/launch-browser.sh" << 'EOF'
#!/bin/bash

# Wait for X server to be ready
while ! xset q &>/dev/null; do
    echo "Waiting for X server..."
    sleep 2
done

# Hide cursor after inactivity
unclutter -idle 1 &

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Wait for BingHome service to be ready
echo "Waiting for BingHome service..."
while ! curl -s http://localhost:5000 > /dev/null; do
    sleep 3
done

echo "Launching browser in kiosk mode..."

# Launch Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --incognito \
    --disable-infobars \
    --disable-web-security \
    --disable-features=TranslateUI \
    --disable-component-extensions-with-background-pages \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-backgrounding-occluded-windows \
    --autoplay-policy=no-user-gesture-required \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-default-apps \
    --no-default-browser-check \
    --disable-translate \
    --disable-features=VizDisplayCompositor \
    --window-position=0,0 \
    --window-size=1920,1080 \
    http://localhost:5000 &

# Keep script running
wait
EOF
    
    chmod +x "$INSTALL_DIR/launch-browser.sh"
    
    # Create LXDE autostart
    cat > "$HOME/.config/lxsession/LXDE-pi/autostart" << EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@$INSTALL_DIR/launch-browser.sh
EOF
    
    # Create openbox autostart as fallback
    cat > "$HOME/.config/openbox/autostart" << EOF
# Launch BingHome browser
$INSTALL_DIR/launch-browser.sh &
EOF
    
    chmod +x "$HOME/.config/openbox/autostart"
    
    echo -e "${GREEN}✓ Browser auto-start configured${NC}"
}

# Setup desktop environment for kiosk mode
setup_desktop() {
    echo -e "\n${BLUE}Configuring desktop environment...${NC}"
    
    # Configure lightdm for auto-login
    sudo mkdir -p /etc/lightdm/lightdm.conf.d
    
    cat > /tmp/01-autologin.conf << EOF
[Seat:*]
autologin-user=$USER
autologin-user-timeout=0
user-session=LXDE-pi
EOF
    
    sudo mv /tmp/01-autologin.conf /etc/lightdm/lightdm.conf.d/01-autologin.conf
    
    # Create .dmrc for session selection
    cat > "$HOME/.dmrc" << EOF
[Desktop]
Session=LXDE-pi
EOF
    
    echo -e "${GREEN}✓ Desktop environment configured${NC}"
}

# Create systemd service with proper startup order
create_service() {
    echo -e "\n${BLUE}Creating systemd service...${NC}"
    
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=BingHome Smart Hub
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStartPre=/bin/sleep 10
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=15
StandardOutput=append:/var/log/binghome.log
StandardError=append:/var/log/binghome.error.log

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=$INSTALL_DIR /var/log

[Install]
WantedBy=multi-user.target
EOF
    
    # Create log files with proper permissions
    sudo touch /var/log/binghome.log /var/log/binghome.error.log
    sudo chown $USER:$USER /var/log/binghome.log /var/log/binghome.error.log
    
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}.service
    
    echo -e "${GREEN}✓ Service created and enabled${NC}"
}

# Create helper scripts
create_scripts() {
    echo -e "\n${BLUE}Creating helper scripts...${NC}"
    
    cd "$INSTALL_DIR"
    
    # Start script
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
EOF
    chmod +x start.sh
    
    # Update script
    cat > update.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart binghome
EOF
    chmod +x update.sh
    
    # Control script
    cat > binghome-control.sh << 'EOF'
#!/bin/bash

SERVICE_NAME="binghome"

case "$1" in
    start)
        echo "Starting BingHome service..."
        sudo systemctl start $SERVICE_NAME
        ;;
    stop)
        echo "Stopping BingHome service..."
        sudo systemctl stop $SERVICE_NAME
        pkill -f chromium-browser 2>/dev/null || true
        ;;
    restart)
        echo "Restarting BingHome service..."
        sudo systemctl restart $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME
        ;;
    logs)
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    browser)
        echo "Launching browser..."
        ./launch-browser.sh &
        ;;
    kiosk)
        echo "Stopping browser and restarting in kiosk mode..."
        pkill -f chromium-browser 2>/dev/null || true
        sleep 2
        ./launch-browser.sh &
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|browser|kiosk}"
        exit 1
        ;;
esac
EOF
    chmod +x binghome-control.sh
    
    # Create global command
    sudo ln -sf "$INSTALL_DIR/binghome-control.sh" /usr/local/bin/binghome
    
    echo -e "${GREEN}✓ Helper scripts created${NC}"
}

# Test and start
start_service() {
    echo -e "\n${BLUE}Starting BingHome...${NC}"
    
    sudo systemctl start ${SERVICE_NAME}
    sleep 5
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}✓ BingHome service is running${NC}"
    else
        echo -e "${YELLOW}⚠ Service may not be running. Check logs with:${NC}"
        echo -e "  journalctl -u ${SERVICE_NAME} -f"
    fi
}

# Main installation
main() {
    check_python
    update_system
    install_dependencies
    setup_project
    create_core_modules
    setup_python_env
    setup_autostart
    setup_desktop
    create_service
    create_scripts
    start_service
    
    # Get IP
    IP=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}=====================================${NC}"
    echo -e "${GREEN}   Installation Complete! 🎉         ${NC}"
    echo -e "${GREEN}=====================================${NC}"
    
    echo -e "\n${CYAN}Access BingHome at:${NC}"
    echo -e "  ${GREEN}http://$IP:5000${NC}"
    
    echo -e "\n${CYAN}Available Commands:${NC}"
    echo -e "  Start service:    ${GREEN}binghome start${NC}"
    echo -e "  Stop service:     ${GREEN}binghome stop${NC}"
    echo -e "  Restart:          ${GREEN}binghome restart${NC}"
    echo -e "  View logs:        ${GREEN}binghome logs${NC}"
    echo -e "  Launch browser:   ${GREEN}binghome browser${NC}"
    echo -e "  Kiosk mode:       ${GREEN}binghome kiosk${NC}"
    
    echo -e "\n${CYAN}Auto-Start Features:${NC}"
    echo -e "  ✓ Service auto-starts on boot"
    echo -e "  ✓ Desktop auto-login configured"
    echo -e "  ✓ Browser kiosk mode on login"
    echo -e "  ✓ Screen blanking disabled"
    
    echo -e "\n${YELLOW}Reboot to activate auto-start:${NC}"
    echo -e "  ${GREEN}sudo reboot${NC}"
    
    echo -e "\n${BLUE}After reboot, the system will:${NC}"
    echo -e "  1. Auto-login to desktop"
    echo -e "  2. Start BingHome service"
    echo -e "  3. Launch browser in kiosk mode"
    echo -e "  4. Display BingHome interface"
}

# Run
main
