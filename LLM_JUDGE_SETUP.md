# LLM-as-Judge Implementation Guide

## Overview

The LLM-as-Judge feature validates redaction quality by sampling approximately 15% of requests and sending sanitized context to a Large Language Model (OpenAI GPT-4o-mini). This ensures comprehensive PII/PCI coverage and detects both over-redaction and under-redaction.

## ✅ What Was Implemented

### 1. Core LLM Judge Module (`src/llm_judge.py`)
- **LLMJudge Class**: Handles LLM API calls with OpenAI and Anthropic support
- **Sampling Logic**: Random sampling based on configured rate (default 15%)
- **Context Preparation**: Sanitizes data before sending to LLM
  - Snippet limiting (max 500 chars)
  - Partial masking of PII in original context
  - Never sends raw sensitive data
- **Prompt Engineering**: Structured validation prompt checking:
  - Coverage completeness
  - Over-redaction of non-sensitive fields
  - Under-redaction of sensitive fields
  - Confidence scoring
- **Timeout & Error Handling**: Graceful fallback on errors
- **Budget Controls**: Hourly/daily call limits to manage costs

### 2. Enhanced Data Models (`src/models.py`)
- **JudgeResult**: Validation result model with:
  - `coverage_complete`: bool
  - `over_redacted`: bool
  - `under_redacted`: bool
  - `confidence`: float (0-100%)
  - `suggestions`: list of improvement recommendations
  - `processing_time_ms`: judge processing time
  - `sampled`: flag indicating if request was sampled
- **RedactionResponse**: Updated to include `judge_result` field

### 3. API Integration (`src/main.py`)
- `/redact` endpoint now includes LLM judge validation
- Samples requests based on configured rate
- Stores original data for comparison
- Calls judge asynchronously after redaction
- Records metrics (judge calls, fallbacks)
- Gracefully handles judge errors without blocking redaction

### 4. Configuration (`config/config.yaml`)
```yaml
llm_judge:
  enabled: true
  sampling_rate: 0.15  # 15% of requests
  timeout_seconds: 5
  fallback_on_error: true
  provider: "openai"
  model: "gpt-4o-mini"  # Fast, cost-effective
  api_key: "${LLM_API_KEY}"
  
  budget:
    max_calls_per_hour: 100
    max_calls_per_day: 1000
    alert_on_limit: true
  
  validation:
    check_coverage: true
    check_over_redaction: true
    check_under_redaction: true
    max_context_chars: 500
    include_partial_mask: true
```

### 5. Dependencies (`requirements.txt`)
- `openai>=1.0.0`: OpenAI API client
- `anthropic>=0.7.0`: Anthropic API client (alternative)

### 6. Environment Variables (`.env.sample`)
```bash
# Get your OpenAI API key from: https://platform.openai.com/api-keys
LLM_API_KEY=sk-proj-your-openai-api-key-here
```

### 7. Test Script (`test_llm_judge.ps1`)
- Sends 20 requests to test sampling
- Tracks sampled vs non-sampled requests
- Analyzes judge results (confidence, coverage, timing)
- Verifies sampling rate matches configuration

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```powershell
# Install new LLM client libraries
pip install openai anthropic

# Or reinstall all requirements
pip install -r requirements.txt
```

### Step 2: Configure OpenAI API Key

1. **Get API Key**:
   - Visit https://platform.openai.com/api-keys
   - Create a new API key
   - Copy the key (starts with `sk-proj-...`)

2. **Set Environment Variable**:

**Option A: Create `.env` file (Recommended)**
```powershell
# Copy sample file
cp .env.sample .env

# Edit .env and set your key
notepad .env
```

In `.env`:
```bash
LLM_API_KEY=sk-proj-YOUR-ACTUAL-KEY-HERE
```

**Option B: Set system environment variable**
```powershell
# PowerShell (current session)
$env:LLM_API_KEY="sk-proj-YOUR-ACTUAL-KEY-HERE"

# Or set permanently in Windows
[Environment]::SetEnvironmentVariable("LLM_API_KEY", "sk-proj-YOUR-ACTUAL-KEY-HERE", "User")
```

### Step 3: Enable LLM Judge

Edit `config/config.yaml`:
```yaml
llm_judge:
  enabled: true  # Make sure this is true
  sampling_rate: 0.15  # Adjust as needed (0.05 = 5%, 0.15 = 15%, 0.20 = 20%)
```

### Step 4: Start the Server

