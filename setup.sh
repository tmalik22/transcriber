#!/bin/bash

# setup.sh - Install and configure the always-on transcription service

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

print_header() {
    echo -e "${BLUE}"
    echo "=================================="
    echo "  Always-On Transcription Setup  "
    echo "=================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        print_error "This setup script is designed for macOS only"
        exit 1
    fi
    
    # Check macOS version
    MACOS_VERSION=$(sw_vers -productVersion)
    print_step "Detected macOS version: $MACOS_VERSION"
}

check_homebrew() {
    print_step "Checking Homebrew installation..."
    
    if ! command -v brew &> /dev/null; then
        print_warning "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add to PATH for this session
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f "/usr/local/bin/brew" ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    else
        print_step "Homebrew found: $(brew --version | head -n1)"
    fi
}

install_system_dependencies() {
    print_step "Installing system dependencies..."
    
    # Update Homebrew
    brew update
    
    # Install required tools
    BREW_PACKAGES=(
        "python@3.11"
        "ffmpeg"
        "sox"
        "portaudio"
        "git"
    )
    
    for package in "${BREW_PACKAGES[@]}"; do
        if brew list "$package" &>/dev/null; then
            print_step "$package already installed"
        else
            print_step "Installing $package..."
            brew install "$package"
        fi
    done
}

install_blackhole() {
    print_step "Checking BlackHole 2ch installation..."
    
    # Check if BlackHole is already installed
    if system_profiler SPAudioDataType | grep -q "BlackHole 2ch"; then
        print_step "BlackHole 2ch already installed"
        return
    fi
    
    print_warning "BlackHole 2ch not found. This is required for audio routing."
    echo "Please follow these steps:"
    echo "1. Download BlackHole 2ch from: https://existential.audio/blackhole/"
    echo "2. Install the .pkg file"
    echo "3. Set up an Aggregate Device in Audio MIDI Setup:"
    echo "   - Open Audio MIDI Setup (/Applications/Utilities/)"
    echo "   - Click '+' and select 'Create Aggregate Device'"
    echo "   - Name it 'Meeting Audio'"
    echo "   - Check both your microphone and BlackHole 2ch"
    echo "   - Set as default input/output in System Preferences"
    echo ""
    read -p "Press Enter after installing BlackHole 2ch..."
}

setup_python_environment() {
    print_step "Setting up Python environment..."
    
    # Ensure we're using Python 3.11
    PYTHON_CMD="python3.11"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        PYTHON_CMD="python3"
    fi
    
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version)
    print_step "Using Python: $PYTHON_VERSION"
    
    # Create virtual environment
    if [[ ! -d "$PROJECT_DIR/venv" ]]; then
        print_step "Creating Python virtual environment..."
        $PYTHON_CMD -m venv "$PROJECT_DIR/venv"
    fi
    
    # Activate virtual environment
    source "$PROJECT_DIR/venv/bin/activate"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install Python packages
    print_step "Installing Python packages..."
    pip install -r "$PROJECT_DIR/requirements.txt"
}

install_ollama() {
    print_step "Setting up Ollama for AI summarization..."
    
    if ! command -v ollama &> /dev/null; then
        print_step "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        print_step "Ollama already installed: $(ollama --version)"
    fi
    
    # Start Ollama service
    print_step "Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    
    # Install default model
    print_step "Installing Mistral 7B model (this may take a while)..."
    ollama pull mistral:7b-q4 || print_warning "Failed to pull Mistral model. You can install it later with: ollama pull mistral:7b-q4"
    
    # Stop Ollama for now
    kill $OLLAMA_PID 2>/dev/null || true
}

setup_permissions() {
    print_step "Setting up macOS permissions..."
    
    echo "The transcription service needs the following permissions:"
    echo "1. Microphone access"
    echo "2. Accessibility (for app monitoring)"
    echo "3. Calendar access (optional)"
    echo ""
    echo "Please grant these permissions when prompted, or manually in:"
    echo "System Preferences > Security & Privacy > Privacy"
    
    # Test microphone access
    print_step "Testing microphone access..."
    python3 -c "
import speech_recognition as sr
try:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print('Microphone access granted')
except Exception as e:
    print(f'Microphone permission needed: {e}')
" 2>/dev/null || print_warning "Microphone permission may be needed"
}

