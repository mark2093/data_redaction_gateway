#!/usr/bin/env python3
"""
Test suite runner for the PII/PCI Data Redaction Gateway.
"""
import sys
import subprocess
from pathlib import Path

def run_test_file(test_file: Path) -> bool:
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {test_file.name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_file.parent.parent  # Run from project root
        )
        
        if result.returncode == 0:
            print("✅ PASSED")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("❌ FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all test suites."""
    test_dir = Path(__file__).parent
    
    print("PII/PCI Data Redaction Gateway - Test Suite Runner")
    print("="*60)
    
    # Integration tests
    integration_tests = list((test_dir / "integration").glob("test_*.py"))
    unit_tests = list((test_dir / "unit").glob("test_*.py"))
    
    all_tests = integration_tests + unit_tests
    
    if not all_tests:
        print("No test files found!")
        return False
    
    print(f"Found {len(all_tests)} test files:")
    for test in all_tests:
        print(f"  - {test.relative_to(test_dir)}")
    
    passed = 0
    total = len(all_tests)
    
    for test_file in all_tests:
        if run_test_file(test_file):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed}/{total} files passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 All test files passed!")
        return True
    else:
        print("❌ Some test files failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)