"""
LLM-as-Judge module for validating redaction quality.

This module uses Large Language Models (OpenAI, Anthropic) to validate
that PII/PCI redaction is complete and accurate. It samples a percentage
of requests and provides feedback on coverage, over-redaction, and 
under-redaction.
"""
import asyncio
import json
import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from .models import RedactionMeta, JudgeResult
from .config_loader import get_config

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
        self.config = config or get_config()
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
        provider = self.judge_config.provider.lower()
        
        if provider == "openai":
            api_key = self.judge_config.api_key
            if not api_key or api_key == "null":
                logger.warning("OpenAI API key not configured - LLM judge will be disabled")
                self.judge_config.enabled = False
                return
            
            self.client = AsyncOpenAI(
                api_key=api_key,
                timeout=self.judge_config.timeout_seconds
            )
            logger.info(f"LLM Judge initialized with OpenAI model: {self.judge_config.model}")
        
        elif provider == "anthropic":
            api_key = self.judge_config.api_key
            if not api_key or api_key == "null":
                logger.warning("Anthropic API key not configured - LLM judge will be disabled")
                self.judge_config.enabled = False
                return
            
            self.client = AsyncAnthropic(
                api_key=api_key,
                timeout=self.judge_config.timeout_seconds
            )
            logger.info(f"LLM Judge initialized with Anthropic model: {self.judge_config.model}")
        
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
    
    def _prepare_context(
        self,
        original_data: Any,
        redacted_data: Any,
        redaction_meta: List[RedactionMeta]
    ) -> Dict[str, Any]:
        """
        Prepare sanitized context for LLM validation.
        
        Never sends raw PII - uses snippet limiting and partial masking.
        
        Args:
            original_data: Original data (will be snippet-limited)
            redacted_data: Redacted data
            redaction_meta: Metadata about redactions performed
            
        Returns:
            Sanitized context dictionary
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
                return [snippet_limit(item, max_length) for item in value[:10]]  # Limit list size too
            return value
        
        def apply_partial_mask(value: str) -> str:
            """Apply partial masking to show structure without exposing PII."""
            if not value or len(value) <= 4:
                return "*" * len(value)
            return "*" * (len(value) - 4) + value[-4:]
        
        # Prepare original context (snippet-limited and optionally partially masked)
        original_context = snippet_limit(original_data)
        
        if include_partial_mask and isinstance(original_context, dict):
            # Apply partial masking to fields that were redacted
            redacted_fields = {meta.field for meta in redaction_meta}
            for field in redacted_fields:
                if field in original_context and isinstance(original_context[field], str):
                    original_context[field] = apply_partial_mask(original_context[field])
        
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
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build validation prompt for LLM.
        
        Args:
            context: Sanitized context dictionary
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a PII/PCI data redaction validation expert. Your task is to assess the quality of data redaction performed on sensitive information.

**Original Data (snippet-limited, partially masked):**
```json
{context['original_snippet']}
```

**Redacted Data:**
```json
{context['redacted_data']}
```

**Redactions Applied ({context['redaction_count']} total):**
{json.dumps(context['redactions_applied'], indent=2)}

**Assessment Criteria:**
1. **Coverage**: Are all PII/PCI fields properly redacted? Look for:
   - Email addresses
   - Phone numbers
   - Credit card numbers (PANs)
   - Account numbers
   - IBAN codes
   - SSN/tax IDs
   - Person names
   - Any other sensitive personal information

2. **Over-Redaction**: Were non-sensitive fields unnecessarily redacted?
   - Transaction IDs, order IDs should NOT be redacted
   - Amounts, currencies should NOT be redacted
   - Timestamps should NOT be redacted
   - Merchant names should NOT be redacted

3. **Under-Redaction**: Are there any unredacted sensitive fields that should have been redacted?

4. **Confidence**: How confident are you in this assessment (0-100%)?

**Response Format (JSON only, no explanation):**
```json
{{
  "coverage_complete": true/false,
  "over_redacted": false,
  "under_redacted": false,
  "confidence": 95,
  "suggestions": ["optional improvement feedback"]
}}
```

Respond with ONLY the JSON, no additional text."""

        return prompt
    
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
            
            # Build prompt
            prompt = self._build_prompt(context)
            
            # Call LLM with timeout
            if self.judge_config.provider.lower() == "openai":
                response = await asyncio.wait_for(
                    self._call_openai(prompt),
                    timeout=self.judge_config.timeout_seconds
                )
            elif self.judge_config.provider.lower() == "anthropic":
                response = await asyncio.wait_for(
                    self._call_anthropic(prompt),
                    timeout=self.judge_config.timeout_seconds
                )
            else:
                logger.error(f"Unsupported provider: {self.judge_config.provider}")
                return None
            
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
                raise
            return None
    
    async def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API.
        
        Args:
            prompt: Validation prompt
            
        Returns:
            LLM response text
        """
        response = await self.client.chat.completions.create(
            model=self.judge_config.model,
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
    
    async def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic API.
        
        Args:
            prompt: Validation prompt
            
        Returns:
            LLM response text
        """
        response = await self.client.messages.create(
            model=self.judge_config.model,
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
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed response dictionary
        """
        try:
            # Try to extract JSON from response
            # LLMs sometimes wrap JSON in markdown code blocks
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
