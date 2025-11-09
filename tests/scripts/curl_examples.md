# Curl Commands for Testing Data Redaction Gateway

## Prerequisites
- Server running on `http://localhost:8000`
- API key: `dev-api-key-12345` (from config.yaml)

## 1. Transaction Data Testing

### Basic Transaction Redaction
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "txn_id": "TXN-9876543",
      "account_no": "1234567890",
      "iban": "GB82WEST12345698765432",
      "pan": "5425233430109903",
      "amount": 1500.0,
      "currency": "USD",
      "merchant": "Tech Store Inc",
      "customer_name": "Jane Doe",
      "timestamp": "2025-11-08T14:45:00"
    },
    "include_meta": true
  }'
```

### Transaction Dry-Run (see before/after comparison)
```bash
curl -X POST "http://localhost:8000/redact/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "txn_id": "TXN-9876543",
      "account_no": "1234567890",
      "iban": "GB82WEST12345698765432",
      "pan": "4111111111111111",
      "cvv": "123",
      "amount": 2500.0,
      "currency": "EUR",
      "merchant": "Amazon Web Services Inc",
      "customer_name": "John Smith",
      "customer_email": "john.smith@email.com",
      "timestamp": "2025-11-09T10:30:00"
    }
  }'
```

## 2. Chat/Message Data Testing

### Chat Messages with PII
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": [
      {
        "chat_id": "C12345",
        "timestamp": "2025-11-09T09:15:00",
        "user": "Alice Johnson",
        "message": "Hi, this is Alice Johnson, my card 4111111111111111 expires 12/26"
      },
      {
        "chat_id": "C12346",
        "timestamp": "2025-11-09T09:20:00", 
        "user": "Bob Wilson",
        "message": "My phone number is 555-987-6543, email bob@company.com"
      },
      {
        "chat_id": "C12347",
        "timestamp": "2025-11-09T09:25:00",
        "user": "Support Agent",
        "message": "SSN verification: 123-45-6789, IBAN: DE89370400440532013000"
      }
    ],
    "include_meta": true
  }'
```

## 3. Customer Profile Data

### Customer Information
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "customer_id": "CUST-001",
      "personal_info": {
        "full_name": "Emma Thompson",
        "email": "emma.thompson@gmail.com",
        "phone": "+1-555-123-4567",
        "ssn": "987-65-4321"
      },
      "payment_info": {
        "primary_card": "5555555555554444",
        "backup_card": "378282246310005",
        "bank_account": "9876543210",
        "routing_number": "021000021"
      },
      "address": {
        "street": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "zip": "10001"
      },
      "notes": "Customer called about merchant charge from Microsoft Corp"
    }
  }'
```

## 4. Order/E-commerce Data

### E-commerce Order
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "order_id": "ORD-2025-001",
      "customer": {
        "name": "Michael Davis",
        "email": "mike.davis@outlook.com",
        "phone": "1-800-555-0199"
      },
      "payment": {
        "method": "credit_card",
        "card_number": "6011111111111117",
        "expiry": "03/28",
        "cardholder": "MICHAEL DAVIS"
      },
      "merchant_info": {
        "store_name": "Best Buy Electronics Corp",
        "location": "Store #1234",
        "manager": "Sarah Wilson"
      },
      "items": [
        {"product": "Laptop", "price": 999.99},
        {"product": "Mouse", "price": 29.99}
      ],
      "total": 1029.98
    }
  }'
```

## 5. Financial/Banking Data

### Banking Transaction
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "transaction_type": "wire_transfer",
      "from_account": {
        "holder_name": "Robert Johnson",
        "account_number": "1234567890123456",
        "iban": "US64SVBKUS6S3300958879",
        "bank": "Chase Manhattan Corp"
      },
      "to_account": {
        "holder_name": "Global Tech Solutions Inc",
        "account_number": "9876543210987654",
        "iban": "GB29NWBK60161331926819",
        "bank": "Wells Fargo Bank Corp"
      },
      "amount": 50000.00,
      "currency": "USD",
      "reference": "Invoice payment for services",
      "contact_info": {
        "phone": "555-BANK-001",
        "email": "transfers@bank.com"
      }
    }
  }'
```

## 6. Batch Processing

### Multiple Records at Once
```bash
curl -X POST "http://localhost:8000/redact/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '[
    {
      "data": {
        "user": "Alice Smith",
        "email": "alice@company.com",
        "card": "4000000000000002"
      },
      "include_meta": true
    },
    {
      "data": {
        "user": "Bob Jones", 
        "phone": "555-123-4567",
        "ssn": "123-45-6789"
      },
      "include_meta": true
    },
    {
      "data": {
        "merchant": "Apple Store Inc",
        "transaction": "VISA-1234",
        "amount": 1299.99
      }
    }
  ]'
```

## 7. Health Check & Metrics

### API Health Check
```bash
curl -X GET "http://localhost:8000/health" \
  -H "X-API-Key: dev-api-key-12345"
```

### Redaction Metrics
```bash
curl -X GET "http://localhost:8000/metrics" \
  -H "X-API-Key: dev-api-key-12345"
```

### Policy Information
```bash
curl -X GET "http://localhost:8000/policy" \
  -H "X-API-Key: dev-api-key-12345"
```

## 8. Edge Cases & Error Testing

### Invalid API Key
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{
    "data": {"test": "data"}
  }'
```

### Missing API Key
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"test": "data"}
  }'
```

### Large Payload Test
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "large_text": "This is a large text field containing multiple PII elements: John Doe (john.doe@email.com), phone 555-987-6543, SSN 123-45-6789, credit card 4111111111111111, another person Jane Smith (jane@company.com) with phone 1-800-555-0123, working at Microsoft Corporation, with backup card 5555555555554444 and IBAN GB82WEST12345698765432. Additional merchant references include Apple Inc, Google LLC, Amazon Web Services Corp, and Meta Platforms Inc."
    }
  }'
```

## 9. Different Content Types

### Text-heavy Content
```bash
curl -X POST "http://localhost:8000/redact/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "data": {
      "document_type": "customer_support_transcript",
      "content": "Customer Sarah Johnson called regarding her account. Her email is sarah.j@gmail.com and phone number is 555-234-5678. She mentioned a charge from Netflix Inc on her card ending in 1111. When asked for verification, she provided SSN 987-65-4321. The charge was from Target Corporation for $127.99. Her backup payment method is linked to Wells Fargo Corp account 1234567890."
    }
  }'
```

## Usage Tips

1. **Pretty Print JSON Response**: Add ` | python -m json.tool` to any curl command
2. **Save Response to File**: Add ` > response.json` to save output
3. **Timing**: Add ` -w "@curl-format.txt"` for timing information
4. **Verbose**: Add ` -v` to see full HTTP headers and communication

## Example with Pretty Printing
```bash
curl -X POST "http://localhost:8000/redact/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{"data": {"name": "John Doe", "email": "john@test.com", "card": "4111111111111111"}}' \
  | python -m json.tool
```