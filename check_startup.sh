#!/bin/bash
# BingHome startup checker

echo "Checking BingHome startup..."

# Wait for system to be ready
sleep 30

# Check if service is running
if systemctl is-active --quiet binghome; then
    echo "BingHome is running"
else
    echo "BingHome failed to start, attempting restart..."
    sudo systemctl restart binghome
fi

# Check if port 5000 is listening
if netstat -tln | grep -q ':5000'; then
    echo "BingHome web interface is accessible on port 5000"
else
    echo "Port 5000 is not listening"
fi
