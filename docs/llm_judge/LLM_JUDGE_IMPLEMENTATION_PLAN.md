# LLM-as-Judge Implementation Plan

## Current Status Analysis

### ✅ Already Implemented
1. **Metrics Infrastructure** - Tracking for judge calls and fallbacks in `src/metrics.py`
2. **Configuration Structure** - LLM judge config section in `config/config.yaml`
3. **Model Fields** - `judge_fallback_rate` in metrics response model

### ❌ Not Implemented
1. **Core LLM Judge Module** - No `src/llm_judge.py` exists
2. **LLM Integration** - No actual LLM API calls (OpenAI, Anthropic, etc.)
3. **Sampling Logic** - No random sampling of requests
4. **Validation Prompts** - No prompt engineering for PII validation
5. **Integration in Main Flow** - Not called from redaction endpoint
6. **Graceful Degradation** - Timeout/error handling framework exists but not used

---

## Implementation Plan

### Phase 1: Core LLM Judge Module (30-45 min)

**File**: `src/llm_judge.py`

**Components**:
1. **LLMJudge Class**
   - Initialize with config (provider, model, api_key, timeout)
   - Support multiple providers (OpenAI, Anthropic, local/Ollama)
   - Async API calls with timeout handling

2. **Sampling Logic**
   ```python
   def should_sample(sample_rate: float) -> bool:
       """Randomly decide if request should be sampled."""
       return random.random() < sample_rate
   ```

3. **Context Preparation**
   ```python
   def prepare_context(original_data, redacted_data, redaction_meta):
       """Create sanitized context for LLM with snippet limits."""
       # Limit data size (e.g., max 500 chars per field)
       # Use partially masked data (not raw PII)
       # Include redaction metadata
       return sanitized_context
   ```

4. **Prompt Engineering**
   ```python
   VALIDATION_PROMPT = '''
   You are a PII/PCI data validation expert. Review the redaction results:
   
   Original (sanitized): {original_snippet}
   Redacted: {redacted_data}
   Rules Applied: {rules_applied}
   
   Assess:
   1. Coverage: Are all PII/PCI fields redacted? (Yes/No)
   2. Over-redaction: Were non-sensitive fields unnecessarily redacted? (Yes/No)
   3. Under-redaction: Are there unredacted sensitive fields? (Yes/No)
   4. Confidence: How confident are you? (0-100%)
   
   Respond in JSON format:
   {
     "coverage_complete": true/false,
     "over_redacted": false,
     "under_redacted": false,
     "confidence": 95,
     "suggestions": ["optional feedback"]
   }
   '''
   ```

5. **LLM API Integration**
   - OpenAI (GPT-4, GPT-3.5-turbo)
   - Anthropic (Claude)
   - Local (Ollama - optional)

6. **Error Handling & Fallback**
   ```python
   async def validate_redaction(context):
       try:
           response = await asyncio.wait_for(
               llm_api_call(context),
               timeout=config.timeout_seconds
           )
           return parse_response(response)
       except asyncio.TimeoutError:
           logger.warning("LLM judge timeout - falling back to rules-only")
           metrics.record_judge_call(fallback=True)
           return None
       except Exception as e:
           logger.error(f"LLM judge error: {e}")
           metrics.record_judge_call(fallback=True)
           return None
   ```

---

### Phase 2: Integration with Main Redaction Flow (15-20 min)

**File**: `src/main.py` (modify `/redact` endpoint)

**Changes**:
```python
@app.post("/redact", response_model=RedactionResponse)
async def redact_data(
    request: RedactionRequest,
    api_key: str = Depends(verify_api_key)
):
    # ... existing redaction logic ...
    
    # LLM Judge validation (if enabled and sampled)
    judge_result = None
    if app_config.llm_judge.enabled:
        llm_judge = get_llm_judge()  # Singleton
        
        if llm_judge.should_sample(app_config.llm_judge.sampling_rate):
            judge_result = await llm_judge.validate_redaction(
                original_data=request.data,
                redacted_data=redacted_data,
                redaction_meta=redaction_meta
            )
            
            # Record metrics
            if judge_result:
                app_state['metrics'].record_judge_call(fallback=False)
            else:
                app_state['metrics'].record_judge_call(fallback=True)
    
    # Optionally include judge result in response
    response = RedactionResponse(
        redacted_data=redacted_data,
        redaction_meta=redaction_meta if request.include_meta else None,
        policy_version=policy_version,
        processing_time_ms=processing_time,
        judge_result=judge_result  # Add to model
    )
    
    return response
```

---

### Phase 3: Configuration & Dependencies (10 min)

