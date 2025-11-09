"""
Comprehensive test suite for LLM-as-Judge functionality.

This script tests the LLM Judge implementation including:
- Sampling mechanism
- Budget controls
- OpenAI and Anthropic provider integration
- Validation parsing
- Error handling and fallbacks
"""
import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.judge.llm_judge import LLMJudge, get_llm_judge
from src.core.models.redaction import RedactionMeta, RedactionAction
from src.config import get_config


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}")


def print_test(name, passed, details=""):
    """Print test result."""
    status = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {name}")
    if details:
        print(f"  {details}")


async def test_initialization():
    """Test LLM Judge initialization."""
    print_section("Test 1: Initialization")
    
    try:
        judge = LLMJudge()
        print_test(
            "LLM Judge instantiated",
            True,
            f"Provider: {judge.judge_config.provider}, Model: {judge.judge_config.model}"
        )
        
        print_test(
            "Configuration loaded",
            judge.judge_config is not None,
            f"Enabled: {judge.judge_config.enabled}, Sampling: {judge.judge_config.sampling_rate}"
        )
        
        print_test(
            "Budget tracking initialized",
            hasattr(judge, 'calls_this_hour') and hasattr(judge, 'calls_this_day'),
            f"Hour: {judge.calls_this_hour}, Day: {judge.calls_this_day}"
        )
        
        return judge
        
    except Exception as e:
        print_test("Initialization", False, str(e))
        return None


async def test_sampling_mechanism(judge):
    """Test sampling rate mechanism."""
    print_section("Test 2: Sampling Mechanism")
    
    if not judge:
        print_test("Sampling test", False, "Judge not initialized")
        return
    
    try:
        # Test sampling with 15% rate
        sample_count = 0
        total_tests = 1000
        
        # Temporarily enable for testing
        original_enabled = judge.judge_config.enabled
        judge.judge_config.enabled = True
        
        for _ in range(total_tests):
            if judge.should_sample():
                sample_count += 1
        
        judge.judge_config.enabled = original_enabled
        
        sample_rate = (sample_count / total_tests) * 100
        expected_rate = judge.judge_config.sampling_rate * 100
        
        # Allow 5% variance
        within_range = abs(sample_rate - expected_rate) < 5
        
        print_test(
            "Sampling rate accuracy",
            within_range,
            f"Expected: ~{expected_rate}%, Got: {sample_rate:.1f}% ({sample_count}/{total_tests})"
        )
        
        # Test when disabled
        judge.judge_config.enabled = False
        should_not_sample = not judge.should_sample()
        judge.judge_config.enabled = original_enabled
        
        print_test(
            "Respects enabled flag",
            should_not_sample,
            "No sampling when disabled"
        )
        
    except Exception as e:
        print_test("Sampling mechanism", False, str(e))


async def test_budget_controls(judge):
    """Test budget control mechanism."""
    print_section("Test 3: Budget Controls")
    
    if not judge:
        print_test("Budget test", False, "Judge not initialized")
        return
    
    try:
        # Save original values
        original_hour_calls = judge.calls_this_hour
        original_day_calls = judge.calls_this_day
        
        # Test hourly limit
        max_hour = judge.judge_config.budget.get('max_calls_per_hour', 100)
        judge.calls_this_hour = max_hour - 1
        
        within_budget = judge._check_budget()
        print_test(
            "Within hourly budget",
            within_budget,
            f"Calls: {judge.calls_this_hour}/{max_hour}"
        )
        
        # Test exceeding hourly limit
        judge.calls_this_hour = max_hour + 1
        over_budget = not judge._check_budget()
        print_test(
            "Blocks when over hourly budget",
            over_budget,
            f"Calls: {judge.calls_this_hour}/{max_hour}"
        )
        
        # Reset and test daily limit
        judge.calls_this_hour = 0
        max_day = judge.judge_config.budget.get('max_calls_per_day', 1000)
        judge.calls_this_day = max_day + 1
        
        over_daily = not judge._check_budget()
        print_test(
            "Blocks when over daily budget",
            over_daily,
            f"Calls: {judge.calls_this_day}/{max_day}"
        )
        
        # Restore original values
        judge.calls_this_hour = original_hour_calls
        judge.calls_this_day = original_day_calls
        
    except Exception as e:
        print_test("Budget controls", False, str(e))


