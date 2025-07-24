# Quick Start Guide

🚀 **Welcome to your Always-On Transcription Service!**

This guide will get you up and running in under 30 minutes.

## 📋 Prerequisites

- **macOS 12+** (Monterey or later)
- **8GB+ RAM** (16GB recommended for AI features)
- **5GB free disk space** (for recordings and models)
- **Internet connection** (for initial setup)

## 🔧 Installation

### Step 1: Run Setup
```bash
cd path/to/your/transcription
./setup.sh
```

The setup script will:
- ✅ Install Homebrew (if needed)
- ✅ Install Python, FFmpeg, and dependencies
- ✅ Set up BlackHole audio routing
- ✅ Install Ollama AI for summarization
- ✅ Create LaunchD service for auto-start
- ✅ Configure permissions

### Step 2: Audio Setup
1. **Install BlackHole 2ch**: Download from [existential.audio/blackhole](https://existential.audio/blackhole/)
2. **Create Aggregate Device**:
   - Open `Audio MIDI Setup` (/Applications/Utilities/)
   - Click `+` → `Create Aggregate Device`
   - Name it "Meeting Audio"
   - Check both your microphone AND BlackHole 2ch
   - Set as default in System Preferences → Sound

### Step 3: Grant Permissions
When prompted, grant these permissions:
- 🎤 **Microphone Access**: For audio recording
- 🔐 **Accessibility**: For app monitoring
- 📅 **Calendar Access**: For creating events (optional)

## 🎯 Usage

### Start the Service
```bash
./start-service.sh
```

### Check Status
```bash
./status-service.sh
```

### Stop the Service
```bash
./stop-service.sh
```

## 📊 What Happens Automatically

1. **🔍 Detection**: Monitors for meeting apps (Teams, Zoom, etc.) or audio activity
2. **🎙️ Recording**: Captures audio when meetings are detected
3. **📝 Transcription**: Converts speech to text in real-time
4. **👥 Speaker ID**: Identifies different speakers
5. **🤖 AI Summary**: Extracts key points, decisions, and action items
6. **📅 Calendar**: Creates follow-up events (if enabled)
7. **📄 Notes**: Saves organized notes to `notes/YYYY-MM-DD.md`

## 📁 Where to Find Your Data

```
Transcription/
├── recordings/          # Audio files (.wav)
├── transcripts/         # Raw transcripts (.txt)
├── notes/              # Daily meeting notes (.md)
│   ├── 2025-07-24.md   # Today's meetings
│   ├── index.md        # Overview of all meetings
│   └── 2025-07-summary.md # Monthly summary
└── logs/               # System logs
```

## ⚙️ Configuration

Edit these files to customize behavior:

### `config/settings.json`
```json
{
  "audio": {
    "threshold_db": -50,        // Audio sensitivity
    "min_duration_seconds": 30  // Min meeting length
  },
  "ai": {
    "model": "mistral:7b-q4",   // AI model for summaries
    "temperature": 0.3          // Creativity level
  }
}
```

### `config/apps.json`
```json
{
  "monitored_apps": [
    "Microsoft Teams",
    "zoom.us",
    "Google Chrome"  // Add more apps here
  ]
}
```

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs
tail -f logs/meeting-watch.log

# Test manually
./scripts/meeting-watch.sh
```

### No Audio Recording
1. Verify BlackHole 2ch is installed: `system_profiler SPAudioDataType | grep BlackHole`
2. Check aggregate device setup in Audio MIDI Setup
3. Grant microphone permissions in System Preferences

### AI Summaries Not Working
```bash
# Check Ollama status
ollama list

# Install Mistral model
ollama pull mistral:7b-q4
```

### Transcription Quality Issues
1. **Improve audio quality**: Use a good microphone, reduce background noise
2. **Adjust sensitivity**: Lower `threshold_db` in settings.json
3. **Check language**: Ensure `language` is set correctly

## 🎛️ Advanced Features

### Custom Prompts
Edit `config/prompts.md` to customize AI summarization style.

### Calendar Integration
1. Set up Microsoft Graph API credentials
2. Enable in `config/settings.json`
3. Action items will automatically create calendar events

### MenuBar App (Coming Soon)
GUI toggle for easy enable/disable from the menu bar.

## 💡 Tips & Best Practices

1. **🔇 Test in Silence**: Start with quiet environment to avoid false triggers
2. **📱 Meeting Apps**: Works best with dedicated apps (Teams, Zoom) vs browser meetings
3. **🔋 Battery**: Service uses ~2-3W during active recording
4. **💾 Storage**: Each hour of meeting = ~55MB audio + 2MB text
5. **🤫 Privacy**: Everything runs locally - no cloud uploads!

## 🆘 Support

### View Logs
```bash
# Main service log
tail -f logs/meeting-watch.log

# Session-specific logs
ls logs/meeting_*.log
```

### Reset Service
```bash
./stop-service.sh
rm -f /tmp/meeting_*
./start-service.sh
```

### Uninstall
```bash
./stop-service.sh
launchctl unload ~/Library/LaunchAgents/com.transcription.meeting-watch.plist
rm ~/Library/LaunchAgents/com.transcription.meeting-watch.plist
```

---

## 🎉 You're All Set!

Your always-on transcription service is now ready to capture, transcribe, and organize all your meetings automatically.

**Start your first meeting** and watch as the service:
1. Detects the audio activity
2. Records the conversation
3. Generates a transcript
4. Creates an AI summary
5. Saves organized notes

Check `notes/$(date +%Y-%m-%d).md` for today's meeting notes!

---

*For more details, see the full README.md*
