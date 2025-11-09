# PowerShell script to test content processing middleware

Write-Host "Content Processing Middleware Test Suite" -ForegroundColor Green
Write-Host "="*50

# Check server health
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -UseBasicParsing
    Write-Host "✓ Server is running and healthy" -ForegroundColor Green
} catch {
    Write-Host "✗ Server not accessible" -ForegroundColor Red
    exit 1
}

# Test data
$testData = @{
    data = "John Doe's credit card number is 4532-1234-5678-9012 and his SSN is 123-45-6789"
    include_meta = $true
} | ConvertTo-Json

Write-Host "`n=== Testing Normal Request (Control) ===" -ForegroundColor Cyan

try {
    $headers = @{
        "Authorization" = "Bearer test-api-key"
        "Content-Type" = "application/json"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testData -Headers $headers -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "Response status: $($response.StatusCode)"
    Write-Host "Redacted data: $($result.redacted_data)"
    Write-Host "Redactions: $($result.redaction_meta.Count)"
    
} catch {
    Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
}

Write-Host "`n=== Testing Base64 Encoding ===" -ForegroundColor Cyan

try {
    # Encode test data as base64
    $jsonBytes = [System.Text.Encoding]::UTF8.GetBytes($testData)
    $encodedData = [Convert]::ToBase64String($jsonBytes)
    
    Write-Host "Original data size: $($testData.Length) bytes"
    Write-Host "Encoded data size: $($encodedData.Length) bytes"
    Write-Host "Encoded data (first 100 chars): $($encodedData.Substring(0, [Math]::Min(100, $encodedData.Length)))"
    
    $headers = @{
        "Authorization" = "Bearer test-api-key"
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

Write-Host "`n=== Testing Gzip Compression ===" -ForegroundColor Cyan

try {
    # Create gzip compressed data
    $jsonBytes = [System.Text.Encoding]::UTF8.GetBytes($testData)
    
    # Create gzip stream
    $memoryStream = New-Object System.IO.MemoryStream
    $gzipStream = New-Object System.IO.Compression.GZipStream($memoryStream, [System.IO.Compression.CompressionMode]::Compress)
    $gzipStream.Write($jsonBytes, 0, $jsonBytes.Length)
    $gzipStream.Close()
    $compressedBytes = $memoryStream.ToArray()
    $memoryStream.Close()
    
    Write-Host "Original data size: $($jsonBytes.Length) bytes"
    Write-Host "Compressed data size: $($compressedBytes.Length) bytes"
    Write-Host "Compression ratio: $([Math]::Round($compressedBytes.Length/$jsonBytes.Length*100, 2))%"
    
    $headers = @{
        "Authorization" = "Bearer test-api-key"
        "Content-Type" = "application/json"
        "Content-Encoding" = "gzip"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $compressedBytes -Headers $headers -UseBasicParsing
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

Write-Host "`n" -NoNewline
Write-Host ('='*50) -ForegroundColor Green
Write-Host "Content processing middleware tests completed!" -ForegroundColor Green