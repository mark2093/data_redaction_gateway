# PowerShell script to test content processing middleware

Write-Host "Content Processing Middleware Test Suite" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check server health
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -UseBasicParsing
    Write-Host "Server is running and healthy" -ForegroundColor Green
} catch {
    Write-Host "Server not accessible" -ForegroundColor Red
    exit 1
}

# Test data
$testData = '{"data":"John Doe credit card number is 4532-1234-5678-9012 and his SSN is 123-45-6789","include_meta":true}'

Write-Host ""
Write-Host "Testing Normal Request (Control)" -ForegroundColor Cyan

try {
    $headers = @{
        "X-API-Key" = "test-api-key-67890"
        "Content-Type" = "application/json"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testData -Headers $headers -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "Response status: $($response.StatusCode)"
    Write-Host "Redacted data: $($result.redacted_data)"
    Write-Host "Redactions: $($result.redaction_meta.Count)"
    
} catch {
    Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Testing Base64 Encoding" -ForegroundColor Cyan

try {
    # Encode test data as base64
    $jsonBytes = [System.Text.Encoding]::UTF8.GetBytes($testData)
    $encodedData = [Convert]::ToBase64String($jsonBytes)
    
    Write-Host "Original data size: $($testData.Length) bytes"
    Write-Host "Encoded data size: $($encodedData.Length) bytes"
    
    $headers = @{
        "X-API-Key" = "test-api-key-67890"
        "Content-Type" = "application/json; base64"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $encodedData -Headers $headers -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "Response status: $($response.StatusCode)"
    Write-Host "Redacted data: $($result.redacted_data)"
    Write-Host "Redactions: $($result.redaction_meta.Count)"
    
} catch {
    Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseText = $reader.ReadToEnd()
        Write-Host "Response: $responseText" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Content processing middleware tests completed!" -ForegroundColor Green