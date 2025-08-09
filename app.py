import os
import time
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

# ---------- Optional hardware ----------
GPIO = None
SMBus = None

# Prefer CircuitPython DHT on Pi 5 (no C compile)
adafruit_dht = None
board = None
try:
    import adafruit_dht as _adafruit_dht
    import board as _board
    adafruit_dht = _adafruit_dht
    board = _board
except Exception:
    pass

# Legacy Adafruit_DHT fallback (C extension) – only used if present
Adafruit_DHT = None
if adafruit_dht is None:
    try:
        import Adafruit_DHT as _Adafruit_DHT
        Adafruit_DHT = _Adafruit_DHT
    except Exception:
        pass

try:
    import RPi.GPIO as _GPIO
    GPIO = _GPIO
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

# ---------- Feature modules ----------
from core import media
from core import news as news_mod
from core import weather as weather_mod
from core import timers as timers_mod

# ---------- App ----------
app = Flask(__name__)
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CONFIG_FILE = APP_DIR / "settings.json"
DATA_DIR.mkdir(exist_ok=True)

# -------------------- Config helpers --------------------
DEFAULT_CONFIG = {
    "provider": "openai",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",

    "ha_base_url": "http://localhost:8123",
    "ha_token": "",

    # Location for weather
    "lat": None,     # e.g., -27.4698
    "lon": None,     # e.g., 153.0251
    "timezone": "auto",

    # Wake word (browser-based UI piece; offline later)
    "wake_word_enabled": True,
    "wake_word_phrase": "hey bing",

    # Sensors
    "invert_gas": False,
    "invert_light": False,

    # Voice entity aliases
    "voice_aliases": {}
}

def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
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
DHT_PIN_BCM = 4          # DHT22 on GPIO4
GAS_PIN = 17             # Digital gas sensor on GPIO17
LIGHT_PIN = 27           # Digital light sensor on GPIO27

# CircuitPython DHT + simple cache (avoid hammering, tolerate transient errors)
dht_device = None
_last_dht = {"t": None, "h": None, "ts": 0.0}
if adafruit_dht and board:
    try:
        dht_device = adafruit_dht.DHT22(board.D4, use_pulseio=False)
    except Exception as e:
        print(f"DHT init (CircuitPython) failed: {e}")
        dht_device = None

# Legacy constants if the old lib is available
DHT_SENSOR = Adafruit_DHT.DHT22 if Adafruit_DHT else None

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
        GPIO.setup(GAS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(LIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        print(f"GPIO init: {e}")
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

# -------------------- Volume (I2C amp) --------------------
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
def _read_dht_cached():
    now = time.time()
    if now - _last_dht["ts"] < 2.0:
        return _last_dht["t"], _last_dht["h"]

    t = h = None
    if dht_device:
        try:
            t = dht_device.temperature
            h = dht_device.humidity
        except RuntimeError:
            pass
        except Exception as e:
            print(f"DHT read (CircuitPython) error: {e}")
    elif Adafruit_DHT and DHT_SENSOR:
        try:
            h, t = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN_BCM)
        except Exception as e:
            print(f"DHT read (legacy) error: {e}")

    if t is not None or h is not None:
        _last_dht.update({"t": t, "h": h, "ts": now})
    else:
        _last_dht["ts"] = now
    return _last_dht["t"], _last_dht["h"]

def get_sensor_data():
    t, h = _read_dht_cached()
    gas = light = None

    if GPIO:
        try:
            gas_raw = GPIO.input(GAS_PIN) == GPIO.HIGH
            light_raw = GPIO.input(LIGHT_PIN) == GPIO.HIGH
            gas = (not gas_raw) if CONFIG.get("invert_gas") else gas_raw
            light = (not light_raw) if CONFIG.get("invert_light") else light_raw
        except Exception as e:
            print(f"GPIO read: {e}")

    return {
        "timestamp": time.time(),
        "temperature": round(float(t), 1) if t is not None else None,
        "humidity": round(float(h), 1) if h is not None else None,
        "gas_detected": bool(gas) if gas is not None else False,
        "light_detected": bool(light) if light is not None else False,
        "hardware": {
            "gpio": bool(GPIO),
            "dht": bool(dht_device) or bool(DHT_SENSOR),
            "i2c_audio": audio_available,
        },
    }

# -------------------- Wi-Fi (NM first, iwlist fallback) --------------------
def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def get_wifi_networks() -> List[str]:
    if _have("nmcli"):
        try:
            subprocess.run(["nmcli", "device", "wifi", "rescan"], timeout=10)
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
                text=True, timeout=10
            )
            nets = [ln.strip() for ln in out.splitlines() if ln.strip() and ln.strip() != "--"]
            return sorted(set(nets))
        except Exception as e:
            print(f"nmcli scan: {e}")
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
        print(f"iwlist scan: {e}")
        return []

