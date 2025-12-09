"""
Run Logic-Aware Agent on Actual Lost Pig Game

This script runs the logic-aware agent against the actual Lost Pig game
using frotz. Make sure you have:
1. Installed frotz: brew install frotz (macOS) or sudo apt-get install frotz (Linux)
2. Downloaded Lost Pig game file (lostpig.z5 or lostpig.z8)
3. Placed it in games/ directory

Or just run: ./setup.sh to set everything up automatically.

Usage:
    python run_lost_pig.py [--game-file PATH] [--llm openai|anthropic|gemini|mock] [--max-turns N]
"""

import argparse
import os
import sys
from typing import Optional

from agent import LogicAwareAgent
from frotz_env import create_lost_pig_env, FROTZ_AVAILABLE
from example_llm_client import MockLLMClient, OpenAIClient, AnthropicClient, GeminiClient
from evaluation import AchievementEvaluator


def main():
    parser = argparse.ArgumentParser(
        description="Run logic-aware agent on Lost Pig game"
    )
    parser.add_argument(
        "--game-file",
        type=str,
        default=None,
        help="Path to Lost Pig game file (.z5 or .z8). Auto-detects if not provided."
    )
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "anthropic", "gemini", "mock"],
        default="openai",
        help="LLM client to use (default: openai)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM (or set OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=40,
        help="Maximum number of turns (default: 40)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for game (default: 42)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output"
    )
    
    args = parser.parse_args()
    
    # Check Frotz availability
    if not FROTZ_AVAILABLE:
        print("ERROR: frotz is not installed.")
        print("Install with:")
        print("  macOS: brew install frotz")
        print("  Linux: sudo apt-get install frotz")
        sys.exit(1)
    
    # Initialize LLM client
    if args.llm == "openai":
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
            sys.exit(1)
        llm_client = OpenAIClient(api_key=api_key)
    elif args.llm == "anthropic":
        api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: Anthropic API key required. Set ANTHROPIC_API_KEY env var or use --api-key")
            sys.exit(1)
        llm_client = AnthropicClient(api_key=api_key)
    elif args.llm == "gemini":
        api_key = args.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: Gemini API key required. Set GEMINI_API_KEY env var or use --api-key")
            print("Get your key at: https://aistudio.google.com/app/u/1/apikey")
            sys.exit(1)
        llm_client = GeminiClient(api_key=api_key)
    else:
        print("Using MockLLMClient (for testing)")
        llm_client = MockLLMClient()
    
    # Create environment
    try:
        env = create_lost_pig_env(game_file=args.game_file, seed=args.seed)
        print(f"✓ Loaded Lost Pig game: {env.game_file}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nTo get Lost Pig:")
        print("1. Visit https://ifdb.org/viewgame?id=mohwfk47yjzii14w")
        print("2. Download the game file (.z5 or .z8)")
        print("3. Save as 'games/lostpig.z5' or 'games/lostpig.z8'")
        sys.exit(1)
    
    # Create agent
    agent = LogicAwareAgent(llm_client, env)
    print(f"✓ Initialized agent with {args.llm} LLM")
    
    # Run episode
    print(f"\n{'='*60}")
    print("Starting Lost Pig Episode")
    print(f"{'='*60}\n")
    
    try:
        episode_stats = agent.run_episode(max_turns=args.max_turns)
        
        # Print results
        print(f"\n{'='*60}")
        print("Episode Complete")
        print(f"{'='*60}")
        print(f"Turns: {episode_stats['turns']}")
        print(f"Final Score: {episode_stats['final_score']}")
        print(f"Pig Found: {episode_stats['pig_found']}")
        
        if args.verbose:
            print(f"\nActions taken ({len(episode_stats['actions'])}):")
            for i, (thought, action) in enumerate(zip(episode_stats['thoughts'], episode_stats['actions']), 1):
                print(f"  {i}. {action}")
                if args.verbose:
                    print(f"     Thought: {thought[:100]}...")
        
        # Evaluate achievements
        evaluator = AchievementEvaluator()
        results = evaluator.evaluate(agent, episode_stats)
        print(f"\nAchievements: {results['score']}/{results['max_score']} points")
        print(f"Completed: {len(results['achieved'])}/{len(results['all_achievements'])} achievements")
        
        if results['achieved']:
            print("\nAchieved:")
            for achievement in results['achieved']:
                print(f"  ✓ {achievement}")
        
        if results['missing']:
            print("\nMissing:")
            for achievement in results['missing']:
                print(f"  ✗ {achievement}")
        
    except KeyboardInterrupt:
        print("\n\nEpisode interrupted by user")
    except Exception as e:
        print(f"\nERROR during episode: {e}")
        import traceback
        traceback.print_exc()
    finally:
        env.close()


if __name__ == "__main__":
    main()

