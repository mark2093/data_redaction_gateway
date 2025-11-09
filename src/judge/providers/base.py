"""
Base LLM provider interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config):
        """
        Initialize provider with configuration.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
        self.timeout = config.timeout_seconds
    
    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> str:
        """
        Validate redaction using LLM.
        
        Args:
            context: Sanitized validation context
            
        Returns:
            LLM response string
        """
        pass
    
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
{context['redactions_applied']}

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


__all__ = ["BaseProvider"]