#!/bin/bash

# meeting-watch.sh - Main monitoring daemon for always-on transcription
# This script monitors for meeting activity and triggers recording/processing

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/settings.json"
LOG_FILE="$PROJECT_DIR/logs/meeting-watch.log"
PID_FILE="/tmp/meeting-watch.pid"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if already running
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    log "ERROR: meeting-watch is already running (PID: $(cat "$PID_FILE"))"
    exit 1
fi

# Store PID
echo $$ > "$PID_FILE"

# Cleanup function
cleanup() {
    log "Shutting down meeting-watch daemon..."
    rm -f "$PID_FILE"
    # Kill any child processes
    pkill -P $$ || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

log "Starting meeting-watch daemon..."
log "Project directory: $PROJECT_DIR"
log "Configuration: $CONFIG_FILE"

# Check dependencies
command -v python3 >/dev/null 2>&1 || { log "ERROR: python3 not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { log "ERROR: ffmpeg not found"; exit 1; }

# Start monitoring processes
log "Starting audio monitor..."
python3 "$SCRIPT_DIR/audio-monitor.py" &
AUDIO_PID=$!

log "Starting app monitor..."
python3 "$SCRIPT_DIR/app-monitor.py" &
APP_PID=$!

# Main monitoring loop
RECORDING_PID=""
LAST_CHECK=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    
    # Check if we should start recording
    if [[ -z "$RECORDING_PID" ]]; then
        # Check for trigger files created by monitors
        if [[ -f "/tmp/meeting_trigger" ]]; then
            log "Meeting detected! Starting recording..."
            bash "$SCRIPT_DIR/start-meeting.sh" &
            RECORDING_PID=$!
            rm -f "/tmp/meeting_trigger"
        fi
    else
        # Check if recording is still running
        if ! kill -0 "$RECORDING_PID" 2>/dev/null; then
            log "Recording session ended"
            RECORDING_PID=""
        fi
        
        # Check for stop trigger
        if [[ -f "/tmp/meeting_stop" ]]; then
            log "Stop signal received, ending recording..."
            kill "$RECORDING_PID" 2>/dev/null || true
            wait "$RECORDING_PID" 2>/dev/null || true
            RECORDING_PID=""
            rm -f "/tmp/meeting_stop"
        fi
    fi
    
    # Health check every minute
    if (( CURRENT_TIME - LAST_CHECK >= 60 )); then
        # Check if monitor processes are still running
        if ! kill -0 "$AUDIO_PID" 2>/dev/null; then
            log "Audio monitor died, restarting..."
            python3 "$SCRIPT_DIR/audio-monitor.py" &
            AUDIO_PID=$!
        fi
        
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            log "App monitor died, restarting..."
            python3 "$SCRIPT_DIR/app-monitor.py" &
            APP_PID=$!
        fi
        
        LAST_CHECK=$CURRENT_TIME
    fi
    
    sleep 5
done
