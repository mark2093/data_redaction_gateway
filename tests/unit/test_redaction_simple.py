"""
Basic tests for the PII/PCI Redaction Gateway - Updated for modular structure.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.engines.luhn_engine import LuhnValidator
from src.core.models.redaction import RedactionRule, RedactionAction
from src.policy import get_policy_loader
from src.engines.base import RedactionEngine


def test_luhn_validator():
    """Test Luhn algorithm validation."""
    print("Testing Luhn Validator...")
    validator = LuhnValidator()
    
    # Valid test cards
    valid_cards = [
        "4532015112830366",
        "5425233430109903", 
        "374245455400126",
        "6011111111111117"
    ]
    
    for card in valid_cards:
        assert validator.validate(card), f"Valid card failed: {card}"
        print(f"  [PASS] Valid card: {card}")
    
    # Invalid test cards
    invalid_cards = [
        "1234567890123456",
        "0000000000000000", 
        "4532015112830367"  # Wrong checksum
    ]
    
    for card in invalid_cards:
        assert not validator.validate(card), f"Invalid card passed: {card}"
        print(f"  [PASS] Invalid card rejected: {card}")
    
    print("  [PASS] Luhn validator tests completed")


def test_redaction_engine():
    """Test the main redaction engine."""
    print("Testing Redaction Engine...")
    
    # Load policy rules
    policy_loader = get_policy_loader()
    rules = policy_loader.get_rules()
    
    # Create engine
    engine = RedactionEngine(rules)
    
    # Test data with PAN
    test_data = {
        "pan": "5425233430109903",
        "name": "John Doe",
        "account": "123456789"
    }
    
    # Redact
    result = engine.redact(test_data)
    
    # Verify PAN was redacted
    assert result["pan"] != test_data["pan"], "PAN should be redacted"
    assert "***" in result["pan"], "PAN should contain masking"
    print(f"  [PASS] PAN redacted: {test_data['pan']} -> {result['pan']}")
    
    # Verify other fields unchanged (depending on rules)
    print(f"  [INFO] Name: {test_data['name']} -> {result['name']}")
    print(f"  [INFO] Account: {test_data['account']} -> {result['account']}")
    
    print("  [PASS] Redaction engine tests completed")


def test_policy_loader():
    """Test policy loader."""
    print("Testing Policy Loader...")
    
    loader = get_policy_loader()
    rules = loader.get_rules()
    
    assert len(rules) > 0, "Should have loaded rules"
    print(f"  [PASS] Loaded {len(rules)} rules")
    
    version = loader.get_policy_version()
    assert version, "Should have policy version"
    print(f"  [PASS] Policy version: {version}")
    
    print("  [PASS] Policy loader tests completed")


def main():
    """Run all tests."""
    print("PII/PCI Redaction Gateway - Unit Tests")
    print("=" * 50)
    
    tests = [
        test_luhn_validator,
        test_policy_loader, 
        test_redaction_engine,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"  [FAIL] Test failed: {e}")
            failed += 1
            print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("[SUCCESS] All unit tests passed!")
        return True
    else:
        print("[ERROR] Some unit tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)