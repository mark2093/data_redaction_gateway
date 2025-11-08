# Quick Start Guide for Testing with test_chat.json

## Step 1: Start the Server

Open a PowerShell terminal and run:

```powershell
cd c:\Users\swapnilj1\Documents\hackathon\data_redaction_gateway
python -m src.cli serve --reload
```

Keep this terminal open - the server will run here.

## Step 2: Test with test_chat.json

Open a **NEW** PowerShell terminal and run:

```powershell
cd c:\Users\swapnilj1\Documents\hackathon\data_redaction_gateway
.\test_with_chat.ps1
```

This will process each chat message and show:
- Original message (with PII)
- Redacted message (PII removed/masked)
- What was redacted
- Processing time

## Alternative: Manual Testing

If you prefer to test manually:

```powershell
# In a new terminal (while server is running):
cd c:\Users\swapnilj1\Documents\hackathon\data_redaction_gateway

# Test with a single chat message
$headers = @{
    "X-API-Key" = "dev-api-key-12345"
    "Content-Type" = "application/json"
}

$body = @{
    data = @{
        chat_id = "C12345"
        timestamp = "2025-11-08T09:15:00"
        message = "Hi, this is Alice Johnson, my card 4111111111111111 was declined today."
    }
    include_meta = $true
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method POST -Headers $headers -Body $body

# View results
$response | ConvertTo-Json -Depth 10
```

## What to Expect

The test_chat.json file contains 4 chat messages with:
- ✅ Names (e.g., "Alice Johnson") - will be detected by NER
- ✅ Credit card numbers (e.g., "4111111111111111") - will be detected by Luhn algorithm
- ✅ Phone numbers (e.g., "555-987-6543") - will be detected by regex
- ✅ Email addresses (e.g., "support@customer.com") - will be detected by regex

All PII will be masked or redacted according to the rules in `input/redaction_rules.yaml`.

## Viewing API Documentation

While server is running, open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Try a different port: `python -m src.cli serve --port 8080`

### Connection refused
- Make sure the server is running
- Check the server terminal for errors
- Wait a few seconds after starting before testing

### Permission denied
- Run PowerShell as Administrator
- Or use a different port above 1024
