"""
Security utilities for API authentication and log sanitization.
"""
import os
import re
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
from .config_loader import get_config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Load configuration
app_config = get_config()

# API Key configuration
API_KEY_NAME = app_config.security.api_key_header_name
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get API keys from config
VALID_API_KEYS = app_config.security.api_keys


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from header
        
    Returns:
        Verified API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key


def sanitize_log(message: str) -> str:
    """
    Sanitize log messages to prevent PII leakage.
    
    Removes or masks potential PII from log messages.
    
    Args:
        message: Original log message
        
    Returns:
        Sanitized log message
    """
    if not message:
        return message
    
    # Email pattern
    message = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',
        message
    )
    
    # Credit card pattern (13-19 digits)
    message = re.sub(
        r'\b\d{13,19}\b',
        '[CARD_REDACTED]',
        message
    )
    
    # Phone number patterns
    message = re.sub(
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        '[PHONE_REDACTED]',
        message
    )
    message = re.sub(
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
        '[PHONE_REDACTED]',
        message
    )
    
    # SSN pattern
    message = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN_REDACTED]',
        message
    )
    
    # Generic long numbers that might be sensitive
    message = re.sub(
        r'\b\d{9,}\b',
        '[NUMBER_REDACTED]',
        message
    )
    
    return message


def get_hmac_key() -> str:
    """
    Get HMAC key for tokenization.
    
    Returns:
        HMAC secret key
    """
    return app_config.security.hmac_secret


def get_encryption_key() -> str:
    """
    Get encryption key for FPE.
    
    Returns:
        Encryption key
    """
    return app_config.security.encryption_key


class SecurityConfig:
    """Security configuration holder."""
    
    def __init__(self):
        self.api_keys = app_config.security.api_keys
        self.hmac_key = app_config.security.hmac_secret
        self.encryption_key = app_config.security.encryption_key
        self.tls_enabled = app_config.security.tls_enabled
        self.mtls_enabled = app_config.security.mtls_enabled
    
    def validate(self) -> dict:
        """
        Validate security configuration.
        
        Returns:
            Validation results
        """
        warnings = []
        errors = []
        
        # Check for default keys
        if "default" in self.hmac_key:
            warnings.append("Using default HMAC key - change in production")
        
        if "default" in self.encryption_key:
            warnings.append("Using default encryption key - change in production")
        
        if "dev-api-key" in str(self.api_keys) or "test-api-key" in str(self.api_keys):
            warnings.append("Using default API keys - change in production")
        
        if not self.tls_enabled and app_config.environment == "production":
            warnings.append("TLS is not enabled - enable in production")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'tls_enabled': self.tls_enabled,
            'mtls_enabled': self.mtls_enabled
        }


# Singleton instance
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """
    Get singleton security configuration.
    
    Returns:
        SecurityConfig instance
    """
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config