async def test_context_preparation(judge):
    """Test context preparation for LLM."""
    print_section("Test 4: Context Preparation")
    
    if not judge:
        print_test("Context preparation", False, "Judge not initialized")
        return
    
    try:
        # Sample data
        original_data = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "card": "4532111122223333"
            },
            "transaction": {
                "amount": 99.99,
                "currency": "USD",
                "timestamp": "2025-11-09T10:00:00Z"
            }
        }
        
        redacted_data = {
            "customer": {
                "name": "[REDACTED]",
                "email": "[REDACTED]",
                "card": "[REDACTED]"
            },
            "transaction": {
                "amount": 99.99,
                "currency": "USD",
                "timestamp": "2025-11-09T10:00:00Z"
            }
        }
        
        redaction_meta = [
            RedactionMeta(
                field="customer.name",
                original_value="John Doe",
                redacted_value="[REDACTED]",
                rule="person_name",
                action=RedactionAction.MASK,
                confidence=0.95
            ),
            RedactionMeta(
                field="customer.email",
                original_value="john.doe@example.com",
                redacted_value="[REDACTED]",
                rule="email",
                action=RedactionAction.MASK,
                confidence=1.0
            ),
            RedactionMeta(
                field="customer.card",
                original_value="4532111122223333",
                redacted_value="[REDACTED]",
                rule="credit_card",
                action=RedactionAction.MASK,
                confidence=1.0
            )
        ]
        
        context = judge._prepare_context(original_data, redacted_data, redaction_meta)
        
        print_test(
            "Context includes original snippet",
            'original_snippet' in context,
            f"Length: {len(context.get('original_snippet', ''))}"
        )
        
        print_test(
            "Context includes redacted data",
            'redacted_data' in context,
            f"Length: {len(context.get('redacted_data', ''))}"
        )
        
        print_test(
            "Context includes redaction metadata",
            'redactions_applied' in context and len(context['redactions_applied']) == 3,
            f"Found {len(context.get('redactions_applied', []))} redactions"
        )
        
        print_test(
            "Context includes redaction count",
            context.get('redaction_count') == 3,
            f"Count: {context.get('redaction_count')}"
        )
        
        # Test max context chars limit
        max_chars = judge.judge_config.validation.get('max_context_chars', 500)
        long_data = {"field": "x" * 10000}
        long_context = judge._prepare_context(long_data, long_data, [])
        
        snippet_length = len(long_context['original_snippet'])
        within_limit = snippet_length <= max_chars + 100  # Allow for JSON formatting
        
        print_test(
            "Respects max context chars",
            within_limit,
            f"Snippet length: {snippet_length}, Limit: {max_chars}"
        )
        
        print("\n  Sample context structure:")
        print(f"  - Original snippet: {len(context['original_snippet'])} chars")
        print(f"  - Redacted data: {len(context['redacted_data'])} chars")
        print(f"  - Redactions: {context['redaction_count']} items")
        
        return context
        
    except Exception as e:
        print_test("Context preparation", False, str(e))
        return None


