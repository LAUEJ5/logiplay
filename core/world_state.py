from typing import Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class LocationInfo:
    name: str
    commands_tried: Set[str]
    times_visited: int
    items_found: Set[str]


class WorldState:
    def __init__(self):
        self.current_location: Optional[str] = None
        self.inventory: Set[str] = set()
        self.locations: Dict[str, LocationInfo] = {}
        self.turn: int = 0
        self.pig_found: bool = False
        self.pig_caught: bool = False
        self.items_collected: Set[str] = set()
        self.locations_discovered: Set[str] = set()
    
    def update_from_observation(self, observation: str, action: str) -> None:
        self.turn += 1
        obs_lower = observation.lower()
        
        location = self._parse_location(observation)
        if location:
            self.current_location = location
            if location not in self.locations:
                self.locations[location] = LocationInfo(
                    name=location,
                    commands_tried=set(),
                    times_visited=0,
                    items_found=set()
                )
                self.locations_discovered.add(location)
            self.locations[location].times_visited += 1
            self.locations[location].commands_tried.add(action.lower().strip())
            items_in_obs = self._extract_items(observation)
            self.locations[location].items_found.update(items_in_obs)
        
        self._update_inventory(observation, action)
        
        if "pig" in obs_lower:
            if any(word in obs_lower for word in ["catch", "grab", "hold", "carrying", "have pig"]):
                self.pig_found = True
                self.pig_caught = True
            elif any(word in obs_lower for word in ["see pig", "pig here", "pig there"]):
                self.pig_found = True
    
    def _parse_location(self, observation: str) -> Optional[str]:
        """Extract a simple location identifier from observation."""
        obs_lower = observation.lower()
        lines = observation.split('\n')
        
        # Use first significant word/phrase as location identifier
        for line in lines[:3]:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            words = line.lower().split()
            if words:
                # Use first meaningful word as location
                first_word = words[0]
                if first_word not in ["you", "grunk", "the", "a", "an", "there", "here"]:
                    return first_word[:20]  # Limit length
        
        return None
    
    def _update_inventory(self, observation: str, action: str) -> None:
        """Update inventory from observation."""
        obs_lower = observation.lower()
        action_lower = action.lower()
        
        # Check for explicit inventory listing
        if "grunk have:" in obs_lower or "inventory" in obs_lower:
            items = self._extract_items(observation)
            if items:
                self.inventory = items
                self.items_collected.update(items)
        
        # Track pickups
        if any(verb in action_lower for verb in ["take", "get", "pick", "grab"]):
            if any(word in obs_lower for word in ["got", "take", "pick", "get"]):
                items = self._extract_items(action)
                self.inventory.update(items)
                self.items_collected.update(items)
        
        # Track drops
        if "drop" in action_lower:
            items = self._extract_items(action)
            for item in items:
                self.inventory.discard(item)
    
    def _extract_items(self, text: str) -> Set[str]:
        """Extract item names from text."""
        text_lower = text.lower()
        common_items = [
            "torch", "pole", "key", "coin", "brick", "hat", "whistle", "chair",
            "book", "paper", "powder", "water", "orb", "ball", "pig", "pants",
            "chest", "box", "fountain", "statue", "shelf", "table", "bench",
            "stream", "curtain", "picture", "wall"
        ]
        items = set()
        for item in common_items:
            if item in text_lower:
                items.add(item)
        return items
    
    
    def get_commands_tried_at_location(self, location: Optional[str] = None) -> Set[str]:
        """Get commands already tried at a location."""
        loc = location or self.current_location
        if loc and loc in self.locations:
            return self.locations[loc].commands_tried.copy()
        return set()
    
    def get_summary(self) -> str:
        """Get summary of world state for LLM context."""
        lines = []
        
        # Current location
        if self.current_location:
            lines.append(f"Current Location: {self.current_location}")
            loc_info = self.locations.get(self.current_location)
            if loc_info:
                lines.append(f"  Visited {loc_info.times_visited} time(s)")
                if loc_info.commands_tried:
                    lines.append(f"  Commands tried here: {', '.join(sorted(list(loc_info.commands_tried)[:5]))}")
                if loc_info.items_found:
                    lines.append(f"  Items found here: {', '.join(sorted(list(loc_info.items_found)[:5]))}")
        else:
            lines.append("Current Location: Unknown")
        
        # Inventory
        if self.inventory:
            lines.append(f"Inventory ({len(self.inventory)}): {', '.join(sorted(self.inventory))}")
        else:
            lines.append("Inventory: Empty")
        
        # Discovered locations
        if len(self.locations) > 1:
            lines.append(f"\nDiscovered Locations ({len(self.locations)}):")
            for loc_name, loc_info in sorted(self.locations.items()):
                if loc_name != self.current_location:
                    lines.append(f"  - {loc_name} (visited {loc_info.times_visited}x)")
        
        # Pig status
        if self.pig_caught:
            lines.append("\nPig Status: CAUGHT")
        elif self.pig_found:
            lines.append("\nPig Status: FOUND")
        else:
            lines.append("\nPig Status: NOT FOUND")
        
        return "\n".join(lines)
    
    def get_location_context(self, location: Optional[str] = None) -> str:
        """Get context about what's been tried at a location."""
        loc = location or self.current_location
        if not loc or loc not in self.locations:
            return ""
        
        loc_info = self.locations[loc]
        lines = []
        
        if loc_info.commands_tried:
            lines.append(f"Commands tried: {', '.join(sorted(list(loc_info.commands_tried)[:8]))}")
        
        if loc_info.items_found:
            lines.append(f"Items found: {', '.join(sorted(list(loc_info.items_found)[:6]))}")
        
        return "\n".join(lines)
    
    def get_progress_metrics(self) -> Dict[str, int]:
        """Get progress metrics for evaluation."""
        return {
            "locations_discovered": len(self.locations_discovered),
            "items_collected": len(self.items_collected)
        }
    

