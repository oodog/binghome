#!/bin/bash
set -euo pipefail

# ==========================
# Config
# ==========================
REPO="https://github.com/oodog/binghome.git"
APP_DIR="$HOME/binghome"
SERVICE="binghome"
UPDATE_SERVICE="binghome-updater"
UPDATE_TIMER="binghome-updater.timer"
TZ_DEFAULT="Australia/Brisbane"

echo "🚀 Installing BingHome as $(whoami)"
echo "📁 Target directory: $APP_DIR"

# ==========================
# Detect default branch (main/master)
# ==========================
echo "🔎 Detecting default branch..."
DEFAULT_BRANCH=$(git ls-remote --symref "$REPO" HEAD 2>/dev/null | awk -F'[:\t ]+' '/^ref:/ {print $3; exit}')
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
echo "🌿 Detected default branch: $DEFAULT_BRANCH"

# ==========================
# System packages
# ==========================
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y \
  git curl ca-certificates jq \
  python3 python3-venv python3-pip \
  wireless-tools network-manager \
  i2c-tools libgpiod2 gpiod \
  chromium-browser xserver-xorg x11-xserver-utils xinit openbox unclutter \
  xdotool \
  mpv yt-dlp              # NEW: media playback


# Set timezone (best effort)
if [ -n "${TZ_DEFAULT}" ]; then
  sudo timedatectl set-timezone "${TZ_DEFAULT}" || true
fi

# Make sure NetworkManager is running (for Wi-Fi control)
sudo systemctl enable --now NetworkManager || true
sudo usermod -aG netdev "$USER" || true

# ==========================
# Get code
# ==========================
echo "⬇️  Cloning repository..."
rm -rf "$APP_DIR"
git clone --branch "$DEFAULT_BRANCH" "$REPO" "$APP_DIR" || {
  echo "⚠️  Branch clone failed; cloning default and switching…"
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
  git checkout "$DEFAULT_BRANCH" || true
}
cd "$APP_DIR"

# ==========================
# Python venv + deps
# ==========================
echo "🐍 Setting up Python venv..."
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# ==========================
# Ensure minimal app assets
# ==========================
mkdir -p templates static/images

# Default tiny image (1x1) so the app always has a fallback
if [ ! -f static/images/default.jpg ]; then
  echo "🖼  Adding default fallback image..."
  base64 -d > static/images/default.jpg <<'EOF'
/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEA8QDxAPDw8QDw8PDw8PDw8PDw8QFREWFhUR
ExUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGxAQGy0fHyUtLSstLS0tLS0t
LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKAAoAMBIgACEQEDEQH/
xAAXAAEBAQEAAAAAAAAAAAAAAAAABgUH/8QAHhABAAEDBQAAAAAAAAAAAAAAAQIAAwQREiExQbH/
xAAWAQEBAQAAAAAAAAAAAAAAAAADAgH/xAAWEQEBAQAAAAAAAAAAAAAAAAABAgH/2gAMAwEAAhED
EQA/AK8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/Z
EOF
fi

# ==========================
# systemd service for BingHome
# ==========================
echo "🧩 Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/${SERVICE}.service"
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=BingHome Smart Hub
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=FLASK_ENV=production
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ==========================
# Auto-updater (hourly)
# ==========================
echo "🔁 Creating auto-update service + timer..."
UPDATER_FILE="/etc/systemd/system/${UPDATE_SERVICE}.service"
sudo tee "$UPDATER_FILE" >/dev/null <<EOF
[Unit]
Description=Update BingHome from Git and restart if changed

[Service]
Type=oneshot
User=${USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/update.sh
EOF

TIMER_FILE="/etc/systemd/system/${UPDATE_TIMER}"
sudo tee "$TIMER_FILE" >/dev/null <<EOF
[Unit]
Description=Run BingHome updater hourly

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=${UPDATE_SERVICE}.service

[Install]
WantedBy=timers.target
EOF

# Update helper used by the updater service
cat > update.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .git ]; then
  echo "Not a git repo; skipping update."
  exit 0
fi

UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)
if [ -z "$UPSTREAM" ]; then
  echo "No upstream set for current branch; skipping update."
  exit 0
fi

git fetch --all --prune

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" != "$REMOTE" ]; then
  echo "New version found; updating…"
  git pull --rebase
  if [ -f requirements.txt ]; then
    ./venv/bin/pip install -r requirements.txt || true
  fi
  sudo systemctl restart binghome
  echo "Updated and restarted."
else
  echo "No updates."
