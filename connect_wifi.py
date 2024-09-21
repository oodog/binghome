# connect_wifi.py

import sys
import subprocess
import os

def connect_wifi(ssid, password_file, nmcli_path):
    try:
        # Read password from the temporary file
        with open(password_file, 'r') as f:
            password = f.read().strip()
        
        # Use nmcli to connect to the Wi-Fi network
        connect_command = [
            nmcli_path, 'dev', 'wifi', 'connect', ssid, 'password', password
        ]
        
        subprocess.run(connect_command, check=True)
        print(f"Successfully connected to {ssid}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to connect to {ssid}. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        # Delete the temporary password file if it exists
        if os.path.exists(password_file):
            os.remove(password_file)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 connect_wifi.py <SSID> <password_file> <nmcli_path>")
        sys.exit(1)
    
    ssid = sys.argv[1]
    password_file = sys.argv[2]
    nmcli_path = sys.argv[3]
    connect_wifi(ssid, password_file, nmcli_path)
