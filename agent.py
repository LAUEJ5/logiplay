"""
Logic-Aware Agent for Lost Pig

Logic-aware agent configured specifically for Lost Pig game.
"""

import sys
# Force unbuffered output for real-time display
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

from typing import List, Optional, Dict, Tuple, Protocol
from world_state import WorldState


class LLMClient(Protocol):
    """Abstract LLM client interface."""
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        """Generate text from prompt."""
        ...
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[List[str]] = None,
                                 invalid_actions: Optional[List[str]] = None) -> str:
        """Generate action with constraint guidance."""
        ...


class LogicAwareAgent:
    """
    Logic-aware agent for Lost Pig game.
    
    Uses Lost Pig-specific world state and constraints.
    """
    
    def __init__(self, llm_client: LLMClient, game_env=None):
        # Store LLM and environment
        self.llm = llm_client
        self.env = game_env
        
        # World state tracking
        self.world_state = WorldState()
        
        # ReAct memory
        self.observation_history: List[str] = []
        self.action_history: List[str] = []
        self.thought_history: List[str] = []
    
    def think(self, observation: str) -> str:
        """
        ReAct-style thinking for Lost Pig.
        
        Focuses on finding the lost pig.
        """
        context = self._build_context()
        
        prompt = f"""You are Grunk, an orc searching for a lost pig in Lost Pig text adventure game.

{context}

Current observation:
{observation}

Think about what to do next. Consider:
1. Your goal: Find and catch the lost pig
2. Read the observation CAREFULLY - what does it ACTUALLY say? Look for:
   - Sounds or noises mentioned → you should listen
   - Items ACTUALLY mentioned in the text → you can examine them (ONLY if they're mentioned!)
   - People/NPCs mentioned → you should interact with them
   - Directions mentioned (north, south, east, west, forest, field, etc.) → you can go there
   - Problems mentioned (dark, locked, can't reach) → think about solutions
3. CRITICAL: Only examine, take, or interact with things that are EXPLICITLY mentioned in the observation text. Do NOT invent items or objects that aren't there!
4. What actions have you tried recently? Avoid repeating the same actions.
5. If the observation mentions sounds or that it's dark, "listen" is often a good first action.
6. If you see directions mentioned (forest, field, etc.), you can try moving in those directions.

Provide a brief thought (1-2 sentences) about your next action. Base it ONLY on what's actually in the observation."""

        thought = self.llm.generate(prompt, max_tokens=100, temperature=0.7)
        self.thought_history.append(thought)
        return thought
    
    def _analyze_observation(self, observation: str) -> str:
        """
        Analyze observation to suggest relevant action types based on content.
        This encourages discovery without hardcoding solutions.
        """
        obs_lower = observation.lower()
        hints = []
        
        # Sound/noise clues → suggest listen
        if any(word in obs_lower for word in ["hear", "noise", "sound", "squeal", "gurgle", "snore", "strange noise"]):
            if "listen" not in [a.lower() for a in self.action_history[-5:]]:
                hints.append("The observation mentions sounds or noises - try 'listen' to hear what's making them")
        
        # Dark/difficulty seeing → suggest light source or examine
        if any(word in obs_lower for word in ["dark", "not see", "too dark", "can't see", "black"]):
            hints.append("It's dark - you might need light or to examine things more carefully")
        
        # Items mentioned → suggest examining them
        items_mentioned = []
        for item in ["pole", "torch", "key", "chest", "box", "fountain", "statue", "chair", "curtain", "picture", "wall", "shelf", "book", "bench", "stream", "crack", "hat", "whistle"]:
            if item in obs_lower:
                # Check if we've examined this item recently
                recent_examines = [a for a in self.action_history[-5:] if ("examine" in a.lower() or "x " in a.lower()) and item in a.lower()]
                if not recent_examines:
                    items_mentioned.append(item)
        if items_mentioned:
            hints.append(f"Items mentioned: {', '.join(items_mentioned[:2])} - try 'examine {items_mentioned[0]}' to learn more")
        
        # NPCs present → suggest interaction
        if any(word in obs_lower for word in ["gnome", "person", "little man", "someone"]):
            recent_interactions = [a for a in self.action_history[-5:] if "ask" in a.lower() or "tell" in a.lower() or "give" in a.lower()]
            if len(recent_interactions) < 2:
                hints.append("There's someone here - try 'ask [person] about [topic]' or 'tell [person] about [thing]' to get help")
        
        # Pig present but can't catch → suggest distraction or items
        if "pig" in obs_lower and any(word in obs_lower for word in ["run", "away", "quick", "fast"]):
            if "brick" not in obs_lower:
                hints.append("The pig is quick - you might need something to distract it")
        
        # Locked/closed things → suggest keys or examining
        if any(word in obs_lower for word in ["locked", "closed", "keyhole", "need key"]):
            hints.append("Something is locked - look for a key or examine the lock")
        
        # Water mentioned → suggest collecting or using it
        if "water" in obs_lower and ("stream" in obs_lower or "fountain" in obs_lower):
            if "hat" in obs_lower or any(item in obs_lower for item in ["container", "bowl", "bucket"]):
                hints.append("Water is available - you might need a container to collect it")
        
        # Powder/dehydrated fire mentioned → suggest combining with water
        if any(word in obs_lower for word in ["powder", "black powder", "dehydrated"]) and "water" in " ".join(self.observation_history[-3:]):
            hints.append("You have both powder and water - try combining them")
        
        # Statue pointing → suggest examining what it points at
        if "statue" in obs_lower and any(word in obs_lower for word in ["point", "pointing", "hand point"]):
            hints.append("The statue is pointing somewhere - examine what it's pointing at")
        
        return "\n".join(hints) if hints else ""
    
    def _get_action_diversity_hint(self) -> str:
        """Encourage trying different action types if we've been too focused on one type."""
        if len(self.action_history) < 5:
            return ""
        
        # Count action types
        action_types = {}
        for action in self.action_history[-10:]:
            action_lower = action.lower()
            if any(d in action_lower for d in ["north", "south", "east", "west", "up", "down", "ne", "nw", "se", "sw"]):
                action_types["movement"] = action_types.get("movement", 0) + 1
            elif any(v in action_lower for v in ["take", "get", "pick", "grab"]):
                action_types["take"] = action_types.get("take", 0) + 1
            elif "examine" in action_lower or "x " in action_lower or "look" in action_lower:
                action_types["examine"] = action_types.get("examine", 0) + 1
            elif "listen" in action_lower:
                action_types["listen"] = action_types.get("listen", 0) + 1
            elif "ask" in action_lower or "tell" in action_lower:
                action_types["interact"] = action_types.get("interact", 0) + 1
        
        # If mostly movement, suggest other actions
        if action_types.get("movement", 0) >= 5 and len(action_types) <= 2:
            missing = []
            if "listen" not in action_types:
                missing.append("'listen'")
            if "examine" not in action_types:
                missing.append("'examine'")
            if "interact" not in action_types:
                missing.append("asking/telling NPCs")
            if missing:
                return f"You've been mostly moving around. Try {', '.join(missing)} to discover more."
        
        return ""
    
    def act(self, observation: str, thought: str) -> str:
        """
        Generate action with Lost Pig-specific constraints.
        """
        context = self._build_context()
        
        # Get recent actions to prevent repetition
        recent_actions = ", ".join(self.action_history[-5:]) if self.action_history else "none"
        
        # Get commands already tried at current location
        commands_tried_here = self.world_state.get_commands_tried_at_location()
        tried_commands_hint = ""
        if commands_tried_here:
            tried_commands_hint = f"\n⚠️ Commands already tried at this location: {', '.join(sorted(list(commands_tried_here)[:6]))}\nAvoid repeating these unless necessary.\n"
        
        # Check if we're stuck (repeating actions or getting same responses)
        is_stuck = False
        if len(self.action_history) >= 3:
            last_three = self.action_history[-3:]
            if len(set(last_three)) <= 2:  # Mostly repeating
                is_stuck = True
        
        # Analyze observation for hints
        obs_hints = self._analyze_observation(observation)
        diversity_hint = self._get_action_diversity_hint()
        
        stuck_warning = ""
        if is_stuck:
            stuck_warning = "\n⚠️ WARNING: You're repeating actions! Try something completely different.\n"
        
        # Combine hints
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

