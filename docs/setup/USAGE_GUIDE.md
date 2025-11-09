# PII/PCI Data Redaction Gateway

**Runtime API Gateway for Real-Time PII/PCI Data Redaction**

A high-performance FastAPI-based service that detects and redacts sensitive Personally Identifiable Information (PII) and Payment Card Industry (PCI) data in real-time. Designed for GDPR and PCI DSS 4.0 compliance.

## 🎯 Features

- **Real-time Detection**: Regex patterns, Luhn algorithm for credit cards, and NER for person names
- **Multiple Redaction Methods**: Masking, tokenization, hashing, and format-preserving encryption
- **Policy-as-Code**: YAML-based configuration with versioning
- **Security**: API key authentication, TLS support, log sanitization
- **Observability**: Metrics, latency tracking, OpenTelemetry-ready
- **Performance**: <100ms overhead, caching for repeated patterns
- **Stream Simulator**: Test tool for generating realistic data streams

## 📋 Requirements

- Python 3.8+
- FastAPI & Uvicorn
- spaCy with en_core_web_sm model
- See `requirements.txt` for full dependencies

## 🚀 Quick Start

### 1. Installation

```powershell
# Clone or navigate to the project directory
cd data_redaction_gateway

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Configuration

```powershell
# Copy environment template
copy .env.sample .env

# Edit .env file with your settings (optional for development)
notepad .env
```

### 3. Start the Server

```powershell
# Using CLI
python -m src.cli serve --host 0.0.0.0 --port 8000

# Or directly with uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## 📡 API Endpoints

### Redaction Endpoint

**POST** `/redact`

Redact sensitive data from input.

```bash
curl -X POST "http://localhost:8000/redact" \
  -H "X-API-Key: dev-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "customer": {
        "email": "john.doe@example.com",
        "credit_card": "4111111111111111"
      }
    },
    "include_meta": true
  }'
```

### Dry-Run Endpoint

**POST** `/redact/dry-run`

Preview redactions without modifying data.

```bash
curl -X POST "http://localhost:8000/redact/dry-run" \
  -H "X-API-Key: dev-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"data": {...}, "include_meta": true}'
```

### Health Check

**GET** `/health`

Check service health and status.

```bash
curl http://localhost:8000/health
```

### Metrics

**GET** `/metrics`

Get service performance metrics.

```bash
curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/metrics
```

## 🧪 Testing with Data Stream Simulator

The simulator generates realistic data with PII/PCI information and sends it to the redaction gateway.

### Basic Usage

```powershell
# Mixed stream (all data types)
python utils/data_stream_simulator.py --mode mixed --count 10

# E-commerce orders
python utils/data_stream_simulator.py --mode order --count 20

# Financial transactions
python utils/data_stream_simulator.py --mode transaction --count 15

# Chat messages
python utils/data_stream_simulator.py --mode chat --count 25
```

### Advanced Options

```powershell
# Custom interval (500ms between requests)
python utils/data_stream_simulator.py --mode mixed --count 50 --interval 500

# Load test (10 RPS for 60 seconds)
python utils/data_stream_simulator.py --mode load --rps 10 --duration 60

# Custom API endpoint
python utils/data_stream_simulator.py --mode mixed --count 10 --url http://localhost:8000 --api-key your-api-key
```

## 🛠️ CLI Tool

### Command-Line Interface

```powershell
# Start server
python -m src.cli serve --port 8000 --reload

# Redact data from file
python -m src.cli redact input/sample.json

# Dry-run (local, no server)
python -m src.cli dryrun input/sample.json -o output/redacted.json

# Check health
python -m src.cli health

# View metrics
python -m src.cli metrics

# Validate policy
python -m src.cli validate
```

## 📝 Sample Input/Output

### Input (Order Data)

```json
{
  "order_id": "ORD-764080",
  "customer": {
    "name": "Cameron Solis",
    "email": "james95@yahoo.com",
    "phone": "881-963-7849",
    "credit_card": "6864478669335443"
  }
}
```

### Output (Redacted)

