from typing import Dict


class AchievementEvaluator:
    def __init__(self):
        pass
    
    def evaluate(self, episode_stats: Dict) -> Dict:
        all_observations = episode_stats.get("observations", [])
        final_obs = all_observations[-1] if all_observations else ""
        
        game_score = 0
        for obs in all_observations:
            if "[Grunk score go up one.]" in obs:
                game_score += 1
        
        max_score = 7
        turns_taken = episode_stats.get("turns", 0)
        
        locations_discovered = episode_stats.get("locations_discovered", 0)
        items_collected = episode_stats.get("items_collected", 0)
        
        game_complete = (
            episode_stats.get("pig_found", False) and
            ("farm" in final_obs.lower() or "boss" in final_obs.lower() or "happy" in final_obs.lower() or "won" in final_obs.lower())
        )
        
        results = {
            "game_score": game_score,
            "max_score": max_score,
            "turns_taken": turns_taken,
            "normalized_score": game_score / max_score if max_score > 0 else 0.0,
            "success": game_complete and turns_taken <= 40,
            "locations_discovered": locations_discovered,
            "items_collected": items_collected
        }
        
        return results
    
    def get_achievement_summary(self, results: Dict) -> str:
        lines = [
            f"=== Lost Pig Score ({results['game_score']}/{results['max_score']} points) ===",
            f"Turns taken: {results['turns_taken']}/40",
            f"Normalized score: {results['normalized_score']:.2f}",
            "",
            f"=== Progress Metrics ===",
            f"Locations discovered: {results.get('locations_discovered', 0)}",
            f"Items collected: {results.get('items_collected', 0)}",
            ""
        ]
        
        if results["success"]:
            lines.append("🎉 SUCCESS: Completed the game!")
        else:
            lines.append("❌ Did not complete the game")
        
        return "\n".join(lines)
