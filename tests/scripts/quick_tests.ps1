#!/usr/bin/env powershell

# Quick Test Commands for Data Redaction Gateway
# Run these one-liners for rapid testing

Write-Host "🚀 Quick Test Commands for Data Redaction Gateway" -ForegroundColor Green
Write-Host ""

# Base configuration
$url = "http://localhost:8000"
$key = "dev-api-key-12345"
$headers = @{"Content-Type"="application/json"; "X-API-Key"=$key}

Write-Host "📋 Copy and paste these commands:" -ForegroundColor Yellow
Write-Host ""

# 1. Health Check
Write-Host "1. Health Check:" -ForegroundColor Cyan
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/health" -Headers @{"X-API-Key"="dev-api-key-12345"} | ConvertTo-Json' -ForegroundColor White
Write-Host ""

# 2. Simple Transaction Test
Write-Host "2. Transaction Test:" -ForegroundColor Cyan
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/redact/" -Method POST -Headers @{"Content-Type"="application/json";"X-API-Key"="dev-api-key-12345"} -Body ((@{data=@{name="John Doe";email="john@test.com";card="4111111111111111";merchant="Apple Inc"}} | ConvertTo-Json)) | ConvertTo-Json -Depth 5' -ForegroundColor White
Write-Host ""

# 3. Chat Message Test  
Write-Host "3. Chat Message Test:" -ForegroundColor Cyan
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/redact/" -Method POST -Headers @{"Content-Type"="application/json";"X-API-Key"="dev-api-key-12345"} -Body ((@{data=@{message="Hi, I am Sarah Smith, my phone is 555-123-4567 and email sarah@company.com, card 5555555555554444"}} | ConvertTo-Json)) | ConvertTo-Json -Depth 5' -ForegroundColor White
Write-Host ""

# 4. Dry Run Test
Write-Host "4. Dry Run Test (Before/After):" -ForegroundColor Cyan
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/redact/dry-run" -Method POST -Headers @{"Content-Type"="application/json";"X-API-Key"="dev-api-key-12345"} -Body ((@{data=@{customer="Alice Johnson";phone="555-987-6543";ssn="123-45-6789";merchant="Microsoft Corp"}} | ConvertTo-Json)) | ConvertTo-Json -Depth 5' -ForegroundColor White
Write-Host ""

# 5. Policy Check
Write-Host "5. Policy Information:" -ForegroundColor Cyan  
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/policy" -Headers @{"X-API-Key"="dev-api-key-12345"} | ConvertTo-Json' -ForegroundColor White
Write-Host ""

# 6. Metrics
Write-Host "6. Metrics:" -ForegroundColor Cyan
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/metrics" -Headers @{"X-API-Key"="dev-api-key-12345"} | ConvertTo-Json' -ForegroundColor White
Write-Host ""

Write-Host "💡 Tips:" -ForegroundColor Green
Write-Host "- Replace 'dev-api-key-12345' with your actual API key if different" -ForegroundColor White  
Write-Host "- Add '| ConvertTo-Json -Depth 10' for detailed output" -ForegroundColor White
Write-Host "- Use '| Out-File test_result.json' to save responses" -ForegroundColor White
Write-Host "- Check server logs for additional debugging info" -ForegroundColor White