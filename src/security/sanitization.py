"""
Log sanitization utilities to prevent PII leakage.
"""
import re
import logging

logger = logging.getLogger(__name__)


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


def sanitize_field_name(field_name: str) -> str:
    """
    Sanitize field names that might contain sensitive information.
    
    Args:
        field_name: Original field name
        
    Returns:
        Sanitized field name
    """
    # Replace potential PII in field names
    if 'email' in field_name.lower():
        return field_name.replace(field_name, '[EMAIL_FIELD]')
    elif 'phone' in field_name.lower() or 'tel' in field_name.lower():
        return field_name.replace(field_name, '[PHONE_FIELD]')
    elif 'card' in field_name.lower() or 'pan' in field_name.lower():
        return field_name.replace(field_name, '[CARD_FIELD]')
    elif 'ssn' in field_name.lower() or 'social' in field_name.lower():
        return field_name.replace(field_name, '[SSN_FIELD]')
    
    return field_name


def sanitize_for_monitoring(data: dict) -> dict:
    """
    Sanitize data structure for monitoring/metrics.
    
    Args:
        data: Data dictionary to sanitize
        
    Returns:
        Sanitized data dictionary
    """
    sanitized = {}
    
    for key, value in data.items():
        # Sanitize key
        clean_key = sanitize_field_name(key)
        
        # Sanitize value if string
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_log(value)
        elif isinstance(value, dict):
            sanitized[clean_key] = sanitize_for_monitoring(value)
        elif isinstance(value, list):
            sanitized[clean_key] = [
                sanitize_log(item) if isinstance(item, str) else 
                sanitize_for_monitoring(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[clean_key] = value
    
    return sanitized


__all__ = [
    "sanitize_log",
    "sanitize_field_name", 
    "sanitize_for_monitoring",
]