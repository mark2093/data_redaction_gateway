# TODO List - Runtime PII/PCI Data Redaction Gateway
## Gap Analysis & Missing Implementations

**Status:** Post-Implementation Review  
**Date:** November 9, 2025

---

## 📋 Requirements Analysis vs Current Implementation

Based on the Complete_problem.txt requirements, here's what's missing or needs attention:

---

## 🔴 HIGH PRIORITY - Missing Core Features

### 1. **API Gateway Proxy Functionality** 
**Status:** ❌ NOT IMPLEMENTED  
**Current:** We have a redaction service, but NOT a proxy gateway  
**Required:** "act as an intermediary for API requests, inspecting and transforming request/response bodies"

**TODO:**
- [ ] **Create proxy middleware** to intercept requests to downstream services
- [ ] **Add upstream service routing** configuration
- [ ] **Implement request/response transformation** in-flight
- [ ] **Add route-based policy mapping** (per route/method redaction rules)
- [ ] **Test proxy mode** with real downstream services

### 2. **Stream Processing for Real-time Data**
**Status:** ⚠️ PARTIALLY IMPLEMENTED  
**Current:** We process single requests/batches  
**Required:** "processes data streams in real-time"

**TODO:**
- [ ] **Add NDJSON stream processing** for line-delimited JSON
- [ ] **Implement async stream handlers** for continuous data flow
- [ ] **Add WebSocket support** for real-time streaming
- [ ] **Create streaming endpoint** (/redact/stream)
- [ ] **Test with large data streams** (>1MB payloads)

### 3. **Data Decompression/Decoding**
**Status:** ❌ NOT IMPLEMENTED  
**Required:** "Handle optional base64 decoding and gzip/deflate decompression"

**TODO:**
- [ ] **Add base64 decode** detection and processing
- [ ] **Add gzip/deflate decompression** middleware
- [ ] **Add content-encoding headers** support
- [ ] **Test with compressed payloads**
- [ ] **Handle binary data streams**

### 4. **LLM-as-Judge Sampling**
**Status:** ✅ IMPLEMENTED but needs testing  
**Current:** LLM judge exists but sampling rate may not be working  
**Required:** "10-20% of requests (sampled randomly)"

**TODO:**
- [ ] **Verify sampling mechanism** is working correctly
- [ ] **Test LLM judge integration** end-to-end
- [ ] **Validate budget controls** and fallback behavior
- [ ] **Test timeout handling** and graceful degradation
- [ ] **Ensure secure prompts** don't expose raw PII

---

## 🟡 MEDIUM PRIORITY - Enhancements Needed

### 5. **Format-Preserving Encryption (FPE)**
**Status:** ⚠️ PLACEHOLDER ONLY  
**Current:** Returns masked value  
**Required:** "Format-Preserving Encryption (FPE) specifically for PANs"

**TODO:**
- [ ] **Research FPE libraries** (pyffx, ff3-python)
- [ ] **Implement FPE for PANs** maintaining card number format
- [ ] **Add FPE key management** and rotation
- [ ] **Test FPE reversibility** for authorized systems
- [ ] **Add FPE configuration** to policy rules

### 6. **Enhanced Policy Features**
**Status:** ⚠️ BASIC IMPLEMENTATION  
**Current:** Simple YAML rules  
**Required:** "Rules per route, method, tenant, region"

