"""
LLM-as-Judge module for validating redaction quality.

This module uses Large Language Models to validate
that PII/PCI redaction is complete and accurate.
"""
import asyncio
import json
import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.models.redaction import RedactionMeta
from ..core.models.api import JudgeResult
from ..core.exceptions import JudgeError

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-based validation of redaction quality.
    
    Samples a percentage of requests and sends sanitized context to an LLM
    to validate redaction coverage and quality.
    """
    
    def __init__(self, config=None):
        """
        Initialize LLM Judge.
        
        Args:
            config: Application configuration (uses get_config() if not provided)
        """
        if config is None:
            from ..config import get_config
            config = get_config()
            
        self.config = config
        self.judge_config = self.config.llm_judge
        
        # Initialize LLM client based on provider
        self.client = None
        if self.judge_config.enabled:
            self._init_client()
        
        # Tracking
        self.calls_this_hour = 0
        self.calls_this_day = 0
        self.last_reset_hour = datetime.utcnow().hour
        self.last_reset_day = datetime.utcnow().day
    
    def _init_client(self):
        """Initialize the appropriate LLM client."""
        provider = self.judge_config.provider.lower() if self.judge_config.provider else ""
        
        if provider == "openai":
            from .providers.openai import OpenAIProvider
            try:
                self.client = OpenAIProvider(self.judge_config)
                logger.info(f"LLM Judge initialized with OpenAI model: {self.judge_config.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
                self.judge_config.enabled = False
        
        elif provider == "anthropic":
            from .providers.anthropic import AnthropicProvider
            try:
                self.client = AnthropicProvider(self.judge_config)
                logger.info(f"LLM Judge initialized with Anthropic model: {self.judge_config.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
                self.judge_config.enabled = False
        
        else:
            logger.error(f"Unsupported LLM provider: {provider}")
            self.judge_config.enabled = False
    
    def should_sample(self) -> bool:
        """
        Determine if current request should be sampled for LLM validation.
        
        Returns:
            True if request should be sampled, False otherwise
        """
        if not self.judge_config.enabled:
            return False
        
        # Check budget limits
        if not self._check_budget():
            return False
        
        # Random sampling based on configured rate
        return random.random() < self.judge_config.sampling_rate
    
    def _check_budget(self) -> bool:
        """
        Check if budget limits allow for another LLM call.
        
        Returns:
            True if within budget, False if limit exceeded
        """
        current_hour = datetime.utcnow().hour
        current_day = datetime.utcnow().day
        
        # Reset hourly counter
        if current_hour != self.last_reset_hour:
            self.calls_this_hour = 0
            self.last_reset_hour = current_hour
        
        # Reset daily counter
        if current_day != self.last_reset_day:
            self.calls_this_day = 0
            self.last_reset_day = current_day
        
        # Check limits
        budget = self.judge_config.budget
        
        if self.calls_this_hour >= budget.get('max_calls_per_hour', 100):
            if budget.get('alert_on_limit', True):
                logger.warning(f"LLM judge hourly budget exceeded: {self.calls_this_hour}")
            return False
        
        if self.calls_this_day >= budget.get('max_calls_per_day', 1000):
            if budget.get('alert_on_limit', True):
                logger.warning(f"LLM judge daily budget exceeded: {self.calls_this_day}")
            return False
        
        return True
    
    async def validate_redaction(
        self,
        original_data: Any,
        redacted_data: Any,
        redaction_meta: List[RedactionMeta]
    ) -> Optional[JudgeResult]:
        """
        Validate redaction quality using LLM.
        
        Args:
            original_data: Original data before redaction
            redacted_data: Data after redaction
            redaction_meta: Metadata about redactions performed
            
        Returns:
            JudgeResult if validation succeeds, None on error/timeout
        """
        if not self.judge_config.enabled or not self.client:
            return None
        
        start_time = datetime.utcnow()
        
        try:
            # Prepare sanitized context
            context = self._prepare_context(original_data, redacted_data, redaction_meta)
            
            # Call LLM with timeout
            response = await asyncio.wait_for(
                self.client.validate(context),
                timeout=self.judge_config.timeout_seconds
            )
            
            # Parse response
            result = self._parse_response(response)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update tracking
            self.calls_this_hour += 1
            self.calls_this_day += 1
            
            # Add processing time and sampling flag
            result['processing_time_ms'] = processing_time
            result['sampled'] = True
            
            logger.info(
                f"LLM judge validation complete: coverage={result.get('coverage_complete')}, "
                f"confidence={result.get('confidence')}%, time={processing_time:.2f}ms"
            )
            
            return JudgeResult(**result)
        
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM judge timeout after {self.judge_config.timeout_seconds}s - "
                "falling back to rules-only"
            )
            return None
        
        except Exception as e:
            logger.error(f"LLM judge error: {e}", exc_info=True)
            if not self.judge_config.fallback_on_error:
                raise JudgeError(f"LLM judge validation failed: {e}")
            return None
    
    def _prepare_context(
        self,
        original_data: Any,
        redacted_data: Any,
        redaction_meta: List[RedactionMeta]
    ) -> Dict[str, Any]:
        """
        Prepare sanitized context for LLM validation.
        """
        max_chars = self.judge_config.validation.get('max_context_chars', 500)
        include_partial_mask = self.judge_config.validation.get('include_partial_mask', True)
        
        def snippet_limit(value: Any, max_length: int = max_chars) -> Any:
            """Limit string length for context."""
            if isinstance(value, str):
                if len(value) > max_length:
                    return value[:max_length] + "..."
                return value
            elif isinstance(value, dict):
                return {k: snippet_limit(v, max_length) for k, v in value.items()}
            elif isinstance(value, list):
                return [snippet_limit(item, max_length) for item in value[:10]]
            return value
        
        # Prepare original context (snippet-limited)
        original_context = snippet_limit(original_data)
        
        # Build context
        context = {
            "original_snippet": json.dumps(original_context, indent=2),
            "redacted_data": json.dumps(snippet_limit(redacted_data), indent=2),
            "redactions_applied": [
                {
                    "field": meta.field,
                    "rule": meta.rule,
                    "action": meta.action.value if hasattr(meta.action, 'value') else str(meta.action)
                }
                for meta in redaction_meta
            ],
            "redaction_count": len(redaction_meta)
        }
        
        return context
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        """
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            result = json.loads(response)
            
            # Ensure required fields exist with defaults
            return {
                'coverage_complete': result.get('coverage_complete', True),
                'over_redacted': result.get('over_redacted', False),
                'under_redacted': result.get('under_redacted', False),
                'confidence': float(result.get('confidence', 50.0)),
                'suggestions': result.get('suggestions', [])
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            
            # Return conservative defaults on parse error
            return {
                'coverage_complete': False,
                'over_redacted': False,
                'under_redacted': True,
                'confidence': 0.0,
                'suggestions': ["Failed to parse LLM response"]
            }


# Singleton instance
_llm_judge: Optional[LLMJudge] = None


def get_llm_judge() -> LLMJudge:
    """
    Get singleton LLM judge instance.
    
    Returns:
        LLMJudge instance
    """
    global _llm_judge
    if _llm_judge is None:
        _llm_judge = LLMJudge()
    return _llm_judge


__all__ = ["LLMJudge", "get_llm_judge"]