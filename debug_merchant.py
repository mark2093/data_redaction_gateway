#!/usr/bin/env python3
"""
Debug script to test merchant redaction pattern.
"""
import re
import json
from src.policy.loader import get_policy_loader
from src.engines.regex_engine import RegexEngine
from src.config import get_config

def test_merchant_pattern():
    """Test merchant pattern matching."""
    
    # Load configuration
    config = get_config()
    
    # Load policy
    policy_loader = get_policy_loader()
    rules = policy_loader.get_rules()
    
    # Find merchant rule
    merchant_rule = None
    for rule in rules:
        if rule.id == "MERCHANT_NAME_REGEX":
            merchant_rule = rule
            break
    
    if not merchant_rule:
        print("❌ MERCHANT_NAME_REGEX rule not found!")
        return
    
    print(f"✅ Found merchant rule: {merchant_rule.id}")
    print(f"📋 Pattern: {merchant_rule.pattern}")
    print(f"⚡ Enabled: {merchant_rule.enabled}")
    
    # Test raw pattern
    test_text = "Tech Store Inc"
    flags = re.IGNORECASE
    try:
        pattern = re.compile(merchant_rule.pattern, flags)
        matches = pattern.findall(test_text)
        print(f"\n🔍 Raw regex test:")
        print(f"   Text: '{test_text}'")
        print(f"   Pattern: '{merchant_rule.pattern}'")
        print(f"   Matches: {matches}")
        print(f"   Found: {len(matches) > 0}")
    except Exception as e:
        print(f"❌ Regex compilation error: {e}")
    
    # Test with RegexEngine
    engine = RegexEngine(config=config)
    detections = engine.detect(test_text, merchant_rule)
    print(f"\n🔧 RegexEngine test:")
    print(f"   Detections: {detections}")
    
    # Test full redaction
    redacted = engine.redact(test_text, merchant_rule, field_name="merchant")
    print(f"   Original: '{test_text}'")
    print(f"   Redacted: '{redacted}'")
    
    # Test with JSON data
    json_data = {"merchant": "Tech Store Inc", "amount": 100.0}
    print(f"\n📄 JSON field test:")
    print(f"   JSON: {json_data}")
    print(f"   merchant field: '{json_data['merchant']}'")
    
    # Test with the main RedactionEngine
    from src.engines.base import RedactionEngine
    from src.engines.registry import get_engine_registry
    
    print(f"\n🔧 Engine registry debug:")
    registry = get_engine_registry()
    
    # Check engine selection for merchant rule
    selected_engine = registry.get_engine(merchant_rule)
    print(f"   Selected engine: {selected_engine}")
    print(f"   Engine type: {type(selected_engine)}")
    print(f"   Engine enabled: {selected_engine.enabled if selected_engine else 'N/A'}")
    
    main_engine = RedactionEngine(rules)
    
    print(f"\n🎯 Full redaction test:")
    print(f"   Number of rules: {len(main_engine.rules)}")
    print(f"   Rules: {[r.id for r in main_engine.rules]}")
    
    # Debug the _redact_string method directly
    print(f"\n🐞 Direct _redact_string test:")
    direct_result = main_engine._redact_string("Tech Store Inc", "$.merchant", field_name="merchant")
    print(f"   Direct result: '{direct_result}'")
    print(f"   Direct meta: {main_engine.get_redaction_meta()}")
    
    # Reset and test full JSON  
    main_engine.redaction_meta = []
    print(f"\n🔍 Step-by-step dict processing:")
    
    # Manual step through _redact_dict logic
    result_dict = {}
    for key, value in json_data.items():
        print(f"   Processing field: {key} = '{value}'")
        
        # Check if field should be excluded
        if key in main_engine.exclude_fields:
            print(f"     → Excluded field")
            result_dict[key] = value
            continue
            
        # Check always redact
        if key in main_engine.always_redact_fields:
            print(f"     → Always redact field")
            result_dict[key] = "***REDACTED***"
            continue
        
        if isinstance(value, str):
            print(f"     → Processing string value")
            redacted_value = main_engine._redact_string(value, f"$.{key}", field_name=key)
            print(f"     → Redacted: '{redacted_value}'")
            result_dict[key] = redacted_value
        else:
            print(f"     → Non-string value, keeping as-is")
            result_dict[key] = value
    
    print(f"   Manual result: {result_dict}")
    
    # Now test the actual method
    print(f"\n🔍 Actual _redact_dict method:")
    main_engine.redaction_meta = []  # Reset again
    actual_result = main_engine._redact_dict(json_data, "$")
    print(f"   Actual result: {actual_result}")
    
    redacted_json = main_engine.redact(json_data)
    print(f"   Original JSON: {json.dumps(json_data, indent=2)}")
    print(f"   Redacted JSON: {json.dumps(redacted_json, indent=2)}")
    
    meta = main_engine.get_redaction_meta()
    print(f"\n📊 Redaction metadata:")
    for m in meta:
        print(f"   Field: {m.field}, Rule: {m.rule}, Action: {m.action}")
    
    # Test step-by-step string processing  
    print(f"\n🔍 Step-by-step test:")
    test_merchant_value = "Tech Store Inc"
    print(f"   Testing string: '{test_merchant_value}'")
    
    for rule in main_engine.rules:
        if rule.id == "MERCHANT_NAME_REGEX":
            engine = registry.get_engine(rule)
            print(f"   Rule: {rule.id}, Engine: {engine}")
            if engine:
                engine.reset_meta()
                result = engine.redact(test_merchant_value, rule, field_name="merchant")
                print(f"   Result: '{result}'")
                rule_meta = engine.get_redaction_meta()
                print(f"   Rule meta: {rule_meta}")

if __name__ == "__main__":
    test_merchant_pattern()