# core/timers.py
import json, time, threading, uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

CHIME_PATH = None  # set by init()

class TimerStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {"timers": []}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text() or "{}")
                if "timers" not in self.data: self.data["timers"] = []
            except Exception:
                self.data = {"timers": []}

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)

    def list(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.data["timers"])

    def add(self, when_ts: float, label: str = "") -> Dict[str, Any]:
        with self.lock:
            item = {
                "id": str(uuid.uuid4()),
                "when": float(when_ts),
                "label": label or "Timer",
                "created": time.time(),
                "done": False,
            }
            self.data["timers"].append(item)
            self._save()
            return item

    def mark_done(self, tid: str):
        with self.lock:
            for t in self.data["timers"]:
                if t["id"] == tid:
                    t["done"] = True
                    break
            self._save()

    def delete(self, tid: str) -> bool:
        with self.lock:
            before = len(self.data["timers"])
            self.data["timers"] = [t for t in self.data["timers"] if t["id"] != tid]
            changed = len(self.data["timers"]) != before
            if changed: self._save()
            return changed

def _ensure_chime(path: Path):
    if path.exists(): return
    # write a tiny 440Hz sine “beep” WAV (1 second, 16-bit PCM, 16kHz)
    import math, struct
    sr = 16000; freq = 440; dur = 1.0
    n = int(sr*dur)
    samples = [int(32767*math.sin(2*math.pi*freq*(i/sr))) for i in range(n)]
    import wave
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

def init(data_dir: Path, play_func):
    """
    data_dir: folder for timers.json and chime.wav
    play_func: callable(path: str) -> None (used to play chime via media module)
    """
    global CHIME_PATH
    data_dir.mkdir(parents=True, exist_ok=True)
    CHIME_PATH = data_dir / "chime.wav"
    _ensure_chime(CHIME_PATH)
    store = TimerStore(data_dir / "timers.json")
    sched = BackgroundScheduler(timezone=timezone.utc)
    sched.start()

    def schedule_timer(item: Dict[str, Any]):
        dt = datetime.fromtimestamp(item["when"], tz=timezone.utc)
        def _fire():
            try:
                play_func(str(CHIME_PATH))
                time.sleep(1.2)
            finally:
                store.mark_done(item["id"])
        sched.add_job(_fire, "date", run_date=dt)

    # re-schedule pending timers on start
    now = time.time()
    for t in store.list():
        if not t.get("done") and t["when"] > now:
            schedule_timer(t)

    class API:
        def list(self): return store.list()
        def create_in(self, seconds: int, label: str="Timer") -> Dict[str, Any]:
            when = time.time() + max(1, int(seconds))
            item = store.add(when, label)
            schedule_timer(item)
            return item
        def create_at(self, iso_ts: str, label: str="Alarm") -> Dict[str, Any]:
            # iso like "2025-08-09T07:30:00+10:00" or naive local time
            try:
                from dateutil import parser  # optional
                dt = parser.isoparse(iso_ts)
            except Exception:
                # naive: HH:MM today (local time)
                hh, mm = iso_ts.split(":")
                local = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                dt = local.astimezone(timezone.utc)
            when = dt.timestamp()
            item = store.add(when, label)
            schedule_timer(item)
            return item
        def delete(self, tid: str) -> bool:
            return store.delete(tid)

    return API()
