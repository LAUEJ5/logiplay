"""
Action Self-Verification Module

Validates that actions conform to parser grammar before symbolic checks.
Inspired by CS224N insights on action verification.
"""

import re
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result of action verification."""
    is_valid: bool
    error_message: Optional[str] = None
    normalized_action: Optional[str] = None


class ActionVerifier:
    """
    Verifies that actions are structurally valid commands.
    
    Maintains a cache of valid/invalid actions and uses pattern matching
    to ensure commands conform to expected grammar.
    """
    
    def __init__(self):
        self.valid_cache: set = set()
        self.invalid_cache: set = set()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for common command structures."""
        
        # Common verb patterns
        self.verb_patterns = [
            r"^(go|move|walk|run|travel)\s+(north|south|east|west|up|down|n|s|e|w|u|d|.*)$",
            r"^(take|get|pick\s+up|grab)\s+(?:the\s+)?(.+)$",
            r"^(drop|put\s+down|discard)\s+(?:the\s+)?(.+)$",
            r"^(use|activate|operate)\s+(?:the\s+)?(.+)$",
            r"^(look|examine|inspect|read)\s+(?:at\s+)?(?:the\s+)?(.+)?$",
            r"^(open|close|unlock|lock)\s+(?:the\s+)?(.+)$",
            r"^(talk|speak|say|tell)\s+(?:to\s+)?(.+)$",
            r"^(give|hand|offer)\s+(?:the\s+)?(.+)\s+(?:to\s+)?(.+)$",
            r"^(inventory|inv|i)$",
            r"^(look|examine|l)$",
            r"^(help|h)$",
            r"^(quit|exit|q)$",
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.verb_patterns]
    
    def verify(self, action: str) -> VerificationResult:
        """
        Verify action structure.
        
        Returns:
            VerificationResult with validity and normalized form
        """
        action = action.strip()
        
        # Check cache first
        if action.lower() in self.valid_cache:
            return VerificationResult(is_valid=True, normalized_action=action)
        
        if action.lower() in self.invalid_cache:
            return VerificationResult(
                is_valid=False,
                error_message="Action previously marked as invalid"
            )
        
        # Empty action
        if not action:
            self.invalid_cache.add(action.lower())
            return VerificationResult(
                is_valid=False,
                error_message="Empty action"
            )
        
        # Check against patterns
        for pattern in self.compiled_patterns:
            match = pattern.match(action)
            if match:
                # Normalize action
                normalized = self._normalize_action(action, match)
                self.valid_cache.add(action.lower())
                return VerificationResult(
                    is_valid=True,
                    normalized_action=normalized
                )
        
        # If no pattern matches, check if it's a simple direction
        simple_directions = ["n", "s", "e", "w", "u", "d", "north", "south", 
                           "east", "west", "up", "down"]
        if action.lower() in simple_directions:
            normalized = f"go {action.lower()}"
            self.valid_cache.add(action.lower())
            return VerificationResult(
                is_valid=True,
                normalized_action=normalized
            )
        
        # Action doesn't match known patterns
        # Could be valid but unusual - mark as potentially invalid
        # In practice, might want LLM to verify this
        self.invalid_cache.add(action.lower())
        return VerificationResult(
            is_valid=False,
            error_message=f"Action '{action}' does not match expected command structure"
        )
    
    def _normalize_action(self, action: str, match) -> str:
        """Normalize action to standard form."""
        # For now, just return cleaned version
        # Could expand to standardize verb forms, etc.
        return action.strip().lower()
    
    def verify_with_llm(self, action: str, llm_client) -> VerificationResult:
        """
        Use LLM to verify action if pattern matching fails.
        This is the 'self-verification' aspect.
        """
        prompt = f"""Is the following text adventure command valid?

Command: "{action}"

A valid command should:
- Be a simple action (go, take, use, look, etc.)
- Follow standard text adventure grammar
- Not be a question or statement

Respond with only "VALID" or "INVALID" followed by a brief reason."""

        try:
            response = llm_client.generate(prompt, max_tokens=50)
            response_lower = response.strip().lower()
            
            if response_lower.startswith("valid"):
                normalized = self._normalize_action(action, None)
                self.valid_cache.add(action.lower())
                return VerificationResult(
                    is_valid=True,
                    normalized_action=normalized
                )
            else:
                reason = response_lower.replace("invalid", "").strip()
                self.invalid_cache.add(action.lower())
                return VerificationResult(
                    is_valid=False,
                    error_message=reason or "LLM marked as invalid"
                )
        except Exception as e:
            # Fallback to pattern matching
            return self.verify(action)
    
    def get_verification_prompt(self) -> str:
        """Get prompt that helps LLM generate valid actions."""
        return """Generate a valid text adventure command. Valid commands include:
- Movement: "go north", "n", "south"
- Item actions: "take sword", "drop key", "use lamp"
- Examination: "look", "examine door", "read book"
- Interaction: "talk to guard", "give apple to merchant"
- System: "inventory", "help"

Keep commands simple and direct."""

