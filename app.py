import os
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

# ---------- Optional hardware ----------
GPIO = None
Adafruit_DHT = None
SMBus = None

try:
    import RPi.GPIO as _GPIO
    GPIO = _GPIO
except Exception:
    pass

try:
    import Adafruit_DHT as _Adafruit_DHT
    Adafruit_DHT = _Adafruit_DHT
except Exception:
    pass

try:
    from smbus2 import SMBus as _SMBus
    SMBus = _SMBus
except Exception:
    pass

# ---------- LLM / Voice ----------
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    pass

# ---------- App ----------
app = Flask(__name__)
APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "settings.json"

# -------------------- Config helpers --------------------
DEFAULT_CONFIG = {
    "provider": "openai",         # "openai" or "bing" (bing stubbed)
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "ha_base_url": "http://localhost:8123",
    "ha_token": "",
    "wake_word_enabled": False
}

def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            # migrate defaults if new keys appear
            changed = False
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
                    changed = True
            if changed:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(data, f, indent=2)
            return data
        except Exception:
            pass
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG.copy()

def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

CONFIG = load_config()

# -------------------- Hardware config --------------------
DHT_SENSOR = Adafruit_DHT.DHT22 if Adafruit_DHT else None
DHT_PIN = 4
GAS_PIN = 17
LIGHT_PIN = 27

I2C_BUS = 1
TPA2016_ADDR = 0x58
TPA2016_AGC_CONTROL = 0x01
TPA2016_FIXED_GAIN = 0x05

audio_available = False
i2c_bus = None
if SMBus:
    try:
        i2c_bus = SMBus(I2C_BUS)
        audio_available = True
    except Exception:
        audio_available = False

if GPIO:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GAS_PIN, GPIO.IN)
        GPIO.setup(LIGHT_PIN, GPIO.IN)
    except Exception:
        GPIO = None

# -------------------- Bing wallpaper --------------------
BING_URL = "https://www.bing.com"
IMAGE_DIR = APP_DIR / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

