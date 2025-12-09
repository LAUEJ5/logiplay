"""
Logic-Aware LLM Agents for Lost Pig

A framework for building LLM agents that maintain logical world-state consistency
in Lost Pig text adventure game, using LMQL-style constraint-based reasoning.
"""

from .agent import LogicAwareAgent
from .world_state import WorldState
from .constraints import ConstraintChecker, ConstraintType, ConstraintViolation
from .action_verifier import ActionVerifier, VerificationResult
from .evaluation import AchievementEvaluator, Achievement
from .example_llm_client import LLMClient

__version__ = "0.1.0"

__all__ = [
    "LogicAwareAgent",
    "LLMClient",
    "WorldState",
    "ConstraintChecker",
    "ConstraintType",
    "ConstraintViolation",
    "ActionVerifier",
    "VerificationResult",
    "AchievementEvaluator",
    "Achievement",
]
