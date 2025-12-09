"""
Constraint System for Lost Pig

Hard and soft constraints specific to Lost Pig game mechanics.
Based on actual game mechanics from walkthroughs.
"""

from typing import List, Tuple, Optional, Callable
from enum import Enum
from world_state import WorldState


class ConstraintType(Enum):
    """Types of constraints."""
    HARD = "hard"  # Must be satisfied
    SOFT = "soft"  # Should be satisfied, but can be violated


class ConstraintViolation:
    """Represents a constraint violation."""
    
    def __init__(self, constraint_type: ConstraintType, message: str, severity: float = 1.0):
        self.constraint_type = constraint_type
        self.message = message
        self.severity = severity  # 0.0 to 1.0
    
    def __str__(self):
        return f"[{self.constraint_type.value.upper()}] {self.message}"


class ConstraintChecker:
    """
    Constraint checker for Lost Pig game.
    
    Lost Pig specific constraints based on actual game:
    - Torch needed for dark areas (but can go out)
    - Windy cave needs orb (torch blows out)
    - Color magnet mechanics (pole repels/attracts)
    - Puzzle dependencies
    """
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state
        self.hard_constraints: List[Callable] = []
        self.soft_constraints: List[Callable] = []
        self._register_constraints()
    
    def _register_constraints(self):
        """Register Lost Pig-specific constraints."""
        
        # Hard constraints
        self.hard_constraints.append(self._check_torch_for_dark)
        self.hard_constraints.append(self._check_orb_for_windy)
        self.hard_constraints.append(self._check_item_usage)
        self.hard_constraints.append(self._check_movement)
        self.hard_constraints.append(self._check_pole_color)
        
        # Soft constraints
        self.soft_constraints.append(self._check_pig_search_priority)
        self.soft_constraints.append(self._check_action_coherence)
        self.soft_constraints.append(self._check_torch_management)
    
    def check_action(self, action: str) -> Tuple[bool, List[ConstraintViolation]]:
        """
        Check if action satisfies constraints.
        
        Returns:
            (is_valid, violations) where violations includes both hard and soft
        """
        violations = []
        
        # Check hard constraints
        for constraint_fn in self.hard_constraints:
            violation = constraint_fn(action)
            if violation:
                violations.append(violation)
        
        # Check soft constraints
        for constraint_fn in self.soft_constraints:
            violation = constraint_fn(action)
            if violation:
                violations.append(violation)
        
        # Action is valid if no hard violations
        hard_violations = [v for v in violations if v.constraint_type == ConstraintType.HARD]
        is_valid = len(hard_violations) == 0
        
        return is_valid, violations
    
    def _check_torch_for_dark(self, action: str) -> Optional[ConstraintViolation]:
        """
        Hard: Need light source for dark areas.
        
        Torch can go out, so need to relight it or use orb.
        """
        action_lower = action.lower()
        
        # Check if trying to enter dark areas
        dark_locations = ["hole", "cave", "tunnel", "underground"]
        is_dark_movement = any(loc in action_lower for loc in dark_locations)
        
        if is_dark_movement and self.world_state.player_location:
            # Check if entering hole or dark areas
            if "hole" in action_lower or "northeast" in action_lower or "ne" in action_lower:
                # Can enter hole without light (you fall in)
                return None
            
            # For other dark areas, need light
            if not self.world_state.torch_is_lit() and "orb" not in self.world_state.inventory:
                return ConstraintViolation(
                    ConstraintType.HARD,
                    "Need lit torch or orb to see in dark areas",
                    severity=1.0
                )
        
        return None
    
    def _check_orb_for_windy(self, action: str) -> Optional[ConstraintViolation]:
        """
        Hard: Windy cave requires orb (torch blows out).
        
        From walkthrough: torch goes out in windy tunnels.
        """
        action_lower = action.lower()
        
        # Check if trying to enter windy cave
        if "windy" in action_lower or ("north" in action_lower and self.world_state.player_location == "statue_room"):
            if not self.world_state.secret_door_open:
                # Secret door must be opened first
                return ConstraintViolation(
                    ConstraintType.HARD,
                    "Secret door must be opened first (give chair to statue)",
                    severity=1.0
                )
            
            # Need orb for windy cave (torch blows out)
            if "orb" not in self.world_state.inventory:
                return ConstraintViolation(
                    ConstraintType.HARD,
                    "Need orb for windy cave - torch will blow out",
                    severity=1.0
                )
        
        return None
    
    def _check_pole_color(self, action: str) -> Optional[ConstraintViolation]:
        """
        Hard: Color magnet mechanics.
        
        Green pole repels, need to change color to attract items.
        Black pole attracts white paper.
        """
        action_lower = action.lower()
        
        if "pole" in action_lower and "pole" in self.world_state.inventory:
            # Check if trying to get paper with wrong color pole
            if "paper" in action_lower or "crack" in action_lower:
                if self.world_state.pole_color != "black":
                    return ConstraintViolation(
                        ConstraintType.HARD,
                        f"Need black pole to get white paper (current: {self.world_state.pole_color})",
                        severity=1.0
                    )
        
        return None
    
    def _check_item_usage(self, action: str) -> Optional[ConstraintViolation]:
        """Hard: Can't use items not in inventory."""
        action_lower = action.lower()
        
        item_verbs = ["use", "drop", "give", "put", "open", "close", "read", "eat", "drink", "light", "burn"]
        
        for verb in item_verbs:
            if verb in action_lower:
                words = action_lower.split()
                try:
                    verb_idx = words.index(verb)
                    if verb_idx + 1 < len(words):
                        potential_item = words[verb_idx + 1]
                        
                        # Skip common words
                        if potential_item.lower() in ["the", "a", "an", "it", "them", "torch", "pole"]:
                            continue
                        
                        # Check inventory
                        if not self.world_state.has("player", potential_item):
                            # Check if item exists in world
                            if potential_item not in self.world_state.item_locations:
                                # Special cases
                                if verb == "light" and potential_item == "torch":
                                    # Can light torch if have powder and water
                                    if not (self.world_state.has("player", "powder") and 
                                           self.world_state.has("player", "water")):
                                        return ConstraintViolation(
                                            ConstraintType.HARD,
                                            "Cannot light torch without powder and water",
                                            severity=1.0
                                        )
                                    continue
                                return ConstraintViolation(
                                    ConstraintType.HARD,
                                    f"Cannot {verb} '{potential_item}' - not in inventory",
                                    severity=1.0
                                )
                except ValueError:
                    pass
        
        return None
    
    def _check_movement(self, action: str) -> Optional[ConstraintViolation]:
        """Hard: Can't move through nonexistent exits."""
        action_lower = action.lower()
        
        movement_verbs = ["go", "move", "walk", "run", "enter", "exit", "north", "south", 
                         "east", "west", "up", "down", "n", "s", "e", "w", "u", "d",
                         "northeast", "northwest", "southeast", "southwest", "ne", "nw", "se", "sw"]
        
        is_movement = any(verb in action_lower for verb in movement_verbs)
        
        if is_movement and self.world_state.player_location:
            exits = self.world_state.connections.get(self.world_state.player_location, set())
            
            # Check if trying to access secret door before it's open
            if "north" in action_lower and self.world_state.player_location == "statue_room":
                if not self.world_state.secret_door_open:
                    return ConstraintViolation(
                        ConstraintType.HARD,
                        "Secret door not open - give chair to statue first",
                        severity=1.0
                    )
        
        return None
    
    def _check_pig_search_priority(self, action: str) -> Optional[ConstraintViolation]:
        """
        Soft: Encourage actions that help find/catch the pig.
        
        Discourage actions that don't progress toward catching the pig
        if pig hasn't been caught yet.
        """
        if self.world_state.pig_caught:
            return None
        
        action_lower = action.lower()
        
        # Actions that are likely not helpful for catching pig
        unhelpful_actions = ["quit", "save", "restore", "help", "sing"]
        if any(unhelpful in action_lower for unhelpful in unhelpful_actions):
            return ConstraintViolation(
                ConstraintType.SOFT,
                "Action doesn't help catch the lost pig",
                severity=0.2
            )
        
        # Encourage exploration and item collection
        helpful_actions = ["look", "examine", "go", "take", "search", "get", "brick"]
        if not any(helpful in action_lower for helpful in helpful_actions):
            return ConstraintViolation(
                ConstraintType.SOFT,
                "Consider exploring or collecting items to catch the pig",
                severity=0.1
            )
        
        return None
    
    def _check_action_coherence(self, action: str) -> Optional[ConstraintViolation]:
        """Soft: Check if action makes sense in Lost Pig context."""
        # Check for repetitive actions
        if len(self.world_state.action_history) >= 2:
            recent = self.world_state.action_history[-2:]
            if action.lower() == recent[0].lower() == recent[1].lower():
                return ConstraintViolation(
                    ConstraintType.SOFT,
                    f"Action '{action}' repeated - may not be effective",
                    severity=0.3
                )
        
        # Check if trying to use items in wrong context
        action_lower = action.lower()
        
        # Don't use torch in windy areas (will blow out)
        if "torch" in action_lower and "windy" in action_lower:
            return ConstraintViolation(
                ConstraintType.SOFT,
                "Torch will blow out in windy areas - use orb instead",
                severity=0.3
            )
        
        # Check if trying to catch pig without bricks
        if "catch" in action_lower or "grab" in action_lower:
            if "pig" in action_lower:
                if "brick" not in self.world_state.inventory:
                    return ConstraintViolation(
                        ConstraintType.SOFT,
                        "Pig is too quick - need bricks to distract it first",
                        severity=0.4
                    )
        
        return None
    
    def _check_torch_management(self, action: str) -> Optional[ConstraintViolation]:
        """
        Soft: Encourage proper torch management.
        
        Don't waste torch in areas where it's not needed.
        """
        action_lower = action.lower()
        
        # If torch is unlit and trying to enter dark area
        if not self.world_state.torch_is_lit():
            if any(word in action_lower for word in ["go", "enter", "north", "south", "east", "west"]):
                dark_keywords = ["hole", "cave", "tunnel", "dark"]
                if any(kw in action_lower for kw in dark_keywords):
                    return ConstraintViolation(
                        ConstraintType.SOFT,
                        "Torch is unlit - consider relighting before exploring dark areas",
                        severity=0.2
                    )
        
        return None
    
    def get_constraint_prompt(self) -> str:
        """Generate Lost Pig-specific constraint prompt."""
        constraints = []
        
        constraints.append("=== LOST PIG GAME CONSTRAINTS ===")
        constraints.append("")
        constraints.append("HARD CONSTRAINTS (must be satisfied):")
        constraints.append("- Need light source (lit torch or orb) for dark areas")
        constraints.append("- Windy cave requires orb (torch blows out)")
        constraints.append("- Cannot use items not in inventory")
        constraints.append("- Cannot move through nonexistent exits")
        constraints.append("- Secret door must be opened (give chair to statue)")
        constraints.append("- Color magnet: need black pole to get white paper")
        
        constraints.append("")
        constraints.append("CURRENT STATE:")
        constraints.append(self.world_state.get_state_summary())
        
        constraints.append("")
        constraints.append("SOFT CONSTRAINTS (should be satisfied):")
        constraints.append("- Prioritize actions that help catch the lost pig")
        constraints.append("- Avoid repetitive actions")
        constraints.append("- Manage torch carefully (can go out)")
        constraints.append("- Use bricks to distract pig before catching")
        
        if not self.world_state.pig_caught:
            constraints.append("")
            constraints.append("GOAL: Catch the lost pig and bring it back to farm!")
        
        return "\n".join(constraints)
    
    def penalize_action(self, action: str) -> float:
        """
        Return penalty score for action (0.0 = no penalty, 1.0 = maximum penalty).
        Used for soft constraint enforcement.
        """
        _, violations = self.check_action(action)
        soft_violations = [v for v in violations if v.constraint_type == ConstraintType.SOFT]
        
        if not soft_violations:
            return 0.0
        
        # Sum severity scores
        total_penalty = sum(v.severity for v in soft_violations)
        return min(total_penalty, 1.0)
