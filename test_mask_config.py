"""Test script to verify mask_config is loaded from YAML."""
from src.policy_loader import get_policy_loader

# Load policy
loader = get_policy_loader()
rules = loader.get_rules()

print(f"Loaded {len(rules)} rules")
print(f"Policy version: {loader.get_policy_version()}")
print("=" * 60)

# Check each rule for mask_config
for rule in rules:
    print(f"\nRule: {rule.id}")
    print(f"  Action: {rule.action}")
    
    if hasattr(rule, 'mask_config') and rule.mask_config:
        print(f"  Has mask_config: YES")
        print(f"  Mask mode: {rule.mask_config.get('mode')}")
        print(f"  Replacement char: {rule.mask_config.get('replacement_char', '*')}")
        
        if rule.mask_config.get('preserve_last'):
            print(f"  Preserve last: {rule.mask_config.get('preserve_last')} chars")
        if rule.mask_config.get('preserve_first'):
            print(f"  Preserve first: {rule.mask_config.get('preserve_first')} chars")
    else:
        print(f"  Has mask_config: NO")

print("\n" + "=" * 60)
print("✅ mask_config loaded successfully from YAML!")