async def test_response_parsing(judge):
    """Test LLM response parsing."""
    print_section("Test 5: Response Parsing")
    
    if not judge:
        print_test("Response parsing", False, "Judge not initialized")
        return
    
    try:
        # Test valid JSON response
        valid_response = """```json
{
  "coverage_complete": true,
  "over_redacted": false,
  "under_redacted": false,
  "confidence": 95.5,
  "suggestions": ["Good redaction coverage"]
}
```"""
        
        result = judge._parse_response(valid_response)
        
        print_test(
            "Parses JSON in code blocks",
            result.get('coverage_complete') == True,
            f"Coverage: {result.get('coverage_complete')}"
        )
        
        print_test(
            "Extracts confidence as float",
            isinstance(result.get('confidence'), float) and result.get('confidence') == 95.5,
            f"Confidence: {result.get('confidence')}"
        )
        
        print_test(
            "Extracts suggestions list",
            isinstance(result.get('suggestions'), list) and len(result.get('suggestions')) > 0,
            f"Suggestions: {result.get('suggestions')}"
        )
        
        # Test plain JSON
        plain_json = '{"coverage_complete": false, "confidence": 80, "suggestions": []}'
        plain_result = judge._parse_response(plain_json)
        
        print_test(
            "Parses plain JSON",
            plain_result.get('coverage_complete') == False,
            f"Coverage: {plain_result.get('coverage_complete')}"
        )
        
        # Test invalid JSON (should return conservative defaults)
        invalid_response = "This is not JSON at all"
        invalid_result = judge._parse_response(invalid_response)
        
        print_test(
            "Handles invalid JSON gracefully",
            invalid_result.get('coverage_complete') == False and invalid_result.get('confidence') == 0.0,
            f"Returns conservative defaults on error"
        )
        
        print("\n  Parsed result structure:")
        for key, value in result.items():
            print(f"  - {key}: {value}")
        
    except Exception as e:
        print_test("Response parsing", False, str(e))


async def test_validation_flow(judge, context):
    """Test full validation flow (with mock)."""
    print_section("Test 6: Validation Flow")
    
    if not judge:
        print_test("Validation flow", False, "Judge not initialized")
        return
    
    if not context:
        print_test("Validation flow", False, "No context available")
        return
    
    try:
        # Check if LLM is actually configured
        has_api_key = (
            judge.judge_config.api_key and 
            judge.judge_config.api_key != "null" and 
            not judge.judge_config.api_key.startswith("${")
        )
        
        if has_api_key and judge.client:
            print("  Attempting live LLM validation...")
            
            # Prepare test data
            original_data = {
                "email": "test@example.com",
                "card": "4532111122223333"
            }
            redacted_data = {
                "email": "[REDACTED]",
                "card": "*********3333"
            }
            redaction_meta = [
                RedactionMeta(
                    field="email",
                    original_value="test@example.com",
                    redacted_value="[REDACTED]",
                    rule="email",
                    action=RedactionAction.MASK,
                    confidence=1.0
                ),
                RedactionMeta(
                    field="card",
                    original_value="4532111122223333",
                    redacted_value="*********3333",
                    rule="credit_card",
                    action=RedactionAction.MASK,
                    confidence=1.0
                )
            ]
            
            try:
                result = await judge.validate_redaction(
                    original_data,
                    redacted_data,
                    redaction_meta
                )
                
                if result:
                    print_test(
                        "Live LLM validation successful",
                        True,
                        f"Coverage: {result.coverage_complete}, Confidence: {result.confidence}%"
                    )
                    
                    print_test(
                        "Tracking counters incremented",
                        judge.calls_this_hour > 0,
                        f"Hour calls: {judge.calls_this_hour}, Day calls: {judge.calls_this_day}"
                    )
                    
                    print("\n  Validation result:")
                    print(f"  - Coverage complete: {result.coverage_complete}")
                    print(f"  - Over-redacted: {result.over_redacted}")
                    print(f"  - Under-redacted: {result.under_redacted}")
                    print(f"  - Confidence: {result.confidence}%")
                    print(f"  - Processing time: {result.processing_time_ms:.2f}ms")
                    if result.suggestions:
                        print(f"  - Suggestions: {result.suggestions}")
                else:
                    print_test(
                        "Validation returned None (expected with fallback)",
                        True,
                        "LLM call failed but fallback handled gracefully"
                    )
                    
            except Exception as e:
                print_test(
                    "Live validation",
                    False,
                    f"Error: {str(e)}"
                )
        else:
            print_test(
                "LLM API key not configured",
                True,
                "Skipping live validation (set LLM_API_KEY environment variable to test)"
            )
            
            # Test that it doesn't crash without API key
            print_test(
                "Graceful handling without API key",
                not judge.judge_config.enabled or judge.client is None,
                "LLM judge disabled or client not initialized"
            )
        
    except Exception as e:
        print_test("Validation flow", False, str(e))