**TODO:**
- [ ] **Add route-specific rules** (/api/v1/* vs /api/v2/*)
- [ ] **Add HTTP method-based rules** (GET vs POST policies)
- [ ] **Add tenant/region support** for multi-tenant deployment
- [ ] **Implement effective dates** for time-based policy activation
- [ ] **Add rule inheritance** and override mechanisms

### 7. **HTTP Headers for Downstream**
**Status:** ❌ NOT IMPLEMENTED  
**Required:** "Emit HTTP headers downstream: X-Redaction-Policy and X-Policy-Version"

**TODO:**
- [ ] **Add response headers** to all redacted responses
- [ ] **Include policy version** in headers
- [ ] **Add redaction summary** headers (fields affected count)
- [ ] **Test header propagation** in proxy mode
- [ ] **Document header format** for downstream consumers

### 8. **TLS/mTLS Support**
**Status:** ⚠️ CONFIGURATION READY  
**Current:** Config exists but not tested  
**Required:** "Support TLS termination" and "optional mutual TLS"

**TODO:**
- [ ] **Test TLS configuration** with certificates
- [ ] **Implement mTLS client verification**
- [ ] **Add certificate management** documentation
- [ ] **Test secure communication** end-to-end
- [ ] **Add certificate rotation** procedures

---

## 🟢 LOW PRIORITY - Nice-to-Have Improvements

### 9. **Advanced Caching Strategies**
**Status:** ⚠️ BASIC TTL CACHE  
**Current:** Simple TTL cache  
**Required:** "Never cache raw sensitive values—only decisions"

**TODO:**
- [ ] **Audit cache safety** - ensure no PII cached
- [ ] **Add distributed caching** support (Redis)
- [ ] **Implement cache warming** strategies
- [ ] **Add cache metrics** and monitoring
- [ ] **Test cache performance** under load

### 10. **Enhanced Observability**
**Status:** ⚠️ BASIC METRICS  
**Current:** Basic metrics collection  
**Required:** "minimal OpenTelemetry spans for key stages"

**TODO:**
- [ ] **Add detailed OpenTelemetry spans** for each stage
- [ ] **Implement Prometheus metrics** export
- [ ] **Add structured logging** with correlation IDs
- [ ] **Create observability dashboards** (Grafana)
- [ ] **Add alerting rules** for high failure rates

### 11. **CLI Tool Enhancement**
**Status:** ✅ GOOD but could be better  
**Current:** Basic CLI with dry-run  
**Required:** "Include sample payloads and a Postman collection"

**TODO:**
- [ ] **Create Postman collection** for API testing
- [ ] **Add more sample payloads** for different scenarios
- [ ] **Add CLI replay command** for historical data
- [ ] **Add CLI load testing** command
- [ ] **Create CLI configuration wizard**

---

## 🔧 TECHNICAL DEBT & CODE QUALITY

### 12. **Error Handling & Resilience**
**TODO:**
- [ ] **Add circuit breaker** for LLM judge calls
- [ ] **Implement retry policies** for transient failures
- [ ] **Add input validation** for large payloads
- [ ] **Handle malformed data** gracefully
- [ ] **Add rate limiting** per API key

### 13. **Security Hardening**
**TODO:**
- [ ] **Add input sanitization** to prevent injection attacks
- [ ] **Implement API key rotation** mechanism
- [ ] **Add request signing** for integrity verification
- [ ] **Audit log access patterns** and suspicious activity
- [ ] **Add CORS configuration** for web clients

### 14. **Performance Optimization**
**TODO:**
- [ ] **Profile memory usage** under load
- [ ] **Optimize regex compilation** and caching
- [ ] **Add connection pooling** for downstream services
- [ ] **Implement request batching** for efficiency
- [ ] **Add async queue processing** for heavy workloads

### 15. **Testing & Validation**
**TODO:**
- [ ] **Add integration tests** for all endpoints
- [ ] **Create load testing suite** with realistic data
- [ ] **Add security testing** (penetration testing)
- [ ] **Test with production-scale data** volumes
- [ ] **Add compliance validation** tests (GDPR/PCI)

---

## 📊 PRIORITY MATRIX

### 🔴 Start Immediately (Core Missing Features)
1. **API Gateway Proxy Mode** - Core requirement missing
2. **Stream Processing** - Real-time capability missing
3. **Data Decompression** - Required feature missing

### 🟡 Next Sprint (Important Enhancements)
4. **FPE Implementation** - Security enhancement
5. **Advanced Policy Rules** - Business logic
6. **HTTP Headers** - Integration requirement

### 🟢 Future Iterations (Nice-to-Have)
7. **Enhanced Observability** - Operations improvement
8. **CLI Enhancement** - Developer experience
9. **Performance Optimization** - Scale preparation

---

## 📋 IMMEDIATE ACTION ITEMS

### Week 1: Core Gateway Functionality
- [ ] **Design proxy architecture** - upstream routing config
- [ ] **Implement proxy middleware** - request/response interception  
- [ ] **Add stream processing** - NDJSON and WebSocket support
- [ ] **Add decompression** - gzip/base64 support

### Week 2: Security & Policy Enhancement  
- [ ] **Implement FPE** for PAN redaction
- [ ] **Add route-based policies** and tenant support
- [ ] **Test TLS/mTLS configuration**
- [ ] **Add response headers** for downstream services

### Week 3: Integration & Testing
- [ ] **Create Postman collection** 
- [ ] **Test proxy mode** with real services
- [ ] **Validate LLM judge sampling**
- [ ] **Load test streaming endpoints**

---

## 🎯 SUCCESS CRITERIA

### Proxy Gateway Mode
- ✅ Can intercept requests to downstream APIs
- ✅ Transforms request/response bodies in-flight  
- ✅ Routes based on configurable upstream services
- ✅ Maintains original API contracts

### Real-time Processing
- ✅ Handles NDJSON streams efficiently
- ✅ Processes compressed/encoded data  
- ✅ Maintains <100ms latency overhead
- ✅ Supports WebSocket connections

### Production Readiness
- ✅ TLS/mTLS configured and tested
- ✅ FPE working for credit card data
- ✅ Comprehensive observability
- ✅ Security hardening complete

---

**Next Action:** Start with API Gateway Proxy implementation as it's the core missing piece that transforms this from a "redaction service" to a true "gateway service" as required.

**Estimated Effort:** 2-3 weeks for complete implementation of all high-priority items.

**Risk:** The current implementation is excellent but missing the "gateway proxy" aspect which is fundamental to the problem statement.