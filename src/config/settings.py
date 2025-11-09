"""
Configuration settings classes.

Contains all the dataclasses for application configuration.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"


@dataclass
class SecurityConfig:
    """Security configuration."""
    api_key_header_name: str = "X-API-Key"
    api_keys: List[str] = field(default_factory=lambda: ["dev-api-key-12345"])
    hmac_secret: str = "default-hmac-key"
    encryption_key: str = "default-encryption-key"
    tls_enabled: bool = False
    tls_cert_file: Optional[str] = None
    tls_key_file: Optional[str] = None
    mtls_enabled: bool = False
    sanitize_logs: bool = True
    log_redacted_fields: bool = False


@dataclass
class NERConfig:
    """NER configuration."""
    enabled: bool = False  # Disabled by default since it requires additional model downloads
    model: str = "en_core_web_sm"
    confidence_threshold: float = 0.8
    entity_types: List[str] = field(default_factory=lambda: ["PERSON"])


@dataclass
class RedactionConfig:
    """Redaction configuration."""
    policy_file: str = "input/redaction_rules.yaml"
    default_action: str = "allow"
    preserve_structure: bool = True
    preserve_format: bool = True
    show_last_n_chars: int = 4
    case_sensitive: bool = False
    whole_words_only: bool = False
    validate_checksums: bool = True
    ner: NERConfig = field(default_factory=NERConfig)
    exclude_fields: List[str] = field(default_factory=list)
    always_redact_fields: List[str] = field(default_factory=list)


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    ttl_seconds: int = 300
    max_size: int = 1000
    cache_decisions: bool = True
    cache_patterns: bool = True


@dataclass
class MetricsConfig:
    """Metrics configuration."""
    enabled: bool = True
    collect_latency: bool = True
    collect_coverage: bool = True
    history_size: int = 10000


@dataclass
class TracingConfig:
    """Tracing configuration."""
    enabled: bool = True
    service_name: str = "pii-redaction-gateway"
    export_spans: bool = False
    exporter_endpoint: Optional[str] = None


@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)


@dataclass
class LLMJudgeConfig:
    """LLM Judge configuration."""
    enabled: bool = False
    sampling_rate: float = 0.15
    timeout_seconds: int = 5
    fallback_on_error: bool = True
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    budget: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Main application configuration."""
    name: str = "PII/PCI Data Redaction Gateway"
    version: str = "1.0.0"
    environment: str = "development"
    server: ServerConfig = field(default_factory=ServerConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    llm_judge: LLMJudgeConfig = field(default_factory=LLMJudgeConfig)


__all__ = [
    "AppConfig",
    "ServerConfig",
    "SecurityConfig", 
    "RedactionConfig",
    "CacheConfig",
    "ObservabilityConfig",
    "LLMJudgeConfig",
    "NERConfig",
    "MetricsConfig", 
    "TracingConfig",
]