```json
{
  "order_id": "ORD-764080",
  "customer": {
    "name": "C***********s",
    "email": "j*****5@y****.com",
    "phone": "***-***-7849",
    "credit_card": "************5443"
  },
  "redaction_meta": [
    {"field": "name", "rule": "NAME_NER", "action": "mask"},
    {"field": "email", "rule": "EMAIL_REGEX", "action": "mask"},
    {"field": "phone", "rule": "PHONE_REGEX", "action": "mask"},
    {"field": "credit_card", "rule": "LUHN_PAN", "action": "mask"}
  ]
}
```

## ⚙️ Configuration

### Redaction Rules (input/redaction_rules.yaml)

```yaml
version: "1.3"
effective_date: "2025-10-20"
rules:
  - id: EMAIL_REGEX
    pattern: '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    action: mask
    severity: medium
    tags: [GDPR, PRIVACY]
    enabled: true
```

### Supported Redaction Actions

- **mask**: Replace with asterisks (show last 4 characters)
- **tokenize**: HMAC-based deterministic token
- **hash**: One-way SHA-256 hash
- **encrypt**: Format-preserving encryption (placeholder)

### Supported Detection Methods

- **Regex Patterns**: Email, phone, IBAN, account numbers, SSN
- **Luhn Algorithm**: Credit card validation
- **NER (Named Entity Recognition)**: Person names using spaCy

## 🔒 Security

### API Key Authentication

All endpoints (except `/` and `/health`) require an API key via the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/redact
```

### Environment Variables

```env
API_KEYS=dev-api-key-12345,prod-key-xyz
HMAC_SECRET_KEY=your-secure-key-here
TLS_ENABLED=true
```

### Log Sanitization

All logs are automatically sanitized to prevent PII leakage. Sensitive patterns are replaced with `[REDACTED]`.

## 📊 Observability

### Metrics Available

- Total requests processed
- Total redactions performed
- Average/P95/P99 latency
- Cache hit rate
- Redaction coverage

### Response Headers

- `X-Process-Time-Ms`: Request processing time
- `X-Redaction-Policy`: Policy name
- `X-Policy-Version`: Policy version used

## 🧩 Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  FastAPI Gateway (src/main.py)      │
│  - API Key Auth                     │
│  - Request Validation               │
│  - Response Headers                 │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Redaction Engine                   │
│  (src/redaction_engine.py)          │
│  - Pattern Detection                │
│  - Luhn Validation                  │
│  - NER Processing                   │
│  - Action Application               │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Policy Loader (src/policy_loader.py)│
│  - YAML Parsing                     │
│  - Rule Caching                     │
│  - Version Management               │
└─────────────────────────────────────┘
```

## 🧪 Testing

```powershell
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## 📦 Project Structure

```
data_redaction_gateway/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── redaction_engine.py  # Core redaction logic
│   ├── policy_loader.py     # YAML policy loader
│   ├── security.py          # Authentication & sanitization
│   ├── metrics.py           # Metrics collection
│   └── cli.py               # Command-line interface
├── utils/
│   ├── __init__.py
│   └── data_stream_simulator.py  # Stream simulator
├── input/
│   ├── problem_statement.md
│   ├── redaction_rules.yaml      # Policy configuration
│   └── sample inputs and ouputs.txt
├── config/
│   └── config.yaml
├── tests/
│   └── __init__.py
├── output/
├── requirements.txt
├── .env.sample
├── README.md
└── conversation.log
```

## 🎯 Use Cases

1. **API Gateway**: Deploy as a sidecar service for existing APIs
2. **Data Pipeline**: Process streaming data before storage
3. **Compliance**: Ensure GDPR/PCI DSS compliance
4. **Testing**: Validate redaction rules before production
5. **Audit**: Track redaction operations with metadata

## 🚧 Roadmap

- [ ] LLM-as-Judge integration for validation
- [ ] Redis-based distributed cache
- [ ] Kafka/streaming integration
- [ ] Advanced FPE implementation
- [ ] Multi-language support
- [ ] Web UI dashboard

## 📄 License

This is a hackathon project for educational purposes.

## 🙋 Support

For issues or questions, please refer to the `conversation.log` file for development notes and decisions.

---

**Built for Hackathon: Runtime PII/PCI Data Redaction Gateway**
