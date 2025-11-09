# Test Script for LLM-as-Judge Feature
# This script tests the LLM judge integration by sending multiple requests
# and verifying that sampling works correctly

Write-Host "`n=== LLM-as-Judge Test Script ===" -ForegroundColor Cyan
Write-Host "This will send 20 requests to test LLM judge sampling (15% rate)" -ForegroundColor Yellow
Write-Host ""

# Configuration
$baseUrl = "http://localhost:8000"
$apiKey = "dev-api-key-12345"

# Test data with PII/PCI
$testData = @{
    "user_email" = "john.doe@example.com"
    "phone" = "+1-555-123-4567"
    "credit_card" = "4532015112830366"
    "cvv" = "123"
    "account_number" = "1234567890"
    "message" = "My name is John Smith and I need help with my account."
    "transaction_id" = "TXN-2024-001"
    "amount" = 125.50
    "timestamp" = "2024-01-15T10:30:00Z"
}

# Request body
$requestBody = @{
    "data" = $testData
    "include_meta" = $true
} | ConvertTo-Json -Depth 10

# Headers
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $apiKey
}

# Tracking
$totalRequests = 20
$sampledCount = 0
$nonsampledCount = 0
$judgeResults = @()

Write-Host "Sending $totalRequests requests..." -ForegroundColor Cyan
Write-Host ""

# Send multiple requests
for ($i = 1; $i -le $totalRequests; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/redact" -Method Post -Body $requestBody -Headers $headers -ErrorAction Stop
        
        if ($response.judge_result) {
            $sampledCount++
            $judgeResults += $response.judge_result
            
            Write-Host "[$i/$totalRequests] SAMPLED - " -ForegroundColor Green -NoNewline
            Write-Host "Coverage: $($response.judge_result.coverage_complete), " -NoNewline
            Write-Host "Confidence: $($response.judge_result.confidence)%, " -NoNewline
            Write-Host "Time: $([math]::Round($response.judge_result.processing_time_ms, 2))ms"
            
            if ($response.judge_result.suggestions -and $response.judge_result.suggestions.Count -gt 0) {
                Write-Host "  Suggestions: $($response.judge_result.suggestions -join ', ')" -ForegroundColor Yellow
            }
        } else {
            $nonsampledCount++
            Write-Host "[$i/$totalRequests] Not sampled" -ForegroundColor Gray
        }
        
        # Small delay between requests
        Start-Sleep -Milliseconds 100
        
    } catch {
        Write-Host "[$i/$totalRequests] ERROR: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Test Results ===" -ForegroundColor Cyan
Write-Host "Total Requests: $totalRequests"
Write-Host "Sampled: $sampledCount ($([math]::Round($sampledCount/$totalRequests*100, 1))%)" -ForegroundColor Green
Write-Host "Not Sampled: $nonsampledCount ($([math]::Round($nonsampledCount/$totalRequests*100, 1))%)" -ForegroundColor Gray

if ($sampledCount -gt 0) {
    Write-Host ""
    Write-Host "=== Judge Analysis ===" -ForegroundColor Cyan
    
    $avgConfidence = ($judgeResults | ForEach-Object { $_.confidence } | Measure-Object -Average).Average
    $avgTime = ($judgeResults | ForEach-Object { $_.processing_time_ms } | Measure-Object -Average).Average
    $coverageComplete = ($judgeResults | Where-Object { $_.coverage_complete } | Measure-Object).Count
    $overRedacted = ($judgeResults | Where-Object { $_.over_redacted } | Measure-Object).Count
    $underRedacted = ($judgeResults | Where-Object { $_.under_redacted } | Measure-Object).Count
    
    Write-Host "Average Confidence: $([math]::Round($avgConfidence, 1))%"
    Write-Host "Average Processing Time: $([math]::Round($avgTime, 2))ms"
    Write-Host "Coverage Complete: $coverageComplete / $sampledCount" -ForegroundColor $(if ($coverageComplete -eq $sampledCount) { "Green" } else { "Yellow" })
    Write-Host "Over-Redacted: $overRedacted" -ForegroundColor $(if ($overRedacted -eq 0) { "Green" } else { "Yellow" })
    Write-Host "Under-Redacted: $underRedacted" -ForegroundColor $(if ($underRedacted -eq 0) { "Green" } else { "Red" })
    
    Write-Host ""
    Write-Host "Expected sampling rate: 15%"
    Write-Host "Actual sampling rate: $([math]::Round($sampledCount/$totalRequests*100, 1))%"
    
    $deviation = [math]::Abs(($sampledCount/$totalRequests) - 0.15) * 100
    if ($deviation -lt 10) {
        Write-Host "Sampling rate is within expected range ✓" -ForegroundColor Green
    } else {
        Write-Host "Sampling rate deviation: $([math]::Round($deviation, 1))% (expected with random sampling)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Check Metrics ===" -ForegroundColor Cyan
try {
    $metrics = Invoke-RestMethod -Uri "$baseUrl/metrics" -Method Get -Headers $headers
    Write-Host "Judge Fallback Rate: $([math]::Round($metrics.judge_fallback_rate, 2))%"
    
    if ($metrics.judge_fallback_rate -eq 0) {
        Write-Host "All judge calls succeeded ✓" -ForegroundColor Green
    } else {
        Write-Host "Some judge calls fell back to rules-only" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not retrieve metrics: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Cyan
