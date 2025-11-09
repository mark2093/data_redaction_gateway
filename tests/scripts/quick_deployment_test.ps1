# Quick Pre-Deployment Test Script
# Tests critical functionality before deployment

$ErrorActionPreference = "Continue"
$baseUrl = "http://localhost:8000"

# Test counters
$script:passed = 0
$script:failed = 0
$script:warnings = 0

# Colors
function Write-Success($msg) { Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Warn($msg) { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Section($msg) { Write-Host "`n[$msg]" -ForegroundColor Cyan }

# Test helper
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
        
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            Write-Success "$name (Status: $($response.StatusCode))"
            $script:passed++
            return $true
        } else {
            Write-Warn "$name (Status: $($response.StatusCode))"
            $script:warnings++
            return $false
        }
    } catch {
        Write-Fail "$name - $($_.Exception.Message)"
        $script:failed++
        return $false
    }
}

# START TESTS
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PRE-DEPLOYMENT TEST SUITE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Health Checks
Write-Section "Test 1: Health Checks"
Test-Endpoint "Basic Health" "$baseUrl/health"
Test-Endpoint "API Health" "$baseUrl/api/health"
Test-Endpoint "Readiness" "$baseUrl/health/ready"
Test-Endpoint "Liveness" "$baseUrl/health/live"

# Test 2: Redaction Engine
Write-Section "Test 2: Redaction Engine"
$headers = @{"X-API-Key" = "dev-api-key-12345"}

$maskData = @{
    text = "My card is 4532111122223333 and email is test@example.com"
    method = "mask"
} | ConvertTo-Json

$tokenData = @{
    text = "My SSN is 123-45-6789"
    method = "tokenize"
} | ConvertTo-Json

$hashData = @{
    text = "Sensitive info: john.doe@company.com"
    method = "hash"
} | ConvertTo-Json

Test-Endpoint "Mask Method" "$baseUrl/redact" "POST" $headers $maskData
Test-Endpoint "Tokenize Method" "$baseUrl/redact" "POST" $headers $tokenData
Test-Endpoint "Hash Method" "$baseUrl/redact" "POST" $headers $hashData

# Test 3: Security
Write-Section "Test 3: Security Features"

# Create test user
Write-Host "Creating test user..." -ForegroundColor Gray
$createUserData = @{
    username = "testuser"
    password = "test123"
    roles = @("User")
} | ConvertTo-Json

try {
    Invoke-WebRequest -Uri "$baseUrl/auth/users" -Method POST -Headers $headers -Body $createUserData -ContentType "application/json" -ErrorAction SilentlyContinue | Out-Null
} catch {}

# Test login
$loginData = @{
    username = "testuser"
    password = "test123"
} | ConvertTo-Json

$loginSuccess = Test-Endpoint "JWT Login" "$baseUrl/auth/login" "POST" @{} $loginData

if ($loginSuccess) {
    try {
        $loginResponse = Invoke-WebRequest -Uri "$baseUrl/auth/login" -Method POST -Body $loginData -ContentType "application/json"
        $token = ($loginResponse.Content | ConvertFrom-Json).access_token
        $authHeaders = @{
            "Authorization" = "Bearer $token"
            "X-API-Key" = "dev-api-key-12345"
        }
        Test-Endpoint "Authenticated Request" "$baseUrl/auth/me" "GET" $authHeaders
    } catch {
        Write-Warn "Could not test authenticated request"
        $script:warnings++
    }
}

# Test 4: Audit Logging
Write-Section "Test 4: Audit Logging"
Test-Endpoint "Audit Events" "$baseUrl/audit/events?limit=5" "GET" $headers
Test-Endpoint "Audit Statistics" "$baseUrl/audit/statistics" "GET" $headers

# Test 5: Metrics
Write-Section "Test 5: Metrics"
Test-Endpoint "Basic Metrics" "$baseUrl/metrics" "GET" $headers
Test-Endpoint "Detailed Metrics" "$baseUrl/metrics/detailed" "GET" $headers

# Test 6: Policy Management
Write-Section "Test 6: Policy Management"
Test-Endpoint "List Policies" "$baseUrl/policies" "GET" $headers
Test-Endpoint "Active Policies" "$baseUrl/policies/active" "GET" $headers

# Test 7: Content Processing
Write-Section "Test 7: Content Processing"
$contentData = @{
    content = "Customer John called about card 4532111122223333"
} | ConvertTo-Json

Test-Endpoint "Process Content" "$baseUrl/process" "POST" $headers $contentData

# Test 8: Error Handling
Write-Section "Test 8: Error Handling"
$invalidData = @{
    invalid = "data"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/redact" -Method POST -Headers $headers -Body $invalidData -ContentType "application/json" -ErrorAction Stop
    Write-Warn "Should have rejected invalid data"
    $script:warnings++
} catch {
    if ($_.Exception.Response.StatusCode -eq 400 -or $_.Exception.Response.StatusCode -eq 422) {
        Write-Success "Proper error handling (400/422)"
        $script:passed++
    } else {
        Write-Fail "Unexpected error response"
        $script:failed++
    }
}

# Test 9: Load Test (10 concurrent requests)
Write-Section "Test 9: Basic Load Test"
Write-Host "Sending 10 concurrent requests..." -ForegroundColor Gray

$jobs = @()
for ($i = 1; $i -le 10; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($url, $headers)
        try {
            $response = Invoke-WebRequest -Uri "$url/health" -Headers $headers -TimeoutSec 5
            return $response.StatusCode
        } catch {
            return 500
        }
    } -ArgumentList $baseUrl, $headers
}

$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$successCount = ($results | Where-Object { $_ -eq 200 }).Count
if ($successCount -ge 8) {
    Write-Success "Load test passed - $successCount of 10 successful"
    $script:passed++
} elseif ($successCount -ge 5) {
    Write-Warn "Load test partial - $successCount of 10 successful"
    $script:warnings++
} else {
    Write-Fail "Load test failed - $successCount of 10 successful"
    $script:failed++
}

# RESULTS
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST RESULTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed:   $passed" -ForegroundColor Green
Write-Host "Failed:   $failed" -ForegroundColor Red
Write-Host "Warnings: $warnings" -ForegroundColor Yellow

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
} else {
    Write-Host "✗ NO-GO FOR DEPLOYMENT" -ForegroundColor Red -BackgroundColor DarkRed
    Write-Host "  Critical failures detected" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
exit $(if ($failed -eq 0) {0} else {1})
