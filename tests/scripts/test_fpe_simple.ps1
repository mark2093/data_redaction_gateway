# Simple FPE Test Script

Write-Host "FPE Test Suite" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green

# Test FPE functionality
$testData = '{"data":"Credit card 4532123456789012 and SSN 123-45-6789","include_meta":true}'

$headers = @{
    "X-API-Key" = "test-api-key-67890"
    "Content-Type" = "application/json"
}

try {
    Write-Host "Testing FPE with credit card and SSN..."
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testData -Headers $headers -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "Original: Credit card 4532123456789012 and SSN 123-45-6789"
    Write-Host "Redacted: $($result.redacted_data)" -ForegroundColor Green
    Write-Host "Redactions: $($result.redaction_meta.Count)"
    
    if ($result.redaction_meta) {
        foreach ($meta in $result.redaction_meta) {
            Write-Host "  Rule: $($meta.rule), Action: $($meta.action)"
        }
    }
    
} catch {
    Write-Host "Test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Checking FPE rules in policy..."

try {
    $rulesResponse = Invoke-WebRequest -Uri "http://localhost:8000/policy/rules" -Method GET -Headers $headers -UseBasicParsing
    $rules = $rulesResponse.Content | ConvertFrom-Json
    
    $fpeRules = $rules | Where-Object { $_.action -eq "fpe" }
    
    if ($fpeRules) {
        Write-Host "FPE Rules Found: $($fpeRules.Count)" -ForegroundColor Green
        foreach ($rule in $fpeRules) {
            $status = if ($rule.enabled) { "Enabled" } else { "Disabled" }
            Write-Host "  $($rule.id): $status"
        }
    } else {
        Write-Host "No FPE rules found" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Could not retrieve rules: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "FPE test completed!" -ForegroundColor Green