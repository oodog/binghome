#!/bin/bash
# ============================================
# BingHome Installation Script v2.1.0
# Smart Home System with Voice Control
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/$USER/binghome"
GITHUB_REPO="https://github.com/oodog/binghome.git"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_DIR="/home/$USER/vosk-model-small-en-us-0.15"

# ASCII Art Banner
show_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
 ____  _             _   _                      
| __ )(_)_ __   __ _| | | | ___  _ __ ___   ___ 
|  _ \| | '_ \ / _` | |_| |/ _ \| '_ ` _ \ / _ \
| |_) | | | | | (_| |  _  | (_) | | | | | |  __/
|____/|_|_| |_|\__, |_| |_|\___/|_| |_| |_|\___|
               |___/                             
EOF
    echo -e "${NC}"
    echo -e "${GREEN}Smart Home Control System v2.1.0${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(tr -d '\0' < /proc/device-tree/model)
        echo -e "${GREEN}✓ Detected: $MODEL${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Not running on Raspberry Pi${NC}"
        echo -e "${YELLOW}  Some features may not work properly${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        return 1
    fi
}

# Check system requirements
check_requirements() {
    echo -e "\n${BLUE}Checking system requirements...${NC}"
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        # Check if Python 3.9 or higher
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
        else
            echo -e "${RED}✗ Python $PYTHON_VERSION (3.9+ required)${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        exit 1
    fi
    
    # Check available RAM
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 1024 ]; then
        echo -e "${YELLOW}⚠ Low RAM: ${TOTAL_RAM}MB (1GB+ recommended)${NC}"
        echo -e "${YELLOW}  Consider using Vosk instead of Whisper${NC}"
    else
        echo -e "${GREEN}✓ RAM: ${TOTAL_RAM}MB${NC}"
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df -h /home | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$(echo "$AVAILABLE_SPACE < 2" | bc)" -eq 1 ]; then
        echo -e "${RED}✗ Low disk space: ${AVAILABLE_SPACE}GB (2GB+ required)${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Disk space: ${AVAILABLE_SPACE}GB available${NC}"
    fi
}

# Voice mode selection
select_voice_mode() {
    echo -e "\n${BLUE}Select Voice Recognition Mode:${NC}"
    echo "1) Auto (Recommended - automatic fallback)"
    echo "2) Vosk (Offline, lightweight, 200MB RAM)"
    echo "3) Whisper Tiny (Best quality, 1GB RAM)"
    echo "4) Google Speech (Cloud-based, free)"
    echo "5) All (Install everything)"
    echo "6) None (No voice recognition)"
    
    read -p "Choice (1-6) [1]: " choice
    choice=${choice:-1}
    
    case $choice in
        1) VOICE_MODE="auto" ;;
        2) VOICE_MODE="vosk" ;;
        3) VOICE_MODE="whisper" ;;
        4) VOICE_MODE="speech_recognition" ;;
        5) VOICE_MODE="all" ;;
        6) VOICE_MODE="none" ;;
        *) VOICE_MODE="auto" ;;
    esac
    
    echo -e "${GREEN}Selected: $VOICE_MODE${NC}"
}

# Update system packages
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
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        build-essential \
        cmake \
        pkg-config
    
    # Audio dependencies
    sudo apt-get install -y \
        portaudio19-dev \
        python3-pyaudio \
        libportaudio2 \
        libasound2-dev \
        pulseaudio \
        espeak \
        ffmpeg \
        libsndfile1
    
    # GPIO and hardware dependencies
    if check_raspberry_pi; then
        sudo apt-get install -y \
            python3-rpi.gpio \
            i2c-tools \
            python3-smbus
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Enable hardware interfaces
enable_interfaces() {
    if ! check_raspberry_pi; then
        return
    fi
    
    echo -e "\n${BLUE}Enabling hardware interfaces...${NC}"
    
    # Enable I2C
    sudo raspi-config nonint do_i2c 0
    
    # Enable SPI
    sudo raspi-config nonint do_spi 0
    
    # Add user to required groups
    sudo usermod -a -G gpio,i2c,spi,audio $USER
    
    echo -e "${GREEN}✓ Hardware interfaces enabled${NC}"
}

# Clone or update repository
setup_repository() {
    echo -e "\n${BLUE}Setting up repository...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Directory exists. Updating...${NC}"
        cd "$INSTALL_DIR"
        git stash
        git pull origin main || true
    else
        echo -e "${BLUE}Cloning repository...${NC}"
        git clone "$GITHUB_REPO" "$INSTALL_DIR" || {
            echo -e "${YELLOW}Repository not available. Creating local installation...${NC}"
            mkdir -p "$INSTALL_DIR"
        }
    fi
    
    cd "$INSTALL_DIR"
}

# Setup Python virtual environment
setup_venv() {
    echo -e "\n${BLUE}Setting up Python virtual environment...${NC}"
    
    cd "$INSTALL_DIR"
    
    if [ -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment exists. Recreating...${NC}"
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    echo -e "${GREEN}✓ Virtual environment created${NC}"
}

# Install Python packages
install_python_packages() {
    echo -e "\n${BLUE}Installing Python packages...${NC}"
    
    # Core packages
    pip install flask flask-cors flask-socketio
    pip install requests numpy
    
    # Hardware packages (Raspberry Pi)
    if check_raspberry_pi; then
        pip install RPi.GPIO
        pip install adafruit-circuitpython-dht
        pip install adafruit-circuitpython-tpa2016
    fi
    
    # Audio packages
    pip install sounddevice pyaudio
    
    # TTS packages
    pip install pyttsx3 gTTS pygame
    
    # Voice recognition based on selection
    case $VOICE_MODE in
        "vosk"|"auto"|"all")
            echo -e "${BLUE}Installing Vosk...${NC}"
            pip install vosk
            ;;
    esac
    
    case $VOICE_MODE in
        "speech_recognition"|"auto"|"all")
            echo -e "${BLUE}Installing SpeechRecognition...${NC}"
            pip install SpeechRecognition
            ;;
    esac
    
    case $VOICE_MODE in
        "whisper"|"all")
            echo -e "${BLUE}Installing Whisper...${NC}"
            # Install PyTorch CPU version
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
            pip install openai-whisper
            
            # Pre-download tiny model
            echo -e "${BLUE}Downloading Whisper model...${NC}"
            python3 -c "import whisper; whisper.load_model('tiny')" || true
            ;;
    esac
    
    # OpenAI SDK
    if [ "$VOICE_MODE" != "none" ]; then
        pip install openai
    fi
    
    echo -e "${GREEN}✓ Python packages installed${NC}"
}

# Download Vosk model
setup_vosk_model() {
    if [[ "$VOICE_MODE" == "vosk" || "$VOICE_MODE" == "auto" || "$VOICE_MODE" == "all" ]]; then
        echo -e "\n${BLUE}Setting up Vosk model...${NC}"
        
        if [ ! -d "$VOSK_MODEL_DIR" ]; then
            echo -e "${BLUE}Downloading Vosk model (50MB)...${NC}"
            cd /home/$USER
            wget -q --show-progress "$VOSK_MODEL_URL" -O vosk-model.zip
            unzip -q vosk-model.zip
            rm vosk-model.zip
            echo -e "${GREEN}✓ Vosk model installed${NC}"
        else
            echo -e "${GREEN}✓ Vosk model already exists${NC}"
        fi
        
        cd "$INSTALL_DIR"
    fi
}

# Create application files
create_app_files() {
    echo -e "\n${BLUE}Creating application files...${NC}"
    
    cd "$INSTALL_DIR"
    
    # Create directories
    mkdir -p templates static docs systemd
    
    # Create .env file
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# BingHome Configuration
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# API Keys (add your keys here)
OPENAI_API_KEY=
BING_API_KEY=

# OAuth (optional)
OPENAI_CLIENT_ID=
OPENAI_CLIENT_SECRET=

# Server
PORT=5000

# Home Assistant
HOME_ASSISTANT_URL=http://localhost:8123
HOME_ASSISTANT_TOKEN=
EOF
        echo -e "${GREEN}✓ Configuration file created${NC}"
    fi
    
    # Create settings.json
    if [ ! -f "settings.json" ]; then
        cat > settings.json << EOF
{
  "voice_mode": "$VOICE_MODE",
  "wake_words": ["hey bing", "okay bing", "bing"],
  "tts_engine": "pyttsx3",
  "language": "en-US"
}
EOF
    fi
    
    echo -e "${YELLOW}Note: Copy app.py and templates/index.html from the repository${NC}"
}

# Setup systemd service
setup_service() {
    echo -e "\n${BLUE}Setting up systemd service...${NC}"
    
    cat > /tmp/binghome.service << EOF
[Unit]
Description=BingHome Smart Home System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/binghome.log
StandardError=append:/var/log/binghome.error.log

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/binghome.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable binghome.service
    
    echo -e "${GREEN}✓ Service installed and enabled${NC}"
}

# Setup audio
setup_audio() {
    echo -e "\n${BLUE}Configuring audio...${NC}"
    
    # Set audio output
    amixer cset numid=3 1 2>/dev/null || true
    
    # Test audio
    echo -e "${BLUE}Testing audio...${NC}"
    espeak "BingHome installation complete" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Audio configured${NC}"
}

# Create helper scripts
create_scripts() {
    echo -e "\n${BLUE}Creating helper scripts...${NC}"
    
    # Start script
    cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
EOF
    chmod +x "$INSTALL_DIR/start.sh"
    
    # Update script
    cat > "$INSTALL_DIR/update.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart binghome
EOF
    chmod +x "$INSTALL_DIR/update.sh"
    
    echo -e "${GREEN}✓ Helper scripts created${NC}"
}

# Final setup
final_setup() {
    echo -e "\n${BLUE}Finalizing installation...${NC}"
    
    # Get IP address
    IP=$(hostname -I | awk '{print $1}')
    
    # Create completion marker
    touch "$INSTALL_DIR/.installed"
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}   Installation Complete! 🎉            ${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    echo -e "\n${CYAN}Access BingHome at:${NC}"
    echo -e "  ${GREEN}http://$IP:5000${NC}"
    
    echo -e "\n${CYAN}Voice Mode:${NC} $VOICE_MODE"
    
    echo -e "\n${CYAN}Quick Commands:${NC}"
    echo -e "  Start:   ${GREEN}sudo systemctl start binghome${NC}"
    echo -e "  Stop:    ${GREEN}sudo systemctl stop binghome${NC}"
    echo -e "  Status:  ${GREEN}sudo systemctl status binghome${NC}"
    echo -e "  Logs:    ${GREEN}journalctl -u binghome -f${NC}"
    
    echo -e "\n${CYAN}Next Steps:${NC}"
    echo -e "  1. Open ${GREEN}http://$IP:5000${NC} in your browser"
    echo -e "  2. Click the settings icon (⚙️)"
    echo -e "  3. Add your API keys or sign in with ChatGPT"
    echo -e "  4. Say '${GREEN}Hey Bing${NC}' to start using voice control!"
    
    echo -e "\n${YELLOW}Note: Reboot recommended for hardware changes${NC}"
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
}

# Main installation flow
main() {
    show_banner
    check_raspberry_pi
    check_requirements
    select_voice_mode
    
    echo -e "\n${CYAN}Starting installation...${NC}"
    
    update_system
    install_dependencies
    enable_interfaces
    setup_repository
    setup_venv
    install_python_packages
    setup_vosk_model
    create_app_files
    setup_service
    setup_audio
    create_scripts
    final_setup
}

# Run installation
main
