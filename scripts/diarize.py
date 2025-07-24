#!/usr/bin/env python3

"""
diarize.py - Speaker diarization using pyannote.audio
Identifies different speakers in the audio recording
"""

import sys
import json
import time
import argparse
import torch
import torchaudio
from pathlib import Path
import subprocess

# Add project root to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

def load_config():
    """Load configuration from settings.json"""
    config_path = PROJECT_DIR / "config" / "settings.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def log(message, session_id=None):
    """Log message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if session_id:
        log_file = PROJECT_DIR / "logs" / f"{session_id}.log"
    else:
        log_file = PROJECT_DIR / "logs" / "diarize.log"
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def simple_voice_activity_detection(audio_file, session_id):
    """Simple VAD using energy-based detection"""
    try:
        import librosa
        import numpy as np
        
        log("Loading audio for VAD...", session_id)
        y, sr = librosa.load(str(audio_file), sr=16000)
        
        # Simple energy-based VAD
        frame_length = 2048
        hop_length = 512
        
        # Compute RMS energy
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Threshold for voice activity (adjust based on your needs)
        threshold = np.percentile(rms, 30)  # Use 30th percentile as threshold
        
        # Create voice activity segments
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
        
        segments = []
        start_time = None
        
        for i, (time_val, energy) in enumerate(zip(times, rms)):
            if energy > threshold:
                if start_time is None:
                    start_time = time_val
            else:
                if start_time is not None:
                    segments.append((start_time, time_val))
                    start_time = None
        
        # Close final segment if needed
        if start_time is not None:
            segments.append((start_time, times[-1]))
        
        log(f"Found {len(segments)} voice activity segments", session_id)
        return segments
        
    except ImportError:
        log("librosa not available, skipping VAD", session_id)
        return []
    except Exception as e:
        log(f"VAD error: {e}", session_id)
        return []

def cluster_speakers_simple(segments, max_speakers=4):
    """Simple speaker clustering based on segment timing"""
    if not segments:
        return []
    
    # For simple implementation, alternate between speakers
    # This is very basic - real implementation would use audio features
    speaker_segments = []
    current_speaker = 0
    
    for start, end in segments:
        duration = end - start
        
        # Switch speakers for segments longer than 10 seconds
        if duration > 10:
            current_speaker = (current_speaker + 1) % max_speakers
        
        speaker_segments.append({
            'start': start,
            'end': end, 
            'speaker': f"Speaker_{current_speaker + 1}"
        })
    
    return speaker_segments

def pyannote_diarization(audio_file, session_id):
    """Speaker diarization using pyannote.audio"""
    try:
        from pyannote.audio import Pipeline
        
        log("Initializing pyannote pipeline...", session_id)
        
        # Initialize the pipeline
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",
                                          use_auth_token=None)
        
        log("Running speaker diarization...", session_id)
        
        # Run diarization
        diarization = pipeline(str(audio_file))
        
        # Convert to our format
        speaker_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        log(f"Pyannote found {len(speaker_segments)} speaker segments", session_id)
        return speaker_segments
        
    except ImportError:
        log("pyannote.audio not available, using simple method", session_id)
        return None
    except Exception as e:
        log(f"Pyannote error: {e}, falling back to simple method", session_id)
        return None

def merge_transcript_with_speakers(transcript_file, speaker_segments, session_id):
    """Merge transcript with speaker information"""
    try:
        # Read transcript
        with open(transcript_file, 'r') as f:
            transcript_content = f.read()
        
        if not speaker_segments:
            log("No speaker segments available", session_id)
            return transcript_content
        
        # For now, we'll do a simple assignment
        # In a real implementation, you'd align transcript timestamps with speaker segments
        
        lines = transcript_content.split('\n')
        processed_lines = []
        current_speaker_idx = 0
        
        for line in lines:
            if line.strip() and not line.startswith('#') and not line.startswith('Generated:'):
                # Assign speaker to this line
                if current_speaker_idx < len(speaker_segments):
                    speaker = speaker_segments[current_speaker_idx]['speaker']
                    processed_lines.append(f"[{speaker}]: {line}")
                    current_speaker_idx = (current_speaker_idx + 1) % len(speaker_segments)
                else:
                    processed_lines.append(f"[Speaker_1]: {line}")
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
        
    except Exception as e:
        log(f"Error merging transcript with speakers: {e}", session_id)
        return transcript_content

def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("Usage: python diarize.py <audio_file> <session_id>")
        sys.exit(1)
    
    audio_file = Path(sys.argv[1])
    session_id = sys.argv[2]
    
    if not audio_file.exists():
        log(f"Error: Audio file not found: {audio_file}", session_id)
        sys.exit(1)
    
    config = load_config()
    diarization_config = config.get('diarization', {})
    
    if not diarization_config.get('enable', True):
        log("Diarization disabled in config", session_id)
        return
    
    log(f"Starting speaker diarization for: {audio_file}", session_id)
    
    # Try pyannote first, fall back to simple method
    speaker_segments = pyannote_diarization(audio_file, session_id)
    
    if speaker_segments is None:
        # Fall back to simple voice activity detection + clustering
        log("Using simple diarization method", session_id)
        vad_segments = simple_voice_activity_detection(audio_file, session_id)
        speaker_segments = cluster_speakers_simple(vad_segments, 
                                                 diarization_config.get('max_speakers', 4))
    
    # Save diarization results
    diarization_file = PROJECT_DIR / "transcripts" / f"{session_id}_diarization.json"
    with open(diarization_file, 'w') as f:
        json.dump(speaker_segments, f, indent=2)
    
    log(f"Diarization results saved to: {diarization_file}", session_id)
    
    # Merge with transcript if available
    transcript_file = PROJECT_DIR / "transcripts" / f"{session_id}.txt"
    if transcript_file.exists():
        log("Merging transcript with speaker information", session_id)
        merged_content = merge_transcript_with_speakers(transcript_file, speaker_segments, session_id)
        
        # Save merged transcript
        merged_file = PROJECT_DIR / "transcripts" / f"{session_id}_with_speakers.txt"
        with open(merged_file, 'w') as f:
            f.write(merged_content)
        
        log(f"Speaker-annotated transcript saved to: {merged_file}", session_id)
    else:
        log("No transcript file found to merge with", session_id)
    
    # Print summary
    unique_speakers = set()
    total_speech_time = 0
    
    for segment in speaker_segments:
        unique_speakers.add(segment['speaker'])
        total_speech_time += segment['end'] - segment['start']
    
    log(f"Diarization completed: {len(unique_speakers)} speakers, {total_speech_time:.1f}s total speech", session_id)

if __name__ == "__main__":
    main()
