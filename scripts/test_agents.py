import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

from agents.logic_aware_agent import LogicAwareAgent
from agents.baseline_agent import BaselineAgent
from env.frotz_env import create_lost_pig_env
from clients.llm_client import OpenAIClient, AnthropicClient, GeminiClient
from core.evaluation import AchievementEvaluator


def get_llm_client(llm_type: str, api_key: Optional[str] = None):
    if llm_type == "openai":
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set. Set it as env var or pass --api-key")
        return OpenAIClient(model_name="gpt-4o-mini", api_key=api_key)
    
    elif llm_type == "anthropic":
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Set it as env var or pass --api-key")
        return AnthropicClient(model_name="claude-3-5-sonnet-20241022", api_key=api_key)
    
    elif llm_type == "gemini":
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Set it as env var or pass --api-key")
        return GeminiClient(model_name="gemini-1.5-pro", api_key=api_key)
    
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}. Choose: openai, anthropic, gemini")


def main():
    parser = argparse.ArgumentParser(description="Test different agents and LLMs on Lost Pig")
    parser.add_argument("--agent", type=str, default="logic-aware", choices=["logic-aware", "baseline"],
                       help="Agent type: 'logic-aware' (with world state) or 'baseline' (simple prompts)")
    parser.add_argument("--llm", type=str, default="openai", choices=["openai", "anthropic", "gemini"],
                       help="LLM provider")
    parser.add_argument("--api-key", type=str, default=None,
                       help="API key (or set env var: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY)")
    parser.add_argument("--game-file", type=str, default=None,
                       help="Path to Lost Pig game file (.z5 or .z8)")
    parser.add_argument("--max-turns", type=int, default=50,
                       help="Maximum number of turns")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    parser.add_argument("--log-file", type=str, default=None,
                       help="Save game log to file")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed output")
    
    args = parser.parse_args()
    
    llm_client = get_llm_client(args.llm, args.api_key)
    
    try:
        env = create_lost_pig_env(game_file=args.game_file, seed=args.seed)
        print(f"✓ Loaded Lost Pig game: {env.game_file}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    if args.agent == "logic-aware":
        agent = LogicAwareAgent(llm_client, env)
        print(f"✓ Initialized LogicAwareAgent with {args.llm} LLM")
    else:
        agent = BaselineAgent(llm_client, env)
        print(f"✓ Initialized BaselineAgent with {args.llm} LLM")
    
    log_file = None
    if args.log_file:
        log_file = open(args.log_file, 'w', buffering=1)
        print(f"📝 Logging to: {args.log_file}")
    
    print(f"\n{'='*60}")
    print(f"Testing {args.agent} agent with {args.llm} LLM")
    print(f"{'='*60}\n")
    
    try:
        episode_stats = agent.run_episode(max_turns=args.max_turns, verbose=args.verbose, log_file=log_file)
        
        print(f"\n{'='*60}")
        print("📊 Episode Complete")
        print(f"{'='*60}")
        print(f"🎯 Turns: {episode_stats['turns']}")
        print(f"⭐ Final Score: {episode_stats['final_score']}")
        print(f"🐷 Pig Found: {'Yes' if episode_stats['pig_found'] else 'No'}")
        
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

