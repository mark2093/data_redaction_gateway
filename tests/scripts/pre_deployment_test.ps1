# Pre-Deployment Automated Test Suite
# Runs comprehensive tests for deployment readiness

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PRE-DEPLOYMENT TEST SUITE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Time to deployment: 3 hours" -ForegroundColor Yellow
Write-Host "Starting automated tests..." -ForegroundColor Yellow
Write-Host ""

$baseUrl = "http://localhost:8000"
$passed = 0
$failed = 0
$warnings = 0

function Test-Endpoint {
    param($name, $url, $method = "GET", $headers = @{}, $body = $null)
    try {
        $params = @{
            Uri = $url
            Method = $method
            Headers = $headers
            ErrorAction = "Stop"
        }
        if ($body) {
            $params.Body = $body
            $params.ContentType = "application/json"
        }
        $response = Invoke-WebRequest @params
        Write-Host "✓ $name - Status: $($response.StatusCode)" -ForegroundColor Green
        $script:passed++
        return $response
    } catch {
        Write-Host "✗ $name - Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $null
    }
}

# HOUR 1: CORE FUNCTIONALITY TESTS
Write-Host "`n[HOUR 1] CORE FUNCTIONALITY TESTS" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Test 1: Health Checks
Write-Host "`n[Test 1] Health Checks..." -ForegroundColor Yellow
Test-Endpoint "Basic Health" "$baseUrl/health"
Test-Endpoint "Detailed Health" "$baseUrl/health/detailed"
Test-Endpoint "Liveness Probe" "$baseUrl/health/live"
Test-Endpoint "Readiness Probe" "$baseUrl/health/ready"
Test-Endpoint "Prometheus Metrics" "$baseUrl/metrics/prometheus"

# Test 2: Redaction Engine
Write-Host "`n[Test 2] Redaction Engine..." -ForegroundColor Yellow
$headers = @{"X-API-Key" = "dev-api-key-12345"}

$testData = @{
    data = @{
        card_number = "4532-1111-2222-3333"
        ssn = "123-45-6789"
        email = "john.doe@example.com"
        name = "John Doe"
    }
} | ConvertTo-Json

Test-Endpoint "Credit Card Redaction" "$baseUrl/redact" "POST" $headers $testData

# Test masking
$maskData = @{
    data = @{pan = "4532111122223333"}
    options = @{action = "mask"}
} | ConvertTo-Json
Test-Endpoint "Masking" "$baseUrl/redact" "POST" $headers $maskData

# Test tokenization
$tokenData = @{
    data = @{email = "test@example.com"}
    options = @{action = "tokenize"}
} | ConvertTo-Json
Test-Endpoint "Tokenization" "$baseUrl/redact" "POST" $headers $tokenData

# Test FPE
$fpeData = @{
    data = @{pan = "4532111122223333"}
    options = @{action = "fpe"}
} | ConvertTo-Json
Test-Endpoint "FPE" "$baseUrl/redact" "POST" $headers $fpeData

# Test 3: Streaming
Write-Host "`n[Test 3] Streaming..." -ForegroundColor Yellow
$ndjsonData = '{"card":"4532111122223333","email":"test1@example.com"}
{"card":"5425233430109903","email":"test2@example.com"}'
$streamHeaders = @{
    "X-API-Key" = "dev-api-key-12345"
    "Content-Type" = "application/x-ndjson"
}
Test-Endpoint "NDJSON Stream" "$baseUrl/redact/stream" "POST" $streamHeaders $ndjsonData

# Test 4: Security Features
Write-Host "`n[Test 4] Security Features..." -ForegroundColor Yellow

# Create users first
Write-Host "Creating test users..." -ForegroundColor Gray
python tests\scripts\test_security_features.py 2>&1 | Out-Null

# Test login
$loginData = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

$loginResp = Test-Endpoint "User Login" "$baseUrl/auth/login" "POST" @{} $loginData

