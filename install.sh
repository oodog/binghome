#!/bin/bash
# ============================================
# BingHome Hub Installation Script
# Complete automated installation with all dependencies
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
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   BingHome Hub Installer v3.0      ${NC}"
echo -e "${CYAN}   Smart Home Hub System             ${NC}"
echo -e "${CYAN}=====================================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as regular user (not root)${NC}"
    exit 1
fi

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        echo -e "${RED}Cannot detect OS${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Detected OS: $OS $VER${NC}"
}

# Check Python version
check_python() {
    echo -e "\n${BLUE}Checking Python version...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
        PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
        else
            echo -e "${RED}✗ Python 3.8+ required (found $PYTHON_VERSION)${NC}"
            exit 1
        fi
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

# Install system dependencies
install_dependencies() {
    echo -e "\n${BLUE}Installing system dependencies...${NC}"
    
    # Core dependencies
    sudo apt-get install -y \
        python3-pip python3-venv python3-dev \
        git curl wget build-essential \
        ffmpeg libssl-dev libffi-dev \
        python3-setuptools || true
    
    # Audio dependencies
    sudo apt-get install -y \
        portaudio19-dev python3-pyaudio \
        espeak libespeak-dev \
        pulseaudio pulseaudio-utils \
        alsa-base alsa-utils \
        libsndfile1 libsndfile1-dev || true
    
    # Network tools
    sudo apt-get install -y \
        network-manager \
        wireless-tools \
        wpasupplicant || true
    
    # Development tools
    sudo apt-get install -y \
        pkg-config \
        libatlas-base-dev \
        libopenblas-dev \
        liblapack-dev || true
    
    # Browser for kiosk mode
    sudo apt-get install -y \
        chromium-browser \
        xdotool \
        unclutter \
        x11-xserver-utils || true
    
    # Raspberry Pi specific
    if [ -f /proc/device-tree/model ]; then
        echo -e "${BLUE}Configuring Raspberry Pi specific packages...${NC}"
        sudo apt-get install -y \
            python3-rpi.gpio \
            i2c-tools \
            python3-smbus || true
        
        # Enable interfaces
        sudo raspi-config nonint do_i2c 0 2>/dev/null || true
        sudo raspi-config nonint do_spi 0 2>/dev/null || true
        
        # Add user to groups
        sudo usermod -a -G gpio,i2c,spi,audio,dialout,video $USER || true
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Install Node.js for better web performance
install_nodejs() {
    echo -e "\n${BLUE}Installing Node.js for enhanced performance...${NC}"

    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
        echo -e "${GREEN}✓ Node.js installed${NC}"
    else
        echo -e "${GREEN}✓ Node.js already installed${NC}"
    fi
}

# Install Docker for Home Assistant
install_docker() {
    echo -e "\n${BLUE}Installing Docker for Home Assistant...${NC}"

    if ! command -v docker &> /dev/null; then
        echo -e "${BLUE}Installing Docker...${NC}"
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh

        # Add user to docker group
        sudo usermod -aG docker $USER

        # Enable Docker service
        sudo systemctl enable docker
        sudo systemctl start docker

        echo -e "${GREEN}✓ Docker installed${NC}"
        echo -e "${YELLOW}Note: You may need to log out and back in for Docker permissions${NC}"
    else
        echo -e "${GREEN}✓ Docker already installed${NC}"
    fi

    # Install Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${BLUE}Installing Docker Compose...${NC}"
        sudo apt-get install -y docker-compose || {
            # Fallback to pip installation
            sudo pip3 install docker-compose
        }
        echo -e "${GREEN}✓ Docker Compose installed${NC}"
    else
        echo -e "${GREEN}✓ Docker Compose already installed${NC}"
    fi
}

# Install Home Assistant
install_home_assistant() {
    echo -e "\n${BLUE}Setting up Home Assistant...${NC}"

    HA_DIR="$HOME/homeassistant"
    mkdir -p "$HA_DIR"

    # Create docker-compose file for Home Assistant
    cat > "$HA_DIR/docker-compose.yml" << 'EOF'
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

    echo -e "${GREEN}✓ Home Assistant configuration created${NC}"

    # Create systemd service for Home Assistant
    sudo tee /etc/systemd/system/homeassistant-docker.service > /dev/null << EOF
[Unit]
Description=Home Assistant Docker Container
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$HA_DIR
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=$USER

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable homeassistant-docker.service

    echo -e "${GREEN}✓ Home Assistant service created${NC}"

    # Start Home Assistant
    echo -e "${BLUE}Starting Home Assistant (this may take a few minutes)...${NC}"
    cd "$HA_DIR"
    docker-compose up -d || {
        echo -e "${YELLOW}⚠ Failed to start Home Assistant automatically${NC}"
        echo -e "${YELLOW}  You can start it manually with: cd $HA_DIR && docker-compose up -d${NC}"
    }

    echo -e "${GREEN}✓ Home Assistant installation complete${NC}"
    echo -e "${CYAN}Access Home Assistant at: http://localhost:8123${NC}"
}

# Setup project
setup_project() {
    echo -e "\n${BLUE}Setting up BingHome Hub project...${NC}"
    
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
    mkdir -p core templates static/js static/css models logs
    
    echo -e "${GREEN}✓ Project structure created${NC}"
}

# Setup Python environment
setup_python_env() {
    echo -e "\n${BLUE}Setting up Python virtual environment...${NC}"
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install core requirements first
    echo -e "${BLUE}Installing core Python packages...${NC}"
    pip install flask flask-cors flask-socketio
    pip install requests python-dotenv psutil
    pip install numpy python-dateutil pytz
    
    # Install audio packages
    echo -e "${BLUE}Installing audio packages...${NC}"
    pip install pyttsx3 pygame || true
    pip install SpeechRecognition || true
    pip install sounddevice || true
    
    # Try to install PyAudio
    pip install PyAudio || {
        echo -e "${YELLOW}PyAudio installation failed, trying alternative method...${NC}"
        sudo apt-get install -y python3-pyaudio
    }
    
    # Install hardware packages (Raspberry Pi)
    if [ -f /proc/device-tree/model ]; then
        echo -e "${BLUE}Installing Raspberry Pi packages...${NC}"
        pip install RPi.GPIO || true
        pip install adafruit-blinka adafruit-circuitpython-dht || true
    fi
    
    # Install local AI models
    echo -e "${BLUE}Installing AI packages...${NC}"
    pip install vosk || true
    
    # Optional: Install Whisper (requires more resources)
    if [ "$1" == "--with-whisper" ]; then
        echo -e "${BLUE}Installing Whisper (this may take a while)...${NC}"
        pip install openai-whisper || true
    fi
    
    # Install Home Assistant API
    echo -e "${BLUE}Installing Home Automation packages...${NC}"
    pip install homeassistant-api paho-mqtt || true
    
    echo -e "${GREEN}✓ Python environment ready${NC}"
}

# Download Vosk model
download_vosk_model() {
    echo -e "\n${BLUE}Downloading Vosk speech recognition model...${NC}"
    
    MODELS_DIR="$INSTALL_DIR/models"
    mkdir -p "$MODELS_DIR"
    
    if [ ! -d "$MODELS_DIR/vosk-model-small-en-us-0.15" ]; then
        cd "$MODELS_DIR"
        echo -e "${YELLOW}Downloading Vosk model (39MB)...${NC}"
        wget -q --show-progress "$VOSK_MODEL_URL" -O vosk-model.zip
        
        echo -e "${BLUE}Extracting model...${NC}"
        unzip -q vosk-model.zip
        rm vosk-model.zip
        
        echo -e "${GREEN}✓ Vosk model installed${NC}"
    else
        echo -e "${GREEN}✓ Vosk model already installed${NC}"
    fi
    
    cd "$INSTALL_DIR"
}

# Create configuration files
create_config_files() {
    echo -e "\n${BLUE}Creating configuration files...${NC}"
    
    cd "$INSTALL_DIR"
    
    # Create default settings.json
    if [ ! -f "settings.json" ]; then
        cat > settings.json << 'EOF'
{
  "voice_provider": "local",
  "voice_model": "vosk",
  "openai_api_key": "",
  "azure_speech_key": "",
  "google_cloud_key": "",
  "amazon_polly_key": "",
  "bing_api_key": "",
  "weather_api_key": "",
  "home_assistant_url": "http://localhost:8123",
  "home_assistant_token": "",
  "wake_words": ["hey bing", "okay bing", "bing"],
  "tts_engine": "pyttsx3",
  "tts_rate": 150,
  "tts_volume": 0.9,
  "language": "en-US",
  "kiosk_mode": true,
  "auto_start_browser": true,
  "network_interface": "auto",
  "gpio_pins": {
    "dht22": 4,
    "gas_sensor": 17,
    "light_sensor": 27
  },
  "apps": {
    "netflix": {"enabled": true, "url": "https://www.netflix.com"},
    "prime_video": {"enabled": true, "url": "https://www.primevideo.com"},
    "youtube": {"enabled": true, "url": "https://www.youtube.com/tv"},
    "xbox_cloud": {"enabled": true, "url": "https://www.xbox.com/play"},
    "spotify": {"enabled": true, "url": "https://open.spotify.com"},
    "google_photos": {"enabled": true, "url": "https://photos.google.com"}
  }
}
EOF
        echo -e "${GREEN}✓ Settings file created${NC}"
    fi
    
    # Create .env file
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
# BingHome Hub Environment Variables
SECRET_KEY=binghome-hub-secret-change-this-$(openssl rand -hex 16)
HOST=0.0.0.0
PORT=5000
DEBUG=False
EOF
        echo -e "${GREEN}✓ Environment file created${NC}"
    fi
}

# Setup systemd service
create_service() {
    echo -e "\n${BLUE}Creating systemd service...${NC}"
    
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=BingHome Smart Home Hub
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="PYTHONUNBUFFERED=1"
ExecStartPre=/bin/sleep 10
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=15
StandardOutput=append:/var/log/binghome.log
StandardError=append:/var/log/binghome.error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Create log files
    sudo touch /var/log/binghome.log /var/log/binghome.error.log
    sudo chown $USER:$USER /var/log/binghome.log /var/log/binghome.error.log
    
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}.service
    
    echo -e "${GREEN}✓ Service created and enabled${NC}"
}

# Setup auto-start for desktop
setup_autostart() {
    echo -e "\n${BLUE}Setting up desktop auto-start...${NC}"
    
    # Create autostart directory
    mkdir -p "$HOME/.config/autostart"
    
    # Create desktop entry
    cat > "$HOME/.config/autostart/binghome.desktop" << EOF
[Desktop Entry]
Type=Application
Name=BingHome Hub
Exec=chromium-browser --kiosk --incognito --disable-infobars --window-position=0,0 --window-size=1920,1080 http://localhost:5000
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
    
    echo -e "${GREEN}✓ Auto-start configured${NC}"
}

# Configure audio
configure_audio() {
    echo -e "\n${BLUE}Configuring audio system...${NC}"
    
    # Set default audio output
    if command -v pactl &> /dev/null; then
        pactl set-default-sink 0 2>/dev/null || true
    fi
    
    # Configure ALSA
    if [ ! -f "$HOME/.asoundrc" ]; then
        cat > "$HOME/.asoundrc" << 'EOF'
pcm.!default {
    type hw
    card 0
}
ctl.!default {
    type hw
    card 0
}
EOF
    fi
    
    # Add user to audio group
    sudo usermod -a -G audio $USER
    
    echo -e "${GREEN}✓ Audio configured${NC}"
}

# Create helper scripts
create_helper_scripts() {
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
pip install --upgrade -r requirements.txt
sudo systemctl restart binghome
echo "BingHome Hub updated successfully!"
EOF
    chmod +x update.sh
    
    # Voice test script
    cat > test-voice.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -c "
import speech_recognition as sr
import pyttsx3

# Test TTS
engine = pyttsx3.init()
engine.say('Hello, BingHome Hub voice system is working')
engine.runAndWait()

# Test microphone
r = sr.Recognizer()
m = sr.Microphone()
with m as source:
    r.adjust_for_ambient_noise(source)
    print('Say something!')
    audio = r.listen(source, timeout=5)
    try:
        text = r.recognize_google(audio)
        print(f'You said: {text}')
    except:
        print('Could not understand audio')
"
EOF
    chmod +x test-voice.sh
    
    # Control script
    cat > binghome << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "Starting BingHome Hub..."
        sudo systemctl start binghome
        ;;
    stop)
        echo "Stopping BingHome Hub..."
        sudo systemctl stop binghome
        ;;
    restart)
        echo "Restarting BingHome Hub..."
        sudo systemctl restart binghome
        ;;
    status)
        sudo systemctl status binghome
        ;;
    logs)
        sudo journalctl -u binghome -f
        ;;
    update)
        ./update.sh
        ;;
    test-voice)
        ./test-voice.sh
        ;;
    *)
        echo "Usage: binghome {start|stop|restart|status|logs|update|test-voice}"
        exit 1
        ;;
