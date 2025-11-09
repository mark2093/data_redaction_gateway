"""
Regex-based redaction engine.
"""
import re
import logging
from typing import List, Tuple, Optional, Dict, Any

from .base import BaseRedactionEngine
from ..core.models.redaction import RedactionRule
from ..core.exceptions import EngineError

logger = logging.getLogger(__name__)


class RegexEngine(BaseRedactionEngine):
    """Regex-based redaction engine."""
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize regex engine.
        
        Args:
            config: Application configuration
        """
        super().__init__(config=config)
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        # Access case_sensitive from the RedactionConfig dataclass
        if config and hasattr(config, 'redaction'):
            self.case_sensitive = config.redaction.case_sensitive
        else:
            self.case_sensitive = False
    
    def detect(self, text: str, rule: RedactionRule) -> List[Tuple[int, int, str]]:
        """
        Detect sensitive data using regex patterns.
        
        Args:
            text: Text to analyze
            rule: Redaction rule with regex pattern
            
        Returns:
            List of (start, end, matched_text) tuples
        """
        if not rule.pattern:
            return []
        
        try:
            # Get or compile pattern
            pattern = self._get_compiled_pattern(rule)
            if not pattern:
                return []
            
            # Find all matches
            matches = []
            for match in pattern.finditer(text):
                matches.append((match.start(), match.end(), match.group(0)))
            
            return matches
            
        except Exception as e:
            logger.error(f"Regex detection error for rule {rule.id}: {e}")
            return []
    
    def _get_compiled_pattern(self, rule: RedactionRule) -> Optional[re.Pattern]:
        """
        Get compiled regex pattern for rule.
        
        Args:
            rule: Redaction rule
            
        Returns:
            Compiled regex pattern or None
        """
        if rule.id not in self.compiled_patterns:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self.compiled_patterns[rule.id] = re.compile(rule.pattern, flags)
                logger.debug(f"Compiled pattern for rule {rule.id}")
            except re.error as e:
                logger.error(f"Invalid regex pattern for rule {rule.id}: {e}")
                return None
        
        return self.compiled_patterns.get(rule.id)


__all__ = ["RegexEngine"]