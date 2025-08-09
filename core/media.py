# core/media.py
import os, json, time, socket, subprocess, threading
from pathlib import Path
from typing import Optional, Dict, Any

class MPV:
    def __init__(self, sock_path="/tmp/mpv-binghome.sock"):
        self.sock = sock_path
        self.proc = None
        self.lock = threading.Lock()

    def _ensure(self):
        if self.proc and self.proc.poll() is None:
            return
        try:
            if os.path.exists(self.sock):
                os.remove(self.sock)
        except Exception:
            pass
        self.proc = subprocess.Popen([
            "mpv", "--idle=yes", f"--input-ipc-server={self.sock}",
            "--no-video", "--force-window=no", "--volume=70"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # wait for socket
        for _ in range(50):
            if os.path.exists(self.sock):
                break
            time.sleep(0.1)

    def _cmd(self, command):
        self._ensure()
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(self.sock)
        payload = json.dumps({"command": command}).encode("utf-8") + b"\n"
        s.sendall(payload)
        data = s.recv(4096)
        s.close()
        try:
            return json.loads(data.decode("utf-8").strip() or "{}")
        except Exception:
            return {}

    def play(self, url_or_path: str):
        return self._cmd(["loadfile", url_or_path, "replace"])

    def pause(self, state: Optional[bool] = None):
        if state is None:
            # toggle
            cur = self.get_property("pause") or False
            return self.set_property("pause", not cur)
        return self.set_property("pause", bool(state))

    def stop(self):
        return self._cmd(["stop"])

    def volume(self, v: Optional[int] = None):
        if v is None:
            return self.get_property("volume")
        return self.set_property("volume", max(0, min(100, int(v))))

    def get_property(self, name: str):
        res = self._cmd(["get_property", name])
        return res.get("data")

    def set_property(self, name: str, value: Any):
        return self._cmd(["set_property", name, value])

    def status(self) -> Dict[str, Any]:
        return {
            "path": self.get_property("path"),
            "pause": self.get_property("pause"),
            "volume": self.get_property("volume"),
            "time-pos": self.get_property("time-pos"),
            "duration": self.get_property("duration"),
        }

_player = MPV()

def play(url_or_path: str):
    _player.play(url_or_path)

def pause(state: Optional[bool]=None):
    _player.pause(state)

def stop():
    _player.stop()

def set_volume(v: int):
    _player.volume(v)

def status() -> Dict[str, Any]:
    return _player.status()
