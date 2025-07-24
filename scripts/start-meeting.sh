#!/bin/bash

# start-meeting.sh - Begin recording and transcription session

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/settings.json"

# Generate unique session ID
SESSION_ID="meeting_$(date +%Y%m%d_%H%M%S)"
RECORDING_FILE="$PROJECT_DIR/recordings/${SESSION_ID}.wav"
TRANSCRIPT_FILE="$PROJECT_DIR/transcripts/${SESSION_ID}.txt"
LOG_FILE="$PROJECT_DIR/logs/${SESSION_ID}.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting meeting recording session: $SESSION_ID"

# Create necessary directories
mkdir -p "$(dirname "$RECORDING_FILE")"
mkdir -p "$(dirname "$TRANSCRIPT_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

# Store session info for cleanup
echo "$SESSION_ID" > "/tmp/current_meeting_session"
echo "$RECORDING_FILE" > "/tmp/current_recording_file"

# Send notification
osascript -e 'display notification "Meeting recording started" with title "Transcription Service"' 2>/dev/null || true

# Start audio recording with ffmpeg
log "Starting audio recording: $RECORDING_FILE"

# Try BlackHole first, fall back to default mic
AUDIO_DEVICE="BlackHole 2ch"
if ! ffmpeg -f avfoundation -list_devices true 2>&1 | grep -q "BlackHole 2ch"; then
    log "Warning: BlackHole 2ch not found, using default microphone"
    AUDIO_DEVICE=":0"  # Default microphone
else
    AUDIO_DEVICE=":BlackHole 2ch"
fi

# Background recording process
{
    ffmpeg -f avfoundation -i "$AUDIO_DEVICE" \
           -ac 1 -ar 16000 -acodec pcm_s16le \
           -t 7200 \
           "$RECORDING_FILE" \
           >> "$LOG_FILE" 2>&1
    
    # When recording ends, trigger processing
    log "Recording completed, starting processing..."
    bash "$SCRIPT_DIR/end-meeting.sh" "$SESSION_ID" >> "$LOG_FILE" 2>&1 &
} &

RECORDING_PID=$!
echo $RECORDING_PID > "/tmp/current_recording_pid"

# Start real-time transcription
log "Starting real-time transcription"
{
    python3 "$SCRIPT_DIR/transcribe.py" --live --session "$SESSION_ID" \
            --audio-device "$AUDIO_DEVICE" \
            >> "$LOG_FILE" 2>&1 &
} &

TRANSCRIBE_PID=$!
echo $TRANSCRIBE_PID > "/tmp/current_transcribe_pid"

log "Meeting session started successfully"
log "Recording PID: $RECORDING_PID"
log "Transcription PID: $TRANSCRIBE_PID"
log "Session will auto-stop after 2 hours or when silence detected"

# Wait for recording to complete
wait $RECORDING_PID
