"""
Anthropic provider for LLM judge.
"""
import logging
from typing import Dict, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic LLM provider."""
    
    def __init__(self, config):
        """Initialize Anthropic provider."""
        super().__init__(config)
        
        if not self.api_key or self.api_key == "null":
            raise ValueError("Anthropic API key not configured")
        
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        except ImportError:
            raise ImportError("anthropic package not installed")
    
    async def validate(self, context: Dict[str, Any]) -> str:
        """
        Validate using Anthropic API.
        
        Args:
            context: Validation context
            
        Returns:
            LLM response text
        """
        prompt = self._build_prompt(context)
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return response.content[0].text


__all__ = ["AnthropicProvider"]