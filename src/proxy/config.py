"""
Proxy configuration loader and management.
"""
import os
import logging
from typing import Optional
import yaml
from ..core.models.proxy import ProxyConfig, get_default_proxy_config

logger = logging.getLogger(__name__)

# Global proxy config instance
_proxy_config: Optional[ProxyConfig] = None


def load_proxy_config(config_file: str = "config/proxy.yaml") -> ProxyConfig:
    """
    Load proxy configuration from YAML file.
    
    Args:
        config_file: Path to proxy configuration file
        
    Returns:
        ProxyConfig instance
    """
    global _proxy_config
    
    if not os.path.exists(config_file):
        logger.warning(f"Proxy config file not found: {config_file}, using default")
        _proxy_config = get_default_proxy_config()
        return _proxy_config
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Environment variable substitution
        config_data = _substitute_env_vars(config_data)
        
        _proxy_config = ProxyConfig(**config_data)
        logger.info(f"Loaded proxy configuration from {config_file}")
        
        if _proxy_config.proxy_mode:
            logger.info(f"Proxy mode enabled with {len(_proxy_config.routes)} routes")
        else:
            logger.info("Proxy mode disabled")
            
        return _proxy_config
        
    except Exception as e:
        logger.error(f"Error loading proxy config from {config_file}: {e}")
        logger.info("Using default proxy configuration")
        _proxy_config = get_default_proxy_config()
        return _proxy_config


def get_proxy_config() -> ProxyConfig:
    """
    Get current proxy configuration.
    
    Returns:
        ProxyConfig instance
    """
    global _proxy_config
    
    if _proxy_config is None:
        _proxy_config = load_proxy_config()
    
    return _proxy_config


def reload_proxy_config(config_file: str = "config/proxy.yaml") -> ProxyConfig:
    """
    Reload proxy configuration from file.
    
    Args:
        config_file: Path to proxy configuration file
        
    Returns:
        ProxyConfig instance
    """
    global _proxy_config
    _proxy_config = None
    return load_proxy_config(config_file)


def _substitute_env_vars(data):
    """Recursively substitute environment variables in configuration."""
    if isinstance(data, dict):
        return {key: _substitute_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Simple environment variable substitution
        if data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data
    else:
        return data


def validate_proxy_config(config: ProxyConfig) -> dict:
    """
    Validate proxy configuration.
    
    Args:
        config: ProxyConfig to validate
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Check if proxy mode is enabled but no routes configured
    if config.proxy_mode and not config.routes:
        errors.append("Proxy mode enabled but no routes configured")
    
    # Check upstream services
    for route in config.routes:
        if route.upstream_service not in config.upstream_services:
            errors.append(f"Route {route.path_pattern} references unknown upstream service: {route.upstream_service}")
    
    # Check for duplicate route patterns
    patterns = [route.path_pattern for route in config.routes]
    duplicates = set([x for x in patterns if patterns.count(x) > 1])
    if duplicates:
        warnings.append(f"Duplicate route patterns found: {duplicates}")
    
    # Check upstream service URLs
    for name, service in config.upstream_services.items():
        try:
            # Basic URL validation
            str(service.base_url)  # This will validate the URL
        except Exception as e:
            errors.append(f"Invalid base_url for upstream service {name}: {e}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


__all__ = [
    "load_proxy_config",
    "get_proxy_config", 
    "reload_proxy_config",
    "validate_proxy_config"
]