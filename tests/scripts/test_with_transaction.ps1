# Test script for redacting test_transaction.json
# Make sure the server is running first

Write-Host "`n=== Testing PII/PCI Data Redaction with test_transaction.json ===" -ForegroundColor Cyan
Write-Host "Server should be running on http://localhost:8000`n" -ForegroundColor Yellow

# Read the test file
$testData = Get-Content "input\test_transaction.json" -Raw | ConvertFrom-Json

Write-Host "Processing transaction $($testData.txn_id)..." -ForegroundColor Green

# Prepare request
$headers = @{
    "X-API-Key" = "dev-api-key-12345"
    "Content-Type" = "application/json"
}

$body = @{
    data = $testData
    include_meta = $true
} | ConvertTo-Json -Depth 10

try {
    # Send request
    $response = Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method POST -Headers $headers -Body $body
    
    Write-Host "`n=== ORIGINAL DATA ===" -ForegroundColor Yellow
    $testData | Format-List
    
    Write-Host "`n=== REDACTED DATA ===" -ForegroundColor Green
    $response.redacted_data | Format-List
    
    if ($response.redaction_meta) {
        Write-Host "`n=== REDACTIONS APPLIED ===" -ForegroundColor Cyan
        $response.redaction_meta | Format-Table -Property field, rule, action -AutoSize
    }
    
    Write-Host "`nProcessing Time: $($response.processing_time_ms) ms" -ForegroundColor Magenta
    
    # Show specific field comparisons
    Write-Host "`n=== FIELD-BY-FIELD COMPARISON ===" -ForegroundColor White
    Write-Host ("-" * 80) -ForegroundColor DarkGray
    
    $fields = @("pan", "account_no", "iban", "customer_name")
    foreach ($field in $fields) {
        if ($testData.$field) {
            Write-Host "`n${field}:" -ForegroundColor Yellow
            Write-Host "  Original : $($testData.$field)" -ForegroundColor Gray
            Write-Host "  Redacted : $($response.redacted_data.$field)" -ForegroundColor Green
            
            # Show which rule was applied
            $meta = $response.redaction_meta | Where-Object { $_.field -eq $field }
            if ($meta) {
                Write-Host "  Rule     : $($meta.rule)" -ForegroundColor Cyan
            }
        }
    }
    
    Write-Host "`n" + ("-" * 80) -ForegroundColor DarkGray
    Write-Host "`n✅ Transaction processed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "`nError processing transaction: $_" -ForegroundColor Red
    Write-Host "Make sure the server is running: python -m src.cli serve`n" -ForegroundColor Yellow
    exit 1
}
