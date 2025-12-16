# Logic-Aware LLM Agents for Text Adventures

A framework for building LLM agents that maintain logical world-state consistency in text adventure games, specifically designed for **Lost Pig**.

## Overview

This project implements a **logic-aware LLM agent** that combines:
- **Symbolic world-state tracking** - Tracks locations, inventory, and game progress
- **Action generation with context** - World state provides hints about valid actions
- **ReAct-style reasoning** - Think → Act → Observe loop

The agent plays **Lost Pig**, a text adventure where you play as Grunk, an orc searching for a lost pig.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/logiplay.git
cd logiplay
```

### 2. Run Setup

```bash
./setup.sh
```

This script will:
- Check for frotz (install if needed)
- Download the Lost Pig game file
- Install Python dependencies

### 3. Set Your API Key

Set your API key as an environment variable or in `config.sh`:

```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"

# Anthropic
export ANTHROPIC_API_KEY="your-key-here"

# Gemini
export GEMINI_API_KEY="your-key-here"
```

Get API keys:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- Gemini: https://makersuite.google.com/app/apikey

### 4. Run the Agent

```bash
# Run with OpenAI (default)
./run.sh --llm openai

# Run with Anthropic
./run.sh --llm anthropic

# Run with Gemini
./run.sh --llm gemini
```

Or use the test script to compare agents:

```bash
# Test logic-aware agent
python scripts/test_agents.py --agent logic-aware --llm openai

# Test baseline agent
python scripts/test_agents.py --agent baseline --llm openai
```

## Prerequisites

- **frotz** (Z-machine interpreter)
  - macOS: `brew install frotz`
  - Linux: `sudo apt-get install frotz`
  - The setup script will install it automatically if missing
- **Python 3.8+**
- **API key** for one of: OpenAI, Anthropic, or Gemini

## Project Structure

```
logiplay/
├── agents/
│   ├── logic_aware_agent.py  # Main agent with world state tracking
│   └── baseline_agent.py      # Simple baseline agent for comparison
├── clients/
│   └── llm_client.py          # LLM client implementations (OpenAI, Anthropic, Gemini)
├── core/
│   ├── world_state.py         # World state tracking (locations, inventory, progress)
│   └── evaluation.py          # Evaluation metrics (score, progress tracking)
├── env/
│   └── frotz_env.py           # Frotz environment wrapper for Lost Pig
├── scripts/
│   ├── run_lost_pig.py        # Main script to run logic-aware agent
│   └── test_agents.py         # Script to test different agents and LLMs
├── games/
│   └── lostpig.z8             # Lost Pig game file
├── setup.sh                   # Setup script
├── run.sh                     # Run script
└── README.md                  # This file
```

## How It Works

1. **Setup** (`setup.sh`):
   - Checks/installs frotz (Z-machine interpreter)
   - Downloads Lost Pig game file (.z8)
   - Installs Python dependencies

2. **Run** (`run.sh` or `scripts/run_lost_pig.py`):
   - Initializes the Frotz environment
   - Creates a logic-aware agent with world state tracking
   - Runs the agent through the game
   - Displays results and metrics

3. **Agent**:
   - Uses world state to track locations, inventory, and progress
   - Generates actions using your chosen LLM
   - Updates world state from observations
   - Evaluates performance based on score and progress metrics

## Agents

### Logic-Aware Agent

The main agent that maintains world state:
- Tracks current location and visited locations
- Maintains inventory of collected items
- Records commands tried at each location
- Provides context to the LLM about game state

### Baseline Agent

A simplified agent for comparison:
- Only uses current observation
- No world state tracking
- Minimal prompt structure

## Evaluation Metrics

The evaluation system tracks:

1. **Game Score** - Based on "[Grunk score go up one.]" messages (max 7 points)
2. **Locations Discovered** - Number of unique locations visited
3. **Items Collected** - Number of unique items that have been in inventory

Results are displayed after each episode with:
- Final score and normalized score
- Turns taken
- Progress metrics (locations, items)
- Success status (completed within 40 turns)

## Using Different LLMs

The framework supports three LLM providers:

### OpenAI

```bash
export OPENAI_API_KEY="your-key"
./run.sh --llm openai
```

### Anthropic

```bash
export ANTHROPIC_API_KEY="your-key"
./run.sh --llm anthropic
```

### Gemini

```bash
export GEMINI_API_KEY="your-key"
./run.sh --llm gemini
```


## Architecture

The agent follows a ReAct-style loop:

1. **Observe** - Read game state from Frotz environment
2. **Think** - LLM reasons about current situation and world state
3. **Act** - LLM generates action command
4. **Update** - Update world state from observation
5. **Repeat** - Continue until game ends or max turns reached

The world state tracks:
- Current location and discovered locations
- Inventory and collected items
- Commands tried at each location
- Pig status (found/caught)

## Key Features

### 1. World State Tracking

Tracks game state including:
- Current location and location history
- Inventory and item collection history
- Commands tried at each location
- Progress metrics (locations discovered, items collected)

### 2. Multi-LLM Support

Supports multiple LLM providers:
- OpenAI
- Anthropic
- Gemini

### 3. ReAct-Style Agent Loop

Standard ReAct loop:
1. **Observe** environment text
2. **Think** (LLM reasoning about next action with world state context)
3. **Act** (generate action command)
4. **Update** world state from observation

### 4. Progress Tracking

Tracks incremental progress beyond game score:
- Locations discovered (exploration progress)
- Items collected (acquisition progress)

## Research Context

This implementation is designed for research on:
- World-state consistency in LLM agents
- Constraint-based reasoning for long-horizon tasks
- Symbolic + neural hybrid approaches
- Multi-LLM agent comparison