def get_bing_wallpaper():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(BING_URL + "/", headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        bg_image = None

        body = soup.find("body", style=True)
        if body:
            style = body["style"]
            if "url(" in style:
                start = style.find("url(") + 4
                end = style.find(")", start)
                if start > 3 and end > 0:
                    bg = style[start:end].strip("'\"")
                    bg_image = bg if bg.startswith("http") else BING_URL + bg

        if not bg_image:
            meta = soup.find("meta", {"property": "og:image"})
            if meta and meta.get("content"):
                img_url = meta["content"]
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = BING_URL + img_url
                bg_image = img_url

        if bg_image:
            img_name = os.path.basename(bg_image.split("?")[0])
            img_path = IMAGE_DIR / img_name
            if not img_path.exists():
                img_data = requests.get(bg_image, headers=headers, timeout=10).content
                img_path.write_bytes(img_data)
            return f"/static/images/{img_name}", "Today’s Bing Wallpaper"
    except Exception as e:
        print(f"[BING] {e}")
    return "/static/images/default.jpg", "Bing Wallpaper"

# -------------------- Simple volume via I2C amp --------------------
class VolumeController:
    def __init__(self):
        self.current_volume = 50
        self.muted = False
        self.previous_volume = 50

    def _write_gain(self, gain_0_to_30):
        if not audio_available or not i2c_bus:
            return False
        try:
            i2c_bus.write_byte_data(TPA2016_ADDR, TPA2016_FIXED_GAIN, gain_0_to_30)
            return True
        except Exception as e:
            print(f"Volume err: {e}")
            return False

    def set_volume(self, volume):
        volume = max(0, min(100, int(volume)))
        reg = int((volume / 100) * 30)
        ok = self._write_gain(reg)
        if ok:
            self.current_volume = volume
            self.muted = False
        return ok

    def volume_up(self, step=5):
        return self.set_volume(self.current_volume + step)

    def volume_down(self, step=5):
        return self.set_volume(self.current_volume - step)

    def mute_toggle(self):
        if self.muted:
            self.set_volume(self.previous_volume)
            self.muted = False
        else:
            self.previous_volume = self.current_volume
            self.set_volume(0)
            self.muted = True
        return self.muted

volume_controller = VolumeController()

# -------------------- Sensors --------------------
def get_sensor_data():
    data = {
        "timestamp": time.time(),
        "temperature": None,
        "humidity": None,
        "gas_detected": False,
        "light_detected": False,
        "hardware": {
            "gpio": bool(GPIO),
            "dht": bool(Adafruit_DHT),
            "i2c_audio": audio_available,
        },
    }
    if Adafruit_DHT and DHT_SENSOR:
        try:
            h, t = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
            if h is not None and t is not None:
                data["temperature"] = round(float(t), 1)
                data["humidity"] = round(float(h), 1)
        except Exception as e:
            print(f"DHT22: {e}")
    if GPIO:
        try:
            data["gas_detected"] = GPIO.input(GAS_PIN) == GPIO.HIGH
            data["light_detected"] = GPIO.input(LIGHT_PIN) == GPIO.HIGH
        except Exception as e:
            print(f"GPIO read: {e}")
    return data

# -------------------- Wi-Fi helpers --------------------
def get_wifi_networks():
    try:
        result = subprocess.run(
            ["sudo", "iwlist", "wlan0", "scan"],
            capture_output=True, text=True, timeout=20
        )
        networks = []
        for line in result.stdout.splitlines():
            if "ESSID:" in line:
                essid = line.split("ESSID:")[1].strip().strip('"')
                if essid and essid != "<hidden>":
                    networks.append(essid)
        return sorted(set(networks))
    except Exception as e:
        print(f"WiFi scan: {e}")
        return []

def connect_wifi(ssid, password):
    try:
        cfg = f'network={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n'
        tmp = "/tmp/wpa_temp.conf"
        with open(tmp, "w") as f:
            f.write(cfg)
        subprocess.run(["sudo", "wpa_supplicant", "-B", "-i", "wlan0", "-c", tmp],
                       capture_output=True, text=True, timeout=20)
        subprocess.run(["sudo", "dhclient", "wlan0"], timeout=15)
        return True
    except Exception as e:
        print(f"WiFi connect: {e}")
        return False

# -------------------- Home Assistant helpers --------------------
def ha_headers():
    if not CONFIG.get("ha_token"):
        return None
    return {
        "Authorization": f"Bearer {CONFIG['ha_token']}",
        "Content-Type": "application/json"
    }

def ha_call(service_domain, service, payload):
    """Call HA: POST /api/services/<domain>/<service>"""
    if not CONFIG.get("ha_base_url") or not CONFIG.get("ha_token"):
        return False, "Home Assistant not configured"
    try:
        url = f"{CONFIG['ha_base_url'].rstrip('/')}/api/services/{service_domain}/{service}"
        r = requests.post(url, headers=ha_headers(), json=payload, timeout=8)
        return r.ok, (r.text if not r.ok else "OK")
    except Exception as e:
        return False, str(e)

# Basic intent mapping
def handle_intent_text(text: str):
    """
    Ultra-simple NLU for demo. If OpenAI key present, we’ll use LLM to parse structured intent.
    Otherwise some keyword rules as fallback.
    """
    text_l = text.lower()

    # Fallback rules
    if "turn on" in text_l or "switch on" in text_l:
        # crude entity guess
        entity = None
        if "light" in text_l:
            entity = "light.living_room"
            domain = "light"
            return ha_call(domain, "turn_on", {"entity_id": entity})
        if "fan" in text_l:
            entity = "fan.living_room"
            domain = "fan"
            return ha_call(domain, "turn_on", {"entity_id": entity})
    if "turn off" in text_l or "switch off" in text_l:
        if "light" in text_l:
            entity = "light.living_room"
            return ha_call("light", "turn_off", {"entity_id": entity})
        if "fan" in text_l:
            entity = "fan.living_room"
            return ha_call("fan", "turn_off", {"entity_id": entity})
    if "set" in text_l and "temperature" in text_l:
        # naive temp extractor
        import re
        m = re.search(r"(\d{2})", text_l)
        if m:
            temp = int(m.group(1))
            return ha_call("climate", "set_temperature",
                           {"entity_id": "climate.home", "temperature": temp})

    # Try LLM for structured intent when available
    if CONFIG.get("provider") == "openai" and CONFIG.get("openai_api_key") and OPENAI_AVAILABLE:
        try:
            client = OpenAI(api_key=CONFIG["openai_api_key"])
            system = (
                "You convert user voice commands into Home Assistant service calls. "
                "Return pure JSON with keys: domain, service, payload (object). "
                "Use entity_id values the user likely has, or infer from text (e.g., 'light.living_room'). "
                "If unclear, include 'question' key asking a short clarification."
            )
            msg = [{"role": "system", "content": system},
                   {"role": "user", "content": text}]
            resp = client.chat.completions.create(
                model=CONFIG.get("openai_model", "gpt-4o-mini"),
                messages=msg,
                temperature=0
            )
            content = resp.choices[0].message.content.strip()
            # attempt JSON extraction
            import json as _json, re as _re
            match = _re.search(r"\{.*\}", content, _re.S)
            if not match:
                return False, "Could not parse intent."
            data = _json.loads(match.group(0))
            if "question" in data:
                return False, data["question"]
            domain = data["domain"]
            service = data["service"]
            payload = data.get("payload", {})
            return ha_call(domain, service, payload)
        except Exception as e:
            return False, f"LLM intent error: {e}"

    return False, "Sorry, I couldn’t understand that."

# -------------------- Routes: UI --------------------
@app.route("/")
def index():
    img_url, title = get_bing_wallpaper()
    return render_template("index.html",
                           img_url=img_url,
                           title=title,
                           audio_available=audio_available)

@app.route("/settings")
def settings():
    sensor_data = get_sensor_data()
    cfg = load_config()
    return render_template("settings.html",
                           sensor_data=sensor_data,
                           current_volume=volume_controller.current_volume,
                           audio_available=audio_available,
                           cfg=cfg)

@app.route("/settings/system_status")
def system_status():
    system_info = {}
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                system_info["cpu_temp"] = round(float(f.read()) / 1000.0, 1)

        mem_total = mem_avail = None
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                if line.startswith("MemAvailable:"):
                    mem_avail = int(line.split()[1])
        if mem_total and mem_avail:
            system_info["memory_used_percent"] = round(
                (mem_total - mem_avail) / mem_total * 100, 1
            )

        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout
        parts = disk.splitlines()[1].split()
        system_info["disk_used_percent"] = int(parts[4].strip("%"))

        system_info["uptime"] = subprocess.run(
            ["uptime", "-p"], capture_output=True, text=True
        ).stdout.strip()
    except Exception as e:
        print(f"Sysinfo: {e}")

    return render_template("system_status.html",
                           system_info=system_info,
                           sensor_data=get_sensor_data())

@app.route("/settings/wifi")
def wifi_settings():
    return render_template("wifi_settings.html", networks=get_wifi_networks())

# -------------------- API: config --------------------
@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    global CONFIG
    if request.method == "GET":
        return jsonify(load_config())
    data = request.get_json(silent=True) or {}
    CONFIG.update({
        "provider": data.get("provider", CONFIG["provider"]),
        "openai_api_key": data.get("openai_api_key", CONFIG["openai_api_key"]),
        "openai_model": data.get("openai_model", CONFIG["openai_model"]),
        "ha_base_url": data.get("ha_base_url", CONFIG["ha_base_url"]),
        "ha_token": data.get("ha_token", CONFIG["ha_token"]),
        "wake_word_enabled": bool(data.get("wake_word_enabled", CONFIG["wake_word_enabled"]))
    })
    save_config(CONFIG)
    return jsonify({"success": True})

# -------------------- API: sensors/health --------------------
@app.route("/api/sensor_data")
def api_sensor_data():
    return jsonify(get_sensor_data())

@app.route("/api/health")
def api_health():
    return jsonify({"status": "healthy", "timestamp": time.time(), "audio_available": audio_available})

# -------------------- API: volume --------------------
@app.route("/api/volume/up", methods=["POST"])
def api_volume_up():
    step = request.json.get("step", 5) if request.is_json else 5
    ok = volume_controller.volume_up(step)
    return jsonify({"success": ok, "volume": volume_controller.current_volume, "muted": volume_controller.muted})

@app.route("/api/volume/down", methods=["POST"])
def api_volume_down():
    step = request.json.get("step", 5) if request.is_json else 5
    ok = volume_controller.volume_down(step)
    return jsonify({"success": ok, "volume": volume_controller.current_volume, "muted": volume_controller.muted})

@app.route("/api/volume/set", methods=["POST"])
def api_volume_set():
    vol = request.json.get("volume", 50) if request.is_json else 50
    ok = volume_controller.set_volume(vol)
    return jsonify({"success": ok, "volume": volume_controller.current_volume, "muted": volume_controller.muted})

@app.route("/api/volume/mute", methods=["POST"])
def api_volume_mute():
    return jsonify({"success": True, "volume": volume_controller.current_volume, "muted": volume_controller.mute_toggle()})

# -------------------- API: WiFi --------------------
@app.route("/api/wifi_scan")
def api_wifi_scan():
    return jsonify({"networks": get_wifi_networks()})

@app.route("/api/wifi_connect", methods=["POST"])
def api_wifi_connect():
    data = request.get_json(silent=True) or {}
    ssid = data.get("ssid")
    password = data.get("password") or ""
    if not ssid:
        return jsonify({"success": False, "error": "SSID required"}), 400
    ok = connect_wifi(ssid, password)
    return jsonify({"success": ok})

# -------------------- API: HA service passthrough --------------------
@app.route("/api/ha/service", methods=["POST"])
def api_ha_service():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain")
    service = data.get("service")
    payload = data.get("payload", {})
    if not domain or not service:
        return jsonify({"success": False, "error": "domain and service required"}), 400
    ok, info = ha_call(domain, service, payload)
    return jsonify({"success": ok, "info": info}), (200 if ok else 500)

# -------------------- API: Voice (push-to-talk) --------------------
@app.route("/api/voice", methods=["POST"])
def api_voice():
    """
    Accepts:
      - multipart/form-data with file 'audio' (webm/opus)
      - OR JSON with 'text' (if browser did speech already)
    Returns: { success, text, result }
    """
    # If text already provided (e.g., browser did recognition), just handle it
    if request.is_json:
        text = (request.get_json() or {}).get("text", "").strip()
        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400
        ok, info = handle_intent_text(text)
        return jsonify({"success": ok, "text": text, "result": info}), (200 if ok else 200)

    # Otherwise transcribe server-side with OpenAI Whisper
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file"}), 400

    if CONFIG.get("provider") != "openai" or not CONFIG.get("openai_api_key") or not OPENAI_AVAILABLE:
        return jsonify({"success": False, "error": "Voice transcription not configured (OpenAI)"}), 400

    try:
        client = OpenAI(api_key=CONFIG["openai_api_key"])
        f = request.files["audio"]
        # Save temp and send to Whisper
        tmp = APP_DIR / "tmp_voice.webm"
        f.save(tmp)
        with open(tmp, "rb") as af:
            tr = client.audio.transcriptions.create(model="whisper-1", file=af)
        text = tr.text.strip() if hasattr(tr, "text") else (tr.get("text", "").strip() if isinstance(tr, dict) else "")
        if not text:
            return jsonify({"success": False, "error": "Empty transcription"}), 200
        ok, info = handle_intent_text(text)
        return jsonify({"success": ok, "text": text, "result": info}), (200 if ok else 200)
    except Exception as e:
        return jsonify({"success": False, "error": f"Transcription failed: {e}"}), 200

# -------------------- Main --------------------
if __name__ == "__main__":
    try:
        if audio_available and i2c_bus:
            try:
                i2c_bus.write_byte_data(TPA2016_ADDR, TPA2016_AGC_CONTROL, 0x05)
            except Exception as e:
                print(f"TPA2016 init: {e}")
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        if GPIO:
            GPIO.cleanup()