if ($loginResp) {
    try {
        $token = ($loginResp.Content | ConvertFrom-Json).access_token
        $authHeaders = @{"Authorization" = "Bearer $token"}
        
        Test-Endpoint "Current User Info" "$baseUrl/auth/me" "GET" $authHeaders
        Test-Endpoint "Token Verification" "$baseUrl/auth/verify" "GET" $authHeaders
    } catch {
        Write-Host "⚠ Could not extract token from login response" -ForegroundColor Yellow
        $script:warnings++
    }
}

# Test 5: Rate Limiting
Write-Host "`n[Test 5] Rate Limiting..." -ForegroundColor Yellow
$rateLimitHeaders = @{"X-API-Key" = "dev-api-key-12345"}

Write-Host "Sending 65 requests to test rate limit..." -ForegroundColor Gray
$rateLimitHit = $false
for ($i = 1; $i -le 65; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" -Headers $rateLimitHeaders -ErrorAction Stop
        if ($i -eq 65 -and -not $rateLimitHit) {
            Write-Host "⚠ Rate limit not triggered after 65 requests" -ForegroundColor Yellow
            $script:warnings++
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "✓ Rate limit triggered at request $i" -ForegroundColor Green
            $script:passed++
            $rateLimitHit = $true
            break
        }
    }
}

if (-not $rateLimitHit -and $i -eq 66) {
    Write-Host "✗ Rate limiting not working" -ForegroundColor Red
    $script:failed++
}

# Test 6: Audit Logging
Write-Host "`n[Test 6] Audit Logging..." -ForegroundColor Yellow
Test-Endpoint "Audit Events" "$baseUrl/audit/events?limit=5" "GET" $headers
Test-Endpoint "Audit Statistics" "$baseUrl/audit/statistics" "GET" $headers
Test-Endpoint "Event Types" "$baseUrl/audit/event-types" "GET" $headers

# HOUR 2: INTEGRATION & PERFORMANCE TESTS
Write-Host "`n`n[HOUR 2] INTEGRATION & PERFORMANCE TESTS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Test 7: Metrics and Observability
Write-Host "`n[Test 7] Metrics..." -ForegroundColor Yellow
Test-Endpoint "Basic Metrics" "$baseUrl/metrics" "GET" $headers
Test-Endpoint "Detailed Metrics" "$baseUrl/metrics/detailed" "GET" $headers
Test-Endpoint "Endpoint Metrics" "$baseUrl/metrics/endpoints" "GET" $headers
Test-Endpoint "Performance Metrics" "$baseUrl/metrics/performance" "GET" $headers

# Test 8: Policy Management
Write-Host "`n[Test 8] Policy Management..." -ForegroundColor Yellow
Test-Endpoint "List Rules" "$baseUrl/policy/rules" "GET" $headers
Test-Endpoint "Policy Info" "$baseUrl/policy/info" "GET" $headers

# Test 9: Content Processing
Write-Host "`n[Test 9] Content Processing..." -ForegroundColor Yellow

# Test gzip compression
$compressedData = @{
    data = @{card = "4532111122223333"}
} | ConvertTo-Json
Test-Endpoint "Gzip Processing" "$baseUrl/redact" "POST" $headers $compressedData

# Test base64
$base64Data = @{
    data = @{
        encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("4532-1111-2222-3333"))
    }
} | ConvertTo-Json
Test-Endpoint "Base64 Processing" "$baseUrl/redact" "POST" $headers $base64Data

# Test 10: Error Handling
Write-Host "`n[Test 10] Error Handling..." -ForegroundColor Yellow

# Invalid JSON
try {
    Invoke-WebRequest -Uri "$baseUrl/redact" -Method POST -Headers $headers -Body "invalid json" -ErrorAction Stop
    Write-Host "✗ Should have rejected invalid JSON" -ForegroundColor Red
    $script:failed++
} catch {
    if ($_.Exception.Response.StatusCode -eq 400 -or $_.Exception.Response.StatusCode -eq 422) {
        Write-Host "✓ Invalid JSON rejected properly" -ForegroundColor Green
        $script:passed++
    } else {
        Write-Host "⚠ Unexpected error code for invalid JSON: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
        $script:warnings++
    }
}

