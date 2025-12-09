"""
Achievement Evaluation for Lost Pig

Defines achievements for Lost Pig game evaluation based on actual game.
Based on EntropicThoughts protocol: score = achievements reached in ≤40 turns.
"""

from typing import List, Dict
from dataclasses import dataclass
from world_state import WorldState


@dataclass
class Achievement:
    """Represents a Lost Pig achievement."""
    name: str
    description: str
    check_fn: callable  # Function(state, observation) -> bool
    points: int = 1


class AchievementEvaluator:
    """
    Achievement evaluator for Lost Pig.
    
    Based on actual game achievements (7 points total):
    1. Start game / Find pig location (1 point)
    2. Get torch (1 point)
    3. Light torch (1 point) - using powder + water
    4. Get key (1 point) - using pole
    5. Open chest (1 point) - using key
    6. Catch pig (1 point) - using bricks
    7. Bring pig back to farm (1 point) - final goal
    """
    
    def __init__(self):
        self.achievements: List[Achievement] = []
        self._register_achievements()
    
    def _register_achievements(self):
        """Register Lost Pig achievements based on actual game."""
        
        self.achievements = [
            Achievement(
                name="game_started",
                description="Game started successfully",
                check_fn=lambda state, obs: state.turn > 0,
                points=1
            ),
            Achievement(
                name="found_pig_location",
                description="Found where the pig is (heard noise, fell in hole)",
                check_fn=lambda state, obs: state.pig_found or state.player_location == "hole",
                points=1
            ),
            Achievement(
                name="got_torch",
                description="Picked up the torch",
                check_fn=lambda state, obs: state.has("player", "torch"),
                points=1
            ),
            Achievement(
                name="lit_torch",
                description="Lit the torch using powder and water",
                check_fn=lambda state, obs: state.puzzle_solved("light_torch") or 
                                          (state.has("player", "torch") and state.torch_is_lit()),
                points=1
            ),
            Achievement(
                name="got_key",
                description="Got the red key using pole (color magnet)",
                check_fn=lambda state, obs: state.has("player", "key"),
                points=1
            ),
            Achievement(
                name="opened_chest",
                description="Opened the chest in shelf room",
                check_fn=lambda state, obs: state.puzzle_solved("cave_chest"),
                points=1
            ),
            Achievement(
                name="caught_pig",
                description="Caught the lost pig using bricks",
                check_fn=lambda state, obs: state.pig_caught,
                points=1
            ),
            Achievement(
                name="brought_pig_back",
                description="Brought pig back to farm (game complete)",
                check_fn=lambda state, obs: state.pig_caught and state.player_location == "forest",
                points=1  # This is the main win condition
            ),
        ]
    
    def evaluate(self, world_state: WorldState, episode_stats: Dict) -> Dict:
        """
        Evaluate achievements reached.
        
        Args:
            world_state: Lost Pig world state
            episode_stats: Episode statistics
        
        Returns:
            Dictionary with achievement results
        """
        results = {
            "total_achievements": len(self.achievements),
            "achievements_reached": [],
            "achievements_missed": [],
            "total_points": 0,
            "max_points": sum(a.points for a in self.achievements),
            "turns_taken": episode_stats.get("turns", 0),
            "details": {}
        }
        
        # Use final observation
        final_obs = episode_stats.get("observations", [""])[-1] if episode_stats.get("observations") else ""
        
        # Check each achievement
        for achievement in self.achievements:
            if achievement.check_fn(world_state, final_obs):
                results["achievements_reached"].append(achievement.name)
                results["total_points"] += achievement.points
                results["details"][achievement.name] = {
                    "achieved": True,
                    "points": achievement.points,
                    "description": achievement.description
                }
            else:
                results["achievements_missed"].append(achievement.name)
                results["details"][achievement.name] = {
                    "achieved": False,
                    "points": 0,
                    "description": achievement.description
                }
        
        # Normalized score (0-1)
        if results["max_points"] > 0:
            results["normalized_score"] = results["total_points"] / results["max_points"]
        else:
            results["normalized_score"] = 0.0
        
        # Success criteria: caught pig and brought back in ≤40 turns
        results["success"] = (
            world_state.pig_caught and 
            (world_state.player_location == "forest" or "farm" in final_obs.lower()) and
            results["turns_taken"] <= 40
        )
        
        return results
    
    def get_achievement_summary(self, results: Dict) -> str:
        """Get human-readable achievement summary."""
        lines = [
            f"=== Lost Pig Achievements ({results['total_points']}/{results['max_points']} points) ===",
            f"Turns taken: {results['turns_taken']}/40",
            "",
            "Achieved:"
        ]
        
        for ach_name in results["achievements_reached"]:
            details = results["details"][ach_name]
            lines.append(f"  ✓ {details['description']} (+{details['points']} points)")
        
        if results["achievements_missed"]:
            lines.append("")
            lines.append("Missed:")
            for ach_name in results["achievements_missed"]:
                details = results["details"][ach_name]
                lines.append(f"  ✗ {details['description']}")
        
        lines.append("")
        if results["success"]:
            lines.append("🎉 SUCCESS: Caught pig and brought it back to farm within 40 turns!")
        else:
            lines.append("❌ Did not complete the game within 40 turns")
        
        return "\n".join(lines)
