"""
World State Model for Lost Pig

Defines the game world for Lost Pig, including:
- Locations and their connections
- Items and their initial locations
- Puzzles and their dependencies
- Character states
"""

from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class WorldState:
    """
    World state model for Lost Pig game.
    
    Lost Pig is a text adventure where you play as Grunk, an orc
    searching for a lost pig. The game has specific locations,
    items, and puzzles based on the actual game.
    """
    
    # Lost Pig specific constants
    MAX_INVENTORY = 10  # Actually flexible in game, but reasonable limit
    PLAYER_NAME = "grunk"
    TARGET_ENTITY = "pig"
    
    # Note: Lost Pig doesn't have strict inventory limit like some games
    # Grunk can carry multiple items, but be reasonable
    
    def __init__(self):
        # Player location
        self.player_location: Optional[str] = None
        
        # Inventory: set of items player has
        self.inventory: Set[str] = set()
        
        # Character states: alive/dead
        self.character_states: Dict[str, bool] = {}
        
        # Location connectivity graph
        self.connections: Dict[str, Set[str]] = defaultdict(set)
        
        # Item locations (where items are in the world)
        self.item_locations: Dict[str, str] = {}
        
        # Action history for tracking
        self.action_history: List[str] = []
        
        # Turn counter
        self.turn: int = 0
        
        # Lost Pig specific
        self.puzzles_solved: Set[str] = set()
        self.pig_found = False
        self.pig_location: Optional[str] = None
        self.pig_caught = False
        
        # Torch state
        self.torch_lit = True  # Starts lit
        
        # Pole color (color magnet mechanics)
        self.pole_color = "green"  # Starts green (repels)
        
        # Secret door state
        self.secret_door_open = False
        
        # Autobaker state
        self.autobaker_has_coin = False
        
        self._initialize_world()
    
    def _initialize_world(self):
        """Initialize Lost Pig game world based on actual game."""
        
        # Set starting location
        self.player_location = "outside"
        
        # Define connections based on actual game map
        connections = [
            # Outside area
            ("outside", "forest_north"),
            ("outside", "forest_east"),
            ("outside", "field_west"),
            ("outside", "farm_south"),
            
            # Forest leads to hole
            ("forest_north", "hole"),  # When going NE from forest
            ("forest_east", "hole"),
            
            # Underground shrine connections
            ("hole", "fountain_room"),  # East tunnel
            ("fountain_room", "shelf_room"),  # SE
            ("fountain_room", "table_room"),  # SW
            ("fountain_room", "statue_room"),  # N
            ("fountain_room", "cave_with_stream"),  # E/W tunnels
            
            ("shelf_room", "gnome_room"),  # W
            ("table_room", "gnome_room"),  # E
            ("table_room", "fountain_room"),  # NE (back to fountain room)
            
            ("statue_room", "windy_cave"),  # N (secret door, only when open)
            ("windy_cave", "twisty_cave"),  # N
            ("twisty_cave", "forest"),  # Exit (with gnome help or whistle)
        ]
        
        for loc1, loc2 in connections:
            self.add_connection(loc1, loc2, bidirectional=True)
        
        # Additional connections
        self.add_connection("fountain_room", "table_room", bidirectional=True)
        
        # Define items and their initial locations (from walkthrough)
        self.item_locations = {
            "torch": "outside",  # Starts lit, can go out
            "pants": "player",  # Worn (always with player)
            "pole": "shelf_room",  # Green pole (color magnet, repels)
            "key": "cave_with_stream",  # Red key, across stream (need pole)
            "coin": "fountain_room",  # In fountain bowl
            "chair": "table_room",  # Movable chair (used to reach top shelf, open secret door)
            "hat": "statue_room",  # On statue (can hold water)
            "whistle": "hole",  # On broken stairs (can call for help)
            "book": "shelf_room",  # Top shelf (need chair to reach)
            "paper": "hole",  # In crack (need black pole to get)
            "powder": "shelf_room",  # In chest (black powder, dehydrated fire, need key)
            "brick": None,  # From autobaker (not in world initially, need coin)
            "orb": "gnome_room",  # Glowing ball (mossfuressence, need to trade torch)
        }
        
        # Pig starts in hole/fountain room area (moves around)
        self.pig_location = "fountain_room"
        
        # Add table_room connection
        self.add_connection("fountain_room", "table_room", bidirectional=True)
        
        # Define puzzles and their requirements
        self.puzzle_requirements = {
            "windy_cave": {
                "required_item": "orb", 
                "description": "Need light source that won't blow out in wind (orb)"
            },
            "shelf_room_top": {
                "required_item": "chair",
                "description": "Need chair to reach top shelf"
            },
            "cave_chest": {
                "required_item": "key",
                "description": "Need key to unlock chest"
            },
            "statue_secret": {
                "required_item": "chair",
                "description": "Give chair to statue to open secret door"
            },
            "light_torch": {
                "required_items": ["powder", "water"],
                "description": "Need water + black powder to light torch"
            },
            "get_key": {
                "required_item": "pole",
                "description": "Need pole to get key across stream (color magnet)"
            },
            "get_paper": {
                "required_item": "pole",
                "required_color": "black",  # Pole must be black to attract white paper
                "description": "Need black pole to get white paper from crack"
            },
            "catch_pig": {
                "required_item": "brick",
                "required_count": 2,  # Need multiple bricks
                "description": "Need multiple bricks to distract and catch pig"
            },
        }
        
        # Character states
        self.character_states = {
            "grunk": True,  # Player is always alive
            "pig": True,    # Pig is alive (just lost)
            "gnome": True,  # Gnome in gnome room
        }
    
    def at(self, entity: str, location: str) -> bool:
        """Check if entity is at location."""
        if entity == "player":
            return self.player_location == location
        elif entity == "pig":
            return self.pig_location == location
        return False
    
    def has(self, entity: str, item: str) -> bool:
        """Check if entity has item."""
        if entity == "player":
            return item in self.inventory
        return False
    
    def alive(self, character: str) -> bool:
        """Check if character is alive."""
        return self.character_states.get(character, True)  # Default alive
    
    def connected(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are connected."""
        return loc2 in self.connections.get(loc1, set())
    
    def can_carry(self, item: str) -> bool:
        """Check if Grunk can carry another item."""
        # Lost Pig doesn't have strict inventory limit, but reasonable check
        return len(self.inventory) < self.MAX_INVENTORY
    
    def puzzle_solved(self, puzzle_name: str) -> bool:
        """Check if a puzzle is solved."""
        return puzzle_name in self.puzzles_solved
    
    def mark_puzzle_solved(self, puzzle_name: str) -> None:
        """Mark a puzzle as solved."""
        self.puzzles_solved.add(puzzle_name)
    
    def can_access_location(self, location: str) -> bool:
        """
        Check if player can access a location based on puzzles/items.
        
        Returns True if location is accessible given current state.
        """
        if location not in self.puzzle_requirements:
            return True
        
        puzzle = self.puzzle_requirements[location]
        required_item = puzzle.get("required_item")
        
        if required_item is None:
            return True
        
        return self.has("player", required_item)
    
    def torch_is_lit(self) -> bool:
        """Check if torch is currently lit."""
        return self.torch_lit and "torch" in self.inventory
    
    def set_torch_lit(self, lit: bool) -> None:
        """Set torch lit/unlit state."""
        self.torch_lit = lit
    
    def get_pole_color(self) -> str:
        """Get current pole color."""
        return self.pole_color
    
    def set_pole_color(self, color: str) -> None:
        """Set pole color (for color magnet mechanics)."""
        self.pole_color = color
    
    def set_location(self, location: str) -> None:
        """Set player location."""
        self.player_location = location
    
    def add_item(self, item: str) -> None:
        """Add item to inventory."""
        self.inventory.add(item)
        # Special handling
        if item == "torch" and not self.torch_lit:
            # Torch can be picked up unlit
            pass
    
    def remove_item(self, item: str) -> None:
        """Remove item from inventory."""
        self.inventory.discard(item)
    
    def set_character_alive(self, character: str, alive: bool) -> None:
        """Set character alive/dead state."""
        self.character_states[character] = alive
    
    def add_connection(self, loc1: str, loc2: str, bidirectional: bool = True) -> None:
        """Add connection between locations."""
        self.connections[loc1].add(loc2)
        if bidirectional:
            self.connections[loc2].add(loc1)
    
    def update_from_observation(self, observation: str, action: str) -> None:
        """
        Update world state from Lost Pig observation.
        
        Extracts facts from game text using heuristics.
        """
        self.turn += 1
        self.action_history.append(action)
        
        obs_lower = observation.lower()
        action_lower = action.lower()
        
        # Track pig location and catching
        if "pig" in obs_lower:
            if any(word in obs_lower for word in ["catch", "grab", "hold", "have pig", "carrying pig"]):
                self.pig_found = True
                self.pig_caught = True
                self.pig_location = self.player_location
            elif any(word in obs_lower for word in ["see pig", "pig here", "pig there"]):
                self.pig_found = True
                if "fountain" in obs_lower:
                    self.pig_location = "fountain_room"
                elif "shelf" in obs_lower:
                    self.pig_location = "shelf_room"
                elif "table" in obs_lower:
                    self.pig_location = "table_room"
                elif "gnome" in obs_lower:
                    self.pig_location = "gnome_room"
        
        # Track item pickups
        if any(verb in action_lower for verb in ["take", "get", "pick", "grab"]):
            for item in list(self.item_locations.keys()):
                if item in action_lower and item in obs_lower:
                    if any(word in obs_lower for word in ["take", "pick", "get", "got it", "ok, got"]):
                        self.add_item(item)
                        # Remove from world location
                        if item in self.item_locations:
                            del self.item_locations[item]
        
        # Track item drops
        if "drop" in action_lower:
            for item in list(self.inventory):
                if item in action_lower:
                    self.remove_item(item)
                    self.item_locations[item] = self.player_location
        
        # Track torch state
        if "torch" in obs_lower:
            if any(word in obs_lower for word in ["go out", "extinguished", "not lit", "black and sooty"]):
                self.torch_lit = False
            elif any(word in obs_lower for word in ["light", "on fire", "burning", "lit"]):
                self.torch_lit = True
        
        # Track location changes
        location_keywords = {
            "outside": ["outside", "clearing", "open area"],
            "forest_north": ["forest", "north forest"],
            "forest_east": ["forest", "east forest"],
            "hole": ["hole", "bottom of", "deep hole", "fall down"],
            "fountain_room": ["fountain room", "fountain", "glowing wall", "all wall glow"],
            "shelf_room": ["shelf room", "shelfs", "shelves"],
            "gnome_room": ["gnome room", "closet", "little person room"],
            "table_room": ["table room", "table", "autobaker"],
            "statue_room": ["statue room", "statue"],
            "cave_with_stream": ["cave with stream", "stream", "cave"],
            "windy_cave": ["windy cave", "wind"],
            "twisty_cave": ["twisty cave", "twisty tunnel"],
            "forest": ["forest", "outside again"],
        }
        
        for loc, keywords in location_keywords.items():
            if any(kw in obs_lower for kw in keywords):
                self.player_location = loc
                break
        
        # Track puzzle solving
        if "unlock" in obs_lower or "open" in obs_lower:
            if "chest" in obs_lower:
                self.mark_puzzle_solved("cave_chest")
        
        if "secret door" in obs_lower or "wall open" in obs_lower:
            self.secret_door_open = True
            self.mark_puzzle_solved("statue_secret")
        
        if "light" in obs_lower and "torch" in obs_lower:
            if "fire" in obs_lower or "burning" in obs_lower:
                self.torch_lit = True
                self.mark_puzzle_solved("light_torch")
        
        # Track pole color changes (burning changes green to black)
        if "burn" in action_lower and "pole" in action_lower:
            if "black" in obs_lower or "sooty" in obs_lower:
                self.pole_color = "black"
        
        # Track autobaker usage
        if "coin" in action_lower and "slot" in action_lower:
            self.autobaker_has_coin = True
        if "lever" in action_lower and "brick" in obs_lower:
            self.autobaker_has_coin = False
            if "brick" not in self.item_locations:
                self.item_locations["brick"] = "table_room"
    
    def get_state_summary(self) -> str:
        """Get Lost Pig-specific state summary."""
        lines = [
            f"=== Lost Pig Game State (Turn {self.turn}) ===",
            f"Player (Grunk) Location: {self.player_location or 'Unknown'}",
            f"Inventory ({len(self.inventory)}): {', '.join(self.inventory) if self.inventory else 'Empty'}",
        ]
        
        if "torch" in self.inventory:
            torch_status = "LIT" if self.torch_lit else "UNLIT"
            lines.append(f"Torch: {torch_status}")
        
        if "pole" in self.inventory:
            lines.append(f"Pole color: {self.pole_color}")
        
        if self.pig_found:
            if self.pig_caught:
                lines.append(f"Pig Status: CAUGHT")
            else:
                lines.append(f"Pig Status: FOUND at {self.pig_location}")
        else:
            lines.append("Pig Status: NOT FOUND")
        
        if self.puzzles_solved:
            lines.append(f"Puzzles Solved: {', '.join(self.puzzles_solved)}")
        
        if self.player_location and self.player_location in self.connections:
            exits = self.connections[self.player_location]
            lines.append(f"Exits: {', '.join(exits)}")
        
        # Show items in current location
        items_here = [item for item, loc in self.item_locations.items() if loc == self.player_location]
        if items_here:
            lines.append(f"Items here: {', '.join(items_here)}")
        
        return "\n".join(lines)
    
    def to_predicates(self) -> List[str]:
        """Convert to Lost Pig-specific predicates."""
        predicates = []
        
        if self.player_location:
            predicates.append(f"at(player, {self.player_location})")
        
        for item in self.inventory:
            predicates.append(f"has(player, {item})")
        
        for char, alive in self.character_states.items():
            if alive:
                predicates.append(f"alive({char})")
            else:
                predicates.append(f"not alive({char})")
        
        for loc1, exits in self.connections.items():
            for loc2 in exits:
                predicates.append(f"connected({loc1}, {loc2})")
        
        # Add Lost Pig specific predicates
        if self.pig_found:
            predicates.append(f"found({self.TARGET_ENTITY})")
            if self.pig_location:
                predicates.append(f"at({self.TARGET_ENTITY}, {self.pig_location})")
            if self.pig_caught:
                predicates.append(f"caught({self.TARGET_ENTITY})")
        
        for puzzle in self.puzzles_solved:
            predicates.append(f"solved({puzzle})")
        
        if "torch" in self.inventory:
            predicates.append(f"torch_lit({self.torch_lit})")
        
        if "pole" in self.inventory:
            predicates.append(f"pole_color({self.pole_color})")
        
        if self.secret_door_open:
            predicates.append("secret_door_open")
        
        return predicates