esac
EOF
    chmod +x binghome
    
    # Create global command
    sudo ln -sf "$INSTALL_DIR/binghome" /usr/local/bin/binghome
    
    echo -e "${GREEN}✓ Helper scripts created${NC}"
}

# Optimize for Raspberry Pi
optimize_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        echo -e "\n${BLUE}Optimizing for Raspberry Pi...${NC}"
        
        # Increase GPU memory split for better browser performance
        if ! grep -q "gpu_mem=" /boot/config.txt; then
            echo "gpu_mem=128" | sudo tee -a /boot/config.txt > /dev/null
        fi
        
        # Disable unnecessary services
        sudo systemctl disable bluetooth 2>/dev/null || true
        
        # Configure swap for better performance
        if [ ! -f /swapfile ]; then
            sudo fallocate -l 2G /swapfile
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
            echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
        fi
        
        echo -e "${GREEN}✓ Raspberry Pi optimized${NC}"
    fi
}

# Test installation
test_installation() {
    echo -e "\n${BLUE}Testing installation...${NC}"
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Test Python imports
    python -c "
import flask
import socketio
import speech_recognition
import pyttsx3
print('✓ Core packages working')
" || echo -e "${YELLOW}⚠ Some packages may need manual installation${NC}"
    
    # Test Vosk model
    if [ -d "models/vosk-model-small-en-us-0.15" ]; then
        python -c "
import vosk
import json
model = vosk.Model('models/vosk-model-small-en-us-0.15')
print('✓ Vosk model loaded successfully')
" || echo -e "${YELLOW}⚠ Vosk model test failed${NC}"
    fi
}

