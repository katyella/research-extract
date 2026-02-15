#!/bin/bash
# Setup script for research-extract skill
# Run this once to install dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Setting up research-extract skill..."
echo ""

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install dependencies
echo "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo ""

# Check system dependencies
MISSING=""

if ! command -v yt-dlp &> /dev/null; then
    MISSING="$MISSING\n  - yt-dlp: brew install yt-dlp (macOS) or pip install yt-dlp"
fi

if ! command -v pdftotext &> /dev/null; then
    echo "Optional: pdftotext not found (needed for PDF ingestion)"
    echo "  Install with: brew install poppler (macOS) or apt install poppler-utils (Linux)"
    echo ""
fi

if ! command -v whisper &> /dev/null; then
    echo "Optional: whisper not found (needed for audio transcription when captions unavailable)"
    echo "  Install with: pip install openai-whisper"
    echo ""
fi

if [ -n "$MISSING" ]; then
    echo "Required dependencies missing:"
    echo -e "$MISSING"
    echo ""
    echo "Install them and re-run this script."
    exit 1
fi

echo "Setup complete!"
echo ""
echo "The skill is ready to use with /research-extract"
