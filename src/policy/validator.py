"""
Policy validation utilities.
"""
import logging
from typing import Dict, List, Any

from ..core.models.config import PolicyConfig
from ..core.exceptions import PolicyError

logger = logging.getLogger(__name__)


class PolicyValidator:
    """Validates redaction policies."""
    
    def __init__(self, policy: PolicyConfig):
        """
        Initialize validator with policy.
        
        Args:
            policy: Policy configuration to validate
        """
        self.policy = policy
    
    def validate_policy(self) -> Dict[str, Any]:
        """
        Validate current policy configuration.
        
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        
        # Check for duplicate rule IDs
        rule_ids = [rule.id for rule in self.policy.rules]
        duplicates = [rid for rid in rule_ids if rule_ids.count(rid) > 1]
        if duplicates:
            errors.append(f"Duplicate rule IDs: {set(duplicates)}")
        
        # Check each rule has either pattern or engine
        for rule in self.policy.rules:
            if not rule.pattern and not rule.engine:
                errors.append(f"Rule {rule.id} has neither pattern nor engine")
        
        # Check for common issues
        for rule in self.policy.rules:
            if rule.pattern:
                # Check if pattern looks like it might have issues
                if '\\b' in rule.pattern and not rule.pattern.startswith('\\b'):
                    warnings.append(f"Rule {rule.id} pattern may need adjustment")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'rule_count': len(self.policy.rules),
            'enabled_count': len([r for r in self.policy.rules if r.enabled])
        }
    
    def validate_rule_syntax(self) -> List[str]:
        """
        Validate rule syntax.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for rule in self.policy.rules:
            if rule.pattern:
                try:
                    import re
                    re.compile(rule.pattern)
                except re.error as e:
                    errors.append(f"Invalid regex in rule {rule.id}: {e}")
        
        return errors
    
    def check_coverage(self) -> Dict[str, Any]:
        """
        Check policy coverage for common PII types.
        
        Returns:
            Coverage analysis
        """
        coverage = {
            'email': False,
            'phone': False, 
            'credit_card': False,
            'ssn': False,
            'person_names': False
        }
        
        for rule in self.policy.rules:
            if not rule.enabled:
                continue
                
            # Check for common patterns
            if rule.pattern:
                pattern = rule.pattern.lower()
                if 'email' in pattern or '@' in pattern:
                    coverage['email'] = True
                if 'phone' in pattern or r'\d{3}' in pattern:
                    coverage['phone'] = True
                if 'card' in pattern or r'\d{4}' in pattern:
                    coverage['credit_card'] = True
                if 'ssn' in pattern or r'\d{3}-\d{2}-\d{4}' in pattern:
                    coverage['ssn'] = True
            
            if rule.engine == 'NER':
                coverage['person_names'] = True
            
            if rule.id == 'LUHN_PAN':
                coverage['credit_card'] = True
        
        return {
            'coverage': coverage,
            'coverage_score': sum(coverage.values()) / len(coverage) * 100
        }


__all__ = ["PolicyValidator"]