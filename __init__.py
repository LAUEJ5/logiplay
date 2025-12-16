"""
Logic-Aware LLM Agents for Lost Pig

A framework for building LLM agents that maintain logical world-state consistency
in Lost Pig text adventure game, using LMQL-style constraint-based reasoning.
"""

from agent import LogicAwareAgent
from evaluation import AchievementEvaluator
from example_llm_client import LLMClient
from world_state import WorldState

__version__ = "0.1.0"

__all__ = [
    "LogicAwareAgent",
    "LLMClient",
    "AchievementEvaluator",
    "WorldState",
]
