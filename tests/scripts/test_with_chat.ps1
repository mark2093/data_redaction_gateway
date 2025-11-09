# Test script for redacting test_chat.json
# Make sure the server is running first: python -m src.cli serve --reload

Write-Host "`n=== Testing PII/PCI Data Redaction Gateway with test_chat.json ===" -ForegroundColor Cyan
Write-Host "Server should be running on http://localhost:8000`n" -ForegroundColor Yellow

# Read the test file
$testData = Get-Content "input\test_chat.json" -Raw | ConvertFrom-Json

# Process each chat message
foreach ($chat in $testData) {
    Write-Host "Processing chat $($chat.chat_id)..." -ForegroundColor Green
    
    # Prepare request
    $headers = @{
        "X-API-Key" = "dev-api-key-12345"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        data = $chat
        include_meta = $true
    } | ConvertTo-Json -Depth 10
    
    try {
        # Send request
        $response = Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method POST -Headers $headers -Body $body
        
        Write-Host "`nOriginal Message:" -ForegroundColor Yellow
        Write-Host $chat.message
        
        Write-Host "`nRedacted Message:" -ForegroundColor Green
        Write-Host $response.redacted_data.message
        
        if ($response.redaction_meta) {
            Write-Host "`nRedactions Applied:" -ForegroundColor Cyan
            foreach ($meta in $response.redaction_meta) {
                Write-Host "  - Field: $($meta.field), Rule: $($meta.rule), Action: $($meta.action)" -ForegroundColor Gray
            }
        }
        
        Write-Host "`nProcessing Time: $($response.processing_time_ms) ms" -ForegroundColor Magenta
        Write-Host ("-" * 80) -ForegroundColor DarkGray
        
    } catch {
        Write-Host "`nError processing chat $($chat.chat_id): $_" -ForegroundColor Red
        Write-Host "Make sure the server is running: python -m src.cli serve --reload`n" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "`n=== All chats processed successfully ===" -ForegroundColor Green
