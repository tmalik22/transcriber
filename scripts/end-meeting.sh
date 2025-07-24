#!/bin/bash

# end-meeting.sh - Stop recording and process the meeting

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Get session ID from parameter or temp file
if [[ $# -gt 0 ]]; then
    SESSION_ID="$1"
else
    if [[ -f "/tmp/current_meeting_session" ]]; then
        SESSION_ID=$(cat "/tmp/current_meeting_session")
    else
        echo "Error: No session ID provided and no current session found"
        exit 1
    fi
fi

LOG_FILE="$PROJECT_DIR/logs/${SESSION_ID}.log"
RECORDING_FILE="$PROJECT_DIR/recordings/${SESSION_ID}.wav"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Ending meeting session: $SESSION_ID"

# Stop recording processes
if [[ -f "/tmp/current_recording_pid" ]]; then
    RECORDING_PID=$(cat "/tmp/current_recording_pid")
    if kill -0 "$RECORDING_PID" 2>/dev/null; then
        log "Stopping recording process (PID: $RECORDING_PID)"
        kill -TERM "$RECORDING_PID" 2>/dev/null || true
        sleep 2
        kill -KILL "$RECORDING_PID" 2>/dev/null || true
    fi
    rm -f "/tmp/current_recording_pid"
fi

if [[ -f "/tmp/current_transcribe_pid" ]]; then
    TRANSCRIBE_PID=$(cat "/tmp/current_transcribe_pid")
    if kill -0 "$TRANSCRIBE_PID" 2>/dev/null; then
        log "Stopping transcription process (PID: $TRANSCRIBE_PID)"
        kill -TERM "$TRANSCRIBE_PID" 2>/dev/null || true
    fi
    rm -f "/tmp/current_transcribe_pid"
fi

# Clean up temp files
rm -f "/tmp/current_meeting_session"
rm -f "/tmp/current_recording_file"

# Send notification
osascript -e 'display notification "Meeting recording ended, processing..." with title "Transcription Service"' 2>/dev/null || true

# Check if recording file exists and has content
if [[ ! -f "$RECORDING_FILE" ]]; then
    log "Error: Recording file not found: $RECORDING_FILE"
    exit 1
fi

RECORDING_SIZE=$(stat -f%z "$RECORDING_FILE" 2>/dev/null || echo "0")
if [[ "$RECORDING_SIZE" -lt 1000 ]]; then
    log "Warning: Recording file is very small ($RECORDING_SIZE bytes), may be empty"
fi

log "Processing recording: $RECORDING_FILE (${RECORDING_SIZE} bytes)"

# Start post-processing pipeline
log "Starting post-processing pipeline..."

# Step 1: Final transcription (if not already done)
log "Step 1: Generating final transcript..."
python3 "$SCRIPT_DIR/transcribe.py" --file "$RECORDING_FILE" --session "$SESSION_ID" >> "$LOG_FILE" 2>&1

# Step 2: Speaker diarization  
log "Step 2: Running speaker diarization..."
python3 "$SCRIPT_DIR/diarize.py" "$RECORDING_FILE" "$SESSION_ID" >> "$LOG_FILE" 2>&1

# Step 3: AI summarization
log "Step 3: Generating AI summary..."
python3 "$SCRIPT_DIR/summarize.py" "$SESSION_ID" >> "$LOG_FILE" 2>&1

# Step 4: Calendar integration (if enabled)
log "Step 4: Processing calendar events..."
python3 "$SCRIPT_DIR/calendar-post.py" "$SESSION_ID" >> "$LOG_FILE" 2>&1 || log "Calendar integration skipped or failed"

# Step 5: Save notes
log "Step 5: Saving meeting notes..."
bash "$SCRIPT_DIR/save-notes.sh" "$SESSION_ID" >> "$LOG_FILE" 2>&1

log "Post-processing completed for session: $SESSION_ID"

# Final notification
osascript -e 'display notification "Meeting processing completed!" with title "Transcription Service"' 2>/dev/null || true

# Optional: Open notes file
NOTES_FILE="$PROJECT_DIR/notes/$(date +%Y-%m-%d).md"
if [[ -f "$NOTES_FILE" ]]; then
    log "Notes saved to: $NOTES_FILE"
    # Uncomment to auto-open notes file
    # open "$NOTES_FILE"
fi
