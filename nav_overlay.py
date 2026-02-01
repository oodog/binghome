#!/usr/bin/env python3
"""
BingHome Navigation Overlay
A system-level always-on-top navigation bar for Raspberry Pi
Works independently of the browser - sits on top of ALL windows
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import os
import signal
import sys

class NavigationOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BingHome Nav")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Navigation bar dimensions - optimized for 7" 1024x600 display
        bar_width = 200
        bar_height = 50
        
        # Position at bottom center
        x_pos = (screen_width - bar_width) // 2
        y_pos = screen_height - bar_height - 5  # 5px from bottom
        
        # Configure window
        self.root.geometry(f"{bar_width}x{bar_height}+{x_pos}+{y_pos}")
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-type', 'dock')  # Dock type for better WM handling
        
        # Make window stay on top even in fullscreen
        self.root.lift()
        
        # Semi-transparent dark background
        self.root.configure(bg='#1a1a2e')
        
        # Try to set transparency (may not work on all systems)
        try:
            self.root.attributes('-alpha', 0.95)
        except:
            pass
        
        # Create main frame with rounded appearance
        self.frame = tk.Frame(self.root, bg='#1a1a2e', padx=10, pady=5)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Button style
        btn_config = {
            'bg': '#2d2d44',
            'fg': 'white',
            'activebackground': '#667eea',
            'activeforeground': 'white',
            'relief': 'flat',
            'font': ('Arial', 16),
            'width': 3,
            'height': 1,
            'cursor': 'hand2'
        }
        
        # Back button
        self.back_btn = tk.Button(
            self.frame, 
            text='◀',
            command=self.go_back,
            **btn_config
        )
        self.back_btn.pack(side=tk.LEFT, padx=5)
        
        # Home button (larger, highlighted)
        home_config = btn_config.copy()
        home_config['bg'] = '#667eea'
        home_config['font'] = ('Arial', 18, 'bold')
        
        self.home_btn = tk.Button(
            self.frame,
            text='⌂',
            command=self.go_home,
            **home_config
        )
        self.home_btn.pack(side=tk.LEFT, padx=5)
        
        # Forward button
        self.forward_btn = tk.Button(
            self.frame,
            text='▶',
            command=self.go_forward,
            **btn_config
        )
        self.forward_btn.pack(side=tk.LEFT, padx=5)
        
        # Keep window on top periodically
        self.keep_on_top()
        
        # Handle close signals gracefully
        signal.signal(signal.SIGTERM, self.on_close)
        signal.signal(signal.SIGINT, self.on_close)
        
        # Bind hover effects
        for btn in [self.back_btn, self.forward_btn]:
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg='#667eea'))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#2d2d44'))
        
        self.home_btn.bind('<Enter>', lambda e: self.home_btn.configure(bg='#764ba2'))
        self.home_btn.bind('<Leave>', lambda e: self.home_btn.configure(bg='#667eea'))
    
    def keep_on_top(self):
        """Periodically ensure window stays on top"""
        try:
            self.root.lift()
            self.root.attributes('-topmost', True)
            # Force focus back if lost
            self.root.after(500, self.keep_on_top)
        except:
            pass
    
    def send_browser_command(self, command):
        """Send command to browser using xdotool"""
        try:
            if command == 'back':
                # Alt+Left for back
                subprocess.run(['xdotool', 'key', 'alt+Left'], check=False)
            elif command == 'forward':
                # Alt+Right for forward
                subprocess.run(['xdotool', 'key', 'alt+Right'], check=False)
            elif command == 'home':
                # Navigate to home URL
                self.navigate_to_url('http://localhost:5000/')
        except Exception as e:
            print(f"Command error: {e}")
    
    def navigate_to_url(self, url):
        """Navigate browser to URL"""
        try:
            # Try using xdotool to type URL in address bar
            # First, focus the browser and open address bar
            subprocess.run(['xdotool', 'key', 'ctrl+l'], check=False)
            subprocess.run(['xdotool', 'type', '--clearmodifiers', url], check=False)
            subprocess.run(['xdotool', 'key', 'Return'], check=False)
        except Exception as e:
            print(f"Navigation error: {e}")
            # Fallback: try to open URL directly
            try:
                subprocess.Popen(['chromium-browser', url], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            except:
                try:
                    subprocess.Popen(['firefox', url],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except:
                    pass
    
    def go_back(self):
        """Navigate back"""
        self.send_browser_command('back')
    
    def go_home(self):
        """Navigate to home"""
        self.send_browser_command('home')
    
    def go_forward(self):
        """Navigate forward"""
        self.send_browser_command('forward')
    
    def on_close(self, *args):
        """Handle close signal"""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Start the overlay"""
        self.root.mainloop()


def main():
    # Check if xdotool is installed
    try:
        subprocess.run(['which', 'xdotool'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Installing xdotool...")
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'xdotool'], check=False)
    
    overlay = NavigationOverlay()
    overlay.run()


if __name__ == '__main__':
    main()
