"""
Configuration loader and manager.

Loads settings from YAML files and environment variables.
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from .settings import AppConfig, ServerConfig, SecurityConfig, RedactionConfig, CacheConfig
from .settings import ObservabilityConfig, LLMJudgeConfig, NERConfig, MetricsConfig, TracingConfig
from .validator import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages application configuration."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to main configuration file
        """
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.app_config: Optional[AppConfig] = None
        
        # Load .env file first (before loading config)
        self._load_env_file()
        
        self.load_config()
    
    def _load_env_file(self) -> None:
        """
        Load environment variables from .env file.
        
        Searches for .env file in multiple locations:
        1. Current working directory
        2. Project root (where config/ folder is)
        3. Parent of config_path
        """
        env_locations = [
            Path.cwd() / '.env',
            Path(__file__).parent.parent.parent / '.env',  # Project root
            self.config_path.parent.parent / '.env'  # Parent of config/
        ]
        
        for env_path in env_locations:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                logger.info(f"Loaded environment variables from {env_path}")
                return
        
        logger.debug("No .env file found, using system environment variables only")
    
    def load_config(self) -> AppConfig:
        """
        Load configuration from YAML and environment variables.
        
        Returns:
            AppConfig instance
        """
        # Load YAML file
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f) or {}
            logger.info(f"Configuration loaded from {self.config_path}")
        else:
            logger.warning(f"Configuration file not found: {self.config_path}, using defaults")
            self.config_data = {}
        
        # Build configuration objects
        self.app_config = self._build_app_config()
        
        # Override with environment variables
        self._apply_env_overrides()
        
        return self.app_config
    
    def _build_app_config(self) -> AppConfig:
        """Build AppConfig from loaded data."""
        # Server config
        server_data = self.config_data.get('server', {})
        server_config = ServerConfig(
            host=server_data.get('host', '0.0.0.0'),
            port=server_data.get('port', 8000),
            reload=server_data.get('reload', False),
            workers=server_data.get('workers', 1),
            log_level=server_data.get('log_level', 'info')
        )
        
        # Security config
        security_data = self.config_data.get('security', {})
        tls_data = security_data.get('tls', {})
        security_config = SecurityConfig(
            api_key_header_name=security_data.get('api_key_header_name', 'X-API-Key'),
            api_keys=security_data.get('api_keys', ['dev-api-key-12345']),
            hmac_secret=security_data.get('hmac_secret', 'default-hmac-key'),
            encryption_key=security_data.get('encryption_key', 'default-encryption-key'),
            tls_enabled=tls_data.get('enabled', False),
            tls_cert_file=tls_data.get('cert_file'),
            tls_key_file=tls_data.get('key_file'),
            mtls_enabled=security_data.get('mtls', {}).get('enabled', False),
            sanitize_logs=security_data.get('sanitize_logs', True),
            log_redacted_fields=security_data.get('log_redacted_fields', False)
        )
        
        # Redaction config
        redaction_data = self.config_data.get('redaction', {})
        detection_data = redaction_data.get('detection', {})
        ner_data = redaction_data.get('ner', {})
        field_overrides = redaction_data.get('field_overrides', {})
        
        ner_config = NERConfig(
            enabled=ner_data.get('enabled', True),
            model=ner_data.get('model', 'en_core_web_sm'),
            confidence_threshold=ner_data.get('confidence_threshold', 0.8),
            entity_types=ner_data.get('entity_types', ['PERSON'])
        )
        
        redaction_config = RedactionConfig(
            policy_file=redaction_data.get('policy_file', 'input/redaction_rules.yaml'),
            default_action=redaction_data.get('default_action', 'allow'),
            preserve_structure=redaction_data.get('preserve_structure', True),
            preserve_format=redaction_data.get('preserve_format', True),
            show_last_n_chars=redaction_data.get('show_last_n_chars', 4),
            case_sensitive=detection_data.get('case_sensitive', False),
            whole_words_only=detection_data.get('whole_words_only', False),
            validate_checksums=detection_data.get('validate_checksums', True),
            ner=ner_config,
            exclude_fields=field_overrides.get('exclude_fields', []),
            always_redact_fields=field_overrides.get('always_redact_fields', [])
        )
        
        # Cache config
        cache_data = self.config_data.get('cache', {})
        cache_config = CacheConfig(
            enabled=cache_data.get('enabled', True),
            ttl_seconds=cache_data.get('ttl_seconds', 300),
            max_size=cache_data.get('max_size', 1000),
            cache_decisions=cache_data.get('cache_decisions', True),
            cache_patterns=cache_data.get('cache_patterns', True)
        )
        
        # Observability config
        observability_data = self.config_data.get('observability', {})
        metrics_data = observability_data.get('metrics', {})
        tracing_data = observability_data.get('tracing', {})
        
        metrics_config = MetricsConfig(
            enabled=metrics_data.get('enabled', True),
            collect_latency=metrics_data.get('collect_latency', True),
            collect_coverage=metrics_data.get('collect_coverage', True),
            history_size=metrics_data.get('history_size', 10000)
        )
        
        tracing_config = TracingConfig(
            enabled=tracing_data.get('enabled', True),
            service_name=tracing_data.get('service_name', 'pii-redaction-gateway'),
            export_spans=tracing_data.get('export_spans', False),
            exporter_endpoint=tracing_data.get('exporter_endpoint')
        )
        
        observability_config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=tracing_config
        )
        
        # LLM Judge config
        llm_judge_data = self.config_data.get('llm_judge', {})
        llm_judge_config = LLMJudgeConfig(
            enabled=llm_judge_data.get('enabled', False),
            sampling_rate=llm_judge_data.get('sampling_rate', 0.15),
            timeout_seconds=llm_judge_data.get('timeout_seconds', 5),
            fallback_on_error=llm_judge_data.get('fallback_on_error', True),
            provider=llm_judge_data.get('provider'),
            model=llm_judge_data.get('model'),
            api_key=llm_judge_data.get('api_key'),
            endpoint=llm_judge_data.get('endpoint'),
            budget=llm_judge_data.get('budget', {}),
            validation=llm_judge_data.get('validation', {})
        )
        
        # App config
        app_data = self.config_data.get('app', {})
        return AppConfig(
            name=app_data.get('name', 'PII/PCI Data Redaction Gateway'),
            version=app_data.get('version', '1.0.0'),
            environment=app_data.get('environment', 'development'),
            server=server_config,
            security=security_config,
            redaction=redaction_config,
            cache=cache_config,
            observability=observability_config,
            llm_judge=llm_judge_config
        )
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        if not self.app_config:
            return
        
        # API Keys
        api_keys_env = os.getenv('API_KEYS')
        if api_keys_env:
            self.app_config.security.api_keys = api_keys_env.split(',')
            logger.info("API keys overridden from environment")
        
        # HMAC Secret
        hmac_secret = os.getenv('HMAC_SECRET_KEY')
        if hmac_secret:
            self.app_config.security.hmac_secret = hmac_secret
            logger.info("HMAC secret overridden from environment")
        
        # Encryption Key
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key:
            self.app_config.security.encryption_key = encryption_key
            logger.info("Encryption key overridden from environment")
        
        # TLS
        tls_enabled = os.getenv('TLS_ENABLED')
        if tls_enabled:
            self.app_config.security.tls_enabled = tls_enabled.lower() == 'true'
        
        # Server host/port
        host = os.getenv('SERVER_HOST')
        if host:
            self.app_config.server.host = host
        
        port = os.getenv('SERVER_PORT')
        if port:
            self.app_config.server.port = int(port)
        
        # Environment
        environment = os.getenv('ENVIRONMENT')
        if environment:
            self.app_config.environment = environment
        
        # LLM API Key
        llm_api_key = os.getenv('LLM_API_KEY')
        if llm_api_key:
            self.app_config.llm_judge.api_key = llm_api_key
            logger.info("LLM API key overridden from environment")
    
    def get_config(self) -> AppConfig:
        """
        Get application configuration.
        
        Returns:
            AppConfig instance
        """
        if not self.app_config:
            self.load_config()
        return self.app_config
    
    def reload_config(self) -> AppConfig:
        """
        Reload configuration from file.
        
        Returns:
            Updated AppConfig instance
        """
        logger.info("Reloading configuration...")
        return self.load_config()
    
    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value by dot-notation path.
        
        Args:
            key_path: Dot-separated path (e.g., 'server.port')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value


    def validate_config(self):
        """
        Validate current configuration.
        
        Returns:
            Validation results dictionary
        """
        if not self.app_config:
            self.load_config()
        
        validator = ConfigValidator(self.app_config)
        return validator.validate_config()


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: str = "config/config.yaml") -> ConfigLoader:
    """
    Get singleton configuration loader.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def get_config() -> AppConfig:
    """
    Get application configuration.
    
    Returns:
        AppConfig instance
    """
    loader = get_config_loader()
    return loader.get_config()


__all__ = ["ConfigLoader", "get_config_loader", "get_config"]