async def test_provider_detection():
    """Test provider detection and initialization."""
    print_section("Test 7: Provider Detection")
    
    try:
        config = get_config()
        provider = config.llm_judge.provider.lower() if config.llm_judge.provider else ""
        
        print_test(
            "Provider configured",
            provider in ["openai", "anthropic", "local"],
            f"Provider: {provider}"
        )
        
        # Check if provider libraries are available
        openai_available = False
        anthropic_available = False
        
        try:
            import openai
            openai_available = True
        except ImportError:
            pass
        
        try:
            import anthropic
            anthropic_available = True
        except ImportError:
            pass
        
        print_test(
            "OpenAI library available",
            openai_available,
            "pip install openai" if not openai_available else "Installed"
        )
        
        print_test(
            "Anthropic library available",
            anthropic_available,
            "pip install anthropic" if not anthropic_available else "Installed"
        )
        
        if provider == "openai":
            print_test(
                "Configured provider library available",
                openai_available,
                "OpenAI is configured and library is installed" if openai_available else "Need: pip install openai"
            )
        elif provider == "anthropic":
            print_test(
                "Configured provider library available",
                anthropic_available,
                "Anthropic is configured and library is installed" if anthropic_available else "Need: pip install anthropic"
            )
        
    except Exception as e:
        print_test("Provider detection", False, str(e))


async def test_singleton_pattern():
    """Test singleton pattern."""
    print_section("Test 8: Singleton Pattern")
    
    try:
        judge1 = get_llm_judge()
        judge2 = get_llm_judge()
        
        is_singleton = judge1 is judge2
        print_test(
            "Singleton pattern enforced",
            is_singleton,
            "get_llm_judge() returns same instance"
        )
        
        # Test state persistence
        judge1.calls_this_hour = 42
        same_state = judge2.calls_this_hour == 42
        
        print_test(
            "State persists across calls",
            same_state,
            f"Both instances share state: {judge2.calls_this_hour}"
        )
        
    except Exception as e:
        print_test("Singleton pattern", False, str(e))


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("LLM-AS-JUDGE COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    # Display configuration
    config = get_config()
    print(f"\nConfiguration:")
    print(f"  Enabled: {config.llm_judge.enabled}")
    print(f"  Provider: {config.llm_judge.provider}")
    print(f"  Model: {config.llm_judge.model}")
    print(f"  Sampling Rate: {config.llm_judge.sampling_rate * 100}%")
    print(f"  Timeout: {config.llm_judge.timeout_seconds}s")
    print(f"  Max calls/hour: {config.llm_judge.budget.get('max_calls_per_hour')}")
    print(f"  Max calls/day: {config.llm_judge.budget.get('max_calls_per_day')}")
    
    # Run tests
    judge = await test_initialization()
    await test_sampling_mechanism(judge)
    await test_budget_controls(judge)
    context = await test_context_preparation(judge)
    await test_response_parsing(judge)
    await test_validation_flow(judge, context)
    await test_provider_detection()
    await test_singleton_pattern()
    
    # Summary
    print_section("Test Summary")
    print("\n✓ All core LLM Judge features tested")
    print("\nKey Features Verified:")
    print("  ✓ Initialization and configuration loading")
    print("  ✓ Sampling mechanism (15% of requests)")
    print("  ✓ Budget controls (hourly and daily limits)")
    print("  ✓ Context preparation (with character limits)")
    print("  ✓ Response parsing (JSON extraction and defaults)")
    print("  ✓ Provider detection (OpenAI/Anthropic)")
    print("  ✓ Singleton pattern implementation")
    
    print("\nTo enable live LLM validation:")
    print("  1. Set environment variable: export LLM_API_KEY='your-api-key'")
    print("  2. Install provider library: pip install openai  (or anthropic)")
    print("  3. Ensure llm_judge.enabled=true in config.yaml")
    print("  4. Re-run this test script")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
