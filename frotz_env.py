"""
Frotz Environment Wrapper for Lost Pig

Uses the system frotz binary to run Lost Pig game files directly.
This provides a clean interface to the actual game without external dependencies.
"""

import os
import subprocess
import re
from typing import Tuple, Optional, Dict, Any
import tempfile
import time
import select
import sys


class FrotzEnv:
    """
    Wrapper for frotz command-line interpreter to run Lost Pig.
    
    This provides the interface expected by LogicAwareAgent:
    - reset() -> observation string
    - step(action: str) -> (observation, reward, done, info)
    """
    
    def __init__(self, game_file: Optional[str] = None, seed: int = 42):
        """
        Initialize Frotz environment for Lost Pig.
        
        Args:
            game_file: Path to Lost Pig game file (.z5 or .z8).
                      If None, searches for lostpig.z5 or lostpig.z8 in:
                      - games/ directory
                      - current directory
            seed: Random seed (not used by frotz, but kept for compatibility)
        """
        # Find game file
        if game_file is None:
            game_file = self._find_game_file()
        
        if not os.path.exists(game_file):
            raise FileNotFoundError(
                f"Lost Pig game file not found: {game_file}\n"
                f"Download from https://ifdb.org/viewgame?id=mohwfk47yjzii14w\n"
                f"Or search for 'Lost Pig' on ifdb.org\n"
                f"Save as 'lostpig.z5' or 'lostpig.z8' in games/ directory"
            )
        
        self.game_file = game_file
        self.seed = seed
        
        # Frotz process
        self.process: Optional[subprocess.Popen] = None
        
        # Track episode state
        self.turn_count = 0
        self.max_score = 0
        self.score = 0
    
    def _find_game_file(self) -> str:
        """Search for Lost Pig game file in common locations."""
        possible_names = ["lostpig.z5", "lostpig.z8", "lost_pig.z5", "lost_pig.z8"]
        possible_dirs = [
            "games",
            ".",
            os.path.expanduser("~/games"),
        ]
        
        for directory in possible_dirs:
            for name in possible_names:
                path = os.path.join(directory, name)
                if os.path.exists(path):
                    return path
        
        # Return default path for error message
        return os.path.join("games", "lostpig.z8")
    
    def reset(self) -> str:
        """
        Reset the game to initial state.
        
        Returns:
            Initial observation text from the game
        """
        # Close existing process if any
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass
        
        # Start new frotz process
        # Use -i for interpreter mode (better for automation)
        # Use -s for save file (we'll use temp file)
        self.temp_save = tempfile.NamedTemporaryFile(delete=False, suffix='.sav')
        self.temp_save.close()
        
        try:
            # Use frotz in plain mode (no curses)
            # -i = interpreter mode, -p = plain output
            self.process = subprocess.Popen(
                ["frotz", "-p", self.game_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Read initial output
            observation = self._read_output()
            
            self.turn_count = 0
            self.max_score = 0
            self.score = 0
            
            return observation
        except FileNotFoundError:
            raise FileNotFoundError(
                "frotz command not found. Install with:\n"
                "  macOS: brew install frotz\n"
                "  Linux: sudo apt-get install frotz\n"
                "  Or download from: https://frotz.sourceforge.net/"
            )
    
    def _read_output(self, timeout: float = 2.0) -> str:
        """Read output from frotz process."""
        if not self.process:
            return ""
        
        output_lines = []
        start_time = time.time()
        saw_prompt = False
        
        # Read available output
        while time.time() - start_time < timeout:
            # Check if process is still running
            if self.process.poll() is not None:
                # Process ended, read remaining output
                try:
                    remaining = self.process.stdout.read()
                    if remaining:
                        output_lines.extend(remaining.splitlines())
                except:
                    pass
                break
            
            # Try to read a line (non-blocking)
            try:
                # Check if data is available
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline()
                    if not line:
                        if output_lines:
                            break  # Got some output, process might be waiting
                        continue
                    line = line.rstrip()
                    if line:
                        output_lines.append(line)
                    # Check for prompt (">" at end of line or standalone)
                    if '>' in line:
                        saw_prompt = True
                        # Give a tiny bit more time for any trailing text
                        time.sleep(0.05)
                        break
                else:
                    # No more data available
                    if output_lines:
                        # If we have output but no prompt yet, wait a bit more
                        if not saw_prompt:
                            time.sleep(0.1)
                            continue
                        break
                    elif time.time() - start_time > 0.5:
                        # Been waiting, probably no more output
                        break
            except (ValueError, OSError, AttributeError):
                # Process may have closed or stdout unavailable
                break
        
        return "\n".join(output_lines)
    
    def step(self, action: str) -> Tuple[str, float, bool, Dict[str, Any]]:
        """
        Execute an action in the game.
        
        Args:
            action: Text command (e.g., "go north", "take torch")
        
        Returns:
            Tuple of (observation, reward, score_change, done, info):
            - observation: Text description of new game state
            - reward: Score change (if available)
            - done: Whether episode is finished
            - info: Additional info (score, turn, etc.)
        """
        if not self.process:
            raise RuntimeError("Game not initialized. Call reset() first.")
        
        self.turn_count += 1
        
        # Send action to frotz
        try:
            if self.process.stdin:
                self.process.stdin.write(action + "\n")
                self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            # Process may have ended
            pass
        
        # Read response
        observation = self._read_output()
        
        # Extract score if available
        score_match = re.search(r'Score:\s*(\d+)', observation, re.IGNORECASE)
        if score_match:
            new_score = int(score_match.group(1))
            score_change = new_score - self.score
            self.score = new_score
            self.max_score = max(self.max_score, self.score)
        else:
            score_change = 0.0
        
        # Check for game over
        done = False
        if any(phrase in observation.lower() for phrase in [
            "you have won", "you won", "game over", "the end",
            "grunk bring pig back", "boss happy"
        ]):
            done = True
        
        # Check if process ended
        if self.process.poll() is not None:
            done = True
            # Read any remaining output
            remaining = self.process.stdout.read()
            if remaining:
                observation += "\n" + remaining
        
        info = {
            "turn": self.turn_count,
            "score": self.score,
            "max_score": self.max_score
        }
        
        return observation, float(score_change), done, info
    
    def close(self):
        """Close the environment."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
        
        # Clean up temp save file
        if hasattr(self, 'temp_save') and os.path.exists(self.temp_save.name):
            try:
                os.unlink(self.temp_save.name)
            except:
                pass


def create_lost_pig_env(game_file: Optional[str] = None, seed: int = 42) -> FrotzEnv:
    """
    Factory function to create a Lost Pig Frotz environment.
    
    Args:
        game_file: Path to Lost Pig game file. If None, auto-detects.
        seed: Random seed (for compatibility, not used by frotz)
    
    Returns:
        FrotzEnv instance
    """
    return FrotzEnv(game_file=game_file, seed=seed)


# Check if frotz is available
# Try to find frotz in common locations or PATH
FROTZ_AVAILABLE = False
frotz_paths = ["frotz", "/opt/homebrew/bin/frotz", "/usr/local/bin/frotz", "/usr/bin/frotz"]
for frotz_path in frotz_paths:
    try:
        # frotz doesn't have --version, but we can check if it exists and is executable
        result = subprocess.run(["which", frotz_path] if "/" not in frotz_path else ["test", "-x", frotz_path],
                              capture_output=True, 
                              timeout=1)
        if result.returncode == 0:
            FROTZ_AVAILABLE = True
            break
    except:
        # Try direct path check
        if os.path.exists(frotz_path) and os.access(frotz_path, os.X_OK):
            FROTZ_AVAILABLE = True
            break


# Example usage
if __name__ == "__main__":
    # Test the environment
    try:
        env = create_lost_pig_env()
        obs = env.reset()
        print("Initial observation:")
        print(obs)
        print("\n" + "="*60 + "\n")
        
        # Try a few actions
        test_actions = ["look", "go north", "take torch"]
        for action in test_actions:
            print(f"Action: {action}")
            obs, reward, done, info = env.step(action)
            print(f"Reward: {reward}, Done: {done}, Score: {info.get('score', 0)}")
            print(f"Observation (first 200 chars):\n{obs[:200]}...")
            print("\n" + "-"*60 + "\n")
            if done:
                break
        
        env.close()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nTo use Frotz with Lost Pig:")
        print("1. Install frotz: brew install frotz (macOS) or sudo apt-get install frotz (Linux)")
        print("2. Download Lost Pig from https://ifdb.org")
        print("3. Save as 'games/lostpig.z5' or 'games/lostpig.z8'")

