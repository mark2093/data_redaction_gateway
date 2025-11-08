# Configuration Guide

## Overview

The PII/PCI Data Redaction Gateway is now fully **configuration-driven**. All settings are controlled via YAML configuration files, eliminating hardcoded values and enabling easy environment switching without code changes.

## Configuration Files

### Primary Configuration: `config/config.yaml`

This is the main configuration file controlling all aspects of the application:

```yaml
# Application Settings
name: "PII/PCI Data Redaction Gateway"
version: "1.0.0"
environment: "development"  # development, staging, production

# Server Configuration
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  log_level: "INFO"
  timeout_seconds: 30

# Security Configuration
security:
  api_key_header_name: "X-API-Key"
  api_keys:
    - "dev-api-key-12345"
    - "test-api-key-67890"
  hmac_secret: "default-hmac-key-change-in-production"
  # ... more security settings

# Redaction Settings
redaction:
  policy_file: "input/redaction_rules.yaml"
  preserve_structure: true
  show_last_n_chars: 4
  # ... more redaction settings

# And many more sections...
```

### Redaction Rules: `input/redaction_rules.yaml`

Defines the PII/PCI detection rules and actions:

```yaml
version: "1.0"
rules:
  - name: "email"
    pattern: "EMAIL"
    action: "mask"
    description: "Email addresses"
  # ... more rules
```

## Configuration Structure

### Complete Configuration Hierarchy

```
AppConfig
├── name, version, environment
├── server: ServerConfig
│   ├── host, port, workers
│   ├── log_level, timeout_seconds
│   └── cors (enabled, origins)
├── security: SecurityConfig
│   ├── api_key_header_name, api_keys
│   ├── hmac_secret, encryption_key
│   └── tls: TLSConfig
│       ├── enabled, cert_file, key_file
│       └── mtls_enabled, ca_file
├── redaction: RedactionConfig
│   ├── policy_file, preserve_structure
│   ├── show_last_n_chars, case_sensitive
│   ├── validate_checksums
│   ├── ner: NERConfig
│   │   ├── model, confidence_threshold
│   │   └── entity_types
│   └── field_overrides: FieldOverrides
│       ├── exclude_fields
│       └── always_redact_fields
├── cache: CacheConfig
│   ├── enabled, ttl_seconds
│   └── max_size
├── observability: ObservabilityConfig
│   ├── metrics: MetricsConfig
│   └── tracing: TracingConfig
├── logging: LoggingConfig
├── simulator: SimulatorConfig
├── output: OutputConfig
├── llm_judge: LLMJudgeConfig
├── compliance: ComplianceConfig
└── debug: DebugConfig
```

## Environment Variable Overrides

Sensitive configuration values can be overridden using environment variables:

### Supported Environment Variables

```bash
# Security
API_KEYS="prod-key-1,prod-key-2,prod-key-3"
HMAC_SECRET_KEY="your-production-hmac-key-here"
ENCRYPTION_KEY="your-production-encryption-key"

# Server
SERVER_HOST="0.0.0.0"
SERVER_PORT="8080"
SERVER_WORKERS="8"
LOG_LEVEL="WARNING"

# TLS/mTLS
TLS_ENABLED="true"
TLS_CERT_FILE="/path/to/cert.pem"
TLS_KEY_FILE="/path/to/key.pem"
MTLS_ENABLED="true"
MTLS_CA_FILE="/path/to/ca.pem"

# Cache
CACHE_ENABLED="true"
CACHE_TTL_SECONDS="600"
CACHE_MAX_SIZE="200"

# Observability
ENABLE_METRICS="true"
ENABLE_TRACING="true"
TRACING_ENDPOINT="http://jaeger:14268/api/traces"
```

### Environment Variable Priority

1. **Environment variables** (highest priority)
2. **config/config.yaml** values
3. **Default values** in code (fallback)

## Configuration Loader

### Using Configuration in Code

```python
from src.config_loader import get_config

# Get configuration (singleton)
config = get_config()

# Access configuration values
app_name = config.name
server_host = config.server.host
api_keys = config.security.api_keys
ner_model = config.redaction.ner.model
cache_ttl = config.cache.ttl_seconds

# Nested access
exclude_fields = config.redaction.field_overrides.exclude_fields
tls_enabled = config.security.tls.enabled
```

### Configuration Validation

Configuration is automatically validated at application startup:

```python
from src.config_loader import get_config_loader

loader = get_config_loader()
validation_result = loader.validate_config()

if not validation_result['valid']:
    print(f"Configuration errors: {validation_result['errors']}")
```

## Key Configuration Sections

### 1. Redaction Settings

Control how PII/PCI data is detected and redacted:

```yaml
redaction:
  policy_file: "input/redaction_rules.yaml"
  preserve_structure: true  # Keep structure, only redact values
  show_last_n_chars: 4      # Show last N chars for masked values
  case_sensitive: false     # Case-insensitive pattern matching
  validate_checksums: true  # Validate credit card Luhn checksums
  
  # NER Configuration
  ner:
    model: "en_core_web_sm"           # spaCy model
    confidence_threshold: 0.85        # Minimum confidence
    entity_types:                     # Entity types to detect
      - "PERSON"
      - "ORG"
  
  # Field-level overrides
  field_overrides:
    exclude_fields:           # Never redact these fields
      - "order_id"
      - "timestamp"
      - "transaction_id"
    always_redact_fields:     # Always redact, regardless of rules
      - "ssn"
      - "credit_card"
      - "cvv"
```

### 2. Security Configuration

```yaml
security:
  api_key_header_name: "X-API-Key"
  api_keys:
    - "key1"
    - "key2"
  hmac_secret: "change-in-production"
  encryption_key: "change-in-production"
  
  tls:
    enabled: false              # Enable for production
    cert_file: ""
    key_file: ""
    mtls_enabled: false         # Mutual TLS
    ca_file: ""
```

### 3. Cache Configuration

```yaml
cache:
  enabled: true                 # Enable/disable caching
  ttl_seconds: 300             # Cache TTL (5 minutes)
  max_size: 100                # Max cached policy versions
```

### 4. Observability Configuration

```yaml
observability:
  metrics:
    enabled: true
    history_size: 1000
    export_endpoint: ""
  
  tracing:
    enabled: false
    endpoint: ""
    service_name: "pii-redaction-gateway"
    sample_rate: 0.1
```

## Configuration Best Practices

### Development Environment

1. Use default `config/config.yaml` settings
2. Set `environment: "development"`
3. Enable debug mode: `debug.enabled: true`
4. Use development API keys
5. Enable metrics and detailed logging

### Staging Environment

1. Copy `config/config.yaml` to `config/config.staging.yaml`
2. Update `environment: "staging"`
3. Use staging-specific API keys (via env vars)
4. Enable TLS
5. Test with production-like settings

### Production Environment

1. Create `config/config.production.yaml`
2. Set `environment: "production"`
3. **Never commit secrets** - use environment variables:
   ```bash
   export API_KEYS="prod-key-1,prod-key-2"
   export HMAC_SECRET_KEY="secure-hmac-key"
   export ENCRYPTION_KEY="secure-encryption-key"
   ```
4. Enable TLS/mTLS:
   ```yaml
   security:
     tls:
       enabled: true
       cert_file: "/etc/ssl/certs/server.pem"
       key_file: "/etc/ssl/private/server-key.pem"
       mtls_enabled: true
       ca_file: "/etc/ssl/certs/ca.pem"
   ```
5. Increase workers: `workers: 16`
6. Set appropriate log level: `log_level: "WARNING"`
7. Enable tracing for observability

## Loading Different Configurations

### Default Configuration

```bash
# Uses config/config.yaml
python src/cli.py serve
```

### Environment-Specific Configuration

```bash
# Set environment variable to specify config file
export CONFIG_FILE="config/config.production.yaml"
python src/cli.py serve
```

### Override via Environment Variables

```bash
# Override specific settings
export SERVER_PORT=8080
export LOG_LEVEL=DEBUG
export CACHE_ENABLED=false
python src/cli.py serve
```

## Configuration Migration

When migrating from old hardcoded values:

1. **Identify hardcoded values** in your code
2. **Add to config.yaml** in appropriate section
3. **Update code** to use `config.section.setting`
4. **Test** with different config values
5. **Document** new configuration options

## Troubleshooting

### Configuration Not Loading

```bash
# Test configuration loading
python -c "from src.config_loader import get_config; print(get_config())"
```

### Invalid Configuration

```bash
# Validate configuration
python -c "from src.config_loader import get_config_loader; \
loader = get_config_loader(); \
result = loader.validate_config(); \
print(result)"
```

### Environment Variables Not Working

```bash
# Check environment variables
python -c "import os; print({k:v for k,v in os.environ.items() if 'API' in k or 'HMAC' in k})"
```

## Configuration Reference

See `config/config.yaml` for complete configuration reference with comments explaining each setting.

## Benefits of Configuration-Driven Design

✅ **Zero Code Changes**: Switch environments by changing config  
✅ **Flexible**: Easy to add new settings  
✅ **Testable**: Test with different configurations  
✅ **Secure**: Secrets via environment variables  
✅ **Maintainable**: Configuration documented in YAML  
✅ **Type-Safe**: Validated at startup  
✅ **Version Control Friendly**: Separate configs per environment  

---

For questions or issues, refer to the main README.md or TROUBLESHOOTING.md.
