"""
Compatibility layer for migrating from old monolithic structure to new modular architecture.

This file provides aliases for the old imports to ensure backward compatibility.
"""

import warnings

# Core models (moved to src.core.models)
try:
    from .core.models import (
        RedactionAction, RedactionMeta, RedactionRule, JudgeResult, Severity,
        RedactionRequest, RedactionResponse, DryRunResponse, HealthResponse, MetricsResponse,
        PolicyConfig, StreamDataPoint
    )
except ImportError:
    warnings.warn("Could not import core models from new modular structure", ImportWarning)

# Configuration (moved to src.config)
try:
    from .config import get_config, get_config_loader
    
    # Compatibility aliases for old imports
    config_loader = get_config_loader()
    get_config_old = get_config  # Alias for old function name
except ImportError:
    warnings.warn("Could not import config from new modular structure", ImportWarning)

# Redaction Engine (moved to src.engines)  
try:
    from .engines.base import RedactionEngine
    from .engines import get_engine_registry
except ImportError:
    warnings.warn("Could not import engines from new modular structure", ImportWarning)

# Policy Loader (moved to src.policy)
try:
    from .policy import get_policy_loader, PolicyLoader
except ImportError:
    warnings.warn("Could not import policy from new modular structure", ImportWarning)

# Security (moved to src.security)
try:
    from .security import verify_api_key, sanitize_log, get_hmac_key, get_encryption_key
except ImportError:
    warnings.warn("Could not import security from new modular structure", ImportWarning)

# Metrics (moved to src.observability)
try:
    from .observability import MetricsCollector, get_tracer
except ImportError:
    warnings.warn("Could not import observability from new modular structure", ImportWarning)

# LLM Judge (moved to src.judge)
try:
    from .judge import get_llm_judge, LLMJudge
except ImportError:
    warnings.warn("Could not import judge from new modular structure", ImportWarning)

# API App (moved to src.api)
try:
    from .api import app, create_app
except ImportError:
    warnings.warn("Could not import API from new modular structure", ImportWarning)

# CLI (moved to src.cli)
try:
    from .cli import cli
except ImportError:
    warnings.warn("Could not import CLI from new modular structure", ImportWarning)


def show_migration_guide():
    """Show migration guide for updating imports."""
    print("""
    MIGRATION GUIDE: Updating imports for modular architecture
    
    Old Import                          →  New Import
    ─────────────────────────────────────────────────────────────────
    from src.models import *            →  from src.core.models import *
    from src.config_loader import *     →  from src.config import *
    from src.redaction_engine import *  →  from src.engines import *
    from src.policy_loader import *     →  from src.policy import *
    from src.security import *          →  from src.security import *
    from src.metrics import *           →  from src.observability import *
    from src.llm_judge import *         →  from src.judge import *
    from src.main import app            →  from src.api import app
    from src.cli import cli             →  from src.cli import cli
    
    Benefits of the new modular architecture:
    • Better separation of concerns
    • Easier testing and maintenance  
    • More extensible and reusable components
    • Clearer dependency management
    • Improved code organization
    """)


__all__ = [
    # Show the migration guide function
    "show_migration_guide",
    
    # All the re-exported components for compatibility
    "RedactionAction", "RedactionMeta", "RedactionRule", "JudgeResult", "Severity",
    "RedactionRequest", "RedactionResponse", "DryRunResponse", "HealthResponse", "MetricsResponse",
    "PolicyConfig", "StreamDataPoint",
    "get_config", "get_config_loader",
    "RedactionEngine", "get_engine_registry", 
    "get_policy_loader", "PolicyLoader",
    "verify_api_key", "sanitize_log", "get_hmac_key", "get_encryption_key",
    "MetricsCollector", "get_tracer",
    "get_llm_judge", "LLMJudge",
    "app", "create_app",
    "cli"
]