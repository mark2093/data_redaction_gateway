"""
Luhn algorithm-based redaction engine for credit card validation.
"""
import re
import logging
from typing import List, Tuple, Optional, Any

from .base import BaseRedactionEngine
from ..core.models.redaction import RedactionRule
from ..core.exceptions import EngineError

logger = logging.getLogger(__name__)


class LuhnValidator:
    """Validator for credit card numbers using Luhn algorithm."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize Luhn validator.
        
        Args:
            enabled: Whether checksum validation is enabled
        """
        self.enabled = enabled
    
    def validate(self, number: str) -> bool:
        """
        Validate a number using the Luhn algorithm.
        
        Args:
            number: String of digits to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self.enabled:
            # If validation disabled, check basic format only
            clean = re.sub(r'[\s-]', '', number)
            return clean.isdigit() and 13 <= len(clean) <= 19
        
        # Remove spaces and dashes
        number = re.sub(r'[\s-]', '', number)
        
        if not number.isdigit():
            return False
        
        # Must be 13-19 digits for credit cards
        if not (13 <= len(number) <= 19):
            return False
        
        # Luhn algorithm
        digits = [int(d) for d in number]
        checksum = 0
        
        # Process from right to left
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:  # Every second digit from the right
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        
        return checksum % 10 == 0


class LuhnEngine(BaseRedactionEngine):
    """Luhn algorithm-based redaction engine."""
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize Luhn engine.
        
        Args:
            config: Application configuration
        """
        super().__init__(config=config)
        
        # Initialize Luhn validator with configuration
        validate_checksums = True
        if config and hasattr(config, 'redaction'):
            validate_checksums = getattr(config.redaction, 'validate_checksums', True)
        
        self.luhn_validator = LuhnValidator(enabled=validate_checksums)
    
    def detect(self, text: str, rule: RedactionRule) -> List[Tuple[int, int, str]]:
        """
        Detect credit card numbers using Luhn algorithm.
        
        Args:
            text: Text to analyze
            rule: Redaction rule (not used, but kept for interface consistency)
            
        Returns:
            List of (start, end, matched_text) tuples
        """
        # Find potential card numbers (13-19 digits with optional spaces/dashes)
        pattern = re.compile(r'\b\d[\d\s-]{11,17}\d\b')
        matches = []
        
        for match in pattern.finditer(text):
            potential_card = match.group(0)
            
            # Validate using Luhn
            if self.luhn_validator.validate(potential_card):
                matches.append((match.start(), match.end(), potential_card))
        
        return matches


__all__ = ["LuhnEngine", "LuhnValidator"]