def connect_wifi(ssid: str, password: str):
    if _have("nmcli"):
        try:
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
            if password: cmd += ["password", password]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if r.returncode == 0: return True, "OK"
            return False, r.stderr.strip() or r.stdout.strip() or "Failed"
        except Exception as e:
            return False, str(e)
    try:
        cfg = f'network={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n'
        tmp = "/tmp/wpa_temp.conf"
        with open(tmp, "w") as f: f.write(cfg)
        subprocess.run(["sudo", "wpa_supplicant", "-B", "-i", "wlan0", "-c", tmp],
                       capture_output=True, text=True, timeout=20)
        subprocess.run(["sudo", "dhclient", "wlan0"], timeout=15)
        return True, "OK"
    except Exception as e:
        return False, str(e)

# -------------------- Home Assistant helpers --------------------
def ha_headers():
    if not CONFIG.get("ha_token"):
        return None
    return {"Authorization": f"Bearer {CONFIG['ha_token']}", "Content-Type": "application/json"}

def ha_call(service_domain, service, payload):
    if not CONFIG.get("ha_base_url") or not CONFIG.get("ha_token"):
        return False, "Home Assistant not configured"
    try:
        url = f"{CONFIG['ha_base_url'].rstrip('/')}/api/services/{service_domain}/{service}"
        r = requests.post(url, headers=ha_headers(), json=payload, timeout=8)
        return r.ok, (r.text if not r.ok else "OK")
    except Exception as e:
        return False, str(e)

# -------------------- Intent handling (voice) --------------------
def handle_intent_text(text: str):
    tl = (text or "").strip().lower()

    # Teach alias: "remember that <alias> is <entity_id>"
    if tl.startswith("remember that "):
        try:
            rest = tl[len("remember that "):]
            if " is " in rest:
                alias, entity = rest.split(" is ", 1)
                alias = alias.strip().lower()
                entity = entity.strip()
                if alias and entity:
                    CONFIG.setdefault("voice_aliases", {})[alias] = entity
                    save_config(CONFIG)
                    return True, f"Saved alias: '{alias}' -> {entity}"
        except Exception as e:
            return False, f"Teach failed: {e}"

    def resolve_entity(words: List[str]) -> Optional[str]:
        aliases = CONFIG.get("voice_aliases", {})
        for k, v in aliases.items():
            if k in tl:
                return v
        for w in words:
            if "." in w and w.split(".", 1)[0] in {"light","fan","switch","climate","cover","media_player"}:
                return w
        return None

    words = tl.split()

    if "turn on" in tl or "switch on" in tl:
        ent = resolve_entity(words) or "light.living_room"
        return ha_call(ent.split(".", 1)[0], "turn_on", {"entity_id": ent})

    if "turn off" in tl or "switch off" in tl:
        ent = resolve_entity(words) or "light.living_room"
        return ha_call(ent.split(".", 1)[0], "turn_off", {"entity_id": ent})

    if "set" in tl and "temperature" in tl:
        import re
        m = re.search(r"(\d{2})", tl)
        if m:
            temp = int(m.group(1))
            return ha_call("climate", "set_temperature",
                           {"entity_id": "climate.home", "temperature": temp})

    if CONFIG.get("provider") == "openai" and CONFIG.get("openai_api_key") and OPENAI_AVAILABLE:
        try:
            aliases = CONFIG.get("voice_aliases", {})
            alias_text = "; ".join([f"{k} -> {v}" for k, v in aliases.items()]) or "none"
            client = OpenAI(api_key=CONFIG["openai_api_key"])
            system = (
                "Convert user voice commands into Home Assistant service calls. "
                "Return pure JSON with keys: domain, service, payload (object). "
                "If unclear, include 'question' with a short clarification request. "
                f"Known voice aliases: {alias_text}."
            )
            msg = [{"role": "system", "content": system},
                   {"role": "user", "content": text}]
            resp = client.chat.completions.create(
                model=CONFIG.get("openai_model", "gpt-4o-mini"),
                messages=msg, temperature=0
            )
            content = resp.choices[0].message.content.strip()
            import json as _json, re as _re
            match = _re.search(r"\{.*\}", content, _re.S)
            if not match:
                return False, "Could not parse intent."
            data = _json.loads(match.group(0))
            if "question" in data:
                return False, data["question"]
            domain = data["domain"]; service = data["service"]
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
                if line.startswith("MemTotal:"): mem_total = int(line.split()[1])
                if line.startswith("MemAvailable:"): mem_avail = int(line.split()[1])
        if mem_total and mem_avail:
            system_info["memory_used_percent"] = round((mem_total - mem_avail) / mem_total * 100, 1)
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout
        parts = disk.splitlines()[1].split()
        system_info["disk_used_percent"] = int(parts[4].strip("%"))
        system_info["uptime"] = subprocess.run(["uptime", "-p"], capture_output=True, text=True).stdout.strip()
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
        "wake_word_enabled": bool(data.get("wake_word_enabled", CONFIG["wake_word_enabled"])),
        "wake_word_phrase": data.get("wake_word_phrase", CONFIG["wake_word_phrase"]),
        "invert_gas": bool(data.get("invert_gas", CONFIG["invert_gas"])),
        "invert_light": bool(data.get("invert_light", CONFIG["invert_light"])),
        "lat": data.get("lat", CONFIG.get("lat")),
        "lon": data.get("lon", CONFIG.get("lon")),
        "timezone": data.get("timezone", CONFIG.get("timezone", "auto")),
    })
    if "voice_aliases" in data and isinstance(data["voice_aliases"], dict):
        CONFIG["voice_aliases"].update({str(k).lower(): str(v) for k, v in data["voice_aliases"].items()})
    save_config(CONFIG)
    return jsonify({"success": True})

