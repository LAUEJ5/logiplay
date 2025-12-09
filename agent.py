"""
Logic-Aware Agent for Lost Pig

Logic-aware agent configured specifically for Lost Pig game.
"""

from typing import List, Optional, Dict, Tuple, Protocol
from world_state import WorldState
from constraints import ConstraintChecker
from action_verifier import ActionVerifier, VerificationResult


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
        # Initialize with Lost Pig world state
        self.world_state = WorldState()
        
        # Initialize Lost Pig-specific constraint checker
        self.constraint_checker = ConstraintChecker(self.world_state)
        
        # Use standard action verifier
        self.action_verifier = ActionVerifier()
        
        # Store LLM and environment
        self.llm = llm_client
        self.env = game_env
        
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
1. Your goal: Catch the lost pig and bring it back to the farm
2. What items do you have? (torch, pole, key, coin, brick, etc.)
3. Is your torch lit? (It can go out and needs powder + water to relight)
4. What locations can you access?
5. Do you need any items to access new areas or solve puzzles?
6. The pig is quick - you'll need bricks to distract it before catching
7. What constraints must you follow?

Provide a brief thought (1-2 sentences) about your next action."""

        thought = self.llm.generate(prompt, max_tokens=100, temperature=0.7)
        self.thought_history.append(thought)
        return thought
    
    def act(self, observation: str, thought: str) -> str:
        """
        Generate action with Lost Pig-specific constraints.
        """
        context = self._build_context()
        constraints = self.constraint_checker.get_constraint_prompt()
        verification_guide = self.action_verifier.get_verification_prompt()
        
        prompt = f"""You are Grunk, an orc playing Lost Pig text adventure.

{context}

Current observation:
{observation}

Your thought:
{thought}

{constraints}

{verification_guide}

Important Lost Pig mechanics:
- Torch can go out (relight with powder + water)
- Green pole repels, but can be burned to black (attracts white paper)
- Use bricks from autobaker to distract pig before catching
- Secret door opens when you give chair to statue
- Windy caves need orb (torch blows out)

Generate a single action command to help catch the lost pig. Keep it short and direct (1-5 words)."""

        # Generate candidate action
        candidate_action = self.llm.generate_with_constraints(
            prompt,
            valid_actions=self._get_valid_action_hints(),
            invalid_actions=self._get_invalid_action_hints()
        )
        
        # Clean up action
        candidate_action = candidate_action.strip().strip('"').strip("'")
        
        # Verify and constrain
        action = self._apply_constraints(candidate_action)
        
        return action
    
    def _apply_constraints(self, action: str, max_retries: int = 3) -> str:
        """
        Apply Lost Pig constraints to action.
        """
        for attempt in range(max_retries):
            # Step 1: Action verification (structural)
            verification = self.action_verifier.verify(action)
            if not verification.is_valid:
                if hasattr(self.llm, 'generate'):
                    verification = self.action_verifier.verify_with_llm(action, self.llm)
                
                if not verification.is_valid:
                    action = self._regenerate_with_feedback(
                        action, 
                        f"Invalid command structure: {verification.error_message}"
                    )
                    continue
            
            if verification.normalized_action:
                action = verification.normalized_action
            
            # Step 2: Constraint checking (logical)
            is_valid, violations = self.constraint_checker.check_action(action)
            
            if is_valid:
                return action
            else:
                from constraints import ConstraintType
                hard_violations = [v for v in violations if v.constraint_type == ConstraintType.HARD]
                violation_msg = "; ".join(str(v) for v in hard_violations)
                action = self._regenerate_with_feedback(action, violation_msg)
        
        return action
    
    def _regenerate_with_feedback(self, original_action: str, feedback: str) -> str:
        """Regenerate action with constraint violation feedback."""
        prompt = f"""The action "{original_action}" was invalid: {feedback}

Generate a different, valid action that avoids this issue.
Remember: You're Grunk, an orc searching for a lost pig. You need to catch it and bring it back to the farm.
Keep it short (1-5 words)."""

        return self.llm.generate(prompt, max_tokens=30, temperature=0.5)
    
    def _get_valid_action_hints(self) -> List[str]:
        """Get hints about valid actions for Lost Pig."""
        hints = []
        
        # Movement hints
        if self.world_state.player_location and self.world_state.player_location in self.world_state.connections:
            exits = list(self.world_state.connections[self.world_state.player_location])[:3]
            hints.extend([f"go {exit.replace('_', ' ')}" for exit in exits])
        
        # Item hints
        items_here = [item for item, loc in self.world_state.item_locations.items() 
                     if loc == self.world_state.player_location]
        if items_here and self.world_state.can_carry("dummy"):
            hints.extend([f"take {item}" for item in items_here[:2]])
        
        # Exploration hints
        if not self.world_state.pig_found:
            hints.extend(["look", "examine", "search"])
        
        return hints
    
    def _get_invalid_action_hints(self) -> List[str]:
        """Get hints about invalid actions to avoid."""
        invalid = []
        
        # Can't take items if inventory full
        if not self.world_state.can_carry("dummy"):
            invalid.append("take (inventory full)")
        
        return invalid
    
    def _build_context(self) -> str:
        """Build Lost Pig-specific context."""
        lines = [
            "=== LOST PIG GAME STATE ===",
            self.world_state.get_state_summary(),
        ]
        
        if self.observation_history:
            lines.append("\n=== RECENT OBSERVATIONS ===")
            lines.extend(self.observation_history[-3:])
        
        if self.action_history:
            lines.append("\n=== RECENT ACTIONS ===")
            lines.extend(self.action_history[-3:])
        
        return "\n".join(lines)
    
    def step(self, observation: str) -> Tuple[str, str]:
        """Single ReAct step: Think then Act."""
        thought = self.think(observation)
        action = self.act(observation, thought)
        
        self.observation_history.append(observation)
        self.action_history.append(action)
        
        return thought, action
    
    def update_world_state(self, observation: str, action: str) -> None:
        """Update Lost Pig world state from observation."""
        self.world_state.update_from_observation(observation, action)
    
    def run_episode(self, max_turns: int = 40) -> Dict:
        """
        Run a complete Lost Pig episode.
        
        Returns:
            Dictionary with episode statistics
        """
        if not self.env:
            raise ValueError("No environment provided")
        
        observation = self.env.reset()
        episode_stats = {
            "turns": 0,
            "actions": [],
            "thoughts": [],
            "observations": [],
            "constraint_violations": [],
            "final_score": 0,
            "pig_found": False
        }
        
        for turn in range(max_turns):
            thought, action = self.step(observation)
            
            next_obs, reward, done, info = self.env.step(action)
            
            self.update_world_state(next_obs, action)
            
            episode_stats["turns"] = turn + 1
            episode_stats["actions"].append(action)
            episode_stats["thoughts"].append(thought)
            episode_stats["observations"].append(next_obs)
            episode_stats["pig_found"] = self.world_state.pig_found
            
            if "score" in info:
                episode_stats["final_score"] = info["score"]
            
            if done:
                break
            
            observation = next_obs
        
        return episode_stats
