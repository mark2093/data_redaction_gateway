# Test Suite Documentation

## Overview

This comprehensive test suite validates all API endpoints of the PII/PCI Data Redaction Gateway using real test data from `input/` folder.

## Quick Start

### Run All Tests (Single Command)

```powershell
python test_suite\test_all_endpoints.py
```

Or use the runner script:
```powershell
.\test_suite\run_tests.ps1
```

### Prerequisites

1. **Server must be running:**
   ```powershell
   python main_modular.py
   ```

2. **Test data files required:**
   - `input/test_chat.json` - Chat messages with PII
   - `input/test_order.json` - E-commerce order with customer data
   - `input/test_transaction.json` - Financial transaction with PAN/IBAN

## Test Coverage

The test suite validates **11 major sections** with **50+ test cases**:

### 1. Health & Status Checks (4 tests)
- Basic health check
- API health check
- Readiness probe
- Liveness probe

**Purpose:** Ensure server is running and responsive

### 2. Redaction Endpoints (6 tests)
- Chat message redaction (MASK method)
- Order data redaction (TOKENIZE method)
- Transaction data redaction (HASH method)
- Format-Preserving Encryption (FPE)

**Purpose:** Validate core redaction functionality with real test data

**Test Data Used:**
- `test_chat.json` - Tests: email, phone, credit card detection in messages
- `test_order.json` - Tests: customer PII, credit card, address redaction
- `test_transaction.json` - Tests: PAN, IBAN, account number redaction

### 3. Streaming Endpoints (1 test)
- NDJSON stream processing

**Purpose:** Validate high-volume data streaming capabilities

### 4. Content Processing (2 tests)
- Base64 encoded content
- Regular content processing

**Purpose:** Test decompression and decoding middleware

### 5. Policy Management (3 tests)
- List all policies
- Get active policies
- Get specific policy details

**Purpose:** Verify policy configuration and retrieval

### 6. Metrics & Observability (4 tests)
- Basic metrics
- Detailed metrics
- Endpoint metrics
- Performance metrics

**Purpose:** Validate monitoring and observability features

### 7. Authentication & Authorization (4 tests)
- Create test user
- Login with credentials
- Get current user info
- Verify JWT token

**Purpose:** Test JWT authentication and user management

### 8. Audit Logging (4 tests)
- Get audit events
- Get audit statistics
- List event types
- List severity levels

**Purpose:** Validate comprehensive audit trail

### 9. Rate Limiting (3 tests)
- Get rate limit status
- Get rate limit stats
- Test rate limit enforcement (10 rapid requests)

**Purpose:** Verify rate limiting protection

### 10. Error Handling (3 tests)
- Missing API key (401)
- Invalid request data (422)
- Non-existent endpoint (404)

**Purpose:** Validate proper error responses

### 11. Performance & Load (1 test)
- 20 concurrent redaction requests
- Measure avg/min/max response times

**Purpose:** Ensure performance meets <100ms target

## Test Output

### Real-Time Console Output

The test suite provides **color-coded, detailed output**:

```
======================================================================
TEST SECTION 1: HEALTH & STATUS CHECKS
======================================================================
  ✓ PASS Basic Health Check
      Status: 200
      Response time: 15.23ms
  ✓ PASS API Health Check
      Status: 200
      Response time: 12.45ms
  ...
```

**Color Coding:**
- 🟢 **Green** - Test passed
- 🔴 **Red** - Test failed
- 🟡 **Yellow** - Warning or slow response

### Input/Output Visibility

For redaction tests, you see:

```
  ✓ PASS Redact Chat Message #1 (MASK)
      Original:
      Hi, this is Alice Johnson, my card 4111111111111111 was declined today.
      Redacted:
      Hi, this is [REDACTED], my card *********1111 was declined today.
      Response time: 28.45ms
      Redactions applied: 2
```

### Test Summary

At the end, you get a comprehensive summary:

```
======================================================================
TEST SUMMARY
======================================================================
Total Tests:    52
Passed:         50
Failed:         0
Warnings:       2
Pass Rate:      96.2%
Duration:       15.34s

✓ ALL TESTS PASSED - READY FOR DEPLOYMENT
======================================================================
```

### Detailed Results File

Results are automatically saved to:
```
test_suite/test_results_YYYYMMDD_HHMMSS.json
```

Example structure:
```json
{
  "timestamp": "2025-11-09T10:30:00",
  "summary": {
    "total": 52,
    "passed": 50,
    "failed": 0,
    "warnings": 2,
    "pass_rate": 96.2
  },
  "results": [
    {
      "test": "Basic Health Check",
      "status": true,
      "message": "Status: 200",
      "response_time": 15.23
    },
    ...
  ]
}
```

## Test Data Files

### test_chat.json
Contains chat messages with various PII types:
- Person names
- Email addresses
- Phone numbers
- Credit card numbers

**Use Case:** Tests NER (Named Entity Recognition) and pattern matching

### test_order.json
E-commerce order with complete customer profile:
- Customer name, email, phone
- Billing address
- Credit card (PAN), expiry, CVV

