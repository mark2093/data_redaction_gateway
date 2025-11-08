# Direct FastAPI Endpoint Test
# Shows full JSON request and response

Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Testing FastAPI /redact Endpoint with test_transaction.json" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Read test data
$testData = Get-Content "input\test_transaction.json" -Raw | ConvertFrom-Json

# Prepare the request body
$requestBody = @{
    data = $testData
    include_meta = $true
    dry_run = $false
}

# Convert to JSON for display and sending
$requestJson = $requestBody | ConvertTo-Json -Depth 10

Write-Host "┌─ REQUEST DETAILS ───────────────────────────────────────────┐" -ForegroundColor Yellow
Write-Host "│ Endpoint: POST http://localhost:8000/redact                 │" -ForegroundColor Yellow
Write-Host "│ Headers:  X-API-Key: dev-api-key-12345                      │" -ForegroundColor Yellow
Write-Host "│           Content-Type: application/json                    │" -ForegroundColor Yellow
Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

Write-Host "`n📤 REQUEST BODY (JSON):" -ForegroundColor Cyan
Write-Host $requestJson -ForegroundColor Gray

Write-Host "`n⏳ Sending request..." -ForegroundColor Yellow

try {
    # Prepare headers
    $headers = @{
        "X-API-Key" = "dev-api-key-12345"
        "Content-Type" = "application/json"
    }
    
    # Send request and get response
    $response = Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method POST -Headers $headers -Body $requestJson
    
    # Convert response to pretty JSON
    $responseJson = $response | ConvertTo-Json -Depth 10
    
    Write-Host "✅ Response received!" -ForegroundColor Green
    
    Write-Host "`n┌─ RESPONSE DETAILS ──────────────────────────────────────────┐" -ForegroundColor Green
    Write-Host "│ Status: 200 OK                                               │" -ForegroundColor Green
    Write-Host "│ Processing Time: $($response.processing_time_ms) ms" -ForegroundColor Green
    Write-Host "│ Policy Version: $($response.policy_version)" -ForegroundColor Green
    Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Green
    
    Write-Host "`n📥 RESPONSE BODY (JSON):" -ForegroundColor Cyan
    Write-Host $responseJson -ForegroundColor Gray
    
    Write-Host "`n┌─ REDACTED DATA (Formatted) ─────────────────────────────────┐" -ForegroundColor Magenta
    $response.redacted_data | Format-List
    Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Magenta
    
    Write-Host "`n┌─ REDACTION METADATA ────────────────────────────────────────┐" -ForegroundColor Yellow
    if ($response.redaction_meta -and $response.redaction_meta.Count -gt 0) {
        $response.redaction_meta | Format-Table -Property field, rule, action, timestamp -AutoSize
    } else {
        Write-Host "No redactions applied" -ForegroundColor Gray
    }
    Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
    
    # Side-by-side comparison
    Write-Host "`n┌─ BEFORE vs AFTER COMPARISON ────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "│                                                              │" -ForegroundColor Cyan
    
    $fields = @("txn_id", "account_no", "iban", "pan", "customer_name")
    foreach ($field in $fields) {
        $original = $testData.$field
        $redacted = $response.redacted_data.$field
        
        if ($original) {
            $changed = if ($original -ne $redacted) { "🔴 REDACTED" } else { "✅ UNCHANGED" }
            $color = if ($original -ne $redacted) { "Red" } else { "Green" }
            
            Write-Host "│ $field" -ForegroundColor White -NoNewline
            Write-Host " " * (20 - $field.Length) -NoNewline
            Write-Host "$changed" -ForegroundColor $color -NoNewline
            Write-Host " " * (20 - $changed.Length) -NoNewline
            Write-Host "│" -ForegroundColor Cyan
            Write-Host "│   Original : " -ForegroundColor Gray -NoNewline
            Write-Host "$original" -ForegroundColor Yellow
            Write-Host "│   Redacted : " -ForegroundColor Gray -NoNewline
            Write-Host "$redacted" -ForegroundColor Green
            Write-Host "│                                                              │" -ForegroundColor Cyan
        }
    }
    
    Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
    
    # Save response to file
    $responseJson | Out-File -FilePath "output\transaction_redacted_response.json" -Encoding utf8
    Write-Host "`n💾 Full response saved to: output\transaction_redacted_response.json" -ForegroundColor Green
    
    Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "   ✅ API Test Completed Successfully!" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
    
} catch {
    Write-Host "`n❌ Error calling API:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "`nError Details:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Gray
    }
    
    Write-Host "`n💡 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Make sure the server is running: python -m src.cli serve" -ForegroundColor Gray
    Write-Host "2. Check if port 8000 is accessible: http://localhost:8000/health" -ForegroundColor Gray
    Write-Host "3. Verify API key is correct: dev-api-key-12345`n" -ForegroundColor Gray
    
    exit 1
}
