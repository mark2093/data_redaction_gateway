"""
Authentication and authorization utilities.
"""
import os
import logging
from typing import Optional, List
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

from ..core.exceptions import AuthenticationError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration holder."""
    
    def __init__(self, config=None):
        """
        Initialize security configuration.
        
        Args:
            config: Application configuration
        """
        if config is None:
            from ..config import get_config
            config = get_config()
        
        self.config = config
        self.api_keys = config.security.api_keys
        self.hmac_key = config.security.hmac_secret
        self.encryption_key = config.security.encryption_key
        self.tls_enabled = config.security.tls_enabled
        self.mtls_enabled = config.security.mtls_enabled
        self.api_key_header_name = config.security.api_key_header_name
        
        # Initialize API key header
        self.api_key_header = APIKeyHeader(name=self.api_key_header_name, auto_error=False)
    
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
        
        if not self.tls_enabled and self.config.environment == "production":
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


async def verify_api_key(api_key: Optional[str] = Security(get_security_config().api_key_header)) -> str:
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
    
    security_config = get_security_config()
    if api_key not in security_config.api_keys:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key


def get_hmac_key() -> str:
    """
    Get HMAC key for tokenization.
    
    Returns:
        HMAC secret key
    """
    security_config = get_security_config()
    return security_config.hmac_key


def get_encryption_key() -> str:
    """
    Get encryption key for FPE.
    
    Returns:
        Encryption key
    """
    security_config = get_security_config()
    return security_config.encryption_key


__all__ = [
    "SecurityConfig",
    "get_security_config",
    "verify_api_key", 
    "get_hmac_key",
    "get_encryption_key",
]