```powershell
# Start server with uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Look for confirmation in logs:
```
LLM Judge initialized with OpenAI model: gpt-4o-mini
```

If you see "OpenAI API key not configured", check your environment variable.

### Step 5: Test LLM Judge

**Quick Test:**
```powershell
.\test_llm_judge.ps1
```

This will:
- Send 20 requests
- Show which ones were sampled
- Display judge results (coverage, confidence)
- Calculate actual sampling rate
- Show metrics (fallback rate)

**Manual Test:**
```powershell
$testData = @{
    "email" = "john@example.com"
    "credit_card" = "4532015112830366"
    "name" = "John Smith"
} | ConvertTo-Json

$body = @{"data" = $testData | ConvertFrom-Json; "include_meta" = $true} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8000/redact" `
    -Method Post `
    -Body $body `
    -Headers @{"X-API-Key"="dev-api-key-12345"; "Content-Type"="application/json"}
```

Check the response for `judge_result` field (present in ~15% of requests).

## 📊 Understanding the Results

### Sample Response (Sampled Request)
```json
{
  "redacted_data": {
    "email": "j***@e******e.com",
    "credit_card": "************0366",
    "name": "REDACTED_NAME"
  },
  "redaction_meta": [...],
  "policy_version": "1.4",
  "processing_time_ms": 45.2,
  "judge_result": {
    "coverage_complete": true,
    "over_redacted": false,
    "under_redacted": false,
    "confidence": 95.0,
    "suggestions": [],
    "processing_time_ms": 234.5,
    "sampled": true
  }
}
```

### Sample Response (Non-Sampled Request)
```json
{
  "redacted_data": {...},
  "redaction_meta": [...],
  "policy_version": "1.4",
  "processing_time_ms": 42.1,
  "judge_result": null  // Not sampled
}
```

### Judge Result Fields

- **coverage_complete** (bool): All PII/PCI fields were properly redacted
- **over_redacted** (bool): Non-sensitive fields were unnecessarily redacted
- **under_redacted** (bool): Sensitive fields were missed
- **confidence** (0-100): LLM's confidence in its assessment
- **suggestions** (array): Improvement recommendations
- **processing_time_ms**: Time spent on LLM validation
- **sampled**: Always `true` when present

### Interpreting Results

✅ **Good Result:**
```json
{
  "coverage_complete": true,
  "over_redacted": false,
  "under_redacted": false,
  "confidence": 95.0
}
```

⚠️ **Over-Redaction Warning:**
```json
{
  "coverage_complete": true,
  "over_redacted": true,
  "confidence": 85.0,
  "suggestions": ["Transaction ID should not be redacted"]
}
```

🚨 **Under-Redaction Alert:**
```json
{
  "coverage_complete": false,
  "under_redacted": true,
  "confidence": 90.0,
  "suggestions": ["SSN in 'notes' field was not redacted"]
}
```

## 💰 Cost Management

### Expected Costs (with gpt-4o-mini)

**Pricing:**
- Input: $0.150 per 1M tokens (~$0.00015 per request)
- Output: $0.600 per 1M tokens (~$0.0001 per response)
- Total: ~$0.00025 per request

**Monthly Estimates (15% sampling rate):**
- 1,000 requests/day → 150 sampled → ~$0.04/day → **$1.20/month**
- 10,000 requests/day → 1,500 sampled → ~$0.38/day → **$11.40/month**
- 50,000 requests/day → 7,500 sampled → ~$1.88/day → **$56.40/month**

### Budget Controls

Configured in `config.yaml`:
```yaml
budget:
  max_calls_per_hour: 100    # Prevents runaway costs
  max_calls_per_day: 1000    # Daily cap
  alert_on_limit: true       # Log warning when limits hit
```

### Monitoring Costs

Check metrics endpoint:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/metrics" `
    -Headers @{"X-API-Key"="dev-api-key-12345"}
```

Look for:
- `judge_fallback_rate`: Percentage of judge calls that failed (should be ~0%)

Check logs for budget warnings:
```
LLM judge hourly budget exceeded: 100
LLM judge daily budget exceeded: 1000
```

## 🔧 Configuration Options

### Adjust Sampling Rate

Lower rates = less cost, less validation coverage:
```yaml
sampling_rate: 0.05  # 5% - minimal validation, ~$0.40/month for 10k req/day
sampling_rate: 0.10  # 10% - balanced
sampling_rate: 0.15  # 15% - default, recommended
sampling_rate: 0.20  # 20% - more comprehensive, ~$15/month for 10k req/day
```

### Change Model

```yaml
# Fast, cheap (default)
model: "gpt-4o-mini"

# More accurate, expensive
model: "gpt-4o"

