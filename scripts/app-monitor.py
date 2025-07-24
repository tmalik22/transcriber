#!/usr/bin/env python3

"""
app-monitor.py - Monitor foreground applications to detect meeting apps
Detects when meeting/communication apps become active
"""

import json
import time
import subprocess
import os
import sys
import signal
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

def load_config():
    """Load configuration from apps.json and settings.json"""
    apps_path = PROJECT_DIR / "config" / "apps.json"
    with open(apps_path, 'r') as f:
        apps_config = json.load(f)
    
    settings_path = PROJECT_DIR / "config" / "settings.json"
    with open(settings_path, 'r') as f:
        settings_config = json.load(f)
    
    return apps_config, settings_config

def log(message):
    """Log message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_file = PROJECT_DIR / "logs" / "app-monitor.log"
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def get_frontmost_app():
    """Get the name of the frontmost application"""
    try:
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            return frontApp
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return None

def get_active_window_title():
    """Get the title of the active window"""
    try:
        script = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set windowTitle to name of front window of frontApp
            return windowTitle
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return None

def check_meeting_activity(app_name, window_title, monitored_apps, meeting_keywords):
    """Check if current app/window indicates meeting activity"""
    if not app_name:
        return False
    
    # Check if app is in monitored list
    if app_name in monitored_apps:
        log(f"Monitored app active: {app_name}")
        
        # For browsers, check window title for meeting keywords
        if app_name in ['Google Chrome', 'Safari', 'Microsoft Edge', 'Firefox']:
            if window_title:
                for keyword in meeting_keywords:
                    if keyword.lower() in window_title.lower():
                        log(f"Meeting URL detected: {keyword} in {window_title}")
                        return True
        else:
            # For dedicated apps like Teams, Zoom, etc.
            return True
    
    return False

def main():
    """Main monitoring loop"""
    apps_config, settings_config = load_config()
    monitored_apps = apps_config['monitored_apps']
    meeting_keywords = apps_config['meeting_keywords']
    
    log("Starting app monitor...")
    log(f"Monitoring apps: {', '.join(monitored_apps)}")
    log(f"Meeting keywords: {', '.join(meeting_keywords)}")
    
    # State tracking
    current_app = None
    meeting_active = False
    meeting_start_time = None
    
    # Signal handlers
    def signal_handler(signum, frame):
        log("App monitor shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while True:
            app_name = get_frontmost_app()
            window_title = get_active_window_title()
            
            # Log app changes
            if app_name != current_app:
                if app_name:
                    log(f"App changed to: {app_name}")
                current_app = app_name
            
            # Check for meeting activity
            is_meeting_app = check_meeting_activity(app_name, window_title, 
                                                  monitored_apps, meeting_keywords)
            
            if is_meeting_app and not meeting_active:
                # Meeting app became active
                log(f"Meeting app detected: {app_name}")
                meeting_active = True
                meeting_start_time = time.time()
                
                # Create trigger file
                with open("/tmp/meeting_trigger", "w") as f:
                    f.write(f"{meeting_start_time}:{app_name}")
                    
            elif not is_meeting_app and meeting_active:
                # Meeting app is no longer active
                if meeting_start_time and time.time() - meeting_start_time > 30:
                    # Only stop if meeting was active for at least 30 seconds
                    log(f"Meeting app no longer active: {current_app}")
                    meeting_active = False
                    meeting_start_time = None
                    
                    # Create stop trigger file (but only if we think a meeting was happening)
                    with open("/tmp/meeting_stop", "w") as f:
                        f.write(str(time.time()))
            
            time.sleep(3)  # Check every 3 seconds
            
    except KeyboardInterrupt:
        log("App monitor stopped by user")
    except Exception as e:
        log(f"App monitor error: {e}")
        raise

if __name__ == "__main__":
    main()
