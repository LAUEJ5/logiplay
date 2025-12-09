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

# Parse arguments
LLM=${1:-openai}
if [ "$1" = "--llm" ] || [ "$1" = "-l" ]; then
    LLM=${2:-openai}
    shift 2
fi

# Check for API key based on LLM choice
case $LLM in
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "ERROR: OPENAI_API_KEY not set"
            echo "Set it in config.sh or: export OPENAI_API_KEY='your-key'"
            echo "Get your key at: https://platform.openai.com/api-keys"
            exit 1
        fi
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "ERROR: ANTHROPIC_API_KEY not set"
            echo "Set it in config.sh or: export ANTHROPIC_API_KEY='your-key'"
            exit 1
        fi
        ;;
    gemini)
        if [ -z "$GEMINI_API_KEY" ]; then
            echo "ERROR: GEMINI_API_KEY not set"
            echo "Set it in config.sh or: export GEMINI_API_KEY='your-key'"
            echo "Get your key at: https://aistudio.google.com/app/u/1/apikey"
            exit 1
        fi
        ;;
    mock)
        echo "Using mock LLM (no API key needed)"
        ;;
    *)
        echo "ERROR: Unknown LLM: $LLM"
        echo "Choose: openai, anthropic, gemini, or mock"
        exit 1
        ;;
esac

# Check if game file exists
if [ ! -f "games/lostpig.z5" ] && [ ! -f "games/lostpig.z8" ]; then
    echo "ERROR: Game file not found in games/ directory"
    echo "Run ./setup.sh to download it automatically"
    exit 1
fi

# Run the agent
python run_lost_pig.py --llm "$LLM" "$@"