# -------------------- API: sensors/health/news/weather --------------------
@app.route("/api/sensor_data")
def api_sensor_data():
    return jsonify(get_sensor_data())

@app.route("/api/health")
def api_health():
    return jsonify({"status": "healthy", "timestamp": time.time(), "audio_available": audio_available})

@app.route("/api/news")
def api_news():
    return jsonify(news_mod.get_news())

@app.route("/api/weather")
def api_weather():
    lat = CONFIG.get("lat"); lon = CONFIG.get("lon"); tz = CONFIG.get("timezone") or "auto"
    if lat is None or lon is None:
        return jsonify({"success": False, "error": "Set lat/lon in Settings or via /api/config"}), 400
    try:
        data = weather_mod.get_weather(float(lat), float(lon), tz=tz)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

# -------------------- API: Wi-Fi --------------------
@app.route("/api/wifi_scan")
def api_wifi_scan():
    return jsonify({"networks": get_wifi_networks()})

@app.route("/api/wifi_connect", methods=["POST"])
def api_wifi_connect():
    data = request.get_json(silent=True) or {}
    ssid = data.get("ssid"); password = data.get("password") or ""
    if not ssid:
        return jsonify({"success": False, "error": "SSID required"}), 400
    ok, info = connect_wifi(ssid, password)
    code = 200 if ok else 500
    return jsonify({"success": ok, "info": info}), code

# -------------------- API: Home Assistant passthrough & discovery --------------------
@app.route("/api/ha/service", methods=["POST"])
def api_ha_service():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain"); service = data.get("service"); payload = data.get("payload", {})
    if not domain or not service:
        return jsonify({"success": False, "error": "domain and service required"}), 400
    ok, info = ha_call(domain, service, payload)
    return jsonify({"success": ok, "info": info}), (200 if ok else 500)

@app.route("/api/ha/entities")
def api_ha_entities():
    if not CONFIG.get("ha_base_url") or not CONFIG.get("ha_token"):
        return jsonify({"success": False, "error": "Home Assistant not configured"}), 400
    try:
        url = f"{CONFIG['ha_base_url'].rstrip('/')}/api/states"
        r = requests.get(url, headers=ha_headers(), timeout=10); r.raise_for_status()
        items = r.json()
        out = [{"entity_id": it.get("entity_id"),
                "name": (it.get("attributes", {}) or {}).get("friendly_name")} for it in items]
        return jsonify({"success": True, "entities": out})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/voice_alias", methods=["POST"])
