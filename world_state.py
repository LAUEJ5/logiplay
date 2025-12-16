"""
World State Model for Lost Pig

Lightweight world state tracking:
- Current location and discovered locations
- Inventory tracking
- Commands tried at each location (to avoid repetition)
- Location connections (discovered through exploration)
"""

from typing import Dict, Set, Optional, List
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class LocationInfo:
    """Information about a discovered location."""
    name: str
    commands_tried: Set[str]
    times_visited: int
    items_found: Set[str]  # Items that were found/mentioned here
    exits_discovered: Set[str]  # Directions that lead somewhere from here


class WorldState:
    """
    Lightweight world state tracker for Lost Pig.
    
    Tracks:
    - Current location (parsed from observations)
    - Inventory (parsed from observations)
    - Commands tried at each location
    - Discovered locations and their connections
    """
    
    def __init__(self):
        # Current location (parsed from observations)
        self.current_location: Optional[str] = None
        
        # Inventory: items player currently has
        self.inventory: Set[str] = set()
        
        # Location map: location_name -> LocationInfo
        self.locations: Dict[str, LocationInfo] = {}
        
        # Location connections: location -> set of connected locations
        self.connections: Dict[str, Set[str]] = defaultdict(set)
        
        # Turn counter
        self.turn: int = 0
        
        # Track if pig has been found/caught
        self.pig_found: bool = False
        self.pig_caught: bool = False
    
    def update_from_observation(self, observation: str, action: str) -> None:
        """
        Update world state from observation and action.
        Extracts location, inventory, and tracks commands per location.
        """
        self.turn += 1
        obs_lower = observation.lower()
        action_lower = action.lower()
        
        # Parse current location from observation
        location = self._parse_location(observation)
        if location:
            self.current_location = location
            if location not in self.locations:
                self.locations[location] = LocationInfo(
                    name=location,
                    commands_tried=set(),
                    times_visited=0,
                    items_found=set(),
                    exits_discovered=set()
                )
            self.locations[location].times_visited += 1
            
            # Track command tried at this location
            self.locations[location].commands_tried.add(action.lower().strip())
        
        # Parse inventory from observation
        self._update_inventory(observation, action)
        
        # Track pig status
        if "pig" in obs_lower:
            if any(word in obs_lower for word in ["catch", "grab", "hold", "carrying", "have pig"]):
                self.pig_found = True
                self.pig_caught = True
            elif any(word in obs_lower for word in ["see pig", "pig here", "pig there"]):
                self.pig_found = True
        
        # Track location connections (when moving)
        if self._is_movement_action(action):
            # We'll track connections when we see location changes
            pass
        
        # Track items found at current location
        if self.current_location:
            items_in_obs = self._extract_items_from_observation(observation)
            self.locations[self.current_location].items_found.update(items_in_obs)
    
    def _parse_location(self, observation: str) -> Optional[str]:
        """
        Parse location name from observation.
        Looks for location indicators in the text.
        """
        obs_lower = observation.lower()
        
        # Location keywords that appear in room descriptions
        location_keywords = {
            "outside": ["outside", "clearing", "open area", "farm"],
            "forest": ["forest", "dark", "tree", "bush"],
            "hole": ["hole", "bottom of", "deep hole", "fall down", "deep, dark hole"],
            "fountain_room": ["fountain room", "fountain", "glowing wall", "all wall glow"],
            "shelf_room": ["shelf room", "shelfs", "shelves", "shelf"],
            "gnome_room": ["gnome room", "closet", "little person room", "bed", "desk", "gnome"],
            "table_room": ["table room", "table", "autobaker", "metal box"],
            "statue_room": ["statue room", "statue", "picture"],
            "cave_with_stream": ["cave with stream", "stream", "cave", "water"],
            "windy_cave": ["windy cave", "wind"],
            "twisty_cave": ["twisty cave", "twisty tunnel"],
        }
        
        # Check for location indicators
        for loc_name, keywords in location_keywords.items():
            if any(kw in obs_lower for kw in keywords):
                # Additional context checks for ambiguous cases
                if loc_name == "forest" and "outside" in obs_lower:
                    continue  # Prefer "outside" if both present
                if loc_name == "hole" and "fountain" in obs_lower:
                    continue  # Prefer "fountain_room" if both present
                return loc_name
        
        # If no match, try to extract from room title (first line often has location)
        lines = observation.split('\n')
        if lines:
            first_line = lines[0].lower()
            # Look for capitalized words that might be location names
            for word in first_line.split():
                if word and word[0].isupper() and len(word) > 3:
                    # Could be a location name
                    pass
        
        return None
    
    def _update_inventory(self, observation: str, action: str) -> None:
        """
        Update inventory from observation and action.
        Tracks when items are picked up or dropped.
        """
        obs_lower = observation.lower()
        action_lower = action.lower()
        
        # Check for inventory listing (explicit inventory command)
        if "grunk have:" in obs_lower or "inventory" in obs_lower or "i" == action_lower.strip():
            # Parse inventory list
            lines = observation.split('\n')
            in_inventory_section = False
            new_inventory = set()
            for line in lines:
                line_lower = line.lower()
                if "grunk have:" in line_lower or "inventory" in line_lower:
                    in_inventory_section = True
                    continue
                if in_inventory_section:
                    # Extract item names from this line
                    items = self._extract_items_from_text(line)
                    new_inventory.update(items)
                    # Stop at empty line or parenthetical
                    if not line.strip() or (line.strip().startswith('(') and ')' in line):
                        break
            if new_inventory:
                self.inventory = new_inventory
        
        # Track pickups (from action success)
        if any(verb in action_lower for verb in ["take", "get", "pick", "grab"]):
            # Check if action was successful
            if any(word in obs_lower for word in ["got it", "ok, got", "take", "pick", "get", "ok, got it"]):
                items = self._extract_items_from_text(action)
                self.inventory.update(items)
        
        # Track drops
        if "drop" in action_lower:
            items = self._extract_items_from_text(action)
            for item in items:
                self.inventory.discard(item)
        
        # Track item usage/removal (e.g., eating, using up)
        if any(verb in action_lower for verb in ["eat", "use", "drink", "consume"]):
            # Check if item was consumed
            if any(word in obs_lower for word in ["all gone", "eat", "use", "consume", "drink"]):
                items = self._extract_items_from_text(action)
                for item in items:
                    if item in ["brick", "orb", "food"]:  # Items that can be consumed
                        self.inventory.discard(item)
    
    def _extract_items_from_text(self, text: str) -> List[str]:
        """Extract item names from text."""
        text_lower = text.lower()
        common_items = [
            "torch", "pole", "key", "coin", "brick", "hat", "whistle", "chair",
            "book", "paper", "powder", "water", "orb", "ball", "pig", "pants"
        ]
        found_items = []
        for item in common_items:
            if item in text_lower:
                found_items.append(item)
        return found_items
    
    def _extract_items_from_observation(self, observation: str) -> Set[str]:
        """Extract items mentioned in observation."""
        items = set()
        obs_lower = observation.lower()
        
        common_items = [
            "torch", "pole", "key", "coin", "brick", "hat", "whistle", "chair",
            "book", "paper", "powder", "water", "orb", "ball", "pig", "pants",
            "chest", "box", "fountain", "statue", "shelf", "table", "bench",
            "stream", "curtain", "picture", "wall"
        ]
        
        for item in common_items:
            if item in obs_lower:
                items.add(item)
        
        return items
    
    def _is_movement_action(self, action: str) -> bool:
        """Check if action is a movement command."""
        action_lower = action.lower().strip()
        directions = ["north", "south", "east", "west", "up", "down", 
                     "northeast", "northwest", "southeast", "southwest",
                     "ne", "nw", "se", "sw", "n", "s", "e", "w"]
        return action_lower in directions
    
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
            # Group commands by type for better readability
            movement = [c for c in loc_info.commands_tried if self._is_movement_action(c)]
            examine = [c for c in loc_info.commands_tried if "examine" in c or "x " in c or "look" in c]
            other = [c for c in loc_info.commands_tried if c not in movement and c not in examine]
            
            if movement:
                lines.append(f"Directions tried: {', '.join(sorted(movement)[:5])}")
            if examine:
                lines.append(f"Examine commands: {', '.join(sorted(examine)[:5])}")
            if other:
                lines.append(f"Other commands tried: {', '.join(sorted(other)[:5])}")
        
        if loc_info.items_found:
            lines.append(f"Items found/mentioned here: {', '.join(sorted(list(loc_info.items_found)[:6]))}")
        
        return "\n".join(lines)
    
    def should_avoid_command(self, command: str, location: Optional[str] = None) -> bool:
        """Check if a command should be avoided (already tried at this location)."""
        loc = location or self.current_location
        if not loc or loc not in self.locations:
            return False
        
        command_lower = command.lower().strip()
        tried_commands = self.locations[loc].commands_tried
        
        # Check exact match
        if command_lower in tried_commands:
            return True
        
        # Check for similar commands (e.g., "examine pole" vs "x pole")
        if "examine" in command_lower or "x " in command_lower:
            # Extract item name
            item = command_lower.replace("examine", "").replace("x ", "").strip()
            if item:
                # Check if any variation of examining this item was tried
                for tried in tried_commands:
                    tried_lower = tried.lower()
                    if ("examine" in tried_lower or "x " in tried_lower) and item in tried_lower:
                        return True
        
        # Check for "listen" variations
        if command_lower == "listen":
            if "listen" in tried_commands:
                return True
        
        # Check for "look" variations
        if command_lower in ["look", "l"]:
            if "look" in tried_commands or "l" in tried_commands:
                return True
        
        return False
