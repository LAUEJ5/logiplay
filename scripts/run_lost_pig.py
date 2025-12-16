import argparse
import os
import sys
from typing import Optional

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.logic_aware_agent import LogicAwareAgent
from env.frotz_env import create_lost_pig_env, FROTZ_AVAILABLE
from clients.llm_client import OpenAIClient
from core.evaluation import AchievementEvaluator


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
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=50,
        help="Maximum number of turns (default: 10)"
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
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Save output to log file (in addition to terminal)"
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
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
        sys.exit(1)
    llm_client = OpenAIClient(model_name="gpt-4o-mini", api_key=api_key)
    
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
    print(f"✓ Initialized agent with OpenAI LLM", flush=True)
    
    # Set up logging if requested
    log_file = None
    if args.log_file:
        log_file = open(args.log_file, 'w', buffering=1)
        print(f"📝 Logging to: {args.log_file}", flush=True)
    
    # Run episode
    print(f"\n{'='*60}", flush=True)
    print("Starting Lost Pig Episode", flush=True)
    print(f"{'='*60}\n", flush=True)
    
    try:
        episode_stats = agent.run_episode(max_turns=args.max_turns, verbose=True, log_file=log_file)
        
        # Print results
        print(f"\n{'='*60}", flush=True)
        print("📊 Episode Complete", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"🎯 Turns: {episode_stats['turns']}", flush=True)
        print(f"⭐ Final Score: {episode_stats['final_score']}", flush=True)
        print(f"🐷 Pig Found: {'Yes' if episode_stats['pig_found'] else 'No'}", flush=True)
        
        if args.verbose:
            print(f"\nActions taken ({len(episode_stats['actions'])}):")
            for i, (thought, action) in enumerate(zip(episode_stats['thoughts'], episode_stats['actions']), 1):
                print(f"  {i}. {action}")
                if args.verbose:
                    print(f"     Thought: {thought[:100]}...")
        
        # Evaluate score
        evaluator = AchievementEvaluator()
        results = evaluator.evaluate(episode_stats)
        print(f"\nScore: {results['game_score']}/{results['max_score']} points")
        print(f"Normalized score: {results['normalized_score']:.2f}")
        print(f"Turns taken: {results['turns_taken']}/40")
        print(f"\nProgress Metrics:")
        print(f"  Locations discovered: {results.get('locations_discovered', 0)}")
        print(f"  Items collected: {results.get('items_collected', 0)}")
        
        if results['success']:
            print("\n🎉 SUCCESS: Completed the game within 40 turns!")
        else:
            print("\n❌ Did not complete the game within 40 turns")
        
    except KeyboardInterrupt:
        print("\n\nEpisode interrupted by user", flush=True)
    except Exception as e:
        print(f"\nERROR during episode: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if log_file:
            log_file.close()
            print(f"\n✓ Log saved to: {args.log_file}", flush=True)
        env.close()


if __name__ == "__main__":
    main()

