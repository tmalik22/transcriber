#!/usr/bin/env python3

"""
transcribe.py - Speech-to-text transcription using macOS Speech Framework
Supports both live transcription and file-based transcription
"""

import sys
import json
import time
import argparse
import subprocess
import tempfile
from pathlib import Path
import speech_recognition as sr
from pydub import AudioSegment
import wave

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
        log_file = PROJECT_DIR / "logs" / "transcribe.log"
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def transcribe_audio_file(audio_file, session_id):
    """Transcribe an audio file using speech recognition"""
    config = load_config()
    transcript_file = PROJECT_DIR / "transcripts" / f"{session_id}.txt"
    
    log(f"Transcribing audio file: {audio_file}", session_id)
    
    # Initialize speech recognizer
    recognizer = sr.Recognizer()
    
    try:
        # Load audio file
        with sr.AudioFile(str(audio_file)) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio_data = recognizer.record(source)
        
        log("Audio loaded, starting transcription...", session_id)
        
        # Use macOS built-in speech recognition
        try:
            text = recognizer.recognize_whisper(audio_data, language="en-US")
            log("Transcription completed using Whisper", session_id)
        except sr.RequestError:
            # Fallback to Google Speech Recognition
            try:
                text = recognizer.recognize_google(audio_data, language="en-US")
                log("Transcription completed using Google Speech", session_id)
            except sr.RequestError:
                # Final fallback to basic recognition
                text = recognizer.recognize_sphinx(audio_data)
                log("Transcription completed using CMU Sphinx", session_id)
        
        # Save transcript
        with open(transcript_file, 'w') as f:
            f.write(f"# Transcript for {session_id}\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(text)
        
        log(f"Transcript saved to: {transcript_file}", session_id)
        return text
        
    except sr.UnknownValueError:
        log("Could not understand the audio", session_id)
        return ""
    except sr.RequestError as e:
        log(f"Error with speech recognition service: {e}", session_id)
        return ""
    except Exception as e:
        log(f"Transcription error: {e}", session_id)
        return ""

def transcribe_live(session_id, audio_device):
    """Live transcription from audio device"""
    config = load_config()
    transcript_file = PROJECT_DIR / "transcripts" / f"{session_id}_live.txt"
    
    log(f"Starting live transcription for session: {session_id}", session_id)
    
    # Initialize speech recognizer
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # Adjust for ambient noise
    with microphone as source:
        log("Adjusting for ambient noise...", session_id)
        recognizer.adjust_for_ambient_noise(source)
    
    log("Live transcription started. Press Ctrl+C to stop.", session_id)
    
    transcript_chunks = []
    chunk_count = 0
    
    try:
        while True:
            try:
                with microphone as source:
                    # Listen for audio with timeout
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    # Recognize speech
                    text = recognizer.recognize_whisper(audio, language="en-US")
                    
                    if text.strip():
                        chunk_count += 1
                        timestamp = time.strftime('%H:%M:%S')
                        chunk_text = f"[{timestamp}] {text}\n"
                        transcript_chunks.append(chunk_text)
                        
                        # Save incrementally
                        with open(transcript_file, 'w') as f:
                            f.write(f"# Live Transcript for {session_id}\n")
                            f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            f.writelines(transcript_chunks)
                        
                        log(f"Chunk {chunk_count}: {text[:50]}...", session_id)
                
                except sr.UnknownValueError:
                    # No speech detected, continue
                    pass
                except sr.RequestError as e:
                    log(f"Recognition error: {e}", session_id)
                    time.sleep(1)
                    
            except sr.WaitTimeoutError:
                # No audio detected, continue
                pass
                
    except KeyboardInterrupt:
        log("Live transcription stopped by user", session_id)
    except Exception as e:
        log(f"Live transcription error: {e}", session_id)
    
    log(f"Live transcription ended. {chunk_count} chunks processed.", session_id)
    return transcript_file

def convert_audio_format(input_file):
    """Convert audio file to format suitable for speech recognition"""
    try:
        # Load audio file
        audio = AudioSegment.from_file(str(input_file))
        
        # Convert to mono, 16kHz, 16-bit WAV
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Create temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        audio.export(temp_file.name, format='wav')
        
        return temp_file.name
    except Exception as e:
        log(f"Audio conversion error: {e}")
        return str(input_file)  # Return original if conversion fails

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Transcribe audio to text')
    parser.add_argument('--file', type=str, help='Audio file to transcribe')
    parser.add_argument('--live', action='store_true', help='Live transcription mode')
    parser.add_argument('--session', type=str, required=True, help='Session ID')
    parser.add_argument('--audio-device', type=str, help='Audio device for live mode')
    
    args = parser.parse_args()
    
    if args.live:
        # Live transcription mode
        transcribe_live(args.session, args.audio_device)
    elif args.file:
        # File transcription mode
        audio_file = Path(args.file)
        if not audio_file.exists():
            log(f"Error: Audio file not found: {audio_file}")
            sys.exit(1)
        
        # Convert audio format if needed
        converted_file = convert_audio_format(audio_file)
        
        try:
            transcribe_audio_file(converted_file, args.session)
        finally:
            # Clean up temporary file
            if converted_file != str(audio_file):
                Path(converted_file).unlink(missing_ok=True)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
