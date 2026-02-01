# ============================================
# core/device_discovery.py - Smart Device Discovery Module
# ============================================
"""Smart device discovery for WiFi, Bluetooth, Zigbee, Z-Wave, and Home Assistant"""

import os
import logging
import subprocess
import threading
import time
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing Bluetooth library
try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False
    logger.info("Bluetooth library not available")

# Try importing network scanning library
try:
    import nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False
    logger.info("python-nmap not available, using alternative methods")


class DeviceDiscovery:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.discovered_devices = {
            'wifi': [],
            'bluetooth': [],
            'home_assistant': [],
            'zigbee': [],
            'zwave': []
        }
        self.scanning = False
        self.last_scan = None

    def scan_all_devices(self):
        """Scan for all types of devices"""
        self.scanning = True
        self.last_scan = datetime.now().isoformat()

        # Run scans in parallel threads
        threads = [
            threading.Thread(target=self._scan_wifi_devices, daemon=True),
            threading.Thread(target=self._scan_bluetooth_devices, daemon=True),
            threading.Thread(target=self._scan_home_assistant_devices, daemon=True)
        ]

        for thread in threads:
            thread.start()

        # Wait for all threads to complete (with timeout)
        for thread in threads:
            thread.join(timeout=30)

        self.scanning = False
        return self.get_all_devices()

    def _scan_wifi_devices(self):
        """Scan for WiFi/network devices"""
        devices = []

        try:
            # Method 1: Use arp-scan if available (requires sudo)
            try:
                result = subprocess.run(
                    ['sudo', 'arp-scan', '-l', '-q'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 3 and ':' in parts[1]:
                            devices.append({
                                'ip': parts[0],
                                'mac': parts[1],
                                'manufacturer': ' '.join(parts[2:]) if len(parts) > 2 else 'Unknown',
                                'type': 'network',
                                'name': self._get_device_name(parts[0]),
                                'online': True,
                                'last_seen': datetime.now().isoformat()
                            })
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            # Method 2: Use nmap if available
            if NMAP_AVAILABLE and not devices:
                try:
                    nm = nmap.PortScanner()
                    # Scan local network (adjust network range as needed)
                    nm.scan(hosts='192.168.1.0/24', arguments='-sn -T4')

                    for host in nm.all_hosts():
                        if nm[host].state() == 'up':
                            devices.append({
                                'ip': host,
                                'mac': nm[host]['addresses'].get('mac', 'Unknown'),
                                'manufacturer': nm[host]['vendor'].get(nm[host]['addresses'].get('mac', ''), 'Unknown'),
                                'type': 'network',
                                'name': nm[host].hostname() or host,
                                'online': True,
                                'last_seen': datetime.now().isoformat()
                            })
                except Exception as e:
                    logger.error(f"Nmap scan error: {e}")

            # Method 3: Parse arp table (fallback)
            if not devices:
                try:
                    result = subprocess.run(
                        ['arp', '-a'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if '(' in line and ')' in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    ip = parts[1].strip('()')
                                    mac = parts[3]
                                    if ':' in mac or '-' in mac:
                                        devices.append({
                                            'ip': ip,
                                            'mac': mac.replace('-', ':'),
                                            'manufacturer': 'Unknown',
                                            'type': 'network',
                                            'name': parts[0] if parts[0] != '?' else ip,
                                            'online': True,
                                            'last_seen': datetime.now().isoformat()
                                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass

            # Try to identify smart home devices
            devices = self._identify_smart_devices(devices)

            self.discovered_devices['wifi'] = devices
            logger.info(f"Found {len(devices)} WiFi/network devices")

        except Exception as e:
            logger.error(f"WiFi scan error: {e}")

    def _scan_bluetooth_devices(self):
        """Scan for Bluetooth devices"""
        devices = []

        if not BLUETOOTH_AVAILABLE:
            logger.info("Bluetooth scanning not available")
            return

        try:
            logger.info("Starting Bluetooth scan...")
            nearby_devices = bluetooth.discover_devices(
                duration=8,
                lookup_names=True,
                flush_cache=True,
                lookup_class=True
            )

            for addr, name, device_class in nearby_devices:
                devices.append({
                    'address': addr,
                    'name': name or 'Unknown Device',
                    'type': 'bluetooth',
                    'device_class': device_class,
                    'device_type': self._get_bluetooth_device_type(device_class),
                    'online': True,
                    'last_seen': datetime.now().isoformat()
                })

            self.discovered_devices['bluetooth'] = devices
            logger.info(f"Found {len(devices)} Bluetooth devices")

        except Exception as e:
            logger.error(f"Bluetooth scan error: {e}")

    def _scan_home_assistant_devices(self):
        """Scan for Home Assistant devices"""
        devices = []

        ha_url = self.settings.get('home_assistant_url', 'http://localhost:8123')
        ha_token = self.settings.get('home_assistant_token', '')

        if not ha_token:
            logger.info("Home Assistant token not configured")
            return

        try:
            import requests

            headers = {
                'Authorization': f'Bearer {ha_token}',
                'Content-Type': 'application/json'
            }

            # Get all entities from Home Assistant
            response = requests.get(
                f'{ha_url}/api/states',
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                entities = response.json()

                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    domain = entity_id.split('.')[0] if '.' in entity_id else ''

                    # Filter for smart home devices
                    if domain in ['light', 'switch', 'sensor', 'climate', 'cover',
                                 'fan', 'lock', 'media_player', 'camera', 'vacuum']:
                        devices.append({
                            'entity_id': entity_id,
                            'name': entity.get('attributes', {}).get('friendly_name', entity_id),
                            'type': 'home_assistant',
                            'domain': domain,
                            'state': entity.get('state', 'unknown'),
                            'attributes': entity.get('attributes', {}),
                            'last_changed': entity.get('last_changed', ''),
                            'online': entity.get('state', '') != 'unavailable'
                        })

                self.discovered_devices['home_assistant'] = devices
                logger.info(f"Found {len(devices)} Home Assistant devices")
            else:
                logger.error(f"Home Assistant API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Home Assistant scan error: {e}")

    def _identify_smart_devices(self, devices):
        """Try to identify smart home devices from network devices"""
        # Common smart device manufacturers/MAC prefixes
        smart_device_identifiers = {
            'philips': ['hue', 'bridge'],
            'tp-link': ['smart', 'kasa'],
            'amazon': ['echo', 'alexa'],
            'google': ['home', 'nest'],
            'samsung': ['smartthings'],
            'lifx': ['light'],
            'wemo': ['switch', 'plug'],
            'tuya': ['smart'],
            'xiaomi': ['mi', 'yeelight'],
            'sonos': ['speaker'],
            'ring': ['doorbell', 'camera']
        }

        for device in devices:
            manufacturer = device.get('manufacturer', '').lower()
            name = device.get('name', '').lower()

            for brand, keywords in smart_device_identifiers.items():
                if brand in manufacturer or any(keyword in name for keyword in keywords):
                    device['smart_device'] = True
                    device['category'] = brand
                    break

        return devices

    def _get_device_name(self, ip):
        """Try to get device hostname"""
        try:
            result = subprocess.run(
                ['nslookup', ip],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'name =' in line:
                        return line.split('name =')[1].strip().rstrip('.')
        except:
            pass

        return ip

    def _get_bluetooth_device_type(self, device_class):
        """Determine Bluetooth device type from device class"""
        # Major device class (bits 8-12)
        major_class = (device_class >> 8) & 0x1F

        device_types = {
            0x01: 'computer',
            0x02: 'phone',
            0x03: 'network',
            0x04: 'audio',
            0x05: 'peripheral',
            0x06: 'imaging',
            0x07: 'wearable',
            0x08: 'toy',
            0x09: 'health'
        }

        return device_types.get(major_class, 'unknown')

    def control_device(self, device_type, device_id, action, **kwargs):
        """Control a discovered device"""
        if device_type == 'home_assistant':
            return self._control_home_assistant_device(device_id, action, **kwargs)
        else:
            logger.warning(f"Direct control not supported for {device_type}")
            return {'success': False, 'error': 'Control not supported'}

    def _control_home_assistant_device(self, entity_id, action, **kwargs):
        """Control a Home Assistant device"""
        ha_url = self.settings.get('home_assistant_url', 'http://localhost:8123')
        ha_token = self.settings.get('home_assistant_token', '')

        if not ha_token:
            return {'success': False, 'error': 'Home Assistant not configured'}

        try:
            import requests

            headers = {
                'Authorization': f'Bearer {ha_token}',
                'Content-Type': 'application/json'
            }

            # Determine domain from entity_id
            domain = entity_id.split('.')[0] if '.' in entity_id else ''

            # Build service call
            service_data = {
                'entity_id': entity_id
            }
            service_data.update(kwargs)

            response = requests.post(
                f'{ha_url}/api/services/{domain}/{action}',
                headers=headers,
                json=service_data,
                timeout=5
            )

            if response.status_code == 200:
                return {'success': True, 'response': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            logger.error(f"Device control error: {e}")
            return {'success': False, 'error': str(e)}

    def get_all_devices(self):
        """Get all discovered devices"""
        return {
            'devices': self.discovered_devices,
            'last_scan': self.last_scan,
            'scanning': self.scanning,
            'summary': {
                'wifi': len(self.discovered_devices['wifi']),
                'bluetooth': len(self.discovered_devices['bluetooth']),
                'home_assistant': len(self.discovered_devices['home_assistant']),
                'total': sum(len(devices) for devices in self.discovered_devices.values())
            }
        }

    def get_devices_by_type(self, device_type):
        """Get devices of a specific type"""
        return self.discovered_devices.get(device_type, [])

    def update_settings(self, settings):
        """Update discovery settings"""
        self.settings = settings
