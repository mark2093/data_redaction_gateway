"""
Basic tests for the PII/PCI Redaction Gateway.
"""
import pytest
from src.redaction_engine import RedactionEngine, LuhnValidator
from src.models import RedactionRule, RedactionAction, Severity
from src.policy_loader import PolicyLoader


class TestLuhnValidator:
    """Test Luhn algorithm validation."""
    
    def test_valid_credit_cards(self):
        """Test valid credit card numbers."""
        validator = LuhnValidator()
        
        # Valid test cards
        assert validator.validate("4532015112830366") is True
        assert validator.validate("5425233430109903") is True
        assert validator.validate("374245455400126") is True
        assert validator.validate("6011111111111117") is True
    
    def test_invalid_credit_cards(self):
        """Test invalid credit card numbers."""
        validator = LuhnValidator()
        
        assert validator.validate("1234567890123456") is False
        assert validator.validate("0000000000000000") is False
        assert validator.validate("4532015112830367") is False  # Wrong checksum
    
    def test_with_spaces_and_dashes(self):
        """Test cards with formatting."""
        validator = LuhnValidator()
        
        assert validator.validate("4532-0151-1283-0366") is True
        assert validator.validate("4532 0151 1283 0366") is True


class TestRedactionEngine:
    """Test redaction engine."""
    
    def test_email_redaction(self):
        """Test email pattern detection and redaction."""
        rules = [
            RedactionRule(
                id="EMAIL_REGEX",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                action=RedactionAction.MASK,
                severity=Severity.MEDIUM,
                tags=["GDPR"]
            )
        ]
        
        engine = RedactionEngine(rules)
        
        data = {"email": "john.doe@example.com"}
        redacted = engine.redact(data)
        
        assert redacted["email"] != "john.doe@example.com"
        assert "@" in redacted["email"]
        assert len(engine.get_redaction_meta()) == 1
    
    def test_credit_card_redaction(self):
        """Test credit card detection with Luhn."""
        rules = [
            RedactionRule(
                id="LUHN_PAN",
                pattern=r'(?:\d[ -]*?){13,19}',
                action=RedactionAction.MASK,
                severity=Severity.HIGH,
                tags=["PCI_DSS"]
            )
        ]
        
        engine = RedactionEngine(rules)
        
        data = {"card": "4532015112830366"}
        redacted = engine.redact(data)
        
        # Should show last 4 digits
        assert redacted["card"].endswith("0366")
        assert "*" in redacted["card"]
        assert len(engine.get_redaction_meta()) == 1
    
    def test_phone_redaction(self):
        """Test phone number redaction."""
        rules = [
            RedactionRule(
                id="PHONE_REGEX",
                pattern=r'(\+\d{1,3}[- .]?)?\(?\d{3}\)?[- .]?\d{3}[- .]?\d{4}',
                action=RedactionAction.MASK,
                severity=Severity.MEDIUM,
                tags=["GDPR"]
            )
        ]
        
        engine = RedactionEngine(rules)
        
        data = {"phone": "555-123-4567"}
        redacted = engine.redact(data)
        
        assert redacted["phone"] != "555-123-4567"
        assert len(engine.get_redaction_meta()) == 1
    
    def test_nested_data_redaction(self):
        """Test redaction in nested structures."""
        rules = [
            RedactionRule(
                id="EMAIL_REGEX",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                action=RedactionAction.MASK,
                severity=Severity.MEDIUM,
                tags=["GDPR"]
            )
        ]
        
        engine = RedactionEngine(rules)
        
        data = {
            "user": {
                "profile": {
                    "email": "test@example.com"
                }
            }
        }
        
        redacted = engine.redact(data)
        
        assert redacted["user"]["profile"]["email"] != "test@example.com"
        assert len(engine.get_redaction_meta()) == 1
    
    def test_list_data_redaction(self):
        """Test redaction in lists."""
        rules = [
            RedactionRule(
                id="EMAIL_REGEX",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                action=RedactionAction.MASK,
                severity=Severity.MEDIUM,
                tags=["GDPR"]
            )
        ]
        
        engine = RedactionEngine(rules)
        
        data = {
            "users": [
                {"email": "user1@example.com"},
                {"email": "user2@example.com"}
            ]
        }
        
        redacted = engine.redact(data)
        
        assert redacted["users"][0]["email"] != "user1@example.com"
        assert redacted["users"][1]["email"] != "user2@example.com"
        assert len(engine.get_redaction_meta()) == 2


class TestPolicyLoader:
    """Test policy loader."""
    
    def test_load_policy(self):
        """Test loading policy from YAML."""
        loader = PolicyLoader(policy_path="input/redaction_rules.yaml")
        
        policy = loader.get_policy()
        
        assert policy is not None
        assert policy.version is not None
        assert len(policy.rules) > 0
    
    def test_get_rules(self):
        """Test getting enabled rules."""
        loader = PolicyLoader(policy_path="input/redaction_rules.yaml")
        
        rules = loader.get_rules()
        
        assert len(rules) > 0
        for rule in rules:
            assert rule.enabled is True
    
    def test_validate_policy(self):
        """Test policy validation."""
        loader = PolicyLoader(policy_path="input/redaction_rules.yaml")
        
        validation = loader.validate_policy()
        
        assert validation['valid'] is True
        assert validation['rule_count'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