fi
EOF
chmod +x update.sh

# ==========================
# Helper scripts
# ==========================
cat > start.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
EOF
chmod +x start.sh

cat > start_kiosk.sh <<'EOF'
#!/bin/bash
set -euo pipefail

export DISPLAY=:0

# Start the app service (if not already running)
sudo systemctl start binghome

# Wait for health endpoint (max ~30s)
for i in $(seq 1 30); do
  if curl -s http://localhost:5000/api/health | grep -q healthy; then
    break
  fi
  sleep 1
done

# Chromium kiosk
xset s off || true
xset s noblank || true
xset -dpms || true
unclutter -idle 0.5 -root &

chromium-browser \
  --kiosk \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-gpu \
  --no-sandbox \
  --disable-dev-shm-usage \
  --user-data-dir=/tmp/binghome_kiosk \
  http://localhost:5000
EOF
chmod +x start_kiosk.sh

# ==========================
# Kiosk via Openbox autostart
# ==========================
echo "🖥  Configuring kiosk (Openbox autostart)..."
mkdir -p "$HOME/.config/openbox"
cat > "$HOME/.config/openbox/autostart" <<EOF
# Disable screen blanking / power saving
xset s off
xset s noblank
xset -dpms

# Hide mouse cursor after idle
unclutter -idle 0.5 -root &

# Start the kiosk launcher
cd $APP_DIR
./start_kiosk.sh &
EOF
chmod +x "$HOME/.config/openbox/autostart"

# ==========================
# Auto-start X on tty1
# ==========================
echo "🪄 Enabling auto-start of X on tty1..."
if ! grep -q "startx" "$HOME/.bash_profile" 2>/dev/null; then
  {
    echo ''
    echo '# Auto-start X (Openbox) on local console'
    echo 'if [ -z "$SSH_CONNECTION" ] && [ "$(tty)" = "/dev/tty1" ]; then'
    echo '  startx'
    echo 'fi'
  } >> "$HOME/.bash_profile"
fi

# ==========================
# Home Assistant (Docker) + systemd
# ==========================
echo "🏠 Installing Home Assistant (Container)..."

# Install Docker + compose plugin if needed
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi
if ! docker compose version >/dev/null 2>&1; then
  sudo apt install -y docker-compose-plugin
fi

HA_DIR="$HOME/homeassistant"
mkdir -p "$HA_DIR"

cat > "$HA_DIR/docker-compose.yml" <<EOF
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    environment:
      - TZ=${TZ_DEFAULT}
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    network_mode: host
    restart: unless-stopped
EOF

sudo tee /etc/systemd/system/homeassistant.service >/dev/null <<EOF
[Unit]
Description=Home Assistant (Docker Compose)
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${HA_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable homeassistant
sudo systemctl start homeassistant
echo "✅ Home Assistant starting at http://localhost:8123 (first boot may take a few minutes)"

# ==========================
# Polkit rule (optional) for nmcli Wi-Fi control without sudo
# ==========================
echo "🛡  Adding polkit rule to allow nmcli Wi-Fi operations for 'netdev' group..."
sudo tee /etc/polkit-1/rules.d/10-nmcli-wifi.rules >/dev/null <<'EOF'
polkit.addRule(function(action, subject) {
  if (subject.isInGroup("netdev") &&
      (action.id == "org.freedesktop.NetworkManager.enable-disable-wifi" ||
       action.id == "org.freedesktop.NetworkManager.wifi.scan" ||
       action.id == "org.freedesktop.NetworkManager.network-control" ||
       action.id == "org.freedesktop.NetworkManager.settings.modify.system" ||
       action.id == "org.freedesktop.NetworkManager.settings.modify.own")) {
    return polkit.Result.YES;
  }
});
EOF
sudo systemctl restart polkit || true
sudo systemctl restart NetworkManager || true

# ==========================
# Enable and start services
# ==========================
echo "🔧 Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" "$UPDATE_TIMER"
sudo systemctl start "$SERVICE" "$UPDATE_TIMER"

echo ""
echo "✅ Install complete."
echo "➡️  REBOOT recommended: sudo reboot"
echo "💡 After reboot: Pi should auto-login to console, start X, run Openbox, and launch Chromium in kiosk pointed at BingHome."
echo "💡 HA is running via Docker (host mode) on http://localhost:8123"
echo "💡 If Wi-Fi scan still says 'unavailable': sudo rfkill unblock all && sudo nmcli radio wifi on && sudo ip link set wlan0 up"
