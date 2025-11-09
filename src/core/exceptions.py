"""
Custom exceptions for the redaction gateway.
"""


class RedactionError(Exception):
    """Base exception for redaction operations."""
    pass


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class PolicyError(Exception):
    """Exception raised for policy-related errors."""
    pass


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class EngineError(Exception):
    """Exception raised for redaction engine errors."""
    pass


class JudgeError(Exception):
    """Exception raised for LLM judge errors."""
    pass