**File**: `requirements.txt` (add dependencies)
```txt
openai>=1.0.0          # For OpenAI API
anthropic>=0.7.0       # For Claude API
httpx>=0.25.0          # Already included for async HTTP
tenacity>=8.2.0        # For retry logic
```

**File**: `config/config.yaml` (update)
```yaml
llm_judge:
  enabled: true  # Enable the feature
  sampling_rate: 0.15  # 15% of requests
  timeout_seconds: 5
  fallback_on_error: true
  
  # Provider Selection
  provider: "openai"  # openai, anthropic, ollama
  model: "gpt-3.5-turbo"  # Fast and cost-effective
  api_key: "${LLM_API_KEY}"  # From environment variable
  api_endpoint: null  # Optional custom endpoint
  
  # Validation Configuration
  validation:
    check_coverage: true
    check_over_redaction: true
    check_under_redaction: true
    max_context_chars: 500  # Limit snippet size
    include_partial_mask: true  # Show ****1234 instead of raw
  
  # Cost Controls
  budget:
    max_calls_per_hour: 100
    max_calls_per_day: 1000
    alert_on_limit: true
```

**File**: `.env.sample` (add)
```bash
# LLM Judge Configuration
LLM_API_KEY=your-openai-or-anthropic-api-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
```

---

### Phase 4: Enhanced Models (5 min)

**File**: `src/models.py` (add judge response model)

```python
class JudgeResult(BaseModel):
    """LLM judge validation result."""
    coverage_complete: bool = Field(..., description="All PII/PCI redacted")
    over_redacted: bool = Field(default=False, description="Non-sensitive data redacted")
    under_redacted: bool = Field(default=False, description="Sensitive data missed")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score")
    suggestions: Optional[List[str]] = Field(default=None, description="Improvement suggestions")
    processing_time_ms: float = Field(..., description="Judge processing time")
    sampled: bool = Field(default=True, description="Was this request sampled")

class RedactionResponse(BaseModel):
    """Response model for redaction API."""
    redacted_data: Union[Dict[str, Any], List[Dict[str, Any]], str]
    redaction_meta: Optional[List[RedactionMeta]] = None
    policy_version: str
    processing_time_ms: float
    judge_result: Optional[JudgeResult] = None  # NEW FIELD
```

---

### Phase 5: Testing & Validation (15 min)

**Create**: `tests/test_llm_judge.py`

```python
import pytest
from src.llm_judge import LLMJudge, should_sample

def test_sampling_logic():
    """Test that sampling rate is respected."""
    samples = [should_sample(0.15) for _ in range(1000)]
    sample_rate = sum(samples) / len(samples)
    assert 0.10 <= sample_rate <= 0.20  # Allow some variance

@pytest.mark.asyncio
async def test_llm_judge_timeout():
    """Test graceful degradation on timeout."""
    judge = LLMJudge(timeout_seconds=0.1)
    result = await judge.validate_redaction({}, {}, [])
    assert result is None  # Should fallback gracefully

@pytest.mark.asyncio
async def test_llm_judge_success():
    """Test successful LLM validation."""
    # Mock LLM response
    # Verify parsing works correctly
    pass
```

**Create**: `test_llm_judge_endpoint.ps1`

