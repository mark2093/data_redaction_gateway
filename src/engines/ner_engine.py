"""
NER (Named Entity Recognition) based redaction engine.
"""
import logging
from typing import List, Tuple, Optional, Set, Any

from .base import BaseRedactionEngine
from ..core.models.redaction import RedactionRule
from ..core.exceptions import EngineError

logger = logging.getLogger(__name__)


class NEREngine(BaseRedactionEngine):
    """NER-based redaction engine for entity detection."""
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize NER engine.
        
        Args:
            config: Application configuration
        """
        super().__init__(config=config)
        self.ner_model = None
        self.confidence_threshold = 0.8
        self.entity_types = {"PERSON"}
        
        # Load NER configuration
        if config and hasattr(config, 'redaction') and hasattr(config.redaction, 'ner'):
            ner_config = config.redaction.ner
            self.confidence_threshold = ner_config.confidence_threshold
            self.entity_types = set(ner_config.entity_types)
            
            if ner_config.enabled:
                self._init_ner_model(ner_config.model)
    
    def _init_ner_model(self, model_name: str):
        """
        Initialize spaCy NER model.
        
        Args:
            model_name: spaCy model name
        """
        try:
            import spacy
            self.ner_model = spacy.load(model_name)
            self.enabled = True
            logger.info(f"NER engine initialized: {model_name}")
        except ImportError:
            logger.debug("spaCy library not installed - NER engine disabled")
            self.enabled = False
            self.ner_model = None
        except OSError:
            logger.debug(f"spaCy model '{model_name}' not found - NER engine disabled. Install with: python -m spacy download {model_name}")
            self.enabled = False
            self.ner_model = None
        except Exception as e:
            logger.debug(f"Failed to initialize NER engine: {e}")
            self.enabled = False
            self.ner_model = None
    
    def detect(self, text: str, rule: RedactionRule) -> List[Tuple[int, int, str]]:
        """
        Detect named entities using spaCy NER.
        
        Args:
            text: Text to analyze
            rule: Redaction rule (not used but kept for interface consistency)
            
        Returns:
            List of (start, end, matched_text) tuples
        """
        if not self.ner_model or not self.enabled:
            return []
        
        try:
            doc = self.ner_model(text)
            matches = []
            
            for ent in doc.ents:
                # Check if entity type is in configured types
                if ent.label_ in self.entity_types:
                    # Note: spaCy doesn't provide confidence by default, but we keep the structure
                    matches.append((ent.start_char, ent.end_char, ent.text))
            
            return matches
            
        except Exception as e:
            logger.error(f"NER processing error: {e}")
            return []


__all__ = ["NEREngine"]