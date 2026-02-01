"""
Bluetooth utilities for BingHome Hub
Uses bluetoothctl for device management
"""
import subprocess
import re
import logging

logger = logging.getLogger(__name__)

def run_bluetoothctl(*args, timeout=10):
    """Run a bluetoothctl command and return output"""
    try:
        cmd = ['bluetoothctl'] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.warning(f"bluetoothctl timeout: {args}")
        return ""
    except Exception as e:
        logger.error(f"bluetoothctl error: {e}")
        return ""

def get_paired_devices():
    """Get list of paired Bluetooth devices"""
    devices = []
    try:
        output = run_bluetoothctl('devices', 'Paired')
        if not output.strip():
            output = run_bluetoothctl('paired-devices')
        
        # Parse: Device XX:XX:XX:XX:XX:XX DeviceName
        for line in output.split('\n'):
            match = re.search(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', line)
            if match:
                mac = match.group(1)
                name = match.group(2).strip()
                
                # Check if connected
                info_output = run_bluetoothctl('info', mac)
                connected = 'Connected: yes' in info_output
                
                # Try to get device type/icon
                device_type = None
                icon_match = re.search(r'Icon:\s+(.+)', info_output)
                if icon_match:
                    device_type = icon_match.group(1).strip()
                
                devices.append({
                    'mac': mac,
                    'name': name,
                    'connected': connected,
                    'type': device_type
                })
    except Exception as e:
        logger.error(f"Error getting paired devices: {e}")
    
    return devices

def scan_for_devices(duration=8):
    """Scan for nearby Bluetooth devices"""
    devices = []
    try:
        # Power on and make discoverable
        run_bluetoothctl('power', 'on')
        run_bluetoothctl('agent', 'on')
        run_bluetoothctl('default-agent')
        
        # Start scan
        subprocess.run(['bluetoothctl', 'scan', 'on'], 
                      capture_output=True, timeout=2)
        
        # Wait for scan
        import time
        time.sleep(duration)
        
        # Stop scan
        subprocess.run(['bluetoothctl', 'scan', 'off'], 
                      capture_output=True, timeout=2)
        
        # Get discovered devices
        output = run_bluetoothctl('devices')
        
        # Get already paired devices to exclude
        paired = {d['mac'] for d in get_paired_devices()}
        
        for line in output.split('\n'):
            match = re.search(r'Device\s+([0-9A-Fa-f:]{17})\s+(.+)', line)
            if match:
                mac = match.group(1)
                name = match.group(2).strip()
                
                # Skip already paired devices
                if mac in paired:
                    continue
                
                # Get device info for type
                info_output = run_bluetoothctl('info', mac)
                device_type = None
                rssi = None
                
                icon_match = re.search(r'Icon:\s+(.+)', info_output)
                if icon_match:
                    device_type = icon_match.group(1).strip()
                
                rssi_match = re.search(r'RSSI:\s+(-?\d+)', info_output)
                if rssi_match:
                    rssi = int(rssi_match.group(1))
                
                devices.append({
                    'mac': mac,
                    'name': name,
                    'type': device_type,
                    'rssi': rssi
                })
    except Exception as e:
        logger.error(f"Scan error: {e}")
    
    return devices

def pair_device(mac):
    """Pair with a Bluetooth device"""
    try:
        run_bluetoothctl('power', 'on')
        run_bluetoothctl('agent', 'on')
        run_bluetoothctl('default-agent')
        
        # Trust and pair
        run_bluetoothctl('trust', mac)
        output = run_bluetoothctl('pair', mac, timeout=30)
        
        if 'Failed' in output or 'error' in output.lower():
            return False, output
        
        return True, "Paired successfully"
    except Exception as e:
        logger.error(f"Pair error: {e}")
        return False, str(e)

def connect_device(mac):
    """Connect to a paired Bluetooth device"""
    try:
        output = run_bluetoothctl('connect', mac, timeout=15)
        
        if 'Failed' in output or 'error' in output.lower():
            return False, output
        
        return True, "Connected successfully"
    except Exception as e:
        logger.error(f"Connect error: {e}")
        return False, str(e)

def disconnect_device(mac):
    """Disconnect a Bluetooth device"""
    try:
        output = run_bluetoothctl('disconnect', mac)
        return True, "Disconnected"
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return False, str(e)

def remove_device(mac):
    """Remove/unpair a Bluetooth device"""
    try:
        output = run_bluetoothctl('remove', mac)
        
        if 'not available' in output.lower():
            return False, "Device not found"
        
        return True, "Device removed"
    except Exception as e:
        logger.error(f"Remove error: {e}")
        return False, str(e)
