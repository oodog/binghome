#!/bin/bash
# Start BingHome Navigation Overlay
# This script ensures the correct display is used

# Find the active display
export DISPLAY=:0

# Kill any existing overlay
pkill -f "nav_overlay.py" 2>/dev/null

# Wait a moment
sleep 1

# Start the overlay
cd /home/rcook01/binghome
/usr/bin/python3 /home/rcook01/binghome/nav_overlay.py &

echo "Navigation overlay started"
