"""
OpenAI provider for LLM judge.
"""
import logging
from typing import Dict, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, config):
        """Initialize OpenAI provider."""
        super().__init__(config)
        
        if not self.api_key or self.api_key == "null":
            raise ValueError("OpenAI API key not configured")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout
            )
        except ImportError:
            raise ImportError("openai package not installed")
    
    async def validate(self, context: Dict[str, Any]) -> str:
        """
        Validate using OpenAI API.
        
        Args:
            context: Validation context
            
        Returns:
            LLM response text
        """
        prompt = self._build_prompt(context)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a PII/PCI data redaction validation expert. "
                               "Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent validation
            max_tokens=500
        )
        
        return response.choices[0].message.content


__all__ = ["OpenAIProvider"]