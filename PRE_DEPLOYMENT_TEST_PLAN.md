# Pre-Deployment Test Plan - 3 Hour Timeline

## Timeline Breakdown

**Total Time**: 3 hours to deployment

### Hour 1: Core Functionality Testing (60 min)
- ✅ 0-15 min: Start server and verify all endpoints
- ✅ 15-30 min: Test redaction engine (all methods)
- ✅ 30-45 min: Test proxy mode and streaming
- ✅ 45-60 min: Test security features (JWT, RBAC, rate limiting)

### Hour 2: Integration & Performance Testing (60 min)
- ✅ 60-75 min: End-to-end workflow tests
- ✅ 75-90 min: Load testing (concurrent requests)
- ✅ 90-105 min: Error handling and edge cases
- ✅ 105-120 min: LLM judge and FPE validation

### Hour 3: Deployment Preparation (60 min)
- ✅ 120-135 min: Fix critical issues from testing
- ✅ 135-150 min: Production config review
- ✅ 150-165 min: Documentation and deployment checklist
- ✅ 165-180 min: Final smoke test and GO/NO-GO decision

---

## HOUR 1: Core Functionality Testing

### Test 1: Server Startup (5 min)
```powershell
# Start server
python main_modular.py

# Expected: Server starts on port 8000
# Expected: No errors in logs
# Expected: All routers loaded
```

**Checklist**:
- [ ] Server starts without errors
- [ ] All routers loaded (redaction, health, metrics, policy, streaming, auth, audit, rate-limit)
- [ ] Configuration loaded correctly
- [ ] Policy rules loaded

### Test 2: Health Checks (5 min)
```powershell
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Kubernetes probes
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Prometheus metrics
curl http://localhost:8000/metrics/prometheus
```

**Checklist**:
- [ ] All health endpoints return 200
- [ ] Detailed health shows all components healthy
- [ ] Prometheus format is valid
- [ ] Readiness check passes

### Test 3: Redaction Engine (15 min)
```powershell
# Test credit card masking
$body = @{
    data = @{
        card = "4532-1111-2222-3333"
        name = "John Doe"
        ssn = "123-45-6789"
    }
} | ConvertTo-Json

curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d $body

# Test FPE
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{"data":{"pan":"4532111122223333"},"options":{"action":"fpe"}}'

# Test tokenization
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{"data":{"email":"test@example.com"},"options":{"action":"tokenize"}}'
```

**Checklist**:
- [ ] Credit cards masked correctly (shows last 4)
- [ ] SSN redacted
- [ ] Names detected and redacted
- [ ] FPE maintains format
- [ ] Tokenization is deterministic
- [ ] Metadata included in response

### Test 4: Proxy Mode (10 min)
```powershell
# Test proxy routing (if configured)
curl http://localhost:8000/api/v1/test `
    -H "X-API-Key: dev-api-key-12345"

# Should route to upstream and redact response
```

**Checklist**:
- [ ] Proxy routes to upstream service
- [ ] Response is redacted
- [ ] Headers preserved
- [ ] Latency acceptable (<100ms overhead)

### Test 5: Streaming (10 min)
```powershell
# Test NDJSON streaming
$ndjson = @"
{"card":"4532111122223333","email":"test1@example.com"}
{"card":"5425233430109903","email":"test2@example.com"}
{"card":"2221000010000015","email":"test3@example.com"}
"@

curl -X POST http://localhost:8000/redact/stream `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/x-ndjson" `
    -d $ndjson
```

**Checklist**:
- [ ] Streams processed line-by-line
- [ ] All records redacted
- [ ] Response is valid NDJSON
- [ ] No errors in logs

### Test 6: Security Features (15 min)
```powershell
# Test authentication
curl -X POST http://localhost:8000/auth/login `
    -H "Content-Type: application/json" `
    -d '{"username":"admin","password":"admin123"}'

# Test protected endpoint
$token = "eyJhbGc..." # from login
curl http://localhost:8000/auth/me `
    -H "Authorization: Bearer $token"

# Test rate limiting
for ($i=1; $i -le 70; $i++) {
    curl http://localhost:8000/health `
        -H "X-API-Key: dev-api-key-12345"
}
# Should get 429 after ~60 requests
```

**Checklist**:
- [ ] Login successful with valid credentials
- [ ] Login fails with invalid credentials
- [ ] JWT token works for protected endpoints
- [ ] Rate limiting triggers at 60 req/min
- [ ] Audit logs captured

---

## HOUR 2: Integration & Performance Testing

### Test 7: End-to-End Workflow (15 min)
```powershell
# 1. Login
$loginResp = curl -X POST http://localhost:8000/auth/login `
    -H "Content-Type: application/json" `
    -d '{"username":"user1","password":"user123"}'

$token = ($loginResp | ConvertFrom-Json).access_token

# 2. Check policies
curl http://localhost:8000/policy/rules `
    -H "Authorization: Bearer $token"

# 3. Redact data
curl -X POST http://localhost:8000/redact `
    -H "Authorization: Bearer $token" `
    -H "Content-Type: application/json" `
    -d '{"data":{"card":"4532111122223333","ssn":"123-45-6789"}}'

