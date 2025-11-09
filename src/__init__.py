"""
PII/PCI Data Redaction Gateway - Modular Architecture

A comprehensive, modular solution for detecting and redacting sensitive 
personal and payment card industry data in real-time.
"""

from .api import create_app, app
from .cli import cli
from .config import get_config, get_config_loader
from .engines import RedactionEngine, get_engine_registry
from .policy import get_policy_loader
from .security import verify_api_key, sanitize_log
from .judge import get_llm_judge
from .observability import MetricsCollector, get_tracer

__version__ = "1.0.0"
__author__ = "Hackathon Team"

__all__ = [
    # API
    "create_app",
    "app",
    
    # CLI
    "cli",
    
    # Configuration
    "get_config", 
    "get_config_loader",
    
    # Engines
    "RedactionEngine",
    "get_engine_registry",
    
    # Policy
    "get_policy_loader",
    
    # Security
    "verify_api_key",
    "sanitize_log",
    
    # Judge
    "get_llm_judge",
    
    # Observability
    "MetricsCollector",
    "get_tracer",
]