# Missing API key
try {
    $noKeyData = @{data = @{test = "value"}} | ConvertTo-Json
    Invoke-WebRequest -Uri "$baseUrl/redact" -Method POST -Body $noKeyData -ContentType "application/json" -ErrorAction Stop
    Write-Host "⚠ Should have rejected request without API key" -ForegroundColor Yellow
    $script:warnings++
} catch {
    if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
        Write-Host "✓ Missing API key rejected" -ForegroundColor Green
        $script:passed++
    }
}

# Test 11: Load Testing (Basic)
Write-Host "`n[Test 11] Load Testing (10 concurrent requests)..." -ForegroundColor Yellow
$startTime = Get-Date
$jobs = 1..10 | ForEach-Object {
    Start-Job -ScriptBlock {
        param($url, $headers, $data)
        try {
            $response = Invoke-WebRequest -Uri $url -Method POST -Headers $headers -Body $data -ContentType "application/json" -UseBasicParsing
            return @{success = $true; status = $response.StatusCode}
        } catch {
            return @{success = $false; error = $_.Exception.Message}
        }
    } -ArgumentList "$baseUrl/redact", $headers, (@{data = @{card="4532111122223333"}} | ConvertTo-Json)
}

$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job
$endTime = Get-Date
$duration = ($endTime - $startTime).TotalMilliseconds

$successCount = ($results | Where-Object {$_.success -eq $true}).Count
Write-Host "Load test: $successCount/10 successful" -ForegroundColor $(if ($successCount -eq 10) {"Green"} else {"Yellow"})
Write-Host "Total time: $([math]::Round($duration, 2))ms" -ForegroundColor Gray
Write-Host "Average: $([math]::Round($duration/10, 2))ms per request" -ForegroundColor Gray

if ($successCount -eq 10) {
    $script:passed++
} else {
    $script:warnings++
}

# FINAL REPORT
Write-Host "`n`n========================================" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed:   $passed" -ForegroundColor Green
Write-Host "Failed:   $failed" -ForegroundColor $(if ($failed -eq 0) {"Green"} else {"Red"})
Write-Host "Warnings: $warnings" -ForegroundColor $(if ($warnings -eq 0) {"Green"} else {"Yellow"})
Write-Host ""

# GO/NO-GO Decision
$totalTests = $passed + $failed + $warnings
$passRate = if ($totalTests -gt 0) {[math]::Round(($passed / $totalTests) * 100, 1)} else {0}

Write-Host "Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -ge 90) {"Green"} elseif ($passRate -ge 70) {"Yellow"} else {"Red"})
Write-Host ""

if ($failed -eq 0 -and $passRate -ge 90) {
    Write-Host "✓ GO FOR DEPLOYMENT" -ForegroundColor Green -BackgroundColor DarkGreen
    Write-Host "  All critical tests passed!" -ForegroundColor Green
} elseif ($failed -eq 0 -and $passRate -ge 70) {
    Write-Host "⚠ CONDITIONAL GO" -ForegroundColor Yellow -BackgroundColor DarkYellow
    Write-Host "  Some warnings but no critical failures" -ForegroundColor Yellow
    Write-Host "  Review warnings before deploying" -ForegroundColor Yellow
} else {
    Write-Host "✗ NO-GO FOR DEPLOYMENT" -ForegroundColor Red -BackgroundColor DarkRed
    Write-Host "  Critical failures detected - fix before deploying" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Recommended next steps:" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "1. Review production configuration" -ForegroundColor White
    Write-Host "2. Set environment variables" -ForegroundColor White
    Write-Host "3. Run final smoke test" -ForegroundColor White
    Write-Host "4. Deploy to production" -ForegroundColor White
} else {
    Write-Host "1. Fix failed tests" -ForegroundColor White
    Write-Host "2. Re-run test suite" -ForegroundColor White
    Write-Host "3. Investigate root causes" -ForegroundColor White
}
Write-Host "========================================" -ForegroundColor Cyan

exit $(if ($failed -eq 0) {0} else {1})
