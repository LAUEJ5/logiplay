import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

from typing import List, Optional, Dict, Tuple
from clients.llm_client import LLMClient


class BaselineAgent:
    def __init__(self, llm_client: LLMClient, game_env=None):
        self.llm = llm_client
        self.env = game_env
    
    def act(self, observation: str) -> str:
        prompt = f"""{observation}

What do you do?"""

        action = self.llm.generate(prompt, max_tokens=50, temperature=0.3)
        action = action.strip().strip('"').strip("'")
        
        if not action or action.strip() == "":
            action = "look"
        
        return action
    
    def step(self, observation: str) -> str:
        return self.act(observation)
    
    def run_episode(self, max_turns: int = 40, verbose: bool = False, log_file=None) -> Dict:
        if not self.env:
            raise ValueError("No environment provided")
        
        def output(text, end='\n'):
            print(text, end=end, flush=True)
            if log_file:
                print(text, end=end, file=log_file, flush=True)
        
        observation = self.env.reset()
        if verbose:
            output("🎮 Initial Game State:")
            output(observation.strip())
            output("\n" + "-" * 60)
        
        episode_stats = {
            "turns": 0,
            "actions": [],
            "observations": [],
            "final_score": 0,
            "pig_found": False
        }
        
        for turn in range(max_turns):
            if verbose:
                output(f"\n📊 Turn {turn + 1}/{max_turns}")
                output(f"📍 Observation:")
                output(observation.strip())
            
            action = self.step(observation)
            
            if verbose:
                output(f"⚡ Action: {action}")
            
            try:
                next_obs, reward, done, info = self.env.step(action)
                if not next_obs or next_obs.strip() == "":
                    if verbose:
                        output("⚠️  Warning: No response from game. Continuing...")
                    next_obs = "No response from game. Continuing..."
                    
            except Exception as e:
                if verbose:
                    output(f"⚠️  Error executing action: {e}")
                next_obs = f"Error: {str(e)[:100]}"
                reward = 0.0
                done = False
                info = {"turn": turn + 1, "score": 0, "max_score": 0}
            
            if verbose:
                if reward > 0:
                    output(f"✨ Reward: +{reward}")
                if "score" in info:
                    output(f"📈 Score: {info['score']}")
                output(f"📝 Response:")
                clean_obs = next_obs.strip()
                lines = clean_obs.split('\n')
                filtered_lines = []
                for line in lines:
                    if line.strip().startswith('>') and len(line.strip()) > 1:
                        stripped = line.strip()[1:].strip()
                        if stripped and not any(c in stripped for c in ['(', '[', ']']):
                            continue
                    filtered_lines.append(line)
                clean_obs = '\n'.join(filtered_lines)
                output(clean_obs)
            
            episode_stats["turns"] = turn + 1
            episode_stats["actions"].append(action)
            episode_stats["observations"].append(next_obs)
            
            if "pig" in next_obs.lower() and any(word in next_obs.lower() for word in ["catch", "grab", "hold", "carrying"]):
                episode_stats["pig_found"] = True
            
            if "score" in info:
                episode_stats["final_score"] = info["score"]
            
            if done:
                if verbose:
                    output(f"\n🏁 Game Over!")
                break
            
            if verbose:
                output("-" * 60)
            
            observation = next_obs
        
        return episode_stats

