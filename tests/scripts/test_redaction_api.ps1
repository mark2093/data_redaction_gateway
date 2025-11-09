# PowerShell Scripts for Testing Data Redaction Gateway
# These scripts provide easy testing on Windows PowerShell

# Configuration
$BaseUrl = "http://localhost:8000"
$ApiKey = "dev-api-key-12345"

# Common headers
$Headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $ApiKey
}

Write-Host "🚀 Data Redaction Gateway Test Scripts" -ForegroundColor Green
Write-Host "Server: $BaseUrl" -ForegroundColor Yellow
Write-Host "API Key: $ApiKey" -ForegroundColor Yellow
Write-Host ""

# Function to make API calls with error handling
function Invoke-RedactionAPI {
    param(
        [string]$Endpoint,
        [string]$Method = "POST",
        [hashtable]$Body = $null,
        [string]$Description = ""
    )
    
    Write-Host "🔄 Testing: $Description" -ForegroundColor Cyan
    
    try {
        $params = @{
            Uri = "$BaseUrl$Endpoint"
            Method = $Method
            Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body | ConvertTo-Json -Depth 10
        }
        
        $response = Invoke-RestMethod @params
        Write-Host "✅ Success: HTTP 200" -ForegroundColor Green
        Write-Host "Response:" -ForegroundColor White
        $response | ConvertTo-Json -Depth 10 | Write-Host
        Write-Host ("-" * 80) -ForegroundColor Gray
        
        return $response
    }
    catch {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ("-" * 80) -ForegroundColor Gray
        return $null
    }
}

# Test 1: Health Check
Write-Host "1️⃣  Health Check" -ForegroundColor Magenta
Invoke-RedactionAPI -Endpoint "/health" -Method "GET" -Description "API Health Check"

# Test 2: Policy Information  
Write-Host "2️⃣  Policy Information" -ForegroundColor Magenta
Invoke-RedactionAPI -Endpoint "/policy" -Method "GET" -Description "Current Policy Information"

# Test 3: Basic Transaction Redaction
Write-Host "3️⃣  Transaction Data" -ForegroundColor Magenta
$transactionData = @{
    data = @{
        txn_id = "TXN-9876543"
        account_no = "1234567890"
        iban = "GB82WEST12345698765432"
        pan = "5425233430109903"
        amount = 1500.0
        currency = "USD"
        merchant = "Tech Store Inc"
        customer_name = "Jane Doe"
        timestamp = "2025-11-08T14:45:00"
    }
    include_meta = $true
}
Invoke-RedactionAPI -Endpoint "/redact/" -Body $transactionData -Description "Transaction Redaction"

# Test 4: Chat Messages
Write-Host "4️⃣  Chat Messages" -ForegroundColor Magenta
$chatData = @{
    data = @(
        @{
            chat_id = "C12345"
            timestamp = "2025-11-09T09:15:00"
            user = "Alice Johnson"
            message = "Hi, this is Alice Johnson, my card 4111111111111111 expires 12/26"
        },
        @{
            chat_id = "C12346"
            timestamp = "2025-11-09T09:20:00"
            user = "Bob Wilson"
            message = "My phone number is 555-987-6543, email bob@company.com"
        }
    )
    include_meta = $true
}
Invoke-RedactionAPI -Endpoint "/redact/" -Body $chatData -Description "Chat Messages Redaction"

# Test 5: Customer Profile
Write-Host "5️⃣  Customer Profile" -ForegroundColor Magenta
$customerData = @{
    data = @{
        customer_id = "CUST-001"
        personal_info = @{
            full_name = "Emma Thompson"
            email = "emma.thompson@gmail.com"
            phone = "+1-555-123-4567"
            ssn = "987-65-4321"
        }
        payment_info = @{
            primary_card = "5555555555554444"
            backup_card = "378282246310005"
            bank_account = "9876543210"
        }
        notes = "Customer called about merchant charge from Microsoft Corp"
    }
    include_meta = $true
}
Invoke-RedactionAPI -Endpoint "/redact/" -Body $customerData -Description "Customer Profile Redaction"

# Test 6: Dry Run Comparison
Write-Host "6️⃣  Dry Run (Before/After)" -ForegroundColor Magenta
$dryRunData = @{
    data = @{
        user_name = "Michael Davis"
        email = "mike.davis@outlook.com"
        phone = "1-800-555-0199"
        card_number = "6011111111111117"
        merchant_info = "Best Buy Electronics Corp"
        ssn = "123-45-6789"
    }
}
Invoke-RedactionAPI -Endpoint "/redact/dry-run" -Body $dryRunData -Description "Dry Run Redaction"

# Test 7: Large Text Content
Write-Host "7️⃣  Large Text Content" -ForegroundColor Magenta
$largeTextData = @{
    data = @{
        document_type = "support_transcript"
        content = "Customer Sarah Johnson called regarding her account. Her email is sarah.j@gmail.com and phone number is 555-234-5678. She mentioned a charge from Netflix Inc on her card ending in 1111. When asked for verification, she provided SSN 987-65-4321. The charge was from Target Corporation for `$127.99. Her backup payment method is linked to Wells Fargo Corp account 1234567890."
    }
    include_meta = $true
}
Invoke-RedactionAPI -Endpoint "/redact/" -Body $largeTextData -Description "Large Text Redaction"

# Test 8: Metrics Check
Write-Host "8️⃣  Metrics" -ForegroundColor Magenta
Invoke-RedactionAPI -Endpoint "/metrics" -Method "GET" -Description "API Metrics"

# Test 9: Error Cases
Write-Host "9️⃣  Error Testing" -ForegroundColor Magenta

# Test with invalid API key
Write-Host "🔄 Testing: Invalid API Key" -ForegroundColor Cyan
try {
    $invalidHeaders = @{
        "Content-Type" = "application/json"
        "X-API-Key" = "invalid-key-12345"
    }
    
    Invoke-RestMethod -Uri "$BaseUrl/redact/" -Method POST -Headers $invalidHeaders -Body (@{data = @{test = "data"}} | ConvertTo-Json)
}
catch {
    Write-Host "✅ Expected error: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test with missing API key
Write-Host "🔄 Testing: Missing API Key" -ForegroundColor Cyan
try {
    $noKeyHeaders = @{
        "Content-Type" = "application/json"
    }
    
    Invoke-RestMethod -Uri "$BaseUrl/redact/" -Method POST -Headers $noKeyHeaders -Body (@{data = @{test = "data"}} | ConvertTo-Json)
}
catch {
    Write-Host "✅ Expected error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Testing Complete!" -ForegroundColor Green
Write-Host "Check the responses above to verify redaction is working correctly." -ForegroundColor Yellow