```powershell
# Test with LLM judge enabled
$body = @{
    data = @{
        pan = "4111111111111111"
        email = "test@example.com"
    }
    include_meta = $true
} | ConvertTo-Json

# Run multiple times to test sampling
for ($i = 1; $i -le 20; $i++) {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/redact" `
        -Method POST `
        -Headers @{"X-API-Key"="dev-api-key-12345"} `
        -Body $body
    
    if ($response.judge_result) {
        Write-Host "Request $i: LLM Judge SAMPLED" -ForegroundColor Green
        Write-Host "  Coverage: $($response.judge_result.coverage_complete)"
        Write-Host "  Confidence: $($response.judge_result.confidence)%"
    } else {
        Write-Host "Request $i: Rules-only (not sampled)" -ForegroundColor Gray
    }
}
```

---

## Implementation Effort & Timeline

### Estimated Time Breakdown
- **Phase 1**: Core LLM Judge Module - 45 minutes
- **Phase 2**: Integration - 20 minutes
- **Phase 3**: Config & Dependencies - 10 minutes
- **Phase 4**: Models Update - 5 minutes
- **Phase 5**: Testing - 15 minutes

**Total**: ~1.5 hours of focused development

---

## Benefits of This Implementation

### ✅ Compliance
- Validates redaction quality programmatically
- Detects edge cases missed by rules
- Provides audit trail for validation

### ✅ Adaptive Learning
- LLM feedback can improve rule configuration
- Identifies patterns for new rules
- Detects emerging PII formats

### ✅ Production Ready
- Graceful degradation on LLM failure
- Cost controls (sampling, rate limits)
- Timeout handling
- Never exposes raw PII to LLM

### ✅ Observability
- Tracks judge call rate
- Monitors fallback rate
- Measures judge latency separately

---

## Security Considerations

### 🔒 Data Protection
1. **Snippet Limiting**: Max 500 chars per field
2. **Partial Masking**: Show `****1234` not raw PAN in context
3. **No Raw Logs**: Never log LLM prompts with real data
4. **Secure API Keys**: Environment variables only

### 🔒 LLM Provider Security
1. Use providers with data residency guarantees
2. Enable zero-retention policies (OpenAI, Anthropic support this)
3. Consider local/on-prem LLM for sensitive environments (Ollama)

---

## Cost Analysis

### OpenAI GPT-3.5-turbo
- **Cost**: ~$0.002 per request (1K tokens avg)
- **15% sampling**: $0.0003 per request average
- **1000 requests/day**: ~$0.30/day or $9/month

### Anthropic Claude-instant
- **Cost**: ~$0.003 per request
- **15% sampling**: ~$13.50/month for 1000 req/day

### Local (Ollama)
- **Cost**: $0 (runs locally)
- **Latency**: Higher (~2-5 seconds)
- **Privacy**: Complete data control

---

## Rollout Strategy

### Stage 1: Development
1. Implement with mock LLM responses
2. Test sampling logic
3. Validate timeout handling

### Stage 2: Testing
1. Enable with OpenAI in dev environment
2. Start with 5% sampling
3. Monitor fallback rates

### Stage 3: Production
1. Start disabled (enabled: false)
2. Enable with 10% sampling for 1 week
3. Analyze results and adjust
4. Increase to 15-20% if valuable

---

## Alternative: Mock Mode (for demo/testing)

If you don't want to use real LLM APIs initially:

```python
class MockLLMJudge:
    """Mock LLM judge for testing."""
    async def validate_redaction(self, original, redacted, meta):
        # Simulate LLM response without API calls
        return JudgeResult(
            coverage_complete=len(meta) > 0,
            over_redacted=False,
            under_redacted=False,
            confidence=95.0,
            suggestions=[],
            processing_time_ms=10.0,
            sampled=True
        )
```

This lets you:
- Test the integration without API costs
- Demo the feature in presentations
- Develop/test without API keys

---

## Files to Create/Modify

### New Files (3)
1. `src/llm_judge.py` - Core implementation (~200 lines)
2. `tests/test_llm_judge.py` - Unit tests (~150 lines)
3. `test_llm_judge_endpoint.ps1` - Integration test script

### Modified Files (4)
1. `src/main.py` - Add judge integration (~30 lines)
2. `src/models.py` - Add JudgeResult model (~15 lines)
3. `config/config.yaml` - Update llm_judge section (~10 lines)
4. `requirements.txt` - Add dependencies (~4 lines)

**Total New Code**: ~400 lines
**Total Modified Code**: ~60 lines

---

## Decision Points for Approval

### 1. LLM Provider Choice
- [ ] **OpenAI** (fastest, easiest, $9/month)
- [ ] **Anthropic** (more private, similar cost)
- [ ] **Local/Ollama** (free, slower, requires setup)
- [ ] **Mock mode first** (no API, demo-ready)

### 2. Sampling Rate
- [ ] Start with 5% (minimal cost)
- [ ] Start with 10% (balanced)
- [ ] Start with 15% (as specified in requirements)

### 3. Response Integration
- [ ] Include judge result in API response (transparent)
- [ ] Log judge results only (silent validation)
- [ ] Optional flag to include judge result

### 4. Rollout Approach
- [ ] Implement full feature immediately
- [ ] Start with mock mode, then add real LLM
- [ ] Implement but keep disabled by default

---

## Recommended Approach

**My Recommendation**: 

1. **Implement with Mock Mode First** (30 min)
   - Full integration, sampling logic, metrics
   - No API costs, demo-ready immediately
   - Easy to switch to real LLM later

2. **Add Real LLM Support** (45 min)
   - OpenAI integration (easiest)
   - Config flag to toggle mock vs real
   - Start with 10% sampling

3. **Production Ready** (15 min)
   - Add cost controls
   - Enhanced error handling
   - Monitoring dashboard

This approach gives you:
- ✅ Working demo immediately
- ✅ No API costs during development
- ✅ Easy upgrade to production LLM
- ✅ Full feature as specified in requirements

---

## Next Steps

Please approve:
1. ✅ Implementation approach (mock first or real LLM)
2. ✅ LLM provider preference
3. ✅ Sampling rate
4. ✅ Timeline expectations

Once approved, I'll implement the feature with all the components listed above!