CRITICAL: Use simple, standard text adventure commands:
- Directions: "north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest" (just the direction word)
- Actions: "look", "listen", "examine thing", "take item", "drop item", "use item", "open door", "give item to person"
- DO NOT use: "go forest east", "go farm_south", "go field west" - these are invalid!
- DO NOT repeat actions you just tried if they didn't work or led to the same place

CRITICAL RULES - READ CAREFULLY:
- ONLY examine, take, or interact with items/objects that are EXPLICITLY mentioned in the observation text
- Do NOT invent or assume items exist that aren't mentioned (e.g., don't examine "hat" if no hat is mentioned)
- If the observation mentions sounds/noise → try "listen" (this often reveals important clues!)
- If it mentions specific items → try "examine [item]" or "x [item]" to learn more (ONLY if the item is actually mentioned)
- If it mentions directions (north, south, east, west, forest, field, etc.) → you can move in those directions
- If it mentions people/NPCs → try "ask [person] about [topic]" or "tell [person] about [thing]"
- If something is locked → look for keys or examine the lock
- If you see a statue pointing → examine what it's pointing at
- If you're stuck → try different action types, not just movement
- Remember: text adventures reward exploration, but only of things that actually exist!

Recent actions you've tried: {recent_actions if recent_actions != "none" else "none yet"}

