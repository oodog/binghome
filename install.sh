#!/bin/bash
#
# BingHome Smart Hub - Simple Fixed Installer
#

set -e  # Exit on any error

# Configuration
GITHUB_REPO="https://github.com/oodog/binghome.git"
PROJECT_DIR="/home/$USER/binghome"
SERVICE_NAME="binghome"
SERVICE_USER="$USER"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo "🏠 BingHome Smart Hub - Simple Installer"
echo "========================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "Please run this script as a regular user, not as root!"
    exit 1
fi

# Update system and install dependencies
print_info "Updating system and installing dependencies..."
sudo apt update -q

# Install essential packages (split into smaller groups to avoid failures)
print_info "Installing basic tools..."
sudo apt install -y git curl wget python3 python3-pip python3-venv python3-dev build-essential

print_info "Installing audio dependencies..."
sudo apt install -y portaudio19-dev libasound2-dev || print_warning "Audio dependencies may have failed"

print_info "Installing additional libraries..."
sudo apt install -y libffi-dev libssl-dev pkg-config || print_warning "Some libraries may have failed"

print_info "Installing optional packages..."
sudo apt install -y chromium-browser unclutter network-manager i2c-tools || print_warning "Some optional packages may have failed"

# Enable I2C
print_info "Enabling I2C..."
sudo raspi-config nonint do_i2c 0 2>/dev/null || print_warning "Could not enable I2C automatically"

# Add user to gpio group
print_info "Adding user to gpio group..."
sudo usermod -a -G gpio,i2c,dialout $USER 2>/dev/null || print_warning "Could not add user to all groups"

# Remove existing directory if it exists
if [[ -d "$PROJECT_DIR" ]]; then
    print_warning "Existing installation found. Removing..."
    rm -rf "$PROJECT_DIR"
fi

# Clone the repository
print_info "Cloning repository..."
git clone "$GITHUB_REPO" "$PROJECT_DIR"

if [[ ! -d "$PROJECT_DIR" ]]; then
    print_error "Failed to clone repository"
    exit 1
fi

cd "$PROJECT_DIR"

# Create virtual environment
print_info "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install the problematic packages first with fixes
print_info "Installing Adafruit-DHT with --force-pi..."
pip install Adafruit-DHT --force-pi || print_warning "Adafruit-DHT installation failed"

print_info "Installing pyaudio..."
pip install pyaudio || print_warning "pyaudio installation failed"

# Install remaining requirements
if [[ -f requirements.txt ]]; then
    print_info "Installing remaining packages from requirements.txt..."
    pip install -r requirements.txt --no-deps || print_warning "Some packages may have failed"
    
    # Try again without --no-deps for missing dependencies
    print_info "Installing any missing dependencies..."
    pip install -r requirements.txt || print_warning "Some dependencies may be missing"
else
    print_warning "No requirements.txt found, installing basic packages..."
    pip install flask requests psutil
fi

# Install Docker
print_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm -f get-docker.sh
fi

sudo systemctl enable docker
sudo systemctl start docker

# Setup Home Assistant
print_info "Setting up Home Assistant..."
mkdir -p /home/$USER/homeassistant

# Stop existing container if it exists
docker stop homeassistant 2>/dev/null || true
docker rm homeassistant 2>/dev/null || true

# Start Home Assistant
docker run -d \
    --name homeassistant \
    --privileged \
    --restart=unless-stopped \
    -e TZ=Australia/Brisbane \
    -v /home/$USER/homeassistant:/config \
    --network=host \
    ghcr.io/home-assistant/home-assistant:stable

# Create systemd service
print_info "Creating systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=BingHome Smart Hub
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PATH=${PROJECT_DIR}/venv/bin
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🏠 Starting BingHome Smart Hub..."
echo "📱 Open http://localhost:5000 in your browser"
python app.py
EOF

chmod +x start.sh

# Test installation
print_info "Testing installation..."
sudo systemctl start ${SERVICE_NAME}.service
sleep 3

if systemctl is-active --quiet ${SERVICE_NAME}.service; then
    print_success "Service is running!"
else
    print_warning "Service may not be running. Check logs with: journalctl -u ${SERVICE_NAME}.service -f"
fi

print_success "Installation completed!"
echo ""
echo "🎉 BingHome Smart Hub is ready!"
echo ""
echo "📱 Access points:"
echo "   • BingHome: http://localhost:5000"
echo "   • Home Assistant: http://localhost:8123"
echo ""
echo "🚀 Start manually: cd $PROJECT_DIR && ./start.sh"
echo "📋 View logs: journalctl -u ${SERVICE_NAME}.service -f"
echo ""
echo "💡 You may need to reboot to join the gpio group: sudo reboot"