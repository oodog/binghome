#!/bin/bash
# BingHome - ngrok Setup Script
# This script helps set up ngrok for easy Google Photos OAuth

echo "================================================"
echo "BingHome - ngrok Setup for Google Photos"
echo "================================================"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "📦 Installing ngrok..."
    
    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz"
    elif [[ "$ARCH" == "armv7l" ]]; then
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz"
    else
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
    fi
    
    cd /tmp
    wget -q $NGROK_URL -O ngrok.tgz
    tar xzf ngrok.tgz
    sudo mv ngrok /usr/local/bin/
    rm ngrok.tgz
    
    echo "✅ ngrok installed!"
else
    echo "✅ ngrok already installed"
fi

echo ""
echo "================================================"
echo "⚠️  IMPORTANT: You need an ngrok account"
echo "================================================"
echo ""
echo "1. Go to: https://dashboard.ngrok.com/signup"
echo "2. Sign up for FREE (no credit card needed)"
echo "3. Copy your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
read -p "Paste your ngrok authtoken here: " AUTHTOKEN

if [ -z "$AUTHTOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

echo ""
echo "🔐 Configuring ngrok..."
ngrok config add-authtoken $AUTHTOKEN

echo ""
echo "================================================"
echo "🚀 Starting ngrok tunnel..."
echo "================================================"
echo ""
echo "Starting ngrok on port 5000..."
echo "This will give you a public HTTPS URL for BingHome"
echo ""
echo "Press Ctrl+C to stop ngrok when done"
echo ""

# Start ngrok
ngrok http 5000 --log=stdout