def api_voice_alias():
    data = request.get_json(silent=True) or {}
    alias = (data.get("alias") or "").strip().lower()
    entity_id = (data.get("entity_id") or "").strip()
    if not alias or not entity_id:
        return jsonify({"success": False, "error": "alias and entity_id required"}), 400
    CONFIG.setdefault("voice_aliases", {})[alias] = entity_id
    save_config(CONFIG)
    return jsonify({"success": True, "aliases": CONFIG["voice_aliases"]})

# -------------------- API: Voice (push-to-talk) --------------------
@app.route("/api/voice", methods=["POST"])
def api_voice():
    if request.is_json:
        text = (request.get_json() or {}).get("text", "").strip()
        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400
        ok, info = handle_intent_text(text)
        return jsonify({"success": ok, "text": text, "result": info}), 200

    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file"}), 400

    if CONFIG.get("provider") != "openai" or not CONFIG.get("openai_api_key") or not OPENAI_AVAILABLE:
        return jsonify({"success": False, "error": "Voice transcription not configured (OpenAI)"}), 400

    try:
        client = OpenAI(api_key=CONFIG["openai_api_key"])
        f = request.files["audio"]
        tmp = APP_DIR / "tmp_voice.webm"
        f.save(tmp)
        with open(tmp, "rb") as af:
            tr = client.audio.transcriptions.create(model="whisper-1", file=af)
        text = tr.text.strip() if hasattr(tr, "text") else (tr.get("text", "").strip() if isinstance(tr, dict) else "")
        if not text:
            return jsonify({"success": False, "error": "Empty transcription"}), 200
        ok, info = handle_intent_text(text)
        return jsonify({"success": ok, "text": text, "result": info}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Transcription failed: {e}"}), 200

# -------------------- API: Media --------------------
@app.route("/api/media/play", methods=["POST"])
def api_media_play():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or data.get("query") or "").strip()
    if not url:
        return jsonify({"success": False, "error": "Provide 'url' or 'query'"}), 400
    try:
        media.play(url)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/media/pause", methods=["POST"])
def api_media_pause():
    media.pause(None)
    return jsonify({"success": True})

@app.route("/api/media/stop", methods=["POST"])
def api_media_stop():
    media.stop()
    return jsonify({"success": True})

@app.route("/api/media/volume", methods=["POST"])
def api_media_volume():
    data = request.get_json(silent=True) or {}
    v = data.get("volume")
    if v is None:
        return jsonify({"success": True, "volume": media.status().get("volume")})
    media.set_volume(int(v))
    return jsonify({"success": True, "volume": int(v)})

@app.route("/api/media/status")
def api_media_status():
    return jsonify(media.status())

# -------------------- API: Timers/Alarms --------------------
TIMER_API = None

@app.route("/api/timers", methods=["GET", "POST"])
def api_timers():
    if request.method == "GET":
        return jsonify({"success": True, "timers": TIMER_API.list()})
    data = request.get_json(silent=True) or {}
    label = (data.get("label") or "Timer").strip()
    if "seconds" in data:
        item = TIMER_API.create_in(int(data["seconds"]), label)
        return jsonify({"success": True, "timer": item})
    if "at" in data:
        item = TIMER_API.create_at(str(data["at"]), label or "Alarm")
        return jsonify({"success": True, "timer": item})
    return jsonify({"success": False, "error": "Provide 'seconds' or 'at'"}), 400

@app.route("/api/timers/<tid>", methods=["DELETE"])
def api_timers_delete(tid):
    ok = TIMER_API.delete(tid)
    return jsonify({"success": ok})

# -------------------- Main --------------------
if __name__ == "__main__":
    # init timers with media chime
    TIMER_API = timers_mod.init(DATA_DIR, play_func=media.play)

    try:
        if audio_available and 'i2c_bus' in globals() and i2c_bus:
            try:
                i2c_bus.write_byte_data(TPA2016_ADDR, TPA2016_AGC_CONTROL, 0x05)
            except Exception as e:
                print(f"TPA2016 init: {e}")
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        if GPIO:
            GPIO.cleanup()
