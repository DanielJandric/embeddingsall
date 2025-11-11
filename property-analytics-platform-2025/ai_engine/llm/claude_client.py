from typing import Any, Dict, List, Optional
from anthropic import Anthropic
from ...config.settings import settings

class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.client = Anthropic(api_key=key)

    def simple_completion(self, prompt: str, model: str = "claude-sonnet-4-5") -> str:
        resp = self.client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text if resp and resp.content else ""


