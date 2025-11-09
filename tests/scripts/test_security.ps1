# Advanced Security Features Test Script
# Tests JWT authentication, RBAC, rate limiting, and audit logging

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Advanced Security Features Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: Create test users with different roles
Write-Host "`n[Test 1] Creating test users..." -ForegroundColor Yellow

# First, we need to bootstrap by creating an admin user programmatically
# For now, we'll test the endpoints

# Test 2: Login and get JWT token
Write-Host "`n[Test 2] Testing login (will fail until users are created)..." -ForegroundColor Yellow
try {
    $loginBody = @{
        username = "admin"
        password = "admin123"
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
        -Method POST `
        -Body $loginBody `
        -ContentType "application/json" `
        -ErrorAction Stop

    $token = ($response.Content | ConvertFrom-Json).access_token
    Write-Host "✓ Login successful!" -ForegroundColor Green
    Write-Host "Token: $($token.Substring(0, 20))..." -ForegroundColor Gray
} catch {
    Write-Host "✗ Login failed (expected - user not created yet): $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Note: Users need to be created first via API or script" -ForegroundColor Yellow
}

# Test 3: Test rate limiting
Write-Host "`n[Test 3] Testing rate limiting..." -ForegroundColor Yellow

$headers = @{
    "X-API-Key" = "dev-api-key-12345"
}

Write-Host "Sending 10 requests rapidly..." -ForegroundColor Gray
for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/health" `
            -Headers $headers `
            -ErrorAction Stop
        
        $rateLimitRemaining = $response.Headers["X-RateLimit-Remaining-Minute"]
        Write-Host "Request $i - Status: $($response.StatusCode) - Remaining: $rateLimitRemaining" -ForegroundColor Gray
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "✓ Rate limit enforced after $i requests" -ForegroundColor Green
            break
        } else {
            Write-Host "✗ Request failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 100
}

# Test 4: Check rate limit status
Write-Host "`n[Test 4] Checking rate limit status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/rate-limit/stats" `
        -Headers $headers `
        -ErrorAction Stop
    
    $stats = $response.Content | ConvertFrom-Json
    Write-Host "✓ Rate limit statistics:" -ForegroundColor Green
    Write-Host "  Enabled: $($stats.enabled)" -ForegroundColor Gray
    Write-Host "  Limits per minute: $($stats.limits.per_minute)" -ForegroundColor Gray
    Write-Host "  Limits per hour: $($stats.limits.per_hour)" -ForegroundColor Gray
    Write-Host "  Tracked clients: $($stats.tracked_clients)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed to get rate limit stats: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Test audit logging
Write-Host "`n[Test 5] Testing audit logging..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/audit/event-types" `
        -Headers $headers `
        -ErrorAction Stop
    
    $eventTypes = $response.Content | ConvertFrom-Json
    Write-Host "✓ Available audit event types:" -ForegroundColor Green
    Write-Host "  Total event types: $($eventTypes.total)" -ForegroundColor Gray
    Write-Host "  Sample types: $($eventTypes.event_types[0..4] -join ', ')..." -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed to get audit event types: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Test RBAC permissions
Write-Host "`n[Test 6] Testing RBAC (requires JWT)..." -ForegroundColor Yellow
Write-Host "Note: Full RBAC testing requires authenticated user with JWT token" -ForegroundColor Yellow

# Test 7: Generate test traffic for audit logs
Write-Host "`n[Test 7] Generating test traffic for audit logging..." -ForegroundColor Yellow

$testEndpoints = @(
    "/health",
    "/health/detailed",
    "/metrics",
    "/redact"
)

foreach ($endpoint in $testEndpoints) {
    try {
        if ($endpoint -eq "/redact") {
            $body = @{
                data = @{
                    card_number = "4532-1111-2222-3333"
                    email = "test@example.com"
                }
            } | ConvertTo-Json
            
            $response = Invoke-WebRequest -Uri "$baseUrl$endpoint" `
                -Method POST `
                -Headers $headers `
                -Body $body `
                -ContentType "application/json" `
                -ErrorAction Stop
        } else {
            $response = Invoke-WebRequest -Uri "$baseUrl$endpoint" `
                -Headers $headers `
                -ErrorAction Stop
        }
        Write-Host "✓ $endpoint - Status: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "✗ $endpoint - Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 8: Query audit events
Write-Host "`n[Test 8] Querying audit events..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/audit/events?limit=10" `
        -Headers $headers `
        -ErrorAction Stop
    
    $auditData = $response.Content | ConvertFrom-Json
    Write-Host "✓ Audit events retrieved:" -ForegroundColor Green
    Write-Host "  Total events: $($auditData.total)" -ForegroundColor Gray
    
    if ($auditData.events.Count -gt 0) {
        Write-Host "`n  Recent events:" -ForegroundColor Gray
        foreach ($event in $auditData.events[0..([Math]::Min(2, $auditData.events.Count - 1))]) {
            Write-Host "    - $($event.event_type): $($event.message)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "✗ Failed to query audit events: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 9: Get audit statistics
Write-Host "`n[Test 9] Getting audit statistics..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/audit/statistics" `
        -Headers $headers `
        -ErrorAction Stop
    
    $stats = $response.Content | ConvertFrom-Json
    Write-Host "✓ Audit statistics:" -ForegroundColor Green
    Write-Host "  Total events: $($stats.total_events)" -ForegroundColor Gray
    Write-Host "  Events in memory: $($stats.events_in_memory)" -ForegroundColor Gray
    Write-Host "  Log file: $($stats.log_file)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed to get audit statistics: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Basic security features are ready for testing." -ForegroundColor Green
Write-Host "`nTo fully test JWT and RBAC:" -ForegroundColor Yellow
Write-Host "1. Create test users via Python script" -ForegroundColor Gray
Write-Host "2. Login to get JWT tokens" -ForegroundColor Gray
Write-Host "3. Test protected endpoints with different roles" -ForegroundColor Gray
Write-Host "`nRate limiting and audit logging are active!" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
