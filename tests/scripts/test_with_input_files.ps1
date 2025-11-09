# PowerShell Commands to Test Data Redaction Gateway with Input Files
# These commands use the actual test data from the input/ folder

$BaseUrl = "http://localhost:8000"
$ApiKey = "dev-api-key-12345"
$Headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $ApiKey
}

Write-Host "🚀 Testing Data Redaction Gateway with Input Files" -ForegroundColor Green
Write-Host "Server: $BaseUrl" -ForegroundColor Yellow
Write-Host ""

# Test 1: Chat Messages (test_chat.json)
Write-Host "1️⃣  Testing Chat Messages (test_chat.json)" -ForegroundColor Magenta
$chatData = Get-Content "input/test_chat.json" -Raw | ConvertFrom-Json
$chatPayload = @{
    data = $chatData
    include_meta = $true
} | ConvertTo-Json -Depth 10

Write-Host "🔄 Sending chat data to /redact/ endpoint..." -ForegroundColor Cyan
try {
    $chatResponse = Invoke-RestMethod -Uri "$BaseUrl/redact/" -Method POST -Headers $Headers -Body $chatPayload
    Write-Host "✅ Chat redaction successful!" -ForegroundColor Green
    Write-Host "Redacted Data:" -ForegroundColor White
    $chatResponse.redacted_data | ConvertTo-Json -Depth 5 | Write-Host
    Write-Host "`nRedaction Summary:" -ForegroundColor Yellow
    Write-Host "Total redactions: $($chatResponse.redaction_meta.Count)" -ForegroundColor White
    Write-Host "Processing time: $([math]::Round($chatResponse.processing_time_ms, 2))ms" -ForegroundColor White
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ("-" * 80) -ForegroundColor Gray

# Test 2: Transaction Data (test_transaction.json) - Dry Run
Write-Host "2️⃣  Testing Transaction Data - Dry Run (test_transaction.json)" -ForegroundColor Magenta
$transactionData = Get-Content "input/test_transaction.json" -Raw | ConvertFrom-Json
$transactionPayload = @{
    data = $transactionData
} | ConvertTo-Json -Depth 10

Write-Host "🔄 Sending transaction data to /redact/dry-run endpoint..." -ForegroundColor Cyan
try {
    $transactionResponse = Invoke-RestMethod -Uri "$BaseUrl/redact/dry-run" -Method POST -Headers $Headers -Body $transactionPayload
    Write-Host "✅ Transaction dry-run successful!" -ForegroundColor Green
    Write-Host "`nOriginal Data:" -ForegroundColor Yellow
    $transactionResponse.original_data | ConvertTo-Json -Depth 5 | Write-Host
    Write-Host "`nRedacted Data:" -ForegroundColor Yellow  
    $transactionResponse.redacted_data | ConvertTo-Json -Depth 5 | Write-Host
    Write-Host "`nDifferences:" -ForegroundColor Yellow
    Write-Host "Fields affected: $($transactionResponse.diff.fields_affected -join ', ')" -ForegroundColor White
    Write-Host "Rules triggered: $($transactionResponse.diff.rules_triggered -join ', ')" -ForegroundColor White
    Write-Host "Total redactions: $($transactionResponse.diff.redaction_count)" -ForegroundColor White
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ("-" * 80) -ForegroundColor Gray

# Test 3: Order Data (test_order.json)
Write-Host "3️⃣  Testing Order Data (test_order.json)" -ForegroundColor Magenta
$orderData = Get-Content "input/test_order.json" -Raw | ConvertFrom-Json
$orderPayload = @{
    data = $orderData
    include_meta = $true
} | ConvertTo-Json -Depth 10

Write-Host "🔄 Sending order data to /redact/ endpoint..." -ForegroundColor Cyan
try {
    $orderResponse = Invoke-RestMethod -Uri "$BaseUrl/redact/" -Method POST -Headers $Headers -Body $orderPayload
    Write-Host "✅ Order redaction successful!" -ForegroundColor Green
    Write-Host "Redacted Data:" -ForegroundColor White
    $orderResponse.redacted_data | ConvertTo-Json -Depth 5 | Write-Host
    Write-Host "`nRedaction Summary:" -ForegroundColor Yellow
    Write-Host "Total redactions: $($orderResponse.redaction_meta.Count)" -ForegroundColor White
    Write-Host "Processing time: $([math]::Round($orderResponse.processing_time_ms, 2))ms" -ForegroundColor White
    if ($orderResponse.redaction_meta.Count -gt 0) {
        Write-Host "`nRedaction Details:" -ForegroundColor Cyan
        foreach ($meta in $orderResponse.redaction_meta) {
            Write-Host "  Field: $($meta.field), Rule: $($meta.rule), Action: $($meta.action)" -ForegroundColor White
        }
    }
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ("-" * 80) -ForegroundColor Gray

# Test 4: Batch Processing with all three files
Write-Host "4️⃣  Testing Batch Processing (All Files)" -ForegroundColor Magenta
$batchPayload = @(
    @{
        data = $chatData
        include_meta = $true
    },
    @{
        data = $transactionData
        include_meta = $true
    },
    @{
        data = $orderData
        include_meta = $true
    }
) | ConvertTo-Json -Depth 10

Write-Host "🔄 Sending batch data to /redact/batch endpoint..." -ForegroundColor Cyan
try {
    $batchResponse = Invoke-RestMethod -Uri "$BaseUrl/redact/batch" -Method POST -Headers $Headers -Body $batchPayload
    Write-Host "✅ Batch processing successful!" -ForegroundColor Green
    Write-Host "Batch Summary:" -ForegroundColor Yellow
    Write-Host "Total processed: $($batchResponse.total_processed)" -ForegroundColor White
    Write-Host "Total redactions: $($batchResponse.total_redactions)" -ForegroundColor White
    Write-Host "Processing time: $([math]::Round($batchResponse.processing_time_ms, 2))ms" -ForegroundColor White
    Write-Host "Policy version: $($batchResponse.policy_version)" -ForegroundColor White
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ("-" * 80) -ForegroundColor Gray

Write-Host "🎉 All tests completed!" -ForegroundColor Green
Write-Host "Check the responses above to verify redaction is working correctly." -ForegroundColor Yellow