# Start service
start_service() {
    echo -e "\n${BLUE}Starting BingHome Hub...${NC}"
    
    sudo systemctl start ${SERVICE_NAME}
    sleep 5
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}✓ BingHome Hub service is running${NC}"
    else
        echo -e "${YELLOW}⚠ Service may not be running. Check logs with:${NC}"
        echo -e "  journalctl -u ${SERVICE_NAME} -f"
    fi
}

# Main installation
main() {
    detect_os
    check_python
    update_system
    install_dependencies
    install_nodejs
    install_docker
    install_home_assistant
    setup_project
    setup_python_env
    download_vosk_model
    create_config_files
    create_service
    setup_autostart
    configure_audio
    create_helper_scripts
    optimize_raspberry_pi
    test_installation
    start_service
    
    # Get IP
    IP=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}=====================================${NC}"
    echo -e "${GREEN}   Installation Complete! 🎉         ${NC}"
    echo -e "${GREEN}=====================================${NC}"
    
    echo -e "\n${CYAN}Access BingHome Hub at:${NC}"
    echo -e "  ${GREEN}http://$IP:5000${NC}"
    echo -e "  ${GREEN}http://localhost:5000${NC} (local)"
    
    echo -e "\n${CYAN}Available Commands:${NC}"
    echo -e "  ${GREEN}binghome start${NC}     - Start service"
    echo -e "  ${GREEN}binghome stop${NC}      - Stop service"
    echo -e "  ${GREEN}binghome restart${NC}   - Restart service"
    echo -e "  ${GREEN}binghome status${NC}    - Check status"
    echo -e "  ${GREEN}binghome logs${NC}      - View logs"
    echo -e "  ${GREEN}binghome update${NC}    - Update BingHome"
    echo -e "  ${GREEN}binghome test-voice${NC} - Test voice system"
    
    echo -e "\n${CYAN}Features:${NC}"
    echo -e "  ✓ Local voice recognition (Vosk)"
    echo -e "  ✓ Smart home control"
    echo -e "  ✓ Streaming apps integration"
    echo -e "  ✓ Weather & news"
    echo -e "  ✓ Home automation"
    
    echo -e "\n${CYAN}Next Steps:${NC}"
    echo -e "  1. ${YELLOW}IMPORTANT:${NC} Log out and back in for Docker permissions"
    echo -e "  2. Open ${GREEN}http://$IP:8123${NC} to complete Home Assistant setup"
    echo -e "  3. Open ${GREEN}http://$IP:5000${NC} to access BingHome Hub"
    echo -e "  4. Click the settings button (⚙️) in BingHome"
    echo -e "  5. Configure your API keys (optional)"
    echo -e "  6. Enter Home Assistant URL and create a long-lived access token"
    echo -e "  7. Say 'Hey Bing' to activate voice control"

    echo -e "\n${CYAN}Home Assistant Setup:${NC}"
    echo -e "  ${GREEN}http://localhost:8123${NC}"
    echo -e "  • First time setup will take 2-5 minutes"
    echo -e "  • Create an account and onboard devices"
    echo -e "  • Generate a long-lived access token in your profile"
    echo -e "  • Add the token to BingHome Hub settings"
    
    echo -e "\n${YELLOW}Note: Reboot recommended for all features:${NC}"
    echo -e "  ${GREEN}sudo reboot${NC}"
}

# Handle arguments
case "$1" in
    --with-whisper)
        echo -e "${CYAN}Installing with Whisper support...${NC}"
        ;;
    --help)
        echo "Usage: $0 [--with-whisper]"
        echo "  --with-whisper  Install OpenAI Whisper for better voice recognition"
        exit 0
        ;;
esac

# Run installation
main "$@"