# Even cheaper (older model)
model: "gpt-3.5-turbo"
```

### Use Anthropic Instead

```yaml
provider: "anthropic"
model: "claude-3-haiku-20240307"  # Fast, cheap
# OR
model: "claude-3-sonnet-20240229"  # Balanced
```

Get Anthropic key: https://console.anthropic.com/

### Disable LLM Judge

```yaml
llm_judge:
  enabled: false
```

Or via environment:
```powershell
$env:LLM_ENABLED="false"
```

## 🔒 Security Considerations

### What Gets Sent to LLM?

**NOT sent:**
- Raw PII/PCI data
- Full original data

**Sent:**
- Snippet-limited data (max 500 chars)
- Partially masked original values (e.g., `****1234`)
- Redacted data (safe)
- Redaction metadata (field names, rules, actions)

### Example Context Sent:

```json
{
  "original_snippet": "{\"email\": \"****@example.com\", \"card\": \"****0366\"}",
  "redacted_data": "{\"email\": \"j***@e****e.com\", \"card\": \"************0366\"}",
  "redactions_applied": [
    {"field": "email", "rule": "EMAIL_REGEX", "action": "mask"},
    {"field": "card", "rule": "LUHN_PAN", "action": "mask"}
  ]
}
```

### Data Protection

1. **Snippet Limiting**: Max 500 chars prevents full data exposure
2. **Partial Masking**: Original values show only last 4 digits
3. **No Raw Logs**: PII never logged in application
4. **Secure API Keys**: Stored in environment variables, not code
5. **HTTPS Only**: Use TLS in production

## 🐛 Troubleshooting

### "OpenAI API key not configured"

**Cause**: Environment variable not set or invalid

**Fix:**
1. Check `.env` file exists and has correct key
2. Restart server after setting environment variable
3. Verify key format: `sk-proj-...`

### Judge Always Returns `null`

**Cause**: LLM judge disabled or API key missing

**Fix:**
1. Check `config.yaml`: `enabled: true`
2. Set `LLM_API_KEY` environment variable
3. Check server logs for errors

### High Fallback Rate

**Cause**: Timeout or API errors

**Fix:**
1. Increase timeout: `timeout_seconds: 10`
2. Check OpenAI status: https://status.openai.com/
3. Verify API key has credits
4. Check network connectivity

### Sampling Rate Doesn't Match

**Cause**: Random sampling variation (normal)

**Fix:**
- With 20 requests, expect ±5-10% deviation
- Test with 100+ requests for more accuracy
- 15% target means 10-20% actual is normal

### API Rate Limits

**Cause**: Too many requests to OpenAI

**Fix:**
1. Reduce sampling rate: `sampling_rate: 0.05`
2. Lower budget limits
3. Upgrade OpenAI plan

## 📈 Metrics & Monitoring

### Key Metrics

1. **Judge Fallback Rate**: Target <1%
   - High rate indicates API issues
   
2. **Average Confidence**: Target >85%
   - Low confidence suggests complex data
   
3. **Coverage Complete Rate**: Target 100%
   - <100% indicates missed PII/PCI

4. **Judge Processing Time**: Target <1000ms
   - Higher = slower model or large payloads

### Access Metrics

```powershell
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/metrics" `
    -Headers @{"X-API-Key"="dev-api-key-12345"}

Write-Host "Judge Fallback Rate: $($metrics.judge_fallback_rate)%"
```

## 🎯 Best Practices

1. **Start Small**: Begin with 5% sampling, increase gradually
2. **Monitor Costs**: Check OpenAI usage dashboard regularly
3. **Review Suggestions**: Act on judge recommendations to improve rules
4. **Budget Alerts**: Keep `alert_on_limit: true` to catch issues
5. **Production Keys**: Use separate API keys for dev/prod
6. **Graceful Degradation**: Keep `fallback_on_error: true`

## 🔄 Next Steps

1. **Test thoroughly** with `test_llm_judge.ps1`
2. **Monitor costs** in OpenAI dashboard
3. **Review judge results** for improvement opportunities
4. **Adjust sampling rate** based on needs and budget
5. **Set up alerts** for high fallback rates
6. **Document findings** in your deployment guide

## 📝 Related Documentation

- OpenAI API: https://platform.openai.com/docs
- Anthropic API: https://docs.anthropic.com/
- Problem Statement: `input/problem_statement.md` (Requirement #3)
- Configuration Guide: `CONFIGURATION_GUIDE.md`
- Quick Test Guide: `QUICK_TEST_GUIDE.md`

---

**Implementation Status**: ✅ Complete and tested
**Requirement**: Fulfills Problem Statement Requirement #3 (LLM-as-Judge for Validation)
