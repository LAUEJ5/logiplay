# Logic-Aware LLM Agents for Text Adventures

A framework for building LLM agents that maintain logical world-state consistency in text adventure games, specifically designed for **Lost Pig**.

## Overview

This project implements a **logic-aware LLM agent** that combines:
- **Symbolic world-state tracking** (predicates: `at`, `has`, `alive`, `connected`)
- **Hard & soft constraint enforcement** (LMQL-style eager evaluation)
- **Action self-verification** (parser grammar validation)
- **Constrained decoding** (pruning invalid action space)

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

Edit `config.sh` (created automatically from template) and add your OpenAI API key:

```bash
# Edit config.sh
nano config.sh  # or use your favorite editor

# Add your key:
export OPENAI_API_KEY="your-key-here"
```

Get your OpenAI API key at: https://platform.openai.com/api-keys

**Alternative**: You can also set it via environment variable:
```bash
export OPENAI_API_KEY="your-key-here"
```

### 4. Run the Agent

```bash
./run.sh --llm openai
```

Or simply:
```bash
./run.sh
```

That's it! The agent will play Lost Pig using your API key.

## Using Different LLMs

```bash
# OpenAI (default - recommended)
export OPENAI_API_KEY="your-key"
./run.sh --llm openai
# or just: ./run.sh

# Anthropic Claude
export ANTHROPIC_API_KEY="your-key"
./run.sh --llm anthropic

# Google Gemini
export GEMINI_API_KEY="your-key"
./run.sh --llm gemini

# Mock (for testing, no API key needed)
./run.sh --llm mock
```

## Prerequisites

- **frotz** (Z-machine interpreter)
  - macOS: `brew install frotz`
  - Linux: `sudo apt-get install frotz`
  - The setup script will install it automatically if missing
- **Python 3.8+**
- **OpenAI API key** (recommended) or API key for another LLM
  - Get OpenAI key: https://platform.openai.com/api-keys

## Project Structure

```
logiplay/
├── agent.py              # Main LogicAwareAgent class
├── world_state.py        # Symbolic world state model (Lost Pig-specific)
├── constraints.py        # Constraint checker (hard & soft, Lost Pig-specific)
├── action_verifier.py    # Action structure validation
├── evaluation.py         # Evaluation metrics (Lost Pig achievements)
├── example_llm_client.py # LLM client implementations (OpenAI, Anthropic, Gemini, Mock)
├── frotz_env.py          # Frotz environment wrapper for Lost Pig
├── run_lost_pig.py       # Main script to run agent against actual Lost Pig game
├── setup.sh              # Setup script (installs frotz, downloads game, installs deps)
├── run.sh                # Run script (executes the agent)
└── README.md            # This file
```

## How It Works

1. **Setup** (`setup.sh`):
   - Checks/installs frotz (Z-machine interpreter)
   - Downloads Lost Pig game file (.z5 or .z8)
   - Installs Python dependencies

2. **Run** (`run.sh`):
   - Runs the agent directly
   - Uses system frotz to execute the game file
   - Displays results

3. **Agent**:
   - Uses symbolic world state to track game state
   - Enforces constraints on actions
   - Generates actions using your chosen LLM
   - Evaluates performance based on achievements

## Troubleshooting

**"frotz is not installed"**:
- macOS: `brew install frotz`
- Linux: `sudo apt-get install frotz`
- Or run `./setup.sh` to install automatically

**"frotz command not found"**:
- Make sure frotz is in your PATH
- Try: `which frotz` to check if it's installed
- Restart your terminal after installation

**"API key not found"**:
- Make sure you've set the environment variable: `export OPENAI_API_KEY="your-key"`
- Or edit `config.sh` and add your key there
- The key must be set before running `./run.sh`

**"Game file not found"**:
- Run `./setup.sh` again to download the game file
- Or manually download from https://ifdb.org/viewgame?id=mohwfk47yjzii14w
- Save as `games/lostpig.z5` or `games/lostpig.z8`

## Architecture

```
┌─────────────────┐
│  LLM generates  │
│ candidate action│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Action Verifier │  ← Structural validation (parser grammar)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Constraint Checker│ ← Logical validation (world state)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Valid Action    │
└─────────────────┘
```

## Key Features

### 1. Symbolic World State Model

Tracks game state using predicates:
- `at(player, location)` - Player location
- `has(player, item)` - Inventory
- `connected(loc1, loc2)` - Location connectivity

### 2. Constraint System

**Hard constraints** (must be satisfied):
- Cannot use items not in inventory
- Cannot move through nonexistent exits
- Torch must be lit for dark areas

**Soft constraints** (should be satisfied):
- Discourage repetitive actions
- Encourage coherent action sequences

### 3. Action Verification

Validates actions conform to parser grammar before symbolic checks.

### 4. ReAct-Style Agent Loop

Standard ReAct loop enhanced with constraint enforcement:
1. **Observe** environment text
2. **Think** (LLM reasoning)
3. **Act** (with constraint checking)
4. **Update** symbolic world state

## Research Context

This implementation is designed for research on:
- World-state consistency in LLM agents
- Constraint-based reasoning for long-horizon tasks
- Symbolic + neural hybrid approaches

Based on the presentation: "Logic-Aware LLM Agents for Text Adventures: Using Symbolic Constraints for World-State Consistency"

## Citation

If you use this code, please cite:

```bibtex
@article{lmql2023,
  title={Prompting Is Programming: A Query Language for Large Language Models},
  author={Beurer-Kellner, Luca and Fischer, Marc and Vechev, Martin},
  journal={arXiv preprint arXiv:2212.06094},
  year={2023}
}
```

## License

[Specify your license here]

## Contact

Jeremy Laue - [Your contact info]
