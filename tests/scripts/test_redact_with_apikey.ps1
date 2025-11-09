# Complete PowerShell command to test /redact endpoint with API key

Write-Host "`n=== Testing /redact endpoint with proper authentication ===" -ForegroundColor Cyan

$headers = @{
    "X-API-Key" = "dev-api-key-12345"
    "Content-Type" = "application/json"
}

$body = @{
    data = @{
        txn_id = "TXN-9876543"
        account_no = "1234567890"
        iban = "GB82WEST12345698765432"
        pan = "5425233430109903"
        amount = 1500.00
        currency = "USD"
        merchant = "Tech Store Inc"
        customer_name = "Jane Doe"
        timestamp = "2025-11-08T14:45:00"
    }
    include_meta = $true
} | ConvertTo-Json -Depth 10

Write-Host "`nRequest Body:" -ForegroundColor Yellow
Write-Host $body -ForegroundColor Gray

Write-Host "`nSending request to http://localhost:8000/redact..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method POST -Headers $headers -Body $body
    
    Write-Host "`n✅ SUCCESS! Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Cyan
    
} catch {
    Write-Host "`n❌ ERROR:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
