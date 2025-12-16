import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

from typing import List, Optional, Dict, Tuple
from core.world_state import WorldState


class LogicAwareAgent:
    def __init__(self, llm_client, game_env=None):
        self.llm = llm_client
        self.env = game_env
        self.world_state = WorldState()
        self.observation_history: List[str] = []
        self.action_history: List[str] = []
        self.thought_history: List[str] = []
    
    def think(self, observation: str) -> str:
        context = self._build_context()
        
        prompt = f"""You are Grunk, an orc searching for a lost pig in Lost Pig text adventure game.

{context}

Current observation:
{observation}

Think about what to do next. Provide a brief thought about your next action."""

        thought = self.llm.generate(prompt, max_tokens=100, temperature=0.7)
        self.thought_history.append(thought)
        return thought
    
    def _analyze_observation(self, observation: str) -> str:
        return ""
    
    def _get_action_diversity_hint(self) -> str:
        return ""
    
    def act(self, observation: str, thought: str) -> str:
        context = self._build_context()
        recent_actions = ", ".join(self.action_history[-5:]) if self.action_history else "none"
        
        commands_tried_here = self.world_state.get_commands_tried_at_location()
        tried_commands_hint = ""
        if commands_tried_here:
            tried_list = sorted(list(commands_tried_here)[:8])
            tried_commands_hint = f"\n⚠️ WARNING: Commands already tried at this location: {', '.join(tried_list)}\nTry to avoid repeating these unless you have a good reason. Consider trying something different.\n"
        
        is_stuck = False
        if len(self.action_history) >= 3:
            last_three = self.action_history[-3:]
            if len(set(last_three)) <= 2:
                is_stuck = True
        
        obs_hints = self._analyze_observation(observation)
        diversity_hint = self._get_action_diversity_hint()
        
        stuck_warning = ""
        if is_stuck:
            stuck_warning = "\n⚠️ WARNING: You're repeating actions! Try something completely different.\n"
        
        contextual_hints = ""
        if obs_hints or diversity_hint:
            contextual_hints = "\n💡 HINTS FROM OBSERVATION:\n"
            if obs_hints:
                contextual_hints += obs_hints + "\n"
            if diversity_hint:
                contextual_hints += diversity_hint + "\n"
        
        prompt = f"""You are Grunk, an orc playing Lost Pig text adventure.

{context}

Current observation:
{observation}

Your thought:
{thought}
{stuck_warning}
{tried_commands_hint}
{contextual_hints}

Use simple text adventure commands. Only interact with items/objects that are explicitly mentioned in the observation.

Recent actions: {recent_actions if recent_actions != "none" else "none yet"}
{tried_commands_hint}

Generate a single action command."""

        candidate_action = self.llm.generate(prompt, max_tokens=50, temperature=0.3)
        candidate_action = candidate_action.strip().strip('"').strip("'")
        
        if not candidate_action or candidate_action.strip() == "":
            candidate_action = "look"
        
        action_lower = candidate_action.lower()
        
        if "go " in action_lower or "move " in action_lower:
            parts = action_lower.split()
            if len(parts) >= 2:
                direction_words = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest", "ne", "nw", "se", "sw", "n", "s", "e", "w"]
                for word in reversed(parts):
                    if word in direction_words:
                        candidate_action = word
                        break
                    elif word in ["n", "s", "e", "w"]:
                        dir_map = {"n": "north", "s": "south", "e": "east", "w": "west"}
                        candidate_action = dir_map[word]
                        break
        
        direction_map = {
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
            "n": "north", "s": "south", "e": "east", "w": "west"
        }
        if candidate_action.lower() in direction_map:
            candidate_action = direction_map[candidate_action.lower()]
        
        if "_" in candidate_action:
            parts = candidate_action.split("_")
            direction_words = ["north", "south", "east", "west", "up", "down"]
            for part in parts:
                if part in direction_words:
                    candidate_action = part
                    break
        
        return candidate_action
    
    def _build_context(self) -> str:
        lines = []
        lines.append("=== WORLD STATE ===")
        lines.append(self.world_state.get_summary())
        
        if self.world_state.current_location:
            loc_context = self.world_state.get_location_context()
            if loc_context:
                lines.append(f"\n=== {self.world_state.current_location.upper()} CONTEXT ===")
                lines.append(loc_context)
        
        if self.observation_history:
            lines.append("\n=== RECENT OBSERVATIONS ===")
            lines.extend(self.observation_history[-3:])
        
        if self.action_history:
            lines.append("\n=== RECENT ACTIONS ===")
            lines.extend(self.action_history[-3:])
        
        return "\n".join(lines) if lines else ""
    
    def step(self, observation: str) -> Tuple[str, str]:
        if self.action_history:
            self.world_state.update_from_observation(observation, self.action_history[-1])
        else:
            self.world_state.update_from_observation(observation, "")
        
        thought = self.think(observation)
        action = self.act(observation, thought)
        
        self.observation_history.append(observation)
        self.action_history.append(action)
        
        return thought, action
    
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
            "thoughts": [],
            "observations": [],
            "final_score": 0,
            "pig_found": False,
            "locations_discovered": 0,
            "items_collected": 0
        }
        
        for turn in range(max_turns):
            if verbose:
                output(f"\n📊 Turn {turn + 1}/{max_turns}")
                output(f"📍 Observation:")
                output(observation.strip())
            
            if verbose:
                output("🤔 Thinking...")
            thought, action = self.step(observation)
            
            if verbose:
                output(f"💭 Thought: {thought}")
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
                    import traceback
                    output(f"Traceback: {traceback.format_exc()}")
                next_obs = f"Error: {str(e)[:100]}"
                reward = 0.0
                done = False
                info = {"turn": turn + 1, "score": self.world_state.turn, "max_score": 0}
            
            self.world_state.update_from_observation(next_obs, action)
            
            if turn > 2 and len(self.action_history) >= 3:
                last_three = self.action_history[-3:]
                if len(set(last_three)) <= 2:
                    if verbose:
                        output(f"⚠️  Warning: Repeating actions - might be stuck! Last 3: {last_three}")
                if any(phrase in next_obs.lower() for phrase in ["not see that", "not know where", "can't", "cannot", "not allowed"]):
                    if verbose:
                        output(f"⚠️  Warning: Last command may have been invalid - game said: '{next_obs[:80]}...'")
            
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
            episode_stats["thoughts"].append(thought)
            episode_stats["observations"].append(next_obs)
            episode_stats["pig_found"] = self.world_state.pig_found
            
            progress_metrics = self.world_state.get_progress_metrics()
            episode_stats["locations_discovered"] = progress_metrics["locations_discovered"]
            episode_stats["items_collected"] = progress_metrics["items_collected"]
            
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

