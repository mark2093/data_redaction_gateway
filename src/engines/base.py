"""
Base classes for redaction engines.
"""
import re
import hashlib
import hmac
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from ..core.models.redaction import RedactionAction, RedactionMeta, RedactionRule
from ..core.exceptions import EngineError


class BaseRedactionEngine(ABC):
    """Abstract base class for redaction engines."""
    
    def __init__(self, enabled: bool = True, config: Optional[Any] = None):
        """
        Initialize base redaction engine.
        
        Args:
            enabled: Whether the engine is enabled
            config: Configuration object
        """
        self.enabled = enabled
        self.config = config
        self.redaction_meta: List[RedactionMeta] = []
    
    @abstractmethod
    def detect(self, text: str, rule: RedactionRule) -> List[Tuple[int, int, str]]:
        """
        Detect sensitive data in text.
        
        Args:
            text: Text to analyze
            rule: Redaction rule to apply
            
        Returns:
            List of (start, end, matched_text) tuples
        """
        pass
    
    def redact(self, text: str, rule: RedactionRule, field_name: Optional[str] = None) -> str:
        """
        Redact sensitive data from text.
        
        Args:
            text: Text to redact
            rule: Redaction rule to apply
            field_name: Field name for metadata
            
        Returns:
            Redacted text
        """
        if not self.enabled or not text:
            return text
        
        matches = self.detect(text, rule)
        if not matches:
            return text
        
        # Process matches in reverse to maintain string indices
        redacted_text = text
        for start, end, matched_text in reversed(matches):
            redacted_value = self._apply_action(matched_text, rule)
            redacted_text = redacted_text[:start] + redacted_value + redacted_text[end:]
            
            # Record metadata
            self.redaction_meta.append(
                RedactionMeta(
                    field=field_name or "text",
                    rule=rule.id,
                    action=rule.action
                )
            )
        
        return redacted_text
    
    def _apply_action(self, value: str, rule: RedactionRule) -> str:
        """
        Apply redaction action to a value.
        
        Args:
            value: Original value
            rule: Redaction rule with action and config
            
        Returns:
            Redacted value
        """
        if rule.action == RedactionAction.MASK:
            mask_config = getattr(rule, 'metadata', {}).get('mask_config', {})
            return self._mask_value_with_config(value, mask_config)
        elif rule.action == RedactionAction.TOKENIZE:
            return self._tokenize_value(value)
        elif rule.action == RedactionAction.HASH:
            return self._hash_value(value)
        elif rule.action == RedactionAction.ENCRYPT:
            return self._encrypt_value(value)
        elif rule.action == RedactionAction.FPE:
            return self._fpe_encrypt_value(value, rule)
        else:
            return self._mask_value(value)
    
    def _mask_value_with_config(self, value: str, mask_config: Dict[str, Any]) -> str:
        """Mask a value using configuration."""
        if not mask_config:
            return self._mask_value(value)
        
        mode = mask_config.get('mode', 'preserve_last')
        replacement_char = mask_config.get('replacement_char', '*')
        preserve_length = mask_config.get('preserve_length', True)
        
        if mode == 'full':
            if preserve_length:
                return replacement_char * len(value)
            else:
                return replacement_char * 8
        
        if mode == 'preserve_structure':
            # Special handling for email addresses
            if '@' in value and '.' in value.split('@')[-1]:
                return self._mask_email_preserve_structure(value, mask_config)
            # Fall back to preserve_last for non-email values
            mode = 'preserve_last'
        
        if mode == 'preserve_last':
            preserve_last = mask_config.get('preserve_last', 4)
            if len(value) <= preserve_last:
                return replacement_char * len(value)
            return replacement_char * (len(value) - preserve_last) + value[-preserve_last:]
        
        # Default behavior
        preserve_last = mask_config.get('preserve_last', 4)
        if len(value) <= preserve_last:
            return replacement_char * len(value)
        
        return replacement_char * (len(value) - preserve_last) + value[-preserve_last:]
    
    def _mask_email_preserve_structure(self, email: str, mask_config: Dict[str, Any]) -> str:
        """
        Mask email while preserving structure.
        
        Example: john.doe@example.com -> j*******@e*******.com
        
        Args:
            email: Email address to mask
            mask_config: Configuration dict with:
                - preserve_first: Number of chars to preserve in local part (default: 1)
                - preserve_last: Number of chars to preserve in local part (default: 1)
                - preserve_domain: Whether to preserve domain structure (default: True)
                - replacement_char: Character to use for masking (default: '*')
        
        Returns:
            Masked email address
        """
        replacement_char = mask_config.get('replacement_char', '*')
        preserve_first = mask_config.get('preserve_first', 1)
        preserve_last = mask_config.get('preserve_last', 1)
        preserve_domain = mask_config.get('preserve_domain', True)
        
        # Split email into local and domain parts
        if '@' not in email:
            return replacement_char * len(email)
        
        local, domain = email.rsplit('@', 1)
        
        # Mask local part
        if len(local) <= (preserve_first + preserve_last):
            # If local part is too short, just mask it all
            masked_local = replacement_char * len(local)
        else:
            # Preserve first N and last M characters
            mask_length = len(local) - preserve_first - preserve_last
            masked_local = local[:preserve_first] + (replacement_char * mask_length) + local[-preserve_last:]
        
        # Handle domain
        if preserve_domain and '.' in domain:
            # Preserve domain structure: example.com -> e******.com
            domain_parts = domain.split('.')
            masked_domain_parts = []
            
            for part in domain_parts[:-1]:  # All parts except TLD
                if len(part) <= 1:
                    masked_domain_parts.append(part)
                else:
                    # Preserve first character of each domain part
                    masked_part = part[0] + (replacement_char * (len(part) - 1))
                    masked_domain_parts.append(masked_part)
            
            # Keep TLD as-is
            masked_domain_parts.append(domain_parts[-1])
            masked_domain = '.'.join(masked_domain_parts)
        else:
            # Fully mask domain
            masked_domain = replacement_char * len(domain)
        
        return f"{masked_local}@{masked_domain}"
    
    def _mask_value(self, value: str) -> str:
        """Default masking implementation."""
        if len(value) <= 4:
            return '*' * len(value)
        return '*' * (len(value) - 4) + value[-4:]
    
    def _tokenize_value(self, value: str) -> str:
        """Create deterministic token using HMAC."""
        if not self.config or not hasattr(self.config, 'security'):
            return f"TOK_{hashlib.sha256(value.encode()).hexdigest()[:16]}"
        
        token = hmac.new(
            self.config.security.hmac_secret.encode(),
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
        return self._mask_value(value)
    
    def _fpe_encrypt_value(self, value: str, rule: RedactionRule) -> str:
        """
        Apply Format-Preserving Encryption to value.
        
        Args:
            value: Value to encrypt
            rule: Redaction rule containing FPE configuration
            
        Returns:
            FPE-encrypted value maintaining original format
        """
        try:
            from ..security.fpe import get_fpe_instance, FPEError
            
            fpe_instance = get_fpe_instance()
            
            # Determine data type from rule metadata or pattern
            data_type = rule.metadata.get('data_type', 'pan') if rule.metadata else 'pan'
            
            # Clean the value for FPE
            clean_value = re.sub(r'[^0-9]', '', value)  # Extract digits only
            
            # Apply FPE based on data type
            if data_type.lower() == 'pan' or rule.id.upper().find('PAN') >= 0:
                if len(clean_value) >= 13:
                    return fpe_instance.encrypt_pan(clean_value)
            elif data_type.lower() == 'ssn' or rule.id.upper().find('SSN') >= 0:
                if len(clean_value) == 9:
                    encrypted = fpe_instance.encrypt_ssn(clean_value)
                    # Restore original format if it had dashes
                    if '-' in value:
                        return f"{encrypted[:3]}-{encrypted[3:5]}-{encrypted[5:]}"
                    return encrypted
            
            # If we can't determine type or value is invalid, fall back to masking
            return self._mask_value(value)
            
        except (FPEError, ImportError, Exception) as e:
            # Fall back to masking on FPE errors
            from ..core.exceptions import EngineError
            raise EngineError(f"FPE encryption failed: {e}")
            return self._mask_value(value)
    
    def get_redaction_meta(self) -> List[RedactionMeta]:
        """Get metadata about redactions performed."""
        return self.redaction_meta
    
    def reset_meta(self):
        """Reset redaction metadata."""
        self.redaction_meta = []


class RedactionEngine:
    """
    Main redaction engine that orchestrates multiple detection engines.
    """
    
    def __init__(self, rules: List[RedactionRule], config: Optional[Any] = None):
        """
        Initialize the redaction engine.
        
        Args:
            rules: List of redaction rules to apply
            config: Application configuration
        """
        from ..config import get_config
        
        # Load configuration
        if config is None:
            config = get_config()
        self.config = config
        
        # Filter enabled rules
        self.rules = [rule for rule in rules if rule.enabled]
        
        # Redaction metadata
        self.redaction_meta: List[RedactionMeta] = []
        
        # Configuration settings
        self.show_last_n_chars = self.config.redaction.show_last_n_chars
        self.exclude_fields = set(self.config.redaction.exclude_fields)
        self.always_redact_fields = set(self.config.redaction.always_redact_fields)
        
        # Initialize engine registry and engines
        from .registry import get_engine_registry
        self.engine_registry = get_engine_registry()
        self._init_engines()
    
    def _init_engines(self):
        """Initialize specialized engines."""
        # This will be implemented when we create the registry
        pass
    
    def redact(self, data: Union[Dict, List, str], path: str = "$") -> Union[Dict, List, str]:
        """
        Redact sensitive data from input.
        
        Args:
            data: Input data to redact
            path: JSONPath to current location
            
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
        
        # Apply each rule through appropriate engine
        for rule in self.rules:
            engine = self.engine_registry.get_engine(rule)
            if engine and engine.enabled:
                engine.reset_meta()
                redacted_text = engine.redact(redacted_text, rule, field_name)
                # Collect metadata from engine
                self.redaction_meta.extend(engine.get_redaction_meta())
        
        return redacted_text
    
    def _mask_value(self, value: str) -> str:
        """Default masking for always_redact fields."""
        show_last = self.show_last_n_chars
        if len(value) <= show_last:
            return '*' * len(value)
        return '*' * (len(value) - show_last) + value[-show_last:]
    
    def get_redaction_meta(self) -> List[RedactionMeta]:
        """Get metadata about redactions performed."""
        return self.redaction_meta


__all__ = ["BaseRedactionEngine", "RedactionEngine"]