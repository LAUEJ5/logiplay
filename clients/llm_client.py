from typing import Optional, List, Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        ...
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[List[str]] = None,
                                 invalid_actions: Optional[List[str]] = None) -> str:
        ...


class OpenAIClient:
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
        return self.generate(prompt, max_tokens=50, temperature=0.3)


class AnthropicClient:
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Install anthropic package: pip install anthropic")
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        return self.generate(prompt, max_tokens=50, temperature=0.3)


class GeminiClient:
    def __init__(self, model_name: str = "gemini-1.5-pro", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError("Install google-generativeai package: pip install google-generativeai")
    
    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7,
                 constraints: Optional[str] = None) -> str:
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text.strip()
    
    def generate_with_constraints(self, prompt: str, valid_actions: Optional[list] = None,
                                 invalid_actions: Optional[list] = None) -> str:
        return self.generate(prompt, max_tokens=50, temperature=0.3)


