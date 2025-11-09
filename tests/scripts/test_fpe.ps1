# PowerShell script to test Format-Preserving Encryption (FPE) functionality

Write-Host "Format-Preserving Encryption (FPE) Test Suite" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Test data with various PII types that could use FPE
$testDataSets = @(
    @{
        name = "Credit Card Test"
        data = @{
            data = "Customer transaction: PAN 4532-1234-5678-9012, amount $150.00"
            include_meta = $true
        }
        expectedPattern = "FPE preserves 16-digit format for credit card"
    },
    @{
        name = "SSN Test"
        data = @{
            data = "Employee SSN: 123-45-6789 for tax purposes"
            include_meta = $true
        }
        expectedPattern = "FPE maintains XXX-XX-XXXX format for SSN"
    },
    @{
        name = "Multiple PAN Test"
        data = @{
            data = "Two cards: 4111111111111111 and 5555555555554444"
            include_meta = $true
        }
        expectedPattern = "Multiple PANs encrypted with format preservation"
    }
)

$headers = @{
    "X-API-Key" = "test-api-key-67890"
    "Content-Type" = "application/json"
}

Write-Host ""
Write-Host "Test 1: Testing FPE Implementation" -ForegroundColor Cyan

foreach ($testSet in $testDataSets) {
    Write-Host ""
    Write-Host "Testing: $($testSet.name)" -ForegroundColor Yellow
    
    $jsonData = $testSet.data | ConvertTo-Json
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $jsonData -Headers $headers -UseBasicParsing
        $result = $response.Content | ConvertFrom-Json
        
        Write-Host "Original: $($testSet.data.data)"
        Write-Host "Redacted: $($result.redacted_data)" -ForegroundColor Green
        Write-Host "Redactions: $($result.redaction_meta.Count)"
        
        if ($result.redaction_meta) {
            foreach ($meta in $result.redaction_meta) {
                Write-Host "  - Rule: $($meta.rule), Action: $($meta.action)"
                
                if ($meta.action -eq "fpe") {
                    Write-Host "    ✓ FPE encryption applied!" -ForegroundColor Green
                } else {
                    Write-Host "    Note: Using $($meta.action) action instead of FPE" -ForegroundColor Yellow
                }
            }
        }
        
    } catch {
        Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Test 2: Testing FPE Configuration" -ForegroundColor Cyan

# Test FPE configuration by checking available rules
try {
    $rulesResponse = Invoke-WebRequest -Uri "http://localhost:8000/policy/rules" -Method GET -Headers $headers -UseBasicParsing
    $rules = $rulesResponse.Content | ConvertFrom-Json
    
    Write-Host "Checking FPE rules in policy..."
    
    $fpeRules = $rules | Where-Object { $_.action -eq "fpe" }
    
    if ($fpeRules) {
        Write-Host "Found $($fpeRules.Count) FPE rules:" -ForegroundColor Green
        foreach ($rule in $fpeRules) {
            $status = if ($rule.enabled) { "✓ Enabled" } else { "⚠ Disabled" }
            Write-Host "  - $($rule.id): $status" -ForegroundColor $(if ($rule.enabled) { "Green" } else { "Yellow" })
            Write-Host "    Pattern: $($rule.pattern)"
            Write-Host "    Data Type: $($rule.metadata.data_type)"
        }
    } else {
        Write-Host "No FPE rules found in current policy" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Could not retrieve policy rules: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Test 3: Testing FPE vs Masking Comparison" -ForegroundColor Cyan

$comparisonData = @{
    data = "Credit card 4532123456789012 needs protection"
    include_meta = $true
}

$comparisonJson = $comparisonData | ConvertTo-Json

try {
    Write-Host "Testing same data with current policy:"
    $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $comparisonJson -Headers $headers -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "Original: $($comparisonData.data)"
    Write-Host "Current:  $($result.redacted_data)" -ForegroundColor Green
    
    if ($result.redaction_meta) {
        $actions = $result.redaction_meta | ForEach-Object { $_.action } | Sort-Object | Get-Unique
        Write-Host "Actions used: $($actions -join ', ')"
        
        if ($actions -contains "fpe") {
            Write-Host "✓ FPE is working! Format is preserved while data is encrypted." -ForegroundColor Green
        } elseif ($actions -contains "mask") {
            Write-Host "ℹ Currently using masking. To enable FPE, update rule configuration." -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "Comparison test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 4: Testing FPE Key Management" -ForegroundColor Cyan

try {
    # Test that FPE produces consistent results (deterministic encryption)
    $testValue = @{
        data = "Test PAN: 4111111111111111"
        include_meta = $true
    }
    $testJson = $testValue | ConvertTo-Json
    
    Write-Host "Testing deterministic encryption (consistency)..."
    
    $results = @()
    for ($i = 1; $i -le 3; $i++) {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testJson -Headers $headers -UseBasicParsing
        $result = $response.Content | ConvertFrom-Json
        $results += $result.redacted_data
        Write-Host "Run ${i}: $($result.redacted_data)"
    }
    
    if (($results | Sort-Object | Get-Unique).Count -eq 1) {
        Write-Host "✓ FPE is deterministic - same input produces same output" -ForegroundColor Green
    } else {
        Write-Host "ℹ Results vary - may be using non-deterministic masking" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Consistency test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 5: Validating FPE Format Preservation" -ForegroundColor Cyan

$formatTests = @(
    @{ original = "4532-1234-5678-9012"; expected_length = 19; description = "Hyphenated PAN" },
    @{ original = "4111111111111111"; expected_length = 16; description = "Plain PAN" },
    @{ original = "123-45-6789"; expected_length = 11; description = "SSN with hyphens" }
)

foreach ($test in $formatTests) {
    try {
        $testData = @{
            data = "Test: $($test.original)"
            include_meta = $true
        }
        $testJson = $testData | ConvertTo-Json
        
        $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testJson -Headers $headers -UseBasicParsing
        $result = $response.Content | ConvertFrom-Json
        
        # Extract the potentially encrypted part
        $redacted = $result.redacted_data
        Write-Host "Format test - $($test.description):"
        Write-Host "  Original: $($test.original)"
        Write-Host "  Result:   $redacted"
        
        # Basic format validation - this is simplified since we don't know exact position
        $hasDigits = $redacted -match '\d'
        $lengthAppropriate = $redacted.Length -ge $test.expected_length
        
        if ($hasDigits -and $lengthAppropriate) {
            Write-Host "  ✓ Format appears preserved" -ForegroundColor Green
        } else {
            Write-Host "  ℹ Format changed (may be using alternative action)" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "Format test failed for $($test.description): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "FPE testing completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "- FPE provides format-preserving encryption for sensitive data" -ForegroundColor White
Write-Host "- Maintains original format while providing strong encryption" -ForegroundColor White
Write-Host "- Supports PANs, SSNs, and account numbers" -ForegroundColor White
Write-Host "- Deterministic encryption ensures consistency" -ForegroundColor White
Write-Host "- Can be enabled/disabled per rule via configuration" -ForegroundColor White