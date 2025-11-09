"""Quick test to verify LLM judge configuration loads correctly."""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_config
from src.judge import get_llm_judge

def test_config():
    """Test configuration loading."""
    print("Testing LLM Judge Configuration...")
    print("=" * 60)
    
    config = get_config()
    
    print(f"✓ Configuration loaded successfully")
    print(f"  - Environment: {config.environment}")
    print(f"  - Version: {config.version}")
    print()
    
    print("LLM Judge Settings:")
    print(f"  - Enabled: {config.llm_judge.enabled}")
    print(f"  - Provider: {config.llm_judge.provider}")
    print(f"  - Model: {config.llm_judge.model}")
    print(f"  - Sampling Rate: {config.llm_judge.sampling_rate * 100}%")
    print(f"  - Timeout: {config.llm_judge.timeout_seconds}s")
    print(f"  - Fallback on Error: {config.llm_judge.fallback_on_error}")
    print()
    
    # Check API key
    api_key = config.llm_judge.api_key
    if api_key and api_key != "null" and not api_key.startswith("${"):
        print(f"✓ API Key configured: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("⚠ API Key not configured!")
        print("  Set LLM_API_KEY environment variable")
        print("  Example: $env:LLM_API_KEY='sk-proj-YOUR-KEY-HERE'")
    print()
    
    print("Budget Settings:")
    budget = config.llm_judge.budget
    print(f"  - Max calls per hour: {budget.get('max_calls_per_hour', 'N/A')}")
    print(f"  - Max calls per day: {budget.get('max_calls_per_day', 'N/A')}")
    print(f"  - Alert on limit: {budget.get('alert_on_limit', 'N/A')}")
    print()
    
    print("Validation Settings:")
    validation = config.llm_judge.validation
    print(f"  - Check coverage: {validation.get('check_coverage', 'N/A')}")
    print(f"  - Check over-redaction: {validation.get('check_over_redaction', 'N/A')}")
    print(f"  - Check under-redaction: {validation.get('check_under_redaction', 'N/A')}")
    print(f"  - Max context chars: {validation.get('max_context_chars', 'N/A')}")
    print(f"  - Include partial mask: {validation.get('include_partial_mask', 'N/A')}")
    print()
    
    # Try to initialize judge
    print("Initializing LLM Judge...")
    try:
        judge = get_llm_judge()
        if judge.client:
            print(f"✓ LLM Judge initialized successfully")
            print(f"  - Ready to validate redactions")
        else:
            print("⚠ LLM Judge initialized but client is None")
            print("  - API key may be missing or invalid")
    except Exception as e:
        print(f"✗ Error initializing LLM Judge: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("Configuration test complete!")

if __name__ == "__main__":
    test_config()