# 4. Check metrics
curl http://localhost:8000/metrics/detailed `
    -H "Authorization: Bearer $token"

# 5. Check audit logs
curl "http://localhost:8000/audit/events?limit=5" `
    -H "Authorization: Bearer $token"
```

**Checklist**:
- [ ] Complete workflow works end-to-end
- [ ] All APIs accessible with JWT
- [ ] Metrics captured correctly
- [ ] Audit logs show all events

### Test 8: Load Testing (15 min)
```powershell
# Run concurrent requests
$jobs = 1..50 | ForEach-Object {
    Start-Job -ScriptBlock {
        curl -X POST http://localhost:8000/redact `
            -H "X-API-Key: dev-api-key-12345" `
            -H "Content-Type: application/json" `
            -d '{"data":{"card":"4532111122223333"}}'
    }
}

$jobs | Wait-Job | Receive-Job
```

**Checklist**:
- [ ] Server handles 50 concurrent requests
- [ ] No errors or timeouts
- [ ] P95 latency < 200ms
- [ ] No memory leaks
- [ ] Rate limiting works under load

### Test 9: Error Handling (15 min)
```powershell
# Invalid JSON
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{invalid json}'

# Missing API key
curl -X POST http://localhost:8000/redact `
    -H "Content-Type: application/json" `
    -d '{"data":{}}'

# Invalid token
curl http://localhost:8000/auth/me `
    -H "Authorization: Bearer invalid-token"

# Large payload
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{"data":{"field":"'$("x" * 1000000)'"}}'
```

**Checklist**:
- [ ] Returns proper error codes (400, 401, 403, 413)
- [ ] Error messages are helpful
- [ ] No sensitive data in error responses
- [ ] Server remains stable after errors

### Test 10: LLM Judge & FPE (15 min)
```powershell
# Test LLM judge (if API key configured)
$env:LLM_API_KEY = "sk-..."
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{"data":{"card":"4532111122223333","note":"my card is 4532-1111-2222-3333"}}'

# Test FPE encryption/decryption
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: dev-api-key-12345" `
    -H "Content-Type: application/json" `
    -d '{"data":{"pan":"4532111122223333"},"options":{"action":"fpe"}}'
```

**Checklist**:
- [ ] LLM judge triggers for sampled requests
- [ ] Fallback works if LLM unavailable
- [ ] FPE maintains card format
- [ ] FPE values are consistent
- [ ] Metrics track judge calls

---

## HOUR 3: Deployment Preparation

### Critical Issues Resolution (15 min)
- [ ] Fix any critical bugs found in testing
- [ ] Address performance issues
- [ ] Resolve security concerns

### Production Config Review (15 min)
```yaml
# config/config.yaml checklist
- [ ] API keys changed from defaults
- [ ] JWT secret key set via env var
- [ ] HMAC secret changed
- [ ] Encryption key changed
- [ ] TLS enabled (if required)
- [ ] Rate limits appropriate
- [ ] Audit logging enabled
- [ ] Log sanitization enabled
```

### Environment Variables (5 min)
```powershell
# Required for production
$env:JWT_SECRET_KEY = "..."
$env:HMAC_SECRET_KEY = "..."
$env:ENCRYPTION_KEY = "..."
$env:LLM_API_KEY = "..."  # Optional
$env:ENVIRONMENT = "production"
```

### Documentation Review (10 min)
- [ ] README.md up to date
- [ ] START_HERE.md has quick start
- [ ] API documentation complete
- [ ] Security guide reviewed
- [ ] Deployment checklist ready

### Final Smoke Test (10 min)
```powershell
# Complete smoke test
.\tests\scripts\quick_tests.ps1

# Or manual:
curl http://localhost:8000/health/ready
curl -X POST http://localhost:8000/redact `
    -H "X-API-Key: PROD-KEY" `
    -d '{"data":{"card":"4532111122223333"}}'
```

### Deployment Checklist (5 min)
- [ ] All tests passed
- [ ] Production config validated
- [ ] Environment variables set
- [ ] Secrets secured
- [ ] Documentation complete
- [ ] Monitoring configured
- [ ] Rollback plan ready

---

## GO/NO-GO Decision Criteria

### GO if:
✅ All core endpoints functional  
✅ Redaction working correctly  
✅ Security features operational  
✅ No critical bugs  
✅ Performance acceptable (<100ms overhead)  
✅ Error handling robust  
✅ Configuration validated  

### NO-GO if:
❌ Critical functionality broken  
❌ Security vulnerabilities found  
❌ Performance issues (>500ms latency)  
❌ Data leakage detected  
❌ Rate limiting not working  
❌ Audit logging failing  

---

## Next Steps After Testing

1. **If GO**: 
   - Deploy to staging/production
   - Monitor logs and metrics
   - Be ready for hotfixes

2. **If NO-GO**:
   - Document blocking issues
   - Estimate fix time
   - Reschedule deployment

---

## Quick Test Script

Run all tests:
```powershell
.\tests\scripts\pre_deployment_test.ps1
```

(Script to be created below)
