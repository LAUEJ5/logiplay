#!/bin/bash
# Simple setup script for Lost Pig Agent
# This script handles everything: frotz, game file, Python dependencies

set -e

echo "=========================================="
echo "Lost Pig Agent - Setup"
echo "=========================================="
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

# Check if frotz is installed, install if not
if ! command -v frotz > /dev/null 2>&1; then
    echo "frotz is not installed. Installing..."
    echo ""
    
    if [ "$OS" = "Linux" ]; then
        # Linux: Install frotz
        echo "Installing frotz for Linux..."
        if command -v apt-get > /dev/null 2>&1; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y frotz
        elif command -v yum > /dev/null 2>&1; then
            # RHEL/CentOS
            sudo yum install -y frotz
        else
            echo "ERROR: Unsupported Linux distribution. Please install frotz manually:"
            echo "  Debian/Ubuntu: sudo apt-get install frotz"
            echo "  RHEL/CentOS: sudo yum install frotz"
            exit 1
        fi
    elif [ "$OS" = "Darwin" ]; then
        # macOS: Install frotz via Homebrew
        echo "Installing frotz for macOS..."
        if command -v brew > /dev/null 2>&1; then
            brew install frotz
        else
            echo "ERROR: Homebrew is not installed."
            echo "Install Homebrew first: https://brew.sh"
            echo "Then run: brew install frotz"
            exit 1
        fi
    else
        echo "ERROR: Unsupported operating system: $OS"
        echo "Please install frotz manually:"
        echo "  macOS: brew install frotz"
        echo "  Linux: sudo apt-get install frotz"
        exit 1
    fi
fi

echo "✓ frotz is installed"
echo ""

# Create games directory
mkdir -p games

# Download game file if it doesn't exist
if [ ! -f "games/lostpig.z8" ] && [ ! -f "games/lostpig.z5" ]; then
    echo "Downloading Lost Pig game file..."
    curl -L -o games/lostpig.z8 "https://ifarchive.org/if-archive/games/zcode/lostpig.z8" 2>/dev/null || \
    curl -L -o games/lostpig.z5 "https://ifarchive.org/if-archive/games/zcode/lostpig.z5" 2>/dev/null || {
        echo "WARNING: Could not download game file automatically."
        echo "Please download from: https://ifdb.org/viewgame?id=mohwfk47yjzii14w"
        echo "Save as: games/lostpig.z5 or games/lostpig.z8"
    }
fi

if [ -f "games/lostpig.z8" ] || [ -f "games/lostpig.z5" ]; then
    echo "✓ Game file found"
else
    echo "✗ Game file not found - please download manually"
fi
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q openai anthropic google-generativeai || {
    echo "Installing with verbose output..."
    pip install openai anthropic google-generativeai
}

echo "✓ Python dependencies installed"
echo ""

# Create config.sh from example if it doesn't exist
if [ ! -f config.sh ] && [ -f config.sh.example ]; then
    cp config.sh.example config.sh
    echo "✓ Created config.sh from template"
    echo "  Edit config.sh to add your API keys"
    echo ""
fi

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Set your API key in config.sh:"
echo "     Edit config.sh and add your OPENAI_API_KEY"
echo "     (Get key at: https://platform.openai.com/api-keys)"
echo ""
echo "  2. Run the agent:"
echo "     ./run.sh --llm openai"
echo ""
echo "Or use other LLMs (add keys to config.sh):"
echo "  ./run.sh --llm anthropic  # Claude"
echo "  ./run.sh --llm gemini     # Gemini"
echo "  ./run.sh --llm mock       # Mock (no API key needed)"
echo ""
echo "Note: You can also set API keys via environment variables:"
echo "  export OPENAI_API_KEY='your-key' && ./run.sh --llm openai"
echo ""