IMPORTANT: Avoid repeating commands you've already tried at this location unless you have a good reason.
{tried_commands_hint}

Generate a single action command. Keep it short and direct (1-3 words, like "north", "listen", "examine pole", or "take torch")."""

        # Generate candidate action with retry logic to prevent repeats
        max_retries = 3
        candidate_action = None
        
        for attempt in range(max_retries):
            # Generate candidate action
            candidate_action = self.llm.generate(prompt, max_tokens=50, temperature=0.3)
            
            # Clean up action
            candidate_action = candidate_action.strip().strip('"').strip("'")
            
            # Check for hallucinated items (common ones that don't exist)
            hallucinated_items = ["hat", "cap", "helmet", "sword", "knife", "key", "door", "chest", "box"]
            action_lower = candidate_action.lower()
            for item in hallucinated_items:
                if f"examine {item}" in action_lower or f"x {item}" in action_lower or action_lower == f"examine{item}":
                    # Block hallucinated item
                    if attempt < max_retries - 1:
                        prompt += f"\n\n⚠️ BLOCKED: You tried '{candidate_action}' but '{item}' is not mentioned in the observation. Generate a DIFFERENT action that uses items/objects actually mentioned in the observation."
                        continue
                    else:
                        # Last attempt failed, fall back to "look"
                        candidate_action = "look"
                        break
            
            # Check if we should avoid this command (already tried at this location)
            if self.world_state.should_avoid_command(candidate_action):
                # Block ALL repeated commands (including movement) if they've been tried
                if attempt < max_retries - 1:
                    tried_here = self.world_state.get_commands_tried_at_location()
                    tried_list = sorted(list(tried_here)[:8])
                    prompt += f"\n\n⚠️ BLOCKED: You tried '{candidate_action}' but this command was already tried at this location. Commands already tried here: {', '.join(tried_list)}. Generate a COMPLETELY DIFFERENT action that hasn't been tried here yet."
                    continue
                else:
                    # Last attempt failed, try "look" as fallback
                    candidate_action = "look"
                    break
            
            # If we get here, action is valid
            break
        
        # Safety check: ensure we have a valid action
        if not candidate_action or candidate_action.strip() == "":
            candidate_action = "look"
        
        # Fix common command issues
        action_lower = candidate_action.lower()
        
        # Fix compound direction commands
        if "go " in action_lower:
            # Extract just the direction part
            parts = action_lower.split()
            if len(parts) >= 2:
                # "go forest east" -> "east", "go farm south" -> "south"
                direction_words = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest", "ne", "nw", "se", "sw", "n", "s", "e", "w"]
                for word in reversed(parts):  # Check from end
                    if word in direction_words:
                        candidate_action = word
                        break
                    elif word in ["n", "s", "e", "w"]:
                        # Expand abbreviations
                        dir_map = {"n": "north", "s": "south", "e": "east", "w": "west"}
                        candidate_action = dir_map[word]
                        break
        
        # Normalize compound directions
        direction_map = {
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
            "n": "north", "s": "south", "e": "east", "w": "west"
        }
        if candidate_action.lower() in direction_map:
            candidate_action = direction_map[candidate_action.lower()]
        
        # Remove underscores from directions (e.g., "farm_south" -> "south")
        if "_" in candidate_action:
            parts = candidate_action.split("_")
            direction_words = ["north", "south", "east", "west", "up", "down"]
            for part in parts:
                if part in direction_words:
                    candidate_action = part
                    break
        
        return candidate_action
    
    def _build_context(self) -> str:
        """Build context from world state and recent observations/actions."""
        lines = []
        
        # World state summary
        lines.append("=== WORLD STATE ===")
        lines.append(self.world_state.get_summary())
        
        # Location-specific context
        if self.world_state.current_location:
            loc_context = self.world_state.get_location_context()
            if loc_context:
                lines.append(f"\n=== {self.world_state.current_location.upper()} CONTEXT ===")
                lines.append(loc_context)
        
        # Recent observations
        if self.observation_history:
            lines.append("\n=== RECENT OBSERVATIONS ===")
            lines.extend(self.observation_history[-3:])
        
        # Recent actions
        if self.action_history:
            lines.append("\n=== RECENT ACTIONS ===")
            lines.extend(self.action_history[-3:])
        
        return "\n".join(lines) if lines else ""
    
    def step(self, observation: str) -> Tuple[str, str]:
        """Single ReAct step: Think then Act."""
        # Update world state from current observation and last action (if any)
        if self.action_history:
            # We have a previous action, update world state
            self.world_state.update_from_observation(observation, self.action_history[-1])
        else:
            # First step - just update location from initial observation
            self.world_state.update_from_observation(observation, "")
        
        thought = self.think(observation)
        action = self.act(observation, thought)
        
        self.observation_history.append(observation)
        self.action_history.append(action)
        
        return thought, action
    
    
    def run_episode(self, max_turns: int = 40, verbose: bool = False, log_file=None) -> Dict:
        """
        Run a complete Lost Pig episode.
        
        Args:
            max_turns: Maximum number of turns
            verbose: If True, print real-time output
        
        Returns:
            Dictionary with episode statistics
        """
        if not self.env:
            raise ValueError("No environment provided")
        
        def output(text, end='\n'):
            """Output to both terminal and log file."""
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
            "pig_found": False
        }
        
        for turn in range(max_turns):
            if verbose:
                output(f"\n📊 Turn {turn + 1}/{max_turns}")
                output(f"📍 Observation:")
                output(observation.strip())
            
            # Think
            if verbose:
                output("🤔 Thinking...")
            thought, action = self.step(observation)
            
            if verbose:
                output(f"💭 Thought: {thought}")
                output(f"⚡ Action: {action}")
            
            # Execute action (with aggressive timeout protection)
            try:
                next_obs, reward, done, info = self.env.step(action)
                # If we got no observation, something went wrong but continue anyway
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
                info = {"turn": turn + 1, "score": self.world_state.turn, "max_score": 0}
            
            # Update world state from the new observation and action
            self.world_state.update_from_observation(next_obs, action)
            
            # Check if we're stuck (repeating same action or getting errors)
            if turn > 2 and len(self.action_history) >= 3:
                last_three = self.action_history[-3:]
                if len(set(last_three)) <= 2:  # Mostly repeating
                    if verbose:
                        output(f"⚠️  Warning: Repeating actions - might be stuck! Last 3: {last_three}")
                # Check if last response indicates invalid command
                if any(phrase in next_obs.lower() for phrase in ["not see that", "not know where", "can't", "cannot", "not allowed"]):
                    if verbose:
                        output(f"⚠️  Warning: Last command may have been invalid - game said: '{next_obs[:80]}...'")
            
            if verbose:
                if reward > 0:
                    output(f"✨ Reward: +{reward}")
                if "score" in info:
                    output(f"📈 Score: {info['score']}")
                output(f"📝 Response:")
                # Clean up the observation for display (remove command echoes, etc.)
                clean_obs = next_obs.strip()
                # Remove any lines that are just command echoes
                lines = clean_obs.split('\n')
                filtered_lines = []
                for line in lines:
                    # Skip command echo lines (">command" format)
                    if line.strip().startswith('>') and len(line.strip()) > 1:
                        # Check if it's a command echo (not just a prompt)
                        stripped = line.strip()[1:].strip()
                        if stripped and not any(c in stripped for c in ['(', '[', ']']):
                            # Likely a command echo, skip it
                            continue
                    filtered_lines.append(line)
                clean_obs = '\n'.join(filtered_lines)
                output(clean_obs)
            
            episode_stats["turns"] = turn + 1
            episode_stats["actions"].append(action)
            episode_stats["thoughts"].append(thought)
            episode_stats["observations"].append(next_obs)
            # Check if pig was found/caught from observation
            episode_stats["pig_found"] = self.world_state.pig_found
            
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
