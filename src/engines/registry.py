"""
Engine registry for managing redaction engines.
"""
import logging
from typing import Dict, Optional, Type, List

from .base import BaseRedactionEngine
from ..core.models.redaction import RedactionRule
from ..core.exceptions import EngineError

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Registry for redaction engines."""
    
    def __init__(self):
        """Initialize the engine registry."""
        self.engines: Dict[str, Type[BaseRedactionEngine]] = {}
        self.engine_instances: Dict[str, BaseRedactionEngine] = {}
        self._register_default_engines()
    
    def _register_default_engines(self):
        """Register default engines."""
        # Import here to avoid circular imports
        try:
            from .regex_engine import RegexEngine
            from .luhn_engine import LuhnEngine
            from .ner_engine import NEREngine
            
            self.register_engine("regex", RegexEngine)
            self.register_engine("luhn", LuhnEngine)
            self.register_engine("ner", NEREngine)
            
            logger.info("Registered default redaction engines")
        except ImportError as e:
            logger.warning(f"Failed to register some engines: {e}")
    
    def register_engine(self, name: str, engine_class: Type[BaseRedactionEngine]):
        """
        Register a redaction engine.
        
        Args:
            name: Engine name/identifier
            engine_class: Engine class
        """
        self.engines[name.lower()] = engine_class
        logger.debug(f"Registered engine: {name}")
    
    def get_engine_class(self, name: str) -> Optional[Type[BaseRedactionEngine]]:
        """
        Get engine class by name.
        
        Args:
            name: Engine name
            
        Returns:
            Engine class if found, None otherwise
        """
        return self.engines.get(name.lower())
    
    def get_engine(self, rule: RedactionRule) -> Optional[BaseRedactionEngine]:
        """
        Get engine instance for a rule.
        
        Args:
            rule: Redaction rule
            
        Returns:
            Engine instance if appropriate engine found
        """
        # Determine engine type based on rule
        if rule.engine:
            # Explicit engine specified
            engine_name = rule.engine.lower()
        elif rule.id == "LUHN_PAN":
            engine_name = "luhn"
        elif rule.pattern:
            engine_name = "regex"
        else:
            logger.warning(f"No engine found for rule {rule.id}")
            return None
        
        # Get or create engine instance
        if engine_name not in self.engine_instances:
            engine_class = self.get_engine_class(engine_name)
            if not engine_class:
                logger.error(f"Engine class not found: {engine_name}")
                return None
            
            try:
                # Initialize engine with configuration
                from ..config import get_config
                config = get_config()
                self.engine_instances[engine_name] = engine_class(config=config)
                logger.debug(f"Created engine instance: {engine_name}")
            except Exception as e:
                logger.error(f"Failed to create engine {engine_name}: {e}")
                return None
        
        return self.engine_instances.get(engine_name)
    
    def list_engines(self) -> List[str]:
        """
        List registered engine names.
        
        Returns:
            List of engine names
        """
        return list(self.engines.keys())


# Singleton instance
_engine_registry: Optional[EngineRegistry] = None


def get_engine_registry() -> EngineRegistry:
    """
    Get singleton engine registry.
    
    Returns:
        EngineRegistry instance
    """
    global _engine_registry
    if _engine_registry is None:
        _engine_registry = EngineRegistry()
    return _engine_registry


__all__ = ["EngineRegistry", "get_engine_registry"]