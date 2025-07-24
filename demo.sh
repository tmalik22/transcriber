#!/bin/bash

# demo.sh - Test the transcription service with a simple demo

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🎤 Transcription Service Demo${NC}"
echo "=================================="
echo ""

# Check if setup has been run
if [[ ! -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
    echo -e "${RED}❌ Setup not completed yet.${NC}"
    echo "Please run: ./setup.sh"
    exit 1
fi

echo -e "${GREEN}✅ Setup detected${NC}"

# Test 1: Check dependencies
echo -e "${YELLOW}Test 1: Checking dependencies...${NC}"
source "$SCRIPT_DIR/venv/bin/activate"

python3 -c "
import sys
missing = []
required = ['numpy', 'speech_recognition', 'requests', 'json', 'subprocess']
for pkg in required:
    try:
        __import__(pkg)
        print(f'✓ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'✗ {pkg}')

if missing:
    print(f'Missing packages: {missing}')
    sys.exit(1)
else:
    print('All required packages available!')
"

# Test 2: Check audio setup
echo ""
echo -e "${YELLOW}Test 2: Checking audio setup...${NC}"

if system_profiler SPAudioDataType | grep -q "BlackHole"; then
    echo "✓ BlackHole audio device found"
else
    echo "⚠️  BlackHole not found - you'll need to install it for full functionality"
fi

# Test 3: Check Ollama
echo ""
echo -e "${YELLOW}Test 3: Checking AI setup...${NC}"

if command -v ollama &> /dev/null; then
    echo "✓ Ollama installed"
    
    # Start Ollama if not running
    if ! curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
        echo "Starting Ollama service..."
        ollama serve &
        OLLAMA_PID=$!
        sleep 3
    fi
    
    if ollama list | grep -q "mistral"; then
        echo "✓ Mistral model available"
    else
        echo "⚠️  Mistral model not found. Installing..."
        ollama pull mistral:7b-q4
    fi
else
    echo "⚠️  Ollama not installed - AI summaries will not work"
fi

# Test 4: Create a demo session
echo ""
echo -e "${YELLOW}Test 4: Creating demo session...${NC}"

DEMO_SESSION="demo_$(date +%Y%m%d_%H%M%S)"

# Create demo transcript
mkdir -p "$SCRIPT_DIR/transcripts"
cat > "$SCRIPT_DIR/transcripts/${DEMO_SESSION}.txt" << 'EOF'
# Demo Transcript
Generated: 2025-07-24 10:00:00

[Speaker 1]: Hello everyone, thanks for joining today's project planning meeting.
[Speaker 2]: Thanks for organizing this. I wanted to discuss the Q3 deliverables.
[Speaker 1]: Great. So we need to finalize the roadmap by end of week. John, can you handle the technical specs?
[Speaker 2]: Absolutely. I'll have the draft ready by Friday. Should I include the API documentation?
[Speaker 1]: Yes, please include that. Also, we should schedule a follow-up for next Tuesday to review everything.
[Speaker 2]: Sounds good. I'll send out calendar invites after this meeting.
[Speaker 1]: Perfect. Any other items we need to cover today?
[Speaker 2]: I think we're good. Thanks everyone!
EOF

echo "✓ Demo transcript created"

# Test 5: Run summarization
echo ""
echo -e "${YELLOW}Test 5: Testing AI summarization...${NC}"

source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/scripts/summarize.py" "$DEMO_SESSION"

if [[ -f "$SCRIPT_DIR/transcripts/${DEMO_SESSION}_summary.md" ]]; then
    echo "✓ AI summary generated successfully"
    echo ""
    echo "📄 Summary preview:"
    echo "-------------------"
    head -n 20 "$SCRIPT_DIR/transcripts/${DEMO_SESSION}_summary.md"
    echo "..."
else
    echo "⚠️  AI summary failed - check logs"
fi

# Test 6: Save notes
echo ""
echo -e "${YELLOW}Test 6: Testing note saving...${NC}"

bash "$SCRIPT_DIR/scripts/save-notes.sh" "$DEMO_SESSION"

TODAY=$(date +%Y-%m-%d)
if [[ -f "$SCRIPT_DIR/notes/$TODAY.md" ]]; then
    echo "✓ Daily notes created successfully"
    echo ""
    echo "📝 Notes preview:"
    echo "----------------"
    tail -n 15 "$SCRIPT_DIR/notes/$TODAY.md"
else
    echo "⚠️  Note saving failed"
fi

# Cleanup
if [[ -n "${OLLAMA_PID:-}" ]]; then
    kill $OLLAMA_PID 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}🎉 Demo completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Start the service: ./start-service.sh"
echo "2. Join a meeting or speak near your microphone"
echo "3. Check notes in: notes/$TODAY.md"
echo ""
echo "Files created during demo:"
echo "- transcripts/${DEMO_SESSION}.txt"
echo "- transcripts/${DEMO_SESSION}_summary.md"
echo "- notes/$TODAY.md"