**Use Case:** Tests structured data redaction and field-level policies

### test_transaction.json
Financial transaction record:
- Account numbers
- IBAN codes
- PAN (Primary Account Number)
- Customer information

**Use Case:** Tests PCI DSS compliance and financial data protection

## Understanding Test Results

### Success Criteria

**PASS:** Status code matches expected, response time acceptable
- Health checks: Status 200
- Redaction: Status 200, data properly redacted
- Errors: Expected error status (401, 404, 422)

**FAIL:** 
- Server not running
- Wrong status code
- Timeout (>10s)
- Exception thrown

**WARNING:**
- Test data file not found
- Rate limit not triggered (expected)
- Slow response time (>500ms)

### Performance Benchmarks

| Endpoint Type | Target | Good | Warning | Critical |
|---------------|--------|------|---------|----------|
| Health checks | <20ms | <50ms | <100ms | >100ms |
| Redaction | <30ms | <50ms | <100ms | >100ms |
| Streaming | <100ms | <200ms | <500ms | >500ms |
| Authentication | <50ms | <100ms | <200ms | >200ms |

### Pass Rate Guidelines

- **≥90%** - ✅ Production ready
- **70-89%** - ⚠️ Review warnings, may deploy
- **<70%** - ❌ Fix failures before deployment

## Troubleshooting

### "Server is not running"

**Solution:**
```powershell
# Terminal 1: Start server
python main_modular.py

# Terminal 2: Run tests
python test_suite\test_all_endpoints.py
```

### "Could not load test_chat.json"

**Solution:** Ensure test data files exist in `input/` folder:
- `input/test_chat.json`
- `input/test_order.json`
- `input/test_transaction.json`

### Authentication Tests Failing

**Possible causes:**
1. JWT not properly configured
2. User already exists (expected on second run)
3. Password complexity requirements

**Note:** User creation may show "already exists" on subsequent runs - this is expected.

### Rate Limit Not Triggered

**Expected behavior:** Rate limit is 60 requests/minute by default. The test only sends 10 requests, so it may not trigger.

**Not a failure** - just informational warning.

### Connection Timeout

**Causes:**
1. Server overloaded
2. Network issues
3. Endpoint taking too long

**Solution:** Check server logs, restart server, reduce concurrent load.

## Customization

### Change Base URL

Edit `test_all_endpoints.py`:
```python
BASE_URL = "http://localhost:8000"  # Change port or host
```

### Change API Key

Edit `test_all_endpoints.py`:
```python
API_KEY = "dev-api-key-12345"  # Use your API key
```

### Add Custom Tests

Add new test functions following the pattern:
```python
def test_custom_endpoint():
    print_section("MY CUSTOM TESTS")
    
    result = test_endpoint(
        "Test Name",
        "GET",  # or POST
        "/my/endpoint",
        {"key": "value"}  # optional data
    )
    
    if result:
        # Validate result
        assert result.get('expected_field') == 'expected_value'
```

Then call it in `main()`:
```python
def main():
    # ... existing tests ...
    test_custom_endpoint()
    # ...
```

## CI/CD Integration

### GitHub Actions

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start server
        run: python main_modular.py &
      - name: Wait for server
        run: sleep 5
      - name: Run tests
        run: python test_suite/test_all_endpoints.py
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Start Server') {
            steps {
                sh 'python main_modular.py &'
                sh 'sleep 5'
            }
        }
        stage('Test') {
            steps {
                sh 'python test_suite/test_all_endpoints.py'
            }
        }
    }
}
```

## Exit Codes

The test script returns proper exit codes for automation:

- **0** - All tests passed
- **1** - One or more tests failed

Use in scripts:
```powershell
python test_suite\test_all_endpoints.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "Tests passed - deploying..."
} else {
    Write-Host "Tests failed - aborting deployment"
    exit 1
}
```

## Maintenance

### Update Test Data

Modify files in `input/` folder to test new scenarios:

**Add more PII types:**
```json
{
  "message": "My SSN is 123-45-6789 and passport is AB1234567"
}
```

**Add edge cases:**
```json
{
  "message": "Email without @ symbol: invalid_email"
}
```

### Update Expected Responses

If API changes, update expected status codes:
```python
test_endpoint(
    "New Endpoint",
    "POST",
    "/new/endpoint",
    expected_status=201  # Created instead of 200
)
```

## Summary

This test suite provides:

✅ **Comprehensive coverage** - 50+ tests across 11 sections
✅ **Real test data** - Uses actual chat, order, and transaction files
✅ **Single command execution** - `python test_suite\test_all_endpoints.py`
✅ **Visual output** - Color-coded, detailed console output
✅ **Input/Output visibility** - Shows original vs redacted data
✅ **Automated reporting** - JSON results saved automatically
✅ **Performance validation** - Response time tracking
✅ **CI/CD ready** - Exit codes for automation
✅ **Easy customization** - Add tests, modify data, change config

**Run anytime to validate your deployment!** 🚀
