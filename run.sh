#!/bin/bash
# Simple run script for Lost Pig Agent

set -e

# Add Homebrew paths to PATH (for macOS)
if [ -d "/opt/homebrew/bin" ]; then
    export PATH="/opt/homebrew/bin:$PATH"
fi
if [ -d "/usr/local/bin" ]; then
    export PATH="/usr/local/bin:$PATH"
fi

# Load API keys from config.sh file if it exists
if [ -f config.sh ]; then
    source config.sh
elif [ -f .env ]; then
    # Fallback: try .env file (simple key=value format)
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# Check if frotz is installed
if ! command -v frotz > /dev/null 2>&1; then
    echo "ERROR: frotz is not installed."
    echo "Install with:"
    echo "  macOS: brew install frotz"
    echo "  Linux: sudo apt-get install frotz"
    echo ""
    echo "Or run ./setup.sh to install it automatically"
    exit 1
fi

# Check if game file exists
if [ ! -f "games/lostpig.z5" ] && [ ! -f "games/lostpig.z8" ]; then
    echo "Game file not found. Running setup..."
    ./setup.sh
    echo ""
fi

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not set"
    echo "Set it in config.sh or: export OPENAI_API_KEY='your-key'"
    echo "Get your key at: https://platform.openai.com/api-keys"
    exit 1
fi

# Check if game file exists
if [ ! -f "games/lostpig.z5" ] && [ ! -f "games/lostpig.z8" ]; then
    echo "ERROR: Game file not found in games/ directory"
    echo "Run ./setup.sh to download it automatically"
    exit 1
fi

# Run the agent with unbuffered output
python -u scripts/run_lost_pig.py "$@"