make_scripts_executable() {
    print_step "Making scripts executable..."
    
    find "$PROJECT_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
    find "$PROJECT_DIR/scripts" -name "*.py" -exec chmod +x {} \;
    chmod +x "$PROJECT_DIR/setup.sh"
}

create_launchd_service() {
    print_step "Setting up LaunchD service for auto-start..."
    
    SERVICE_NAME="com.transcription.meeting-watch"
    PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/scripts/meeting-watch.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/launchd.err</string>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
    
    print_step "LaunchD service created. To start the service:"
    echo "  launchctl load $PLIST_FILE"
    echo "To stop the service:"
    echo "  launchctl unload $PLIST_FILE"
}

create_control_scripts() {
    print_step "Creating control scripts..."
    
    # Start script
    cat > "$PROJECT_DIR/start-service.sh" << 'EOF'
#!/bin/bash
echo "Starting Always-On Transcription Service..."
launchctl load "$HOME/Library/LaunchAgents/com.transcription.meeting-watch.plist" 2>/dev/null || echo "Service already loaded"
echo "Service started. Check logs in: $PWD/logs/"
EOF
    
    # Stop script
    cat > "$PROJECT_DIR/stop-service.sh" << 'EOF'
#!/bin/bash
echo "Stopping Always-On Transcription Service..."
launchctl unload "$HOME/Library/LaunchAgents/com.transcription.meeting-watch.plist" 2>/dev/null || echo "Service not loaded"
echo "Service stopped."
EOF
    
    # Status script
    cat > "$PROJECT_DIR/status-service.sh" << 'EOF'
#!/bin/bash
echo "=== Always-On Transcription Service Status ==="
if launchctl list | grep -q "com.transcription.meeting-watch"; then
    echo "Status: RUNNING"
    echo "PID: $(launchctl list | grep com.transcription.meeting-watch | awk '{print $1}')"
else
    echo "Status: STOPPED"
fi

echo ""
echo "Recent log entries:"
tail -n 10 logs/meeting-watch.log 2>/dev/null || echo "No logs found"
EOF
    
    chmod +x "$PROJECT_DIR"/*.sh
}

run_tests() {
    print_step "Running system tests..."
    
    # Test Python environment
    source "$PROJECT_DIR/venv/bin/activate"
    
    print_step "Testing Python imports..."
    python3 -c "
import sys
packages = ['numpy', 'scipy', 'speech_recognition', 'requests']
for package in packages:
    try:
        __import__(package)
        print(f'✓ {package}')
    except ImportError:
        print(f'✗ {package} - not available')
"
    
    # Test audio devices
    print_step "Testing audio setup..."
    if system_profiler SPAudioDataType | grep -q "BlackHole"; then
        echo "✓ BlackHole audio device found"
    else
        echo "✗ BlackHole audio device not found"
    fi
    
    # Test Ollama
    print_step "Testing Ollama..."
    if command -v ollama &> /dev/null; then
        echo "✓ Ollama installed"
        if ollama list | grep -q "mistral"; then
            echo "✓ Mistral model available"
        else
            echo "✗ Mistral model not found (run: ollama pull mistral:7b-q4)"
        fi
    else
        echo "✗ Ollama not installed"
    fi
}

main() {
    print_header
    
    check_macos
    check_homebrew
    install_system_dependencies
    install_blackhole
    setup_python_environment
    install_ollama
    setup_permissions
    make_scripts_executable
    create_launchd_service
    create_control_scripts
    run_tests
    
    print_header
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Grant microphone and accessibility permissions when prompted"
    echo "2. Set up BlackHole 2ch aggregate audio device"
    echo "3. Start the service: ./start-service.sh"
    echo "4. Check status: ./status-service.sh"
    echo ""
    echo "Files created:"
    echo "- Configuration: config/"
    echo "- Scripts: scripts/"
    echo "- Logs: logs/"
    echo "- Recordings: recordings/"
    echo "- Notes: notes/"
    echo ""
    echo "Happy transcribing! 🎙️"
}

# Run main function
main "$@"
