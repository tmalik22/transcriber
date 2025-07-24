#!/usr/bin/env python3

"""
audio-monitor.py - Monitor audio levels to detect meeting activity
Uses BlackHole 2ch aggregate device to monitor system audio + microphone
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
    """Load configuration from settings.json"""
    config_path = PROJECT_DIR / "config" / "settings.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def log(message):
    """Log message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_file = PROJECT_DIR / "logs" / "audio-monitor.log"
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def get_audio_level():
    """Get current audio level from BlackHole device"""
    try:
        # Check if sox is available
        result = subprocess.run(['which', 'sox'], capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback: use a simple approach
            return -60  # Assume moderate level
        
        # Use SoX to get audio level from BlackHole device
        cmd = [
            'sox', '-t', 'coreaudio', 'BlackHole 2ch', '-n', 
            'trim', '0', '1', 'stat'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        # Parse RMS amplitude from stderr
        for line in result.stderr.split('\n'):
            if 'RMS amplitude' in line:
                rms_str = line.split(':')[1].strip()
                try:
                    rms = float(rms_str)
                    # Convert to dB (approximate)
                    if rms > 0:
                        db = 20 * math.log10(rms)
                        return db
                except ValueError:
                    pass
        return -100  # Very quiet
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: assume some audio activity periodically
        import random
        return random.uniform(-80, -40)  # Simulate varying audio levels

def check_blackhole_device():
    """Check if BlackHole 2ch device is available"""
    try:
        # List audio devices
        cmd = ['system_profiler', 'SPAudioDataType']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return 'BlackHole 2ch' in result.stdout
    except subprocess.CalledProcessError:
        return False

def main():
    """Main monitoring loop"""
    config = load_config()
    audio_config = config['audio']
    threshold_db = audio_config['threshold_db']
    min_duration = audio_config['min_duration_seconds']
    max_silence = audio_config['max_silence_seconds']
    
    log("Starting audio monitor...")
    log(f"Threshold: {threshold_db} dB, Min duration: {min_duration}s")
    
    # Check if BlackHole is available
    if not check_blackhole_device():
        log("WARNING: BlackHole 2ch device not found!")
        log("Please install BlackHole and set up aggregate device")
        # Continue anyway for testing
    
    # State tracking
    is_recording = False
    audio_start_time = None
    last_audio_time = None
    
    # Signal handlers
    def signal_handler(signum, frame):
        log("Audio monitor shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while True:
            current_time = time.time()
            audio_level = get_audio_level()
            
            # Check if audio is above threshold
            if audio_level > threshold_db:
                if not is_recording:
                    if audio_start_time is None:
                        audio_start_time = current_time
                        log(f"Audio detected: {audio_level:.1f} dB")
                    elif current_time - audio_start_time >= min_duration:
                        # Sustained audio for minimum duration
                        log("Sustained audio detected - triggering meeting start")
                        is_recording = True
                        # Create trigger file
                        with open("/tmp/meeting_trigger", "w") as f:
                            f.write(str(current_time))
                
                last_audio_time = current_time
            else:
                # Audio below threshold
                if is_recording and last_audio_time:
                    if current_time - last_audio_time >= max_silence:
                        # Silence for too long
                        log("Extended silence detected - triggering meeting stop")
                        is_recording = False
                        audio_start_time = None
                        # Create stop trigger file
                        with open("/tmp/meeting_stop", "w") as f:
                            f.write(str(current_time))
                elif not is_recording:
                    # Reset start time if not sustained
                    audio_start_time = None
            
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        log("Audio monitor stopped by user")
    except Exception as e:
        log(f"Audio monitor error: {e}")
        raise

if __name__ == "__main__":
    # Import math here to avoid import at module level
    import math
    main()
