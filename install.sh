#!/bin/bash
#
# BingHome Smart Hub - GitHub Deployment Script for Raspberry Pi OS
# 
# One-command installation:
# curl -sSL https://raw.githubusercontent.com/oodog/binghome/main/install.sh | bash
#
# Or manual:
# wget https://raw.githubusercontent.com/oodog/binghome/main/install.sh
# chmod +x install.sh && ./install.sh
#

set -e  # Exit on any error

# Configuration
GITHUB_REPO="https://github.com/oodog/binghome.git"
GITHUB_RAW="https://raw.githubusercontent.com/oodog/binghome/main"
PROJECT_DIR="/home/$USER/binghome"
SERVICE_NAME="binghome"
SERVICE_USER="$USER"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print functions
print_banner() {
    clear
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║                    🏠 BINGHOME SMART HUB 🏠                      ║"
    echo "║                                                                  ║"
    echo "║                    Raspberry Pi OS Installer                    ║"
    echo "║                                                                  ║"
    echo "║                   GitHub: oodog/binghome                        ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${CYAN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Raspberry Pi OS
check_raspberry_pi() {
    print_step "Checking Raspberry Pi OS compatibility..."
    
    if [[ $EUID -eq 0 ]]; then
        print_error "Please run this script as a regular user, not as root!"
        exit 1
    fi
    
    # Check if running on Raspberry Pi
    if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        if [[ ! -f /etc/rpi-issue ]]; then
            print_warning "This doesn't appear to be a Raspberry Pi, but continuing anyway..."
        fi
    fi
    
    # Check Raspberry Pi OS
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" != "raspbian" ]] && [[ "$ID" != "debian" ]]; then
            print_warning "This script is optimized for Raspberry Pi OS, but will try to continue..."
        fi
    fi
    
    print_success "System check completed"
}

# Update system and install dependencies
install_system_dependencies() {
    print_step "Installing system dependencies..."
    
    # Update package list
    print_info "Updating package lists..."
    sudo apt update -qq
    
    # Install essential packages
    print_info "Installing essential packages..."
    
    # Install basic development tools first
    print_info "Installing development tools..."
    sudo apt install -y \
        git \
        curl \
        wget \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        pkg-config || { print_error "Failed to install basic development tools"; exit 1; }
        
    # Install audio dependencies for pyaudio
    print_info "Installing audio dependencies..."
    sudo apt install -y \
        portaudio19-dev \
        python3-pyaudio \
        libasound2-dev || print_warning "Some audio dependencies failed to install"
        
    # Install core libraries
    print_info "Installing core libraries..."
    sudo apt install -y \
        libffi-dev \
        libssl-dev \
        libjpeg-dev \
        zlib1g-dev || print_warning "Some core libraries failed to install"
        
    # Install optional image processing libraries
    print_info "Installing image processing libraries..."
    sudo apt install -y libfreetype6-dev || print_warning "libfreetype6-dev not available"
    sudo apt install -y liblcms2-dev || print_warning "liblcms2-dev not available"
    sudo apt install -y libopenjp2-7 || print_warning "libopenjp2-7 not available"
    
    # Try to install image library with multiple fallbacks
    print_info "Installing image library..."
    if ! sudo apt install -y libtiff6 2>/dev/null; then
        if ! sudo apt install -y libtiff5 2>/dev/null; then
            if ! sudo apt install -y libtiff-dev 2>/dev/null; then
                print_warning "Could not install any libtiff library version"
            fi
        fi
    fi
        
    # Install system tools
    print_info "Installing system tools..."
    sudo apt install -y \
        chromium-browser \
        unclutter \
        network-manager \
        i2c-tools || print_warning "Some system tools failed to install"
        
    # Install display tools
    print_info "Installing display tools..."        
    sudo apt install -y \
        dbus-x11 \
        xorg \
        xinit \
        lightdm || print_warning "Some display tools failed to install"
        
    # Try to install newer GPIO libraries (optional)
    print_info "Installing GPIO libraries..."
    sudo apt install -y libgpiod2 python3-libgpiod 2>/dev/null || print_warning "Newer GPIO libraries not available"
    
    print_success "System dependencies installed"
}

# Enable Raspberry Pi specific features
enable_pi_features() {
    print_step "Enabling Raspberry Pi features..."
    
    # Enable I2C
    print_info "Enabling I2C interface..."
    sudo raspi-config nonint do_i2c 0 2>/dev/null || print_warning "Could not enable I2C automatically"
    
    # Enable SPI (might be needed for some sensors)
    print_info "Enabling SPI interface..."
    sudo raspi-config nonint do_spi 0 2>/dev/null || print_warning "Could not enable SPI automatically"
    
    # Add user to required groups
    print_info "Adding user to gpio, i2c, spi groups..."
    sudo usermod -a -G gpio,i2c,spi,dialout $USER || print_warning "Could not add user to all groups"
    
    # Update GPU memory split
    print_info "Configuring GPU memory..."
    if [[ -f /boot/config.txt ]]; then
        if ! grep -q "gpu_mem=" /boot/config.txt; then
            echo "gpu_mem=128" | sudo tee -a /boot/config.txt > /dev/null
        fi
        if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
            echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
        fi
    fi
    
    print_success "Raspberry Pi features enabled"
}

# Install Docker for Home Assistant
install_docker() {
    print_step "Installing Docker for Home Assistant..."
    
    if command -v docker &> /dev/null; then
        print_info "Docker is already installed"
    else
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm -f get-docker.sh
        print_info "Docker installed successfully"
    fi
    
    # Start Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    print_success "Docker setup completed"
}

# Clone or update the GitHub repository
setup_project_repository() {
    print_step "Setting up project repository..."
    
    # Remove existing directory if it exists
    if [[ -d "$PROJECT_DIR" ]]; then
        print_warning "Existing installation found. Creating backup..."
        sudo mv "$PROJECT_DIR" "${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    fi
    
    # Clone the repository
    print_info "Cloning repository from GitHub..."
    git clone "$GITHUB_REPO" "$PROJECT_DIR"
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        print_error "Failed to clone repository"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    print_success "Repository cloned successfully"
}

# Setup Python virtual environment
setup_python_environment() {
    print_step "Setting up Python environment..."
    
    cd "$PROJECT_DIR"
    
    # Create virtual environment
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements from requirements.txt with necessary fixes
    if [[ -f requirements.txt ]]; then
        print_info "Installing Python dependencies from requirements.txt..."
        
        # Install problematic packages first with fixes
        print_info "Pre-installing problematic packages with fixes..."
        pip install Adafruit-DHT --force-pi || print_warning "Adafruit-DHT installation failed, will try again with requirements.txt"
        pip install pyaudio || print_warning "pyaudio installation failed, will try again with requirements.txt"
        
        # Install all requirements with force flags to handle Pi detection issues
        print_info "Installing all requirements..."
        pip install -r requirements.txt --force-pi || {
            print_warning "Some packages failed with --force-pi, trying without force flag..."
            pip install -r requirements.txt || print_warning "Some requirements may have failed to install"
        }
    else
        print_error "requirements.txt file not found!"
        exit 1
    fi
    
    print_success "Python environment setup completed"
}

# Install and configure Home Assistant
setup_home_assistant() {
    print_step "Setting up Home Assistant..."
    
    # Create Home Assistant directory
    mkdir -p /home/$USER/homeassistant
    
    # Check if Home Assistant container already exists
    if docker ps -a | grep -q homeassistant; then
        print_info "Stopping existing Home Assistant container..."
        docker stop homeassistant 2>/dev/null || true
        docker rm homeassistant 2>/dev/null || true
    fi
    
    # Start Home Assistant container
    print_info "Starting Home Assistant container..."
    docker run -d \
        --name homeassistant \
        --privileged \
        --restart=unless-stopped \
        -e TZ=Australia/Brisbane \
        -v /home/$USER/homeassistant:/config \
        -v /run/dbus:/run/dbus:ro \
        --network=host \
        ghcr.io/home-assistant/home-assistant:stable
    
    print_success "Home Assistant setup completed"
}

# Create systemd service
create_systemd_service() {
    print_step "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=BingHome Smart Hub
Documentation=https://github.com/oodog/binghome
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PATH=${PROJECT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=${PROJECT_DIR}
Environment=HOME_ASSISTANT_URL=http://localhost:8123
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}.service
    
    print_success "Systemd service created and enabled"
}

# Create startup scripts
create_startup_scripts() {
    print_step "Creating startup scripts..."
    
    cd "$PROJECT_DIR"
    
    # Create manual start script
    cat > start.sh << 'EOF'
#!/bin/bash
# Manual start script for BingHome Smart Hub

cd "$(dirname "$0")"
source venv/bin/activate

export HOME_ASSISTANT_URL="http://localhost:8123"
export HOME_ASSISTANT_TOKEN="${HOME_ASSISTANT_TOKEN:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export BING_API_KEY="${BING_API_KEY:-}"

echo "🏠 Starting BingHome Smart Hub..."
echo "📱 Open http://localhost:5000 in your browser"
echo "🏠 Home Assistant: http://localhost:8123"
echo "⏹️  Press Ctrl+C to stop"

python app.py
EOF

    # Create kiosk start script
    cat > start_kiosk.sh << 'EOF'
#!/bin/bash
# Kiosk mode start script for BingHome Smart Hub

cd "$(dirname "$0")"

# Set display
export DISPLAY=:0

# Start the service if not running
sudo systemctl start binghome.service

# Wait for service to be ready
echo "⏳ Waiting for BingHome to start..."
for i in {1..30}; do
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ BingHome is ready!"
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        echo "❌ BingHome failed to start"
        exit 1
    fi
done

# Configure display for kiosk mode
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true
unclutter -idle 0.5 -root &

# Start Chromium in kiosk mode
echo "🖥️  Starting kiosk mode..."
chromium-browser \
    --kiosk \
    --no-first-run \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-gpu \
    --no-sandbox \
    --disable-dev-shm-usage \
    --user-data-dir=/tmp/binghome_kiosk \
    --window-size=1024,600 \
    --autoplay-policy=no-user-gesture-required \
    http://localhost:5000
EOF

    # Make scripts executable
    chmod +x start.sh start_kiosk.sh
    
    print_success "Startup scripts created"
}

# Configure desktop autostart
configure_desktop_autostart() {
    print_step "Configuring desktop autostart..."
    
    # Create autostart directory
    mkdir -p ~/.config/autostart
    
    # Create autostart desktop entry
    cat > ~/.config/autostart/binghome.desktop << EOF
[Desktop Entry]
Type=Application
Name=BingHome Smart Hub
Comment=Start BingHome Smart Hub in kiosk mode
Exec=${PROJECT_DIR}/start_kiosk.sh
Icon=${PROJECT_DIR}/icon.png
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Categories=System;
EOF

    print_success "Desktop autostart configured"
}

# Test the installation
test_installation() {
    print_step "Testing installation..."
    
    cd "$PROJECT_DIR"
    
    # Start the service
    print_info "Starting BingHome service..."
    sudo systemctl start ${SERVICE_NAME}.service
    
    # Wait for service to start
    sleep 5
    
    # Test if service is running
    if systemctl is-active --quiet ${SERVICE_NAME}.service; then
        print_success "Service is running"
    else
        print_warning "Service may not be running properly"
        print_info "Check logs with: journalctl -u ${SERVICE_NAME}.service -f"
    fi
    
    # Test web interface
    print_info "Testing web interface..."
    if curl -s http://localhost:5000/api/health > /dev/null; then
        print_success "Web interface is responding"
    else
        print_warning "Web interface is not responding yet"
    fi
    
    # Test Home Assistant
    print_info "Testing Home Assistant..."
    if curl -s http://localhost:8123 > /dev/null; then
        print_success "Home Assistant is responding"
    else
        print_warning "Home Assistant may still be starting up"
    fi
    
    print_success "Installation test completed"
}

# Display final instructions
show_completion_info() {
    print_banner
    echo -e "${GREEN}🎉 BingHome Smart Hub Installation Complete! 🎉${NC}\n"
    
    echo -e "${CYAN}📱 Access Points:${NC}"
    echo "   • BingHome Hub: http://localhost:5000"
    echo "   • Home Assistant: http://localhost:8123"
    echo ""
    
    echo -e "${CYAN}🚀 Start Commands:${NC}"
    echo "   • Manual start: cd $PROJECT_DIR && ./start.sh"
    echo "   • Kiosk mode: cd $PROJECT_DIR && ./start_kiosk.sh"
    echo "   • Service: sudo systemctl start ${SERVICE_NAME}"
    echo ""
    
    echo -e "${CYAN}🔧 Management Commands:${NC}"
    echo "   • View logs: journalctl -u ${SERVICE_NAME} -f"
    echo "   • Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo "   • Stop: sudo systemctl stop ${SERVICE_NAME}"
    echo "   • Status: sudo systemctl status ${SERVICE_NAME}"
    echo ""
    
    echo -e "${CYAN}⚙️ Configuration:${NC}"
    echo "   • Project directory: $PROJECT_DIR"
    echo "   • Service runs on boot: Enabled"
    echo "   • Desktop autostart: Configured"
    echo ""
    
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "   1. Reboot your Raspberry Pi to test auto-start"
    echo "   2. Configure Home Assistant at http://localhost:8123"
    echo "   3. Add your API keys to environment variables"
    echo "   4. Wire your sensors according to GPIO pin guide"
    echo "   5. Customize your smart home setup"
    echo ""
    
    echo -e "${YELLOW}🔌 Hardware Setup:${NC}"
    echo "   • DHT22 Sensor: GPIO4 (Pin 7)"
    echo "   • Gas Sensor: GPIO17 (Pin 11)"
    echo "   • Light Sensor: GPIO27 (Pin 13)"
    echo "   • Audio Amp (I2C): SDA/SCL (Pins 3/5)"
    echo ""
    
    echo -e "${GREEN}✅ Installation completed successfully!${NC}"
    echo -e "${GREEN}🏠 Your BingHome Smart Hub is ready to use!${NC}"
    echo ""
    echo -e "${BLUE}For support, visit: https://github.com/oodog/binghome${NC}"
}

# Main installation function
main() {
    print_banner
    
    echo -e "${BLUE}Starting BingHome Smart Hub installation...${NC}\n"
    
    # Run installation steps
    check_raspberry_pi
    install_system_dependencies
    enable_pi_features
    install_docker
    setup_project_repository
    setup_python_environment
    setup_home_assistant
    create_systemd_service
    create_startup_scripts
    configure_desktop_autostart
    test_installation
    show_completion_info
    
    echo -e "\n${GREEN}🎯 Installation completed! Reboot recommended.${NC}"
    echo -e "${YELLOW}💡 Run 'sudo reboot' to restart and test auto-start functionality.${NC}"
}

# Run the installer
main "$@"