"""
Example LLM Client Implementation

Shows how to integrate with actual LLM APIs.
This is a template - users should implement their preferred provider.
"""

from typing import Optional, List
from agent import LLMClient


class OpenAIClient:
    """OpenAI API client implementation."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
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


class AnthropicClient:
    """Anthropic Claude API client implementation."""
    
    def __init__(self, model_name: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Install anthropic package: pip install anthropic")
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        """Generate using Anthropic API."""
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text.strip()
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        """Generate with constraint guidance."""
        return self.generate(prompt, max_tokens=50, temperature=0.3)


class GeminiClient:
    """Google Gemini API client implementation."""
    
    def __init__(self, model_name: str = "gemini-pro", api_key: Optional[str] = None):
        # Try gemini-pro first (most stable), or gemini-2.0-flash, gemini-2.5-pro for newer models
        # If you get 404 errors, try: gemini-pro, gemini-1.5-pro, gemini-2.0-flash
        self.model_name = model_name
        try:
            import google.generativeai as genai
            self.genai = genai
            
            # Get API key from parameter or environment
            import os
            if not api_key:
                api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                raise ValueError("Gemini API key required. Set GEMINI_API_KEY env var or pass api_key parameter")
            
            self.api_key = api_key
            genai.configure(api_key=api_key)
        except ImportError:
            raise ImportError("Install google-generativeai package: pip install google-generativeai")
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        """Generate using Gemini API with retry logic for rate limits."""
        import time
        import random
        
        # Configure generation parameters
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        # Try multiple model names in order of preference
        model_names_to_try = [self.model_name, "gemini-pro", "gemini-1.5-pro", "gemini-2.0-flash"]
        
        last_error = None
        for model_name in model_names_to_try:
            # Retry logic for rate limits (429 errors)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    model = self.genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    # If successful, update self.model_name for future calls
                    if model_name != self.model_name:
                        self.model_name = model_name
                    return response.text.strip()
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                        if attempt < max_retries - 1:
                            # Extract retry delay if available, otherwise use exponential backoff
                            wait_time = 15 + (attempt * 5) + random.uniform(0, 5)
                            if "retry in" in error_str.lower():
                                # Try to extract the suggested wait time
                                import re
                                match = re.search(r'retry in ([\d.]+)s', error_str.lower())
                                if match:
                                    wait_time = float(match.group(1)) + 2
                            print(f"⚠️  Rate limit hit. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                            time.sleep(wait_time)
                            continue
                    # For non-rate-limit errors or final attempt, move to next model
                    last_error = e
                    break
        
        # If all models failed, provide helpful error message
        error_msg = str(last_error)
        if "429" in error_msg or "quota" in error_msg.lower():
            raise RuntimeError(
                f"Gemini API quota/rate limit exceeded.\n"
                f"Options:\n"
                f"  1. Wait a few minutes and try again\n"
                f"  2. Check your usage: https://ai.dev/usage?tab=rate-limit\n"
                f"  3. Use mock LLM for testing: ./run.sh --llm mock\n"
                f"  4. Try a different API key\n"
                f"\nOriginal error: {error_msg[:200]}"
            )
        raise RuntimeError(f"All model attempts failed. Last error: {last_error}")
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        """Generate with constraint guidance."""
        return self.generate(prompt, max_tokens=50, temperature=0.3)


class MockLLMClient:
    """
    Mock LLM client for testing without API calls.
    Returns simple template responses.
    """
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        """Return mock response."""
        prompt_lower = prompt.lower()
        
        if "think" in prompt_lower or "thought" in prompt_lower:
            return "I should explore the area and look for useful items."
        
        if "action" in prompt_lower or "command" in prompt_lower:
            if "north" in prompt_lower or "go" in prompt_lower:
                return "go north"
            elif "take" in prompt_lower or "get" in prompt_lower:
                return "take key"
            else:
                return "look"
        
        return "Mock response"
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        """Return mock constrained response."""
        if valid_actions:
            return valid_actions[0]
        return "look"


