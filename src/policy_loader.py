"""
Policy loader and cache manager for redaction rules.
Configuration-driven policy management.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from cachetools import TTLCache

from src.models import PolicyConfig, RedactionRule
from src.config_loader import get_config

logger = logging.getLogger(__name__)


class PolicyLoader:
    """Loads and caches redaction policies from YAML files."""
    
    def __init__(
        self,
        policy_path: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        cache_size: Optional[int] = None
    ):
        """
        Initialize policy loader with configuration.
        
        Args:
            policy_path: Path to the policy YAML file (overrides config)
            cache_ttl: Time-to-live for cache entries in seconds (overrides config)
            cache_size: Maximum number of cache entries (overrides config)
        """
        # Load application configuration
        self.app_config = get_config()
        
        # Use provided values or fall back to config
        self.policy_path = Path(policy_path or self.app_config.redaction.policy_file)
        
        # Cache configuration from YAML
        cache_enabled = self.app_config.cache.enabled
        cache_ttl = cache_ttl if cache_ttl is not None else self.app_config.cache.ttl_seconds
        cache_size = cache_size if cache_size is not None else self.app_config.cache.max_size
        
        if cache_enabled:
            self.cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        else:
            self.cache = {}  # Disabled cache
        
        self.current_policy: Optional[PolicyConfig] = None
        self.load_time: Optional[datetime] = None
        
        # Load policy on initialization
        self.reload_policy()
    
    def reload_policy(self) -> PolicyConfig:
        """
        Load or reload the policy from YAML file.
        
        Returns:
            Loaded policy configuration
        """
        try:
            if not self.policy_path.exists():
                logger.error(f"Policy file not found: {self.policy_path}")
                raise FileNotFoundError(f"Policy file not found: {self.policy_path}")
            
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            # Parse into Pydantic model
            self.current_policy = PolicyConfig(**policy_data)
            self.load_time = datetime.utcnow()
            
            # Clear cache when policy reloads
            self.cache.clear()
            
            logger.info(
                f"Policy loaded successfully: version {self.current_policy.version}, "
                f"{len(self.current_policy.rules)} rules"
            )
            
            return self.current_policy
            
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            raise
    
    def get_policy(self, version: Optional[str] = None) -> PolicyConfig:
        """
        Get policy configuration.
        
        Args:
            version: Specific version to retrieve (currently only returns current)
            
        Returns:
            Policy configuration
        """
        if not self.current_policy:
            self.reload_policy()
        
        # TODO: Implement version-specific loading if needed
        return self.current_policy
    
    def get_rules(self) -> List[RedactionRule]:
        """
        Get list of active redaction rules.
        
        Returns:
            List of enabled redaction rules
        """
        if not self.current_policy:
            self.reload_policy()
        
        return [rule for rule in self.current_policy.rules if rule.enabled]
    
    def get_rule_by_id(self, rule_id: str) -> Optional[RedactionRule]:
        """
        Get a specific rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            RedactionRule if found, None otherwise
        """
        if not self.current_policy:
            self.reload_policy()
        
        for rule in self.current_policy.rules:
            if rule.id == rule_id:
                return rule
        
        return None
    
    def cache_decision(
        self,
        endpoint: str,
        field: str,
        rule_id: str,
        decision: bool
    ):
        """
        Cache a redaction decision.
        
        Args:
            endpoint: API endpoint
            field: Field name
            rule_id: Rule ID
            decision: Whether redaction was needed
        """
        cache_key = f"{endpoint}:{field}:{rule_id}"
        self.cache[cache_key] = {
            'decision': decision,
            'timestamp': datetime.utcnow()
        }
    
    def get_cached_decision(
        self,
        endpoint: str,
        field: str,
        rule_id: str
    ) -> Optional[bool]:
        """
        Get cached redaction decision.
        
        Args:
            endpoint: API endpoint
            field: Field name
            rule_id: Rule ID
            
        Returns:
            Cached decision if exists, None otherwise
        """
        cache_key = f"{endpoint}:{field}:{rule_id}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached['decision']
        
        return None
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'ttl': self.cache.ttl
        }
    
    def get_policy_version(self) -> str:
        """
        Get current policy version.
        
        Returns:
            Policy version string
        """
        if not self.current_policy:
            self.reload_policy()
        
        return self.current_policy.version
    
    def is_policy_stale(self, max_age_minutes: int = 60) -> bool:
        """
        Check if policy needs reloading.
        
        Args:
            max_age_minutes: Maximum age in minutes
            
        Returns:
            True if policy should be reloaded
        """
        if not self.load_time:
            return True
        
        age = datetime.utcnow() - self.load_time
        return age > timedelta(minutes=max_age_minutes)
    
    def validate_policy(self) -> Dict[str, any]:
        """
        Validate current policy configuration.
        
        Returns:
            Validation results
        """
        if not self.current_policy:
            return {'valid': False, 'errors': ['No policy loaded']}
        
        errors = []
        warnings = []
        
        # Check for duplicate rule IDs
        rule_ids = [rule.id for rule in self.current_policy.rules]
        duplicates = [rid for rid in rule_ids if rule_ids.count(rid) > 1]
        if duplicates:
            errors.append(f"Duplicate rule IDs: {set(duplicates)}")
        
        # Check each rule has either pattern or engine
        for rule in self.current_policy.rules:
            if not rule.pattern and not rule.engine:
                errors.append(f"Rule {rule.id} has neither pattern nor engine")
        
        # Check for common issues
        for rule in self.current_policy.rules:
            if rule.pattern:
                # Check if pattern looks like it might have issues
                if '\\b' in rule.pattern and not rule.pattern.startswith('\\b'):
                    warnings.append(f"Rule {rule.id} pattern may need adjustment")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'rule_count': len(self.current_policy.rules),
            'enabled_count': len([r for r in self.current_policy.rules if r.enabled])
        }


# Singleton instance
_policy_loader: Optional[PolicyLoader] = None


def get_policy_loader() -> PolicyLoader:
    """
    Get singleton policy loader instance.
    
    Returns:
        PolicyLoader instance
    """
    global _policy_loader
    if _policy_loader is None:
        _policy_loader = PolicyLoader()
    return _policy_loader
