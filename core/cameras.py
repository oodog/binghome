"""
BingHome Camera Module
Handles Raspberry Pi camera, USB cameras, and security camera RTSP streams
"""

import os
import subprocess
import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class CameraService:
    """Service for managing local cameras (Pi Camera, USB)"""

    def __init__(self):
        self.cameras = []
        self.active_camera = None
        self.streaming = False
        self.stream_process = None

    def detect_cameras(self):
        """Detect all available cameras"""
        self.cameras = []

        # Check for Raspberry Pi camera
        pi_camera = self._detect_pi_camera()
        if pi_camera:
            self.cameras.append(pi_camera)

        # Check for USB cameras
        usb_cameras = self._detect_usb_cameras()
        self.cameras.extend(usb_cameras)

        return self.cameras

    def _detect_pi_camera(self):
        """Detect Raspberry Pi camera module"""
        try:
            # Check for libcamera (Pi Camera v2/v3)
            result = subprocess.run(
                ['libcamera-hello', '--list-cameras'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and 'Available cameras' in result.stdout:
                # Parse camera info
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'imx' in line.lower() or 'ov' in line.lower():
                        return {
                            'id': 'picamera',
                            'name': 'Raspberry Pi Camera',
                            'type': 'picamera',
                            'device': '/dev/video0',
                            'info': line.strip(),
                            'available': True
                        }
                return {
                    'id': 'picamera',
                    'name': 'Raspberry Pi Camera',
                    'type': 'picamera',
                    'device': '/dev/video0',
                    'info': 'Pi Camera detected',
                    'available': True
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: check for legacy raspistill
        try:
            result = subprocess.run(
                ['vcgencmd', 'get_camera'],
                capture_output=True, text=True, timeout=5
            )
            if 'detected=1' in result.stdout:
                return {
                    'id': 'picamera_legacy',
                    'name': 'Raspberry Pi Camera (Legacy)',
                    'type': 'picamera_legacy',
                    'device': '/dev/video0',
                    'info': 'Legacy Pi Camera',
                    'available': True
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def _detect_usb_cameras(self):
        """Detect USB cameras"""
        cameras = []

        try:
            # List video devices
            video_devices = list(Path('/dev').glob('video*'))

            for device in video_devices:
                device_path = str(device)
                # Skip Pi camera device if already detected
                if device_path == '/dev/video0' and any(c['type'].startswith('picamera') for c in self.cameras):
                    continue

                # Get device info using v4l2
                try:
                    result = subprocess.run(
                        ['v4l2-ctl', '--device', device_path, '--info'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        name = 'USB Camera'
                        for line in result.stdout.split('\n'):
                            if 'Card type' in line:
                                name = line.split(':')[1].strip()
                                break

                        cameras.append({
                            'id': f'usb_{device.name}',
                            'name': name,
                            'type': 'usb',
                            'device': device_path,
                            'info': f'USB camera at {device_path}',
                            'available': True
                        })
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
        except Exception as e:
            logger.error(f"Error detecting USB cameras: {e}")

        return cameras

    def get_camera_snapshot(self, camera_id=None):
        """Capture a snapshot from a camera"""
        if not self.cameras:
            self.detect_cameras()

        camera = None
        if camera_id:
            camera = next((c for c in self.cameras if c['id'] == camera_id), None)
        elif self.cameras:
            camera = self.cameras[0]

        if not camera:
            return None, "No camera available"

        snapshot_path = '/tmp/camera_snapshot.jpg'

        try:
            if camera['type'] == 'picamera':
                # Use libcamera-still for Pi Camera
                subprocess.run([
                    'libcamera-still', '-o', snapshot_path,
                    '--width', '640', '--height', '480',
                    '--timeout', '1000', '--nopreview'
                ], capture_output=True, timeout=10)
            elif camera['type'] == 'picamera_legacy':
                # Use raspistill for legacy Pi Camera
                subprocess.run([
                    'raspistill', '-o', snapshot_path,
                    '-w', '640', '-h', '480', '-t', '1000'
                ], capture_output=True, timeout=10)
            else:
                # Use ffmpeg for USB cameras
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'v4l2',
                    '-i', camera['device'],
                    '-frames:v', '1',
                    '-s', '640x480',
                    snapshot_path
                ], capture_output=True, timeout=10)

            if os.path.exists(snapshot_path):
                return snapshot_path, None
            else:
                return None, "Failed to capture snapshot"
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return None, str(e)

    def start_mjpeg_stream(self, camera_id=None, port=8081):
        """Start MJPEG stream for web viewing"""
        if self.streaming:
            return True, f"Stream already running on port {port}"

        if not self.cameras:
            self.detect_cameras()

        camera = None
        if camera_id:
            camera = next((c for c in self.cameras if c['id'] == camera_id), None)
        elif self.cameras:
            camera = self.cameras[0]

        if not camera:
            return False, "No camera available"

        try:
            if camera['type'] in ['picamera', 'picamera_legacy']:
                # Use libcamera-vid with MJPEG
                self.stream_process = subprocess.Popen([
                    'libcamera-vid', '-t', '0',
                    '--width', '640', '--height', '480',
                    '--codec', 'mjpeg',
                    '--inline', '--listen', '-o', f'tcp://0.0.0.0:{port}'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Use ffmpeg for USB cameras
                self.stream_process = subprocess.Popen([
                    'ffmpeg', '-f', 'v4l2',
                    '-i', camera['device'],
                    '-c:v', 'mjpeg',
                    '-f', 'mjpeg',
                    f'tcp://0.0.0.0:{port}?listen=1'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self.streaming = True
            return True, f"Stream started on port {port}"
        except Exception as e:
            logger.error(f"Stream start error: {e}")
            return False, str(e)

    def stop_stream(self):
        """Stop the camera stream"""
        if self.stream_process:
            self.stream_process.terminate()
            self.stream_process = None
        self.streaming = False
        return True, "Stream stopped"


class SecurityCameraService:
    """Service for managing security cameras (RTSP streams)"""

    # Known vendor default ports and URL patterns
    VENDOR_PATTERNS = {
        'hikvision': {
            'ports': [554, 8554],
            'rtsp_patterns': [
                'rtsp://{user}:{pass}@{ip}:{port}/Streaming/Channels/101',
                'rtsp://{user}:{pass}@{ip}:{port}/Streaming/Channels/102',
                'rtsp://{user}:{pass}@{ip}:{port}/h264/ch1/main/av_stream'
            ],
            'default_user': 'admin',
            'default_pass': 'admin123'
        },
        'reolink': {
            'ports': [554, 8554],
            'rtsp_patterns': [
                'rtsp://{user}:{pass}@{ip}:{port}/h264Preview_01_main',
                'rtsp://{user}:{pass}@{ip}:{port}/h264Preview_01_sub'
            ],
            'default_user': 'admin',
            'default_pass': ''
        },
        'tapo': {
            'ports': [554, 8554],
            'rtsp_patterns': [
                'rtsp://{user}:{pass}@{ip}:{port}/stream1',
                'rtsp://{user}:{pass}@{ip}:{port}/stream2'
            ],
            'default_user': 'admin',
            'default_pass': ''
        },
        'generic': {
            'ports': [554, 8554],
            'rtsp_patterns': [
                'rtsp://{user}:{pass}@{ip}:{port}/live',
                'rtsp://{user}:{pass}@{ip}:{port}/stream',
                'rtsp://{ip}:{port}/live'
            ],
            'default_user': 'admin',
            'default_pass': 'admin'
        }
    }

    def __init__(self, settings_path=None):
        self.settings_path = settings_path or Path(__file__).parent.parent / 'data' / 'security_cameras.json'
        self.cameras = self.load_cameras()

    def load_cameras(self):
        """Load saved cameras from file"""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    return json.load(f).get('cameras', [])
        except Exception as e:
            logger.error(f"Error loading cameras: {e}")
        return []

    def save_cameras(self):
        """Save cameras to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, 'w') as f:
                json.dump({'cameras': self.cameras}, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving cameras: {e}")
            return False

    def add_camera(self, name, rtsp_url, vendor='generic', thumbnail=None):
        """Add a security camera"""
        camera = {
            'id': f'cam_{int(time.time())}',
            'name': name,
            'rtsp_url': rtsp_url,
            'vendor': vendor,
            'thumbnail': thumbnail,
            'enabled': True,
            'added': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.cameras.append(camera)
        self.save_cameras()
        return camera

    def remove_camera(self, camera_id):
        """Remove a security camera"""
        self.cameras = [c for c in self.cameras if c['id'] != camera_id]
        self.save_cameras()
        return True

    def update_camera(self, camera_id, **kwargs):
        """Update camera settings"""
        for camera in self.cameras:
            if camera['id'] == camera_id:
                camera.update(kwargs)
                self.save_cameras()
                return camera
        return None

    def get_cameras(self):
        """Get all cameras"""
        return self.cameras

    def get_camera(self, camera_id):
        """Get a specific camera"""
        return next((c for c in self.cameras if c['id'] == camera_id), None)

    def test_rtsp_stream(self, rtsp_url, timeout=5):
        """Test if RTSP stream is accessible"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1'
            ], capture_output=True, text=True, timeout=timeout)

            if 'video' in result.stdout.lower():
                return True, "Stream accessible"
            else:
                return False, "No video stream found"
        except subprocess.TimeoutExpired:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    def capture_thumbnail(self, rtsp_url, output_path=None):
        """Capture a thumbnail from RTSP stream"""
        if not output_path:
            output_path = f'/tmp/cam_thumb_{int(time.time())}.jpg'

        try:
            subprocess.run([
                'ffmpeg', '-y',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-frames:v', '1',
                '-s', '320x180',
                output_path
            ], capture_output=True, timeout=10)

            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            logger.error(f"Thumbnail capture error: {e}")
        return None

    def discover_cameras(self, ip_range=None):
        """Discover cameras on the network"""
        discovered = []

        if not ip_range:
            # Get local network range
            try:
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'src' in line and '192.168' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'src':
                                local_ip = parts[i + 1]
                                ip_range = '.'.join(local_ip.split('.')[:3]) + '.1/24'
                                break
            except Exception:
                ip_range = '192.168.1.1/24'

        # Scan for open RTSP ports
        try:
            result = subprocess.run([
                'nmap', '-p', '554,8554', '--open', '-oG', '-', ip_range
            ], capture_output=True, text=True, timeout=60)

            for line in result.stdout.split('\n'):
                if '/open/' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        discovered.append({
                            'ip': ip,
                            'ports': [554, 8554],
                            'vendor': 'unknown'
                        })
        except Exception as e:
            logger.error(f"Camera discovery error: {e}")

        return discovered

    def get_rtsp_url_for_vendor(self, vendor, ip, port=554, username='admin', password=''):
        """Generate RTSP URL for a known vendor"""
        patterns = self.VENDOR_PATTERNS.get(vendor, self.VENDOR_PATTERNS['generic'])

        urls = []
        for pattern in patterns['rtsp_patterns']:
            # Replace placeholders manually since 'pass' is a reserved word
            url = pattern.replace('{ip}', ip)
            url = url.replace('{port}', str(port))
            url = url.replace('{user}', username)
            url = url.replace('{pass}', password)
            urls.append(url)

        return urls

    def probe_camera_vendor(self, ip):
        """Try to identify camera vendor"""
        try:
            # Try HTTP to identify web interface
            import requests
            for port in [80, 8080]:
                try:
                    response = requests.get(f'http://{ip}:{port}', timeout=3)
                    content = response.text.lower()

                    if 'hikvision' in content:
                        return 'hikvision'
                    elif 'reolink' in content:
                        return 'reolink'
                    elif 'tapo' in content or 'tp-link' in content:
                        return 'tapo'
                except:
                    continue
        except:
            pass
        return 'generic'


# Global instances
camera_service = CameraService()
security_camera_service = SecurityCameraService()
