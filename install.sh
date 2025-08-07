#!/bin/bash
# binghome - Auto Installer for Raspberry Pi 5 (7" Screen)
# Run with: curl -sSL https://your-link-here/install.sh | bash

echo "🚀 Installing binghome on Raspberry Pi..."

# Ensure we're on Pi OS
if ! [ -f /etc/os-release ] || ! grep -q "Rasp" /etc/os-release; then
    echo "⚠️  Warning: Not running on Raspberry Pi OS, continuing anyway..."
fi

# Install system packages
sudo apt update
sudo apt install -y git python3-pip python3-venv python3-flask \
                   python3-bs4 xserver-xorg x11-xserver-utils \
                   xinit openbox chromium-browser unclutter

# Setup project directory
cd /home/pi || exit
rm -rf binghome
mkdir -p binghome/templates binghome/static/images
cd binghome || exit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install Python deps
pip install --upgrade pip
pip install flask requests beautifulsoup4

# --------------------------------------------------
# Create: binghome.py (Flask App)
# --------------------------------------------------
cat > binghome.py << 'EOF'
import os
import requests
from flask import Flask, render_template, send_from_directory
from bs4 import BeautifulSoup

app = Flask(__name__)

BING_URL = "https://www.bing.com"
IMAGE_DIR = os.path.join(app.static_folder, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def get_bing_wallpaper():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0 Safari/537.36'
        }
        r = requests.get(f"{BING_URL}/", headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        # Try background image in body style
        bg_image = None
        body = soup.find('body', style=True)
        if body:
            style = body['style']
            start = style.find('url(') + 4
            end = style.find(')', start)
            if start != -1 and end != -1:
                bg_image = BING_URL + style[start:end].strip("'\"")

        # Fallback: og:image
        if not bg_image:
            meta = soup.find('meta', {'property': 'og:image'})
            if meta and meta.get('content'):
                img_url = meta['content']
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = BING_URL + img_url
                bg_image = img_url

        if bg_image:
            img_name = os.path.basename(bg_image.split('?')[0])
            img_path = os.path.join(IMAGE_DIR, img_name)

            if not os.path.exists(img_path):
                img_data = requests.get(bg_image, headers=headers, timeout=10).content
                with open(img_path, 'wb') as f:
                    f.write(img_data)

            return f"/static/images/{img_name}", "Today's Bing Wallpaper"
    except Exception as e:
        print(f"[ERROR] Failed to fetch wallpaper: {e}")
    
    return "/static/images/default.jpg", "Bing Wallpaper"

@app.route("/")
def index():
    img_url, title = get_bing_wallpaper()
    return render_template("index.html", img_url=img_url, title=title)

@app.route('/static/images/<filename>')
def download_file(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
EOF

# --------------------------------------------------
# Create: templates/index.html
# --------------------------------------------------
cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no" />
    <title>Bing Home</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        .background {
            background: url("{{ img_url }}") no-repeat center center;
            background-size: cover;
            width: 100%;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
            font-size: 2.2em;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="background">
        {{ title }}
    </div>
</body>
</html>
EOF

# --------------------------------------------------
# Create: start.sh
# --------------------------------------------------
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python binghome.py
EOF
chmod +x start.sh

# --------------------------------------------------
# Setup Auto-Start on Boot (Openbox + Chromium)
# --------------------------------------------------
echo "🔧 Setting up auto-start..."

mkdir -p ~/.config/openbox

cat > ~/.config/openbox/autostart << 'EOF'
# Disable screensaver and power management
xset s off
xset s noblank
xset -dpms
unclutter -idle 0.1 &

# Start Flask server
cd /home/pi/binghome
./start.sh &
sleep 5

# Launch browser in kiosk mode
chromium-browser --kiosk \
                 --no-first-run \
                 --disable-infobars \
                 --disable-session-crashed-bubble \
                 --disable-restore-session-state \
                 --disable-gpu \
                 --disable-software-rasterizer \
                 http://localhost:5000
EOF

chmod +x ~/.config/openbox/autostart

# Add startx to .bash_profile if not exists
if ! grep -q "startx" ~/.bash_profile 2>/dev/null; then
    echo 'if [ -z "${SSH_CONNECTION}" ] && [ "$(tty)" = "/dev/tty1" ]; then startx; fi' >> ~/.bash_profile
fi

# Disable screen blanking in config.txt
if ! grep -q "hdmi_blanking=1" /boot/config.txt 2>/dev/null; then
    echo "hdmi_blanking=1" | sudo tee -a /boot/config.txt
fi

# Final message
echo "✅ Installation complete!"
echo "🔁 Reboot to launch automatically: sudo reboot"