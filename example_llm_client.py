"""
LLM Client Implementation

Provides OpenAI API client for the Lost Pig agent.
"""

from typing import Optional, List
from agent import LLMClient


class OpenAIClient:
    """OpenAI API client implementation."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Install openai package: pip install openai")
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        """Generate using OpenAI API."""
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        """Generate with constraint guidance."""
        return self.generate(prompt, max_tokens=50, temperature=0.3)


