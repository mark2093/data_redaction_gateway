"""
Configuration validator.

Validates configuration settings for correctness and security.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from .settings import AppConfig

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates application configuration."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize validator with configuration.
        
        Args:
            config: Application configuration to validate
        """
        self.config = config
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Returns:
            Validation results with errors and warnings
        """
        errors = []
        warnings = []
        
        # Check for default secrets in production
        if self.config.environment == 'production':
            errors.extend(self._validate_production_security())
        
        # Validate file paths
        errors.extend(self._validate_file_paths())
        
        # Validate cache settings
        warnings.extend(self._validate_cache_settings())
        
        # Validate LLM settings
        warnings.extend(self._validate_llm_settings())
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'environment': self.config.environment,
            'policy_file': self.config.redaction.policy_file
        }
    
    def _validate_production_security(self) -> List[str]:
        """Validate security settings for production."""
        errors = []
        
        if 'default' in self.config.security.hmac_secret:
            errors.append("Using default HMAC secret in production")
        
        if 'default' in self.config.security.encryption_key:
            errors.append("Using default encryption key in production")
        
        if 'dev-api-key' in str(self.config.security.api_keys):
            errors.append("Using default API keys in production")
        
        return errors
    
    def _validate_file_paths(self) -> List[str]:
        """Validate file paths exist."""
        errors = []
        
        # Check policy file exists
        policy_path = Path(self.config.redaction.policy_file)
        if not policy_path.exists():
            errors.append(f"Policy file not found: {policy_path}")
        
        # Check TLS certificate files if TLS is enabled
        if self.config.security.tls_enabled:
            if self.config.security.tls_cert_file:
                cert_path = Path(self.config.security.tls_cert_file)
                if not cert_path.exists():
                    errors.append(f"TLS certificate file not found: {cert_path}")
            
            if self.config.security.tls_key_file:
                key_path = Path(self.config.security.tls_key_file)
                if not key_path.exists():
                    errors.append(f"TLS key file not found: {key_path}")
        
        return errors
    
    def _validate_cache_settings(self) -> List[str]:
        """Validate cache configuration."""
        warnings = []
        
        if self.config.cache.enabled:
            if self.config.cache.ttl_seconds <= 0:
                warnings.append("Cache TTL should be positive")
            
            if self.config.cache.max_size <= 0:
                warnings.append("Cache max size should be positive")
        
        return warnings
    
    def _validate_llm_settings(self) -> List[str]:
        """Validate LLM judge configuration."""
        warnings = []
        
        if self.config.llm_judge.enabled:
            if not self.config.llm_judge.provider:
                warnings.append("LLM judge enabled but no provider specified")
            
            if not self.config.llm_judge.model:
                warnings.append("LLM judge enabled but no model specified")
            
            if not self.config.llm_judge.api_key:
                warnings.append("LLM judge enabled but no API key provided")
            
            if self.config.llm_judge.sampling_rate <= 0 or self.config.llm_judge.sampling_rate > 1:
                warnings.append("LLM judge sampling rate should be between 0 and 1")
        
        # Check for production TLS
        if self.config.environment == 'production' and not self.config.security.tls_enabled:
            warnings.append("TLS not enabled in production")
        
        return warnings


__all__ = ["ConfigValidator"]