"""
Core redaction engine with PII/PCI detection and redaction logic.
Configuration-driven redaction based on YAML settings.
"""
import re
import hashlib
import hmac
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import json
import logging

from src.models import RedactionAction, RedactionMeta, RedactionRule
from src.config_loader import get_config

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


class RedactionEngine:
    """Main engine for detecting and redacting sensitive data. Configuration-driven."""
    
    def __init__(self, rules: List[RedactionRule], config: Optional[Any] = None):
        """
        Initialize the redaction engine.
        
        Args:
            rules: List of redaction rules to apply
            config: Application configuration (loaded from YAML)
        """
        # Load configuration
        if config is None:
            config = get_config()
        self.config = config
        
        # Filter enabled rules
        self.rules = [rule for rule in rules if rule.enabled]
        
        # Get HMAC key from config
        self.hmac_key = self.config.security.hmac_secret
        
        # Initialize Luhn validator with config
        validate_checksums = self.config.redaction.validate_checksums
        self.luhn_validator = LuhnValidator(enabled=validate_checksums)
        
        # Redaction metadata
        self.redaction_meta: List[RedactionMeta] = []
        
        # Get configuration settings
        self.show_last_n_chars = self.config.redaction.show_last_n_chars
        self.exclude_fields = set(self.config.redaction.exclude_fields)
        self.always_redact_fields = set(self.config.redaction.always_redact_fields)
        self.case_sensitive = self.config.redaction.case_sensitive
        
        # Compile regex patterns for efficiency
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        for rule in self.rules:
            if rule.pattern:
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    self.compiled_patterns[rule.id] = re.compile(rule.pattern, flags)
                except re.error as e:
                    logger.error(f"Invalid regex pattern for rule {rule.id}: {e}")
        
        # Initialize NER if needed and enabled
        self.ner_engine = None
        if self.config.redaction.ner.enabled and any(rule.engine == "NER" for rule in self.rules):
            self._init_ner()
    
    def _init_ner(self):
        """Initialize spaCy NER model from configuration."""
        try:
            import spacy
            model_name = self.config.redaction.ner.model
            self.ner_engine = spacy.load(model_name)
            self.ner_confidence_threshold = self.config.redaction.ner.confidence_threshold
            self.ner_entity_types = set(self.config.redaction.ner.entity_types)
            logger.info(f"NER engine initialized: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize NER engine: {e}")
            self.ner_engine = None
    
    def redact(self, data: Union[Dict, List, str], path: str = "$") -> Union[Dict, List, str]:
        """
        Redact sensitive data from input.
        
        Args:
            data: Input data to redact
            path: JSONPath to current location (for metadata)
            
        Returns:
            Redacted data
        """
        self.redaction_meta = []  # Reset metadata
        
        if isinstance(data, dict):
            return self._redact_dict(data, path)
        elif isinstance(data, list):
            return self._redact_list(data, path)
        elif isinstance(data, str):
            return self._redact_string(data, path)
        else:
            return data
    
    def _redact_dict(self, data: Dict[str, Any], path: str) -> Dict[str, Any]:
        """Redact sensitive data from dictionary."""
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}"
            
            # Check if field should be excluded from redaction
            if key in self.exclude_fields:
                result[key] = value
                continue
            
            # Check if field should always be redacted
            if key in self.always_redact_fields:
                if isinstance(value, str):
                    result[key] = self._mask_value(value)
                    self.redaction_meta.append(
                        RedactionMeta(
                            field=key,
                            rule="ALWAYS_REDACT",
                            action=RedactionAction.MASK
                        )
                    )
                else:
                    result[key] = "***REDACTED***"
                continue
            
            if isinstance(value, dict):
                result[key] = self._redact_dict(value, current_path)
            elif isinstance(value, list):
                result[key] = self._redact_list(value, current_path)
            elif isinstance(value, str):
                result[key] = self._redact_string(value, current_path, field_name=key)
            else:
                result[key] = value
        
        return result
    
    def _redact_list(self, data: List[Any], path: str) -> List[Any]:
        """Redact sensitive data from list."""
        result = []
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            
            if isinstance(item, dict):
                result.append(self._redact_dict(item, current_path))
            elif isinstance(item, list):
                result.append(self._redact_list(item, current_path))
            elif isinstance(item, str):
                result.append(self._redact_string(item, current_path))
            else:
                result.append(item)
        
        return result
    
    def _redact_string(self, text: str, path: str, field_name: Optional[str] = None) -> str:
        """
        Redact sensitive data from string.
        
        Args:
            text: String to redact
            path: JSONPath to current location
            field_name: Field name for context
            
        Returns:
            Redacted string
        """
        if not text or not isinstance(text, str):
            return text
        
        redacted_text = text
        
        # Apply each rule
        for rule in self.rules:
            if rule.engine == "NER":
                redacted_text = self._apply_ner_redaction(redacted_text, rule, path, field_name)
            elif rule.id == "LUHN_PAN":
                redacted_text = self._apply_luhn_redaction(redacted_text, rule, path, field_name)
            elif rule.pattern:
                redacted_text = self._apply_regex_redaction(redacted_text, rule, path, field_name)
        
        return redacted_text
    
    def _apply_regex_redaction(
        self, text: str, rule: RedactionRule, path: str, field_name: Optional[str]
    ) -> str:
        """Apply regex-based redaction."""
        if rule.id not in self.compiled_patterns:
            return text
        
        pattern = self.compiled_patterns[rule.id]
        matches = list(pattern.finditer(text))
        
        if not matches:
            return text
        
        # Process matches in reverse to maintain string indices
        for match in reversed(matches):
            original_value = match.group(0)
            redacted_value = self._apply_action_with_config(original_value, rule)
            text = text[:match.start()] + redacted_value + text[match.end():]
            
            # Record metadata
            self.redaction_meta.append(
                RedactionMeta(
                    field=field_name or path,
                    rule=rule.id,
                    action=rule.action
                )
            )
        
        return text
    
    def _apply_luhn_redaction(
        self, text: str, rule: RedactionRule, path: str, field_name: Optional[str]
    ) -> str:
        """Apply Luhn algorithm-based credit card detection and redaction."""
        # Find potential card numbers (13-19 digits with optional spaces/dashes)
        pattern = re.compile(r'\b\d[\d\s-]{11,17}\d\b')
        matches = list(pattern.finditer(text))
        
        if not matches:
            return text
        
        # Process matches in reverse
        for match in reversed(matches):
            potential_card = match.group(0)
            
            # Validate using Luhn
            if self.luhn_validator.validate(potential_card):
                redacted_value = self._apply_action_with_config(potential_card, rule)
                text = text[:match.start()] + redacted_value + text[match.end():]
                
                # Record metadata
                self.redaction_meta.append(
                    RedactionMeta(
                        field=field_name or path,
                        rule=rule.id,
                        action=rule.action
                    )
                )
        
        return text
    
    def _apply_ner_redaction(
        self, text: str, rule: RedactionRule, path: str, field_name: Optional[str]
    ) -> str:
        """Apply NER-based redaction for person names."""
        if not self.ner_engine:
            return text
        
        try:
            doc = self.ner_engine(text)
            
            # Process entities in reverse to maintain indices
            for ent in reversed(doc.ents):
                # Check if entity type is in configured types
                if ent.label_ in self.ner_entity_types:
                    # Check confidence threshold if available
                    # Note: spaCy doesn't provide confidence by default, but we keep the structure
                    redacted_value = self._apply_action_with_config(ent.text, rule)
                    text = text[:ent.start_char] + redacted_value + text[ent.end_char:]
                    
                    # Record metadata
                    self.redaction_meta.append(
                        RedactionMeta(
                            field=field_name or path,
                            rule=rule.id,
                            action=rule.action
                        )
                    )
        except Exception as e:
            logger.error(f"NER processing error: {e}")
        
        return text
    
    def _apply_action(self, value: str, action: RedactionAction) -> str:
        """
        Apply redaction action to a value (legacy method).
        
        Args:
            value: Original value
            action: Redaction action to apply
            
        Returns:
            Redacted value
        """
        if action == RedactionAction.MASK:
            return self._mask_value(value)
        elif action == RedactionAction.TOKENIZE:
            return self._tokenize_value(value)
        elif action == RedactionAction.HASH:
            return self._hash_value(value)
        elif action == RedactionAction.ENCRYPT:
            return self._encrypt_value(value)
        else:
            return self._mask_value(value)
    
    def _apply_action_with_config(self, value: str, rule: RedactionRule) -> str:
        """
        Apply redaction action to a value using rule's mask_config.
        
        Args:
            value: Original value
            rule: Redaction rule with mask_config
            
        Returns:
            Redacted value
        """
        if rule.action == RedactionAction.MASK:
            # Get mask_config from rule metadata or use defaults
            mask_config = getattr(rule, 'metadata', {}).get('mask_config', {})
            return self._mask_value_with_config(value, mask_config)
        elif rule.action == RedactionAction.TOKENIZE:
            return self._tokenize_value(value)
        elif rule.action == RedactionAction.HASH:
            return self._hash_value(value)
        elif rule.action == RedactionAction.ENCRYPT:
            return self._encrypt_value(value)
        else:
            return self._mask_value(value)
    
    def _mask_value_with_config(self, value: str, mask_config: Dict[str, Any]) -> str:
        """
        Mask a value using configuration from YAML.
        
        Args:
            value: Original value to mask
            mask_config: Masking configuration dictionary
                - mode: full, preserve_last, preserve_first_last, preserve_structure
                - preserve_last: Number of chars to preserve at end
                - preserve_first: Number of chars to preserve at start
                - replacement_char: Character to use for masking (default: *)
                - keep_separators: Keep separators like - or . (default: False)
                - preserve_length: Preserve original length (default: True)
                - preserve_domain: For emails, preserve domain (default: True)
                
        Returns:
            Masked value
        """
        if not mask_config:
            # Fallback to legacy method
            return self._mask_value(value)
        
        mode = mask_config.get('mode', 'preserve_last')
        replacement_char = mask_config.get('replacement_char', '*')
        keep_separators = mask_config.get('keep_separators', False)
        preserve_length = mask_config.get('preserve_length', True)
        
        # Mode: full - completely mask the value
        if mode == 'full':
            if preserve_length:
                return replacement_char * len(value)
            else:
                return replacement_char * 8  # Standard length
        
        # Mode: preserve_structure - for emails
        if mode == 'preserve_structure' and '@' in value:
            preserve_first = mask_config.get('preserve_first', 1)
            preserve_last = mask_config.get('preserve_last', 1)
            preserve_domain = mask_config.get('preserve_domain', True)
            
            parts = value.split('@')
            if len(parts) == 2:
                local = parts[0]
                domain_parts = parts[1].split('.')
                
                # Mask local part
                if len(local) <= preserve_first + preserve_last:
                    masked_local = replacement_char * len(local)
                else:
                    masked_local = local[:preserve_first] + replacement_char * (len(local) - preserve_first - preserve_last) + local[-preserve_last:] if preserve_last > 0 else local[:preserve_first] + replacement_char * (len(local) - preserve_first)
                
                # Mask domain if configured
                if preserve_domain and len(domain_parts) >= 2:
                    domain_name = domain_parts[0]
                    tld = '.'.join(domain_parts[1:])
                    if len(domain_name) <= preserve_first + preserve_last:
                        masked_domain = replacement_char * len(domain_name)
                    else:
                        masked_domain = domain_name[:preserve_first] + replacement_char * (len(domain_name) - preserve_first - preserve_last) + domain_name[-preserve_last:] if preserve_last > 0 else domain_name[:preserve_first] + replacement_char * (len(domain_name) - preserve_first)
                    return f"{masked_local}@{masked_domain}.{tld}"
                
                return f"{masked_local}@{parts[1]}"
        
        # Mode: preserve_last - show last N characters
        if mode == 'preserve_last':
            preserve_last = mask_config.get('preserve_last', 4)
            
            if keep_separators:
                # Keep separators in place
                digits_only = re.sub(r'\D', '', value)
                if len(digits_only) <= preserve_last:
                    return value  # Too short, return as is
                
                # Reconstruct with masking
                masked_digits = replacement_char * (len(digits_only) - preserve_last) + digits_only[-preserve_last:]
                result = value
                digit_idx = 0
                for i, char in enumerate(value):
                    if char.isdigit():
                        result = result[:i] + masked_digits[digit_idx] + result[i+1:]
                        digit_idx += 1
                return result
            else:
                # Remove separators
                clean_value = re.sub(r'[\s\-\.\(\)]', '', value)
                if len(clean_value) <= preserve_last:
                    return replacement_char * len(clean_value)
                return replacement_char * (len(clean_value) - preserve_last) + clean_value[-preserve_last:]
        
        # Mode: preserve_first_last - show first N and last M characters
        if mode == 'preserve_first_last':
            preserve_first = mask_config.get('preserve_first', 4)
            preserve_last = mask_config.get('preserve_last', 4)
            
            clean_value = value if keep_separators else re.sub(r'[\s\-\.\(\)]', '', value)
            
            if len(clean_value) <= preserve_first + preserve_last:
                return clean_value
            
            masked_middle = replacement_char * (len(clean_value) - preserve_first - preserve_last)
            return clean_value[:preserve_first] + masked_middle + clean_value[-preserve_last:]
        
        # Default fallback
        return self._mask_value(value)
    
    def _mask_value(self, value: str) -> str:
        """
        Mask a value showing configured number of last characters.
        
        Uses show_last_n_chars from configuration.
        
        Examples:
            - Email: j*****5@y****.com
            - Phone: ***-***-7849
            - Card: ************1234
            - Name: C***********s (first and last char)
        """
        # Use configured value
        show_last = self.show_last_n_chars
        
        # Remove spaces and dashes for processing
        clean_value = re.sub(r'[\s-]', '', value)
        
        # Email pattern
        if '@' in value:
            parts = value.split('@')
            if len(parts) == 2:
                local = parts[0]
                domain_parts = parts[1].split('.')
                if len(domain_parts) >= 2:
                    domain_name = domain_parts[0]
                    tld = '.'.join(domain_parts[1:])
                    masked_local = local[0] + '*' * (len(local) - 1) if len(local) > 1 else '*'
                    masked_domain = domain_name[0] + '*' * (len(domain_name) - 1) if len(domain_name) > 1 else '*'
                    return f"{masked_local}@{masked_domain}.{tld}"
        
        # Phone number pattern
        if re.match(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', value):
            # Show last N digits
            digits = re.sub(r'\D', '', value)
            if len(digits) > show_last:
                return '*' * (len(digits) - show_last) + digits[-show_last:]
            return '*' * len(digits)
        
        # Credit card or numeric (show last N)
        if clean_value.isdigit() and len(clean_value) >= 8:
            last_n = clean_value[-show_last:] if len(clean_value) > show_last else clean_value
            return '*' * (len(clean_value) - len(last_n)) + last_n
        
        # Name or general text (show first and last character)
        if len(value) <= 2:
            return '*' * len(value)
        elif len(value) <= 6:
            return value[0] + '*' * (len(value) - 1)
        else:
            return value[0] + '*' * (len(value) - 2) + value[-1]
    
    def _tokenize_value(self, value: str) -> str:
        """Create deterministic token using HMAC."""
        token = hmac.new(
            self.hmac_key.encode(),
            value.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        return f"TOK_{token}"
    
    def _hash_value(self, value: str) -> str:
        """Create one-way hash."""
        hashed = hashlib.sha256(value.encode()).hexdigest()[:16]
        return f"HASH_{hashed}"
    
    def _encrypt_value(self, value: str) -> str:
        """
        Placeholder for Format-Preserving Encryption.
        In production, use proper FPE library like ff3 or pyffx.
        """
        # For now, use deterministic masking
        return self._mask_value(value)
    
    def get_redaction_meta(self) -> List[RedactionMeta]:
        """Get metadata about redactions performed."""
        return self.redaction_meta
