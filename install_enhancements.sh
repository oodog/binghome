#!/bin/bash
# BingHome Hub - Enhanced Features Installation Script

echo "=========================================="
echo "  BingHome Hub - Enhanced Features"
echo "  Installation Script"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    echo "Some features may not work correctly."
    echo ""
fi

# Step 1: Update system packages
echo -e "${GREEN}Step 1: Updating system packages...${NC}"
sudo apt-get update

# Step 2: Install network scanning tools
echo ""
echo -e "${GREEN}Step 2: Installing network scanning tools...${NC}"
echo "This will install nmap and arp-scan for device discovery"
read -p "Install network scanning tools? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt-get install -y nmap arp-scan
    echo -e "${GREEN}Network tools installed${NC}"
else
    echo -e "${YELLOW}Skipped network tools${NC}"
fi

# Step 3: Install Bluetooth support (optional)
echo ""
echo -e "${GREEN}Step 3: Installing Bluetooth support...${NC}"
echo "This will install Bluetooth libraries for device discovery"
read -p "Install Bluetooth support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt-get install -y bluetooth libbluetooth-dev
    echo -e "${GREEN}Bluetooth libraries installed${NC}"
else
    echo -e "${YELLOW}Skipped Bluetooth support${NC}"
fi

# Step 4: Activate virtual environment
echo ""
echo -e "${GREEN}Step 4: Activating virtual environment...${NC}"
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
    echo -e "${GREEN}Virtual environment activated${NC}"
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Step 5: Install Python dependencies
echo ""
echo -e "${GREEN}Step 5: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Check if specific packages installed correctly
echo ""
echo "Checking installations..."

if python -c "import nmap" 2>/dev/null; then
    echo -e "${GREEN}✓ python-nmap installed${NC}"
else
    echo -e "${YELLOW}⚠ python-nmap not available (network scanning limited)${NC}"
fi

if python -c "import bluetooth" 2>/dev/null; then
    echo -e "${GREEN}✓ pybluez installed${NC}"
else
    echo -e "${YELLOW}⚠ pybluez not available (Bluetooth discovery disabled)${NC}"
fi

if python -c "import flask_socketio" 2>/dev/null; then
    echo -e "${GREEN}✓ flask-socketio installed${NC}"
else
    echo -e "${RED}✗ flask-socketio failed to install${NC}"
fi

# Step 6: Set permissions for network scanning
echo ""
echo -e "${GREEN}Step 6: Setting up permissions...${NC}"
echo "For network device discovery, arp-scan needs sudo access"
read -p "Configure sudo access for arp-scan? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Add user to sudoers for arp-scan only (no password)
    CURRENT_USER=$(whoami)
    SUDOERS_FILE="/etc/sudoers.d/binghome-arpscan"

    echo "$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan" | sudo tee $SUDOERS_FILE > /dev/null
    sudo chmod 0440 $SUDOERS_FILE

    echo -e "${GREEN}Sudo access configured for arp-scan${NC}"
else
    echo -e "${YELLOW}Skipped sudo configuration${NC}"
    echo "You'll need to enter password when scanning devices"
fi

# Step 7: Configure display settings
echo ""
echo -e "${GREEN}Step 7: Display configuration...${NC}"
echo "For optimal display on 7-inch touchscreen:"
echo "1. Resolution should be 1024x600 (or 800x480)"
echo "2. Enable GPU acceleration in raspi-config"
echo "3. Consider auto-starting browser in fullscreen"
echo ""
read -p "Open raspi-config to adjust display settings? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo raspi-config
fi

# Step 8: Test the installation
echo ""
echo -e "${GREEN}Step 8: Testing installation...${NC}"
echo "Starting BingHome Hub for testing..."
echo "Press Ctrl+C to stop when ready"
echo ""
sleep 2

python app.py &
APP_PID=$!

sleep 5

if ps -p $APP_PID > /dev/null; then
    echo -e "${GREEN}✓ BingHome Hub started successfully${NC}"
    echo ""
    echo "Open your browser and navigate to:"
    echo "  http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "Press Enter to stop the test server..."
    read
    kill $APP_PID
else
    echo -e "${RED}✗ Failed to start BingHome Hub${NC}"
    echo "Check logs for errors: tail -f logs/binghome.log"
fi

# Step 9: Set up autostart (optional)
echo ""
echo -e "${GREEN}Step 9: Autostart configuration...${NC}"
echo "Would you like BingHome to start automatically on boot?"
read -p "Configure autostart? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/binghome.service"

    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=BingHome Hub
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable binghome
    sudo systemctl start binghome

    echo -e "${GREEN}Autostart configured${NC}"
    echo "Service status:"
    sudo systemctl status binghome --no-pager
else
    echo -e "${YELLOW}Skipped autostart configuration${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open BingHome in your browser"
echo "2. Go to Settings and configure:"
echo "   - Weather API key (OpenWeatherMap)"
echo "   - Home Assistant URL and token"
echo "   - Voice settings"
echo "3. Go to Devices page and click 'Scan Devices'"
echo "4. Enjoy your enhanced smart home hub!"
echo ""
echo "Documentation:"
echo "  - ENHANCEMENTS.md - Full feature documentation"
echo "  - README.md - Original documentation"
echo ""
echo "For support: https://github.com/oodog/binghome"
echo ""
