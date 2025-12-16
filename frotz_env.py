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
            
            # Read initial output - we want to read until we get the first room description and prompt
            # This includes the game banner and the initial room description
            observation = self._read_output()
            
            # For reset, we want to extract just the initial room description
            # The output typically has: banner -> room title -> room description -> prompt
            # We want everything up to and including the room description, but not the prompt
            lines = observation.split('\n')
            
            # Find the room description part (usually starts with location name like "Outside")
            # and ends before any command echo or prompt
            cleaned_lines = []
            for line in lines:
                # Stop if we see a prompt or command echo
                if line.strip() == '>' or (line.strip().startswith('>') and len(line.strip()) > 1):
                    break
                # Skip game banner lines (version info, etc.)
                if any(banner in line for banner in ['Release', 'Serial number', 'Inform', 'ZCODE', 'For help']):
                    continue
                cleaned_lines.append(line)
            
            observation = '\n'.join(cleaned_lines).strip()
            
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
    
    def _read_output(self, timeout: float = None) -> str:
        """Read output from frotz process."""
        if not self.process:
            return ""
        
        output_lines = []
        saw_prompt = False
        no_output_count = 0
        max_no_output_waits = 10  # After 10 waits with no output, assume done
        
        # Read available output
        while True:
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
            
            # Try to read a line
            try:
                # Check if data is available
                ready, _, _ = select.select([self.process.stdout], [], [], 0.3)
                if ready:
                    line = self.process.stdout.readline()
                    if not line:
                        # Empty read - if we have output, wait longer for potential continuation
                        if output_lines:
                            # Give it multiple chances for more output
                            for _ in range(3):
                                time.sleep(0.2)
                                ready2, _, _ = select.select([self.process.stdout], [], [], 0.1)
                                if ready2:
                                    # More data available, try reading again
                                    line = self.process.stdout.readline()
                                    if line:
                                        break
                            # If still no line after waiting, we're probably done
                            if not line:
                                break
                            # If we got a line, continue processing it below
                        else:
                            # No output yet, keep waiting
                            no_output_count += 1
                            # If we've been waiting a long time with no output at all, probably done
                            # This handles cases where invalid commands don't produce any response
                            if no_output_count > max_no_output_waits:
                                # Been waiting too long with no output - might be invalid command or no response
                                break
                            continue
                    
                    if line:
                        no_output_count = 0  # Reset counter when we get output
                        line = line.rstrip('\n\r')
                        
                        # Skip empty lines unless we're building output
                        if not line.strip() and not output_lines:
                            continue
                        
                        # Check if this is the command echo
                        stripped = line.strip()
                        if stripped.startswith('>') and len(stripped) > 1:
                            after_arrow = stripped[1:].strip()
                            # Skip command echoes
                            if len(after_arrow) > 0 and len(after_arrow) < 50 and not any(c in after_arrow for c in ['(', '[', ']']):
                                continue
                        
                        # Check for prompt (">" standalone)
                        if stripped == '>':
                            saw_prompt = True
                            break
                        
                        # Regular output line
                        if line:
                            output_lines.append(line)
                else:
                    # No data available right now
                    if output_lines:
                        # We have output - wait longer to see if more comes
                        for _ in range(3):
                            time.sleep(0.2)
                            ready2, _, _ = select.select([self.process.stdout], [], [], 0.1)
                            if ready2:
                                # More data available, break to read it
                                break
                        else:
                            # No more data after waiting, we're done
                            break
                    else:
                        # No output yet, keep waiting
                        no_output_count += 1
                        # If we've been waiting a long time with no output at all, probably done
                        if no_output_count > max_no_output_waits:
                            # Been waiting too long with no output - might be invalid command or no response
                            break
                        time.sleep(0.1)
            except (ValueError, OSError, AttributeError):
                # Process may have closed or stdout unavailable
                break
        
        output_text = "\n".join(output_lines)
        
        # Strip ANSI escape codes more aggressively
        import re
        # Remove all ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output_text = ansi_escape.sub('', output_text)
        
        # Remove frotz-specific formatting codes like (B, (C, etc.
        # These are Inform 6 formatting codes: (B = bold, (C = color, etc.
        # Pattern is ( followed by a capital letter, possibly with = before it
        output_text = re.sub(r'=?\(' + r'[A-Z]' + r'\)?', '', output_text)  # Remove (B, (C, =(B, etc.
        
        # Clean up cursor positioning codes and other control characters
        output_text = re.sub(r'\[[\d;]*[HJKd]', '', output_text)  # Cursor movement
        output_text = re.sub(r'\[[\d;]*m', '', output_text)  # Color codes
        output_text = re.sub(r'\[[\d;]*r', '', output_text)  # Scroll region
        output_text = re.sub(r'\[[\?]?[\d;]*[hl]', '', output_text)  # Mode changes
        output_text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', output_text)  # Any remaining escape sequences
        
        # Remove control characters but keep newlines and tabs
        output_text = ''.join(char for char in output_text if ord(char) >= 32 or char in '\n\r\t')
        
        # Clean up multiple consecutive newlines
        output_text = re.sub(r'\n{3,}', '\n\n', output_text)
        
        # Remove command echoes that might have slipped through (lines starting with ">command")
        lines = output_text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines that are just command echoes
            if line.strip().startswith('>') and len(line.strip()) > 1 and not line.strip() == '>':
                # Check if it looks like a command (has spaces or is a single word after >)
                if ' ' in line.strip()[1:] or len(line.strip()) > 5:
                    continue
            cleaned_lines.append(line)
        
        output_text = '\n'.join(cleaned_lines)
        
        result = output_text.strip()
        
        # Always return something, even if empty, to prevent hanging
        # The caller will handle empty responses
        return result if result else ""
    
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
        
        # Read response - this should only be the NEW output after our action
        observation = self._read_output()
        
        # Clean up the observation - remove any duplicate intro text that frotz might re-display
        # Sometimes frotz re-displays the room description, we want to filter that out
        lines = observation.split('\n')
        cleaned_lines = []
        seen_intro = False
        for line in lines:
            # Skip game banner/intro lines if we've already seen them
            if any(banner in line for banner in ['Release', 'Serial number', 'Inform', 'ZCODE', 'For help']):
                if not seen_intro:
                    seen_intro = True
                continue
            # Skip lines that are just the game title repeated
            if line.strip() in ['Lost Pig', 'And Place Under Ground'] and seen_intro:
                continue
            cleaned_lines.append(line)
        
        observation = '\n'.join(cleaned_lines).strip()
        
        # Extract score if available - check for "[Grunk score go up one.]" message
        score_increase = "[Grunk score go up one.]" in observation
        if score_increase:
            self.score += 1
            score_change = 1.0
            self.max_score = max(self.max_score, self.score)
        else:
            # Fallback: try to extract from "Score: X" format if present
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



