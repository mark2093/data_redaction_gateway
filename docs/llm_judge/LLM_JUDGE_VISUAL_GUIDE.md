# LLM Judge - Visual Flow Diagrams

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ POST /redact
                        │ {"data": "card 4532...", "method": "mask"}
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  Redaction API Gateway                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  1. Receive Request                                    │ │
│  │  2. Apply Redaction Rules (Regex, NER, Luhn)          │ │
│  │  3. Generate Redacted Output                          │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ redacted_data + metadata
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                      LLM Judge                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  should_sample() ?                                     │ │
│  │  ├─ random < 15% ? → YES                              │ │
│  │  ├─ budget OK?     → YES                              │ │
│  │  └─ enabled?       → YES                              │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                      │
│         ┌─────────────┴──────────────┐                      │
│         ↓ (15%)                      ↓ (85%)                │
│  ┌──────────────┐           ┌─────────────────┐            │
│  │ SAMPLE THIS  │           │  SKIP SAMPLING  │            │
│  └──────┬───────┘           └─────────────────┘            │
│         │                            │                      │
│         ↓                            │                      │
│  ┌────────────────────────┐          │                      │
│  │ Prepare Context        │          │                      │
│  │ - Snippet original     │          │                      │
│  │ - Full redacted        │          │                      │
│  │ - Metadata             │          │                      │
│  └─────────┬──────────────┘          │                      │
│            │                          │                      │
│            ↓                          │                      │
│  ┌────────────────────────┐          │                      │
│  │ Call LLM API (async)   │          │                      │
│  │ - OpenAI/Anthropic     │          │                      │
│  │ - Timeout: 5s          │          │                      │
│  └─────────┬──────────────┘          │                      │
│            │                          │                      │
│            ↓                          │                      │
│  ┌────────────────────────┐          │                      │
│  │ Parse JSON Response    │          │                      │
│  │ - coverage_complete    │          │                      │
│  │ - confidence           │          │                      │
│  │ - suggestions          │          │                      │
│  └─────────┬──────────────┘          │                      │
│            │                          │                      │
│            └──────────┬───────────────┘                      │
│                       ↓                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Add judge_validation to response
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  Return to Client                            │
│  {                                                           │
│    "redacted_data": "card *********3333",                   │
│    "redactions_applied": 1,                                 │
│    "judge_validation": {         ← Only if sampled         │
│      "coverage_complete": true,                             │
│      "confidence": 95.5                                     │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 2. Sampling Decision Flow

```
Request arrives
      │
      ↓
┌──────────────────┐
│ is enabled?      │───NO──→ Skip LLM Judge
└────────┬─────────┘
         │ YES
         ↓
┌──────────────────┐
│ calls_this_hour  │───≥100──→ Skip (budget limit)
│ < 100 ?          │
└────────┬─────────┘
         │ YES
         ↓
┌──────────────────┐
│ calls_this_day   │───≥1000─→ Skip (budget limit)
│ < 1000 ?         │
└────────┬─────────┘
         │ YES
         ↓
┌──────────────────┐
│ random() < 0.15? │───NO──→ Skip (not in 15%)
└────────┬─────────┘
         │ YES
         ↓
    SAMPLE IT!
```

## 3. Context Preparation

```
Original Data                          Context Sent to LLM
─────────────                          ───────────────────
{                                      {
  "customer": {                          "original_snippet": {
    "name": "John Doe",         →          "customer": {
    "email": "john@example.com",  →          "name": "J***",      ← Partially masked
    "card": "4532111122223333"    →          "email": "j***@***", ← Partially masked
  },                                         "card": "45***3333"  ← Partially masked
  "amount": 99.99,                →        },
  "timestamp": "2025-11-09"       →        "amount": 99.99,
}                                          "timestamp": "..."
                                         },
Redacted Output                          
───────────────                          "redacted_data": {
{                                          "customer": {
  "customer": {                              "name": "[REDACTED]",
    "name": "[REDACTED]",       →            "email": "[REDACTED]",
    "email": "[REDACTED]",      →            "card": "[REDACTED]"
    "card": "[REDACTED]"        →          },
  },                                         "amount": 99.99,
  "amount": 99.99,              →          "timestamp": "2025-11-09"
  "timestamp": "2025-11-09"     →        },
}                                        
                                         "redactions_applied": [
Metadata                                   {"field": "customer.name", ...},
────────                        →          {"field": "customer.email", ...},
- field: customer.name          →          {"field": "customer.card", ...}
- field: customer.email         →        ],
- field: customer.card          →        
                                         "redaction_count": 3
                                       }

        Max 500 chars total ───────────────────┘
```

## 4. LLM Validation Process

```
┌─────────────────────────────────────────────────────────┐
│              LLM (GPT-4o-mini / Claude)                 │
│                                                          │
│  Prompt:                                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │ You are a PII/PCI redaction validator.             │ │
│  │                                                     │ │
│  │ Original (snippet): {...}                          │ │
│  │ Redacted: {...}                                    │ │
│  │ Rules applied: [...]                               │ │
│  │                                                     │ │
│  │ Assess:                                            │ │
│  │ 1. Coverage - All PII redacted?                    │ │
│  │ 2. Over-redaction - Non-PII redacted?              │ │
│  │ 3. Under-redaction - Any PII missed?               │ │
│  │                                                     │ │
│  │ Respond with JSON only:                            │ │
│  │ {                                                  │ │
│  │   "coverage_complete": true/false,                 │ │
│  │   "over_redacted": false,                          │ │
│  │   "under_redacted": false,                         │ │
│  │   "confidence": 95,                                │ │
│  │   "suggestions": [...]                             │ │
│  │ }                                                  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Response (~200-500ms):                                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │ {                                                  │ │
│  │   "coverage_complete": true,                       │ │
│  │   "over_redacted": false,                          │ │
│  │   "under_redacted": false,                         │ │
│  │   "confidence": 95.5,                              │ │
│  │   "suggestions": ["All PII properly masked"]       │ │
│  │ }                                                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 5. Error Handling & Fallback

```
LLM Call Initiated
       │
       ↓
┌──────────────────┐
│ Try LLM API call │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ Success │───────────→ Parse response → Return result
    └─────────┘
         │
    ┌────┴────┐
    │ Timeout │ (>5s)
    │  Error  │
    │ Parse   │
    └────┬────┘
         │
         ↓
┌──────────────────┐
│ fallback_on_     │───YES──→ Log warning
│ error = true?    │          Return None
└────────┬─────────┘          Continue with rules-only
         │ NO
         ↓
    Raise JudgeError
    (if configured)
```

## 6. Budget Tracking

```
Time: 10:00 AM                 Time: 11:00 AM
─────────────                  ──────────────
calls_this_hour = 0            calls_this_hour = 0  ← Reset!
calls_this_day = 0             calls_this_day = 45  ← Persists
last_reset_hour = 10           last_reset_hour = 11

      ↓                               ↓
  Request 1                       Request 46
  calls_this_hour++               calls_this_hour++
  = 1                             = 1  (after reset)

      ↓                               ↓
  Request 45                      Request 100
  calls_this_hour++               calls_this_hour++
  = 45                            = 55

      ↓                               ↓
  UNDER LIMIT                     UNDER LIMIT
  Allow LLM call                  Allow LLM call


Time: 10:00 AM (100th call this hour)
──────────────────────────────────────
calls_this_hour = 100  ← At limit!
calls_this_day = 145

      ↓
  Request 101
  Check: calls_this_hour >= 100?  → YES
      ↓
  OVER LIMIT
  Skip LLM call
  Log warning
```

## 7. Real-World Example

**Scenario:** Credit card transaction redaction

```
INPUT:
─────
POST /redact
{
  "data": "Customer Jane Smith (jane.smith@email.com) purchased 
           item with card 5425233430109903 for $149.99",
  "method": "mask"
}

STEP 1: Redaction Engine
────────────────────────
Detects:
- Person name: "Jane Smith"
- Email: "jane.smith@email.com"  
- Credit card: "5425233430109903" (Luhn valid)
- Amount: "$149.99" (NOT PII)

Redacts:
"Customer [REDACTED] ([REDACTED]) purchased item with 
 card *********9903 for $149.99"

STEP 2: LLM Judge Sampling
───────────────────────────
random() = 0.12 < 0.15 → SAMPLE!
calls_this_hour = 23 < 100 → OK
calls_this_day = 456 < 1000 → OK

STEP 3: Prepare Context
───────────────────────
{
  "original_snippet": "Customer J*** S*** (j***@***.com) ... 
                      card 54***9903 for $149.99",
  "redacted_data": "Customer [REDACTED] ([REDACTED]) ... 
                    card *********9903 for $149.99",
  "redactions_applied": [
    {"field": "person_name", "rule": "ner_person", "action": "mask"},
    {"field": "email", "rule": "email_pattern", "action": "mask"},
    {"field": "credit_card", "rule": "luhn_card", "action": "mask"}
  ],
  "redaction_count": 3
}

STEP 4: LLM Validation (234ms)
───────────────────────────────
GPT-4o-mini analyzes and returns:
{
  "coverage_complete": true,     ← All PII found and redacted
  "over_redacted": false,        ← Amount NOT redacted (correct)
  "under_redacted": false,       ← No PII missed
  "confidence": 98.5,            ← Very confident
  "suggestions": []              ← No improvements needed
}

STEP 5: Response
────────────────
{
  "redacted_data": "Customer [REDACTED] ([REDACTED]) purchased 
                    item with card *********9903 for $149.99",
  "redactions_applied": 3,
  "method": "mask",
  "processing_time_ms": 28,
  "judge_validation": {           ← Added because sampled
    "coverage_complete": true,
    "over_redacted": false,
    "under_redacted": false,
    "confidence": 98.5,
    "processing_time_ms": 234,
    "sampled": true
  }
}

Total time: 28ms (redaction) + 234ms (LLM) = 262ms
```

## 8. Cost Breakdown

```
Assumptions:
- 10,000 requests/day
- 15% sampling rate
- 100 calls/hour limit (enforced)
- gpt-4o-mini pricing

Daily Traffic:
──────────────
Total requests: 10,000
Should sample (15%): 1,500
Actually sampled (budget): 1,000  ← Limited by max_calls_per_day

Per Request:
───────────
Input tokens: ~400 (context)
Output tokens: ~50 (JSON response)
Cost per call: $0.001-0.002

Daily Cost:
──────────
1,000 calls × $0.0015 avg = $1.50/day

Monthly Cost:
────────────
$1.50 × 30 days = $45/month

Annual Cost:
───────────
$45 × 12 = $540/year

ROI:
───
- Catches under-redaction before data leaks
- Validates rule changes automatically
- Quality assurance at 0.015¢ per request
```

## Summary

The LLM Judge provides **intelligent validation** with:

✅ **15% sampling** - Enough for quality assurance
✅ **Budget controls** - Prevents runaway costs  
✅ **Async processing** - Doesn't block requests
✅ **Privacy-safe** - Only snippets sent to LLM
✅ **Error resilient** - Fallback to rules-only
✅ **Cost-effective** - ~$1-2/day typical usage

**Status:** Fully implemented and tested! 🚀
