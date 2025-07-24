# Always-On Transcription Service

🎯 **Goal**: Create an always-running on-device assistant that captures every voice/video call, produces speaker-labelled transcripts, summarizes key points, records action items, and drops calendar blocks—all without cloud services.

## 🔄 End-to-End Workflow

| Stage | Action | Tool / Script |
|-------|--------|---------------|
| 1. Audio merge | Duplicate system output + mic into one Core Audio stream | BlackHole 2-ch Aggregate Device |
| 2. Call detection | Start capture whenever audio on BlackHole exceeds threshold or monitored app becomes frontmost | coreaudiod isActive check + osascript front-app watch |
| 3. Live ASR | Pipe BlackHole stream to SpeechTranscriber CLI (Neural Engine) | ffmpeg + built-in Speech Recognition |
| 4. Post-call diarization | Run SpeechBrain ECAPA on recorded WAV | python diar.py meeting.wav |
| 5. Summaries & actions | Feed speaker-tagged text to Ollama Mistral-7B-Q4 | ollama run mistral |
| 6. Calendar blocks | Parse actions, POST events via Microsoft Graph | curl .../me/events |
| 7. Note storage | Append markdown to per-date notebook | ~/MeetingNotes/YYYY-MM-DD.md |

## 📁 Project Structure

```
Transcription/
├── scripts/
│   ├── meeting-watch.sh          # Main monitoring daemon
│   ├── start-meeting.sh          # Begin recording session
│   ├── end-meeting.sh            # Stop and process recording
│   ├── audio-monitor.py          # Audio level monitoring
│   ├── app-monitor.py            # Application monitoring
│   ├── transcribe.py             # Speech-to-text processing
│   ├── diarize.py                # Speaker diarization
│   ├── summarize.py              # AI summarization
│   ├── calendar-post.py          # Calendar integration
│   └── save-notes.sh             # Note management
├── config/
│   ├── apps.json                 # Monitored applications
│   ├── prompts.md                # AI prompts for summarization
│   └── settings.json             # General settings
├── recordings/                   # Audio recordings storage
├── transcripts/                  # Raw transcripts
├── notes/                        # Processed meeting notes
├── logs/                         # System logs
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   ./setup.sh
   ```

2. **Configure Audio**:
   - Install BlackHole 2ch
   - Set up aggregate audio device

3. **Start the Service**:
   ```bash
   ./start-service.sh
   ```

## 📦 Resource Budget (per hour call)
- Power (live ASR): ~2 Wh
- Power (post steps): ~0.5 Wh  
- Storage: 55 MB WAV + <2 MB text
- Cost: $0 (all local, open-source)

## 🔧 Configuration

Edit `config/settings.json` to customize:
- Audio thresholds
- Monitored applications
- Output directories
- AI model settings

## 📝 Notes Repository

Meeting notes are automatically organized in `notes/YYYY-MM-DD.md` with:
- 🔑 Highlights
- ✅ Decisions  
- ❓ Open questions
- 🔨 Action items (owner, ETA)
