#!/usr/bin/env python3

"""
summarize.py - AI-powered meeting summarization using Ollama
Processes transcripts to extract key points, decisions, and action items
"""

import sys
import json
import time
import subprocess
from pathlib import Path

# Optional imports with fallbacks
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

# Add project root to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

def load_config():
    """Load configuration from settings.json"""
    config_path = PROJECT_DIR / "config" / "settings.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def load_prompt_template():
    """Load the AI prompt template"""
    prompt_path = PROJECT_DIR / "config" / "prompts.md"
    with open(prompt_path, 'r') as f:
        return f.read()

def log(message, session_id=None):
    """Log message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if session_id:
        log_file = PROJECT_DIR / "logs" / f"{session_id}.log"
    else:
        log_file = PROJECT_DIR / "logs" / "summarize.log"
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def check_ollama_availability():
    """Check if Ollama is running and available"""
    if not HAS_REQUESTS:
        log("Warning: requests library not available, cannot check Ollama status")
        return False
    
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def list_ollama_models():
    """List available Ollama models"""
    if not HAS_REQUESTS:
        return []
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        return []
    except requests.RequestException:
        return []

def query_ollama(prompt, model, temperature=0.3, max_tokens=2000):
    """Send query to Ollama API"""
    if not HAS_REQUESTS:
        return "Error: requests library not available"
    
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        else:
            return f"Error: HTTP {response.status_code}"
            
    except requests.RequestException as e:
        return f"Error: {e}"

def fallback_summarization(transcript_content):
    """Simple fallback summarization without AI"""
    lines = transcript_content.split('\n')
    
    # Count speakers
    speakers = set()
    for line in lines:
        if line.strip().startswith('[') and ']:' in line:
            speaker = line.split(']:')[0].strip('[')
            speakers.add(speaker)
    
    # Get word count
    words = transcript_content.split()
    word_count = len(words)
    
    # Estimate duration (assuming 150 words per minute)
    duration_minutes = max(1, word_count // 150)
    
    summary = f"""# Meeting Summary (Auto-generated)

## 📊 Meeting Statistics
- **Duration**: ~{duration_minutes} minutes
- **Participants**: {len(speakers)} speakers identified
- **Word Count**: {word_count} words

## 🎯 Participants
{chr(10).join(f"- {speaker}" for speaker in sorted(speakers))}

## 📝 Notes
*AI summarization not available. Please review the full transcript manually.*

## 🔗 Files
- Full transcript available in transcripts folder
- Audio recording available in recordings folder

---
*Summary generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    return summary

def summarize_meeting(session_id):
    """Generate AI summary of the meeting"""
    config = load_config()
    ai_config = config.get('ai', {})
    
    log(f"Starting summarization for session: {session_id}", session_id)
    
    # Find transcript file (prefer speaker-annotated version)
    transcript_files = [
        PROJECT_DIR / "transcripts" / f"{session_id}_with_speakers.txt",
        PROJECT_DIR / "transcripts" / f"{session_id}.txt",
        PROJECT_DIR / "transcripts" / f"{session_id}_live.txt"
    ]
    
    transcript_file = None
    for file_path in transcript_files:
        if file_path.exists():
            transcript_file = file_path
            break
    
    if not transcript_file:
        log("No transcript file found", session_id)
        return None
    
    log(f"Using transcript: {transcript_file}", session_id)
    
    # Read transcript
    with open(transcript_file, 'r') as f:
        transcript_content = f.read()
    
    if len(transcript_content.strip()) < 100:
        log("Transcript too short for meaningful summarization", session_id)
        return fallback_summarization(transcript_content)
    
    # Check if Ollama is available
    if not check_ollama_availability():
        log("Ollama not available, using fallback summarization", session_id)
        return fallback_summarization(transcript_content)
    
    # Get available models
    available_models = list_ollama_models()
    model = ai_config.get('model', 'mistral:7b-q4')
    
    # Check if preferred model is available
    if model not in available_models:
        if available_models:
            model = available_models[0]
            log(f"Preferred model not found, using: {model}", session_id)
        else:
            log("No Ollama models available, using fallback", session_id)
            return fallback_summarization(transcript_content)
    
    log(f"Using AI model: {model}", session_id)
    
    # Load prompt template
    prompt_template = load_prompt_template()
    
    # Construct full prompt
    full_prompt = f"""{prompt_template}

## Transcript to Analyze:

{transcript_content}

---

Please analyze the above transcript and provide a structured summary following the format specified in the prompt."""
    
    log("Sending request to AI model...", session_id)
    
    # Query AI model
    summary = query_ollama(
        full_prompt,
        model,
        ai_config.get('temperature', 0.3),
        ai_config.get('max_tokens', 2000)
    )
    
    if summary.startswith("Error:"):
        log(f"AI summarization failed: {summary}", session_id)
        return fallback_summarization(transcript_content)
    
    log("AI summarization completed", session_id)
    
    # Add metadata
    final_summary = f"""# Meeting Summary
**Session ID**: {session_id}  
**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Transcript**: {transcript_file.name}  
**AI Model**: {model}

---

{summary}

---

## 📎 Attachments
- **Audio Recording**: `recordings/{session_id}.wav`
- **Raw Transcript**: `transcripts/{session_id}.txt`
- **Speaker Analysis**: `transcripts/{session_id}_diarization.json`
"""
    
    # Save summary
    summary_file = PROJECT_DIR / "transcripts" / f"{session_id}_summary.md"
    with open(summary_file, 'w') as f:
        f.write(final_summary)
    
    log(f"Summary saved to: {summary_file}", session_id)
    
    return final_summary

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python summarize.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    
    try:
        summary = summarize_meeting(session_id)
        if summary:
            print("Summary generated successfully")
        else:
            print("Failed to generate summary")
            sys.exit(1)
    except Exception as e:
        log(f"Summarization error: {e}", session_id)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
