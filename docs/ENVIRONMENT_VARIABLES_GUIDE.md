# Environment Variables Configuration Guide

Complete guide for configuring the PII/PCI Data Redaction Gateway using environment variables.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Required Variables](#required-variables)
4. [Optional Variables](#optional-variables)
5. [Secret Generation](#secret-generation)
6. [Deployment Examples](#deployment-examples)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Data Redaction Gateway uses environment variables for all sensitive configuration values. This approach:

- ✅ Prevents hardcoded secrets in version control
- ✅ Enables different configs per environment (dev/staging/prod)
- ✅ Integrates with cloud secret management services
- ✅ Follows 12-factor app methodology
- ✅ Supports containerized deployments

### Configuration Priority

The system loads configuration in this order (later overrides earlier):

1. `config/config.yaml` - Base configuration with defaults
2. `.env` file - Local environment variables (auto-loaded)
3. System environment variables - OS-level variables
4. Runtime overrides - Passed via command line or container orchestration

---

## Quick Start

### 1. Copy Template

```powershell
# PowerShell
Copy-Item .env.example .env
```

```bash
# Bash
cp .env.example .env
```

### 2. Generate Secrets

**PowerShell:**

```powershell
# Generate all secrets
$apiKey1 = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$apiKey2 = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$jwtSecret = [Convert]::ToBase64String((1..64 | ForEach-Object { Get-Random -Maximum 256 }))
$hmacSecret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$encryptionKey = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

Write-Host "API_KEYS=$apiKey1,$apiKey2"
Write-Host "JWT_SECRET_KEY=$jwtSecret"
Write-Host "HMAC_SECRET_KEY=$hmacSecret"
Write-Host "ENCRYPTION_KEY=$encryptionKey"
```

**Bash/Linux/Mac:**

```bash
echo "API_KEYS=$(openssl rand -base64 32),$(openssl rand -base64 32)"
echo "JWT_SECRET_KEY=$(openssl rand -base64 64)"
echo "HMAC_SECRET_KEY=$(openssl rand -base64 32)"
echo "ENCRYPTION_KEY=$(openssl rand -base64 32)"
```

### 3. Edit .env File

Open `.env` and paste the generated values:

```bash
API_KEYS=generated-key-1,generated-key-2
JWT_SECRET_KEY=generated-jwt-secret
HMAC_SECRET_KEY=generated-hmac-secret
ENCRYPTION_KEY=generated-encryption-key
LLM_API_KEY=your-openai-or-anthropic-key
ENVIRONMENT=development
```

### 4. Verify Configuration

```powershell
# Start the server
python main_modular.py

# Check logs for environment variable confirmations
# You should see:
# - "Loaded environment variables from ..."
# - "API keys overridden from environment"
# - "JWT secret key overridden from environment"
# - "HMAC secret overridden from environment"
# - "Encryption key overridden from environment"
```

---

## Required Variables

### API_KEYS

**Purpose:** Authentication keys for API access

**Format:** Comma-separated list of base64-encoded strings

**Example:**
```bash
API_KEYS=abcd1234efgh5678,ijkl9012mnop3456
```

**Generation:**
```powershell
# PowerShell - Generate 2 keys
$key1 = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$key2 = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host "API_KEYS=$key1,$key2"
```

```bash
# Bash - Generate 2 keys
echo "API_KEYS=$(openssl rand -base64 32),$(openssl rand -base64 32)"
```

**Usage:**
- Include in request header: `X-API-Key: your-api-key`
- Different keys per client/service for tracking
- Minimum 32 bytes (256 bits) of entropy

---

### JWT_SECRET_KEY

**Purpose:** Secret key for signing JWT authentication tokens

**Format:** Base64-encoded string (minimum 64 bytes recommended)

**Example:**
```bash
JWT_SECRET_KEY=your-64-byte-base64-encoded-secret-here
```

**Generation:**
```powershell
# PowerShell
$jwtSecret = [Convert]::ToBase64String((1..64 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host "JWT_SECRET_KEY=$jwtSecret"
```

```bash
# Bash
echo "JWT_SECRET_KEY=$(openssl rand -base64 64)"
```

**Security Notes:**
- NEVER reuse across environments
- Rotate every 90 days minimum
- Compromised key allows token forgery

---

### HMAC_SECRET_KEY

**Purpose:** HMAC key for tokenization and data integrity

**Format:** Base64-encoded string (minimum 32 bytes)

**Example:**
```bash
HMAC_SECRET_KEY=your-32-byte-base64-encoded-secret
```

**Generation:**
```powershell
# PowerShell
$hmacSecret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host "HMAC_SECRET_KEY=$hmacSecret"
```

```bash
# Bash
echo "HMAC_SECRET_KEY=$(openssl rand -base64 32)"
```

**Usage:**
- Generates deterministic tokens from sensitive data
- Ensures data hasn't been tampered with
- Critical for reversible redaction

---

### ENCRYPTION_KEY

**Purpose:** Key for Format-Preserving Encryption (FPE)

**Format:** Base64-encoded string (minimum 32 bytes)

**Example:**
```bash
ENCRYPTION_KEY=your-32-byte-base64-encoded-key
```

**Generation:**
```powershell
# PowerShell
$encryptionKey = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host "ENCRYPTION_KEY=$encryptionKey"
```

```bash
# Bash
echo "ENCRYPTION_KEY=$(openssl rand -base64 32)"
```

**Usage:**
- Encrypts data while preserving format
- Required for FPE redaction modes
- Must be consistent for encryption/decryption

---

### LLM_API_KEY

**Purpose:** API key for LLM Judge validation service

**Format:** Provider-specific API key

**Example:**
```bash
# OpenAI
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Anthropic
LLM_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

**Providers:**
- **OpenAI:** Get from https://platform.openai.com/api-keys
- **Anthropic:** Get from https://console.anthropic.com/

**Notes:**
- Required only if `llm_judge.enabled: true` in config.yaml
- Monitor usage and set budget limits
- Different key per environment recommended

---

## Optional Variables

### JWT Configuration

```bash
# Algorithm for JWT signing (default: HS256)
JWT_ALGORITHM=HS256

# Access token expiration in minutes (default: 30)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh token expiration in days (default: 7)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Server Configuration

```bash
# Server bind address (default: 0.0.0.0)
SERVER_HOST=0.0.0.0

# Server port (default: 8000)
SERVER_PORT=8000

# Environment name (default: development)
ENVIRONMENT=production  # development | staging | production
```

### TLS/SSL Configuration

```bash
# Enable TLS/SSL (default: false)
TLS_ENABLED=true

# TLS certificate file path
TLS_CERT_FILE=/path/to/cert.pem

# TLS private key file path
TLS_KEY_FILE=/path/to/key.pem
```

---

## Secret Generation

### Why Cryptographically Secure Secrets?

Using weak or predictable secrets compromises security:

❌ **BAD:**
```bash
JWT_SECRET_KEY=mysecret123
HMAC_SECRET_KEY=password
```

✅ **GOOD:**
```bash
JWT_SECRET_KEY=kJ8vN2pQ9rT5wX1zA4bC6dE8fG0hI3jK5lM7nO9pQ2rS4tU6vW8xY0zA1bC3dE5f
HMAC_SECRET_KEY=hG6jK8lM0nP2qR4sT6uV8wX0yZ1aB3cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5y
```

### Generation Methods

#### Method 1: OpenSSL (Recommended)

Available on Linux, Mac, Git Bash, and WSL:

```bash
# 32-byte (256-bit) key
openssl rand -base64 32

# 64-byte (512-bit) key
openssl rand -base64 64

# Hex format
openssl rand -hex 32
```

#### Method 2: PowerShell

Native Windows solution:

```powershell
# Function to generate secure random base64 string
function New-SecureSecret {
    param([int]$Length = 32)
    $bytes = 1..$Length | ForEach-Object { Get-Random -Maximum 256 }
    [Convert]::ToBase64String($bytes)
}

# Generate keys
$apiKey = New-SecureSecret -Length 32
$jwtSecret = New-SecureSecret -Length 64
$hmacSecret = New-SecureSecret -Length 32
$encryptionKey = New-SecureSecret -Length 32
```

#### Method 3: Python

Cross-platform using Python:

```python
import secrets
import base64

# 32-byte key
print(base64.b64encode(secrets.token_bytes(32)).decode())

# 64-byte key
print(base64.b64encode(secrets.token_bytes(64)).decode())
```

#### Method 4: Online Tools (Use with Caution)

⚠️ **WARNING:** Only use for development/testing, NEVER for production

- https://generate-secret.vercel.app/
- https://www.grc.com/passwords.htm

**Production:** Always generate secrets locally with cryptographically secure methods.

---

## Deployment Examples

### Local Development

**.env file:**
```bash
API_KEYS=dev-key-1,dev-key-2
JWT_SECRET_KEY=dev-jwt-secret-not-for-production
HMAC_SECRET_KEY=dev-hmac-secret
ENCRYPTION_KEY=dev-encryption-key
LLM_API_KEY=sk-proj-dev-key
ENVIRONMENT=development
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
```

**Start server:**
```powershell
python main_modular.py
```

The `.env` file is automatically loaded by the ConfigLoader.

---

### Docker

**Option 1: Environment file**

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main_modular.py"]
```

```bash
# Run with .env file
docker run --env-file .env -p 8000:8000 gateway
```

**Option 2: Individual variables**

```bash
docker run \
  -e API_KEYS=key1,key2 \
  -e JWT_SECRET_KEY=jwt-secret \
  -e HMAC_SECRET_KEY=hmac-secret \
  -e ENCRYPTION_KEY=enc-key \
  -e LLM_API_KEY=llm-key \
  -e ENVIRONMENT=production \
  -p 8000:8000 \
  gateway
```

---

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  gateway:
    build: .
    ports:
      - "8000:8000"
    environment:
      # Load from .env file in same directory
      API_KEYS: ${API_KEYS}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      HMAC_SECRET_KEY: ${HMAC_SECRET_KEY}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      LLM_API_KEY: ${LLM_API_KEY}
      ENVIRONMENT: ${ENVIRONMENT:-production}
    env_file:
      - .env
    restart: unless-stopped
```

```bash
# Start services
docker-compose up -d
```

---

### Kubernetes

**Create secret from .env file:**

```bash
kubectl create secret generic gateway-secrets --from-env-file=.env
```

**Deployment manifest:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redaction-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
      - name: gateway
        image: your-registry/gateway:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: gateway-secrets
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: SERVER_HOST
          value: "0.0.0.0"
        - name: SERVER_PORT
          value: "8000"
```

**Apply:**

```bash
kubectl apply -f deployment.yaml
```

---

### AWS

#### AWS Secrets Manager

**Store secrets:**

```bash
# Create secret
aws secretsmanager create-secret \
  --name gateway/prod/secrets \
  --secret-string '{
    "API_KEYS": "key1,key2",
    "JWT_SECRET_KEY": "jwt-secret",
    "HMAC_SECRET_KEY": "hmac-secret",
    "ENCRYPTION_KEY": "enc-key",
    "LLM_API_KEY": "llm-key"
  }'
```

**Retrieve in application:**

```python
import boto3
import json
import os

def load_secrets_from_aws():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    secret = client.get_secret_value(SecretId='gateway/prod/secrets')
    secrets = json.loads(secret['SecretString'])
    
    for key, value in secrets.items():
        os.environ[key] = value
```

**ECS Task Definition:**

```json
{
  "containerDefinitions": [{
    "name": "gateway",
    "image": "your-registry/gateway:latest",
    "secrets": [
      {
        "name": "API_KEYS",
        "valueFrom": "arn:aws:secretsmanager:region:account:secret:gateway/prod/secrets:API_KEYS::"
      },
      {
        "name": "JWT_SECRET_KEY",
        "valueFrom": "arn:aws:secretsmanager:region:account:secret:gateway/prod/secrets:JWT_SECRET_KEY::"
      }
    ]
  }]
}
```

---

### Azure

#### Azure Key Vault

**Create Key Vault:**

```bash
az keyvault create \
  --name gateway-kv \
  --resource-group gateway-rg \
  --location eastus
```

**Store secrets:**

```bash
az keyvault secret set --vault-name gateway-kv --name API-KEYS --value "key1,key2"
az keyvault secret set --vault-name gateway-kv --name JWT-SECRET-KEY --value "jwt-secret"
az keyvault secret set --vault-name gateway-kv --name HMAC-SECRET-KEY --value "hmac-secret"
az keyvault secret set --vault-name gateway-kv --name ENCRYPTION-KEY --value "enc-key"
```

**Azure App Service:**

```bash
# Link secrets to environment variables
az webapp config appsettings set \
  --resource-group gateway-rg \
  --name gateway-app \
  --settings \
    API_KEYS="@Microsoft.KeyVault(SecretUri=https://gateway-kv.vault.azure.net/secrets/API-KEYS/)" \
    JWT_SECRET_KEY="@Microsoft.KeyVault(SecretUri=https://gateway-kv.vault.azure.net/secrets/JWT-SECRET-KEY/)"
```

---

### Google Cloud Platform

#### GCP Secret Manager

**Create secrets:**

```bash
# API Keys
echo -n "key1,key2" | gcloud secrets create api-keys --data-file=-

# JWT Secret
echo -n "jwt-secret" | gcloud secrets create jwt-secret-key --data-file=-

# HMAC Secret
echo -n "hmac-secret" | gcloud secrets create hmac-secret-key --data-file=-
```

**Cloud Run:**

```bash
gcloud run deploy gateway \
  --image gcr.io/project/gateway:latest \
  --set-secrets="API_KEYS=api-keys:latest,JWT_SECRET_KEY=jwt-secret-key:latest"
```

---

## Security Best Practices

### 1. Secret Management

✅ **DO:**
- Generate secrets with cryptographically secure methods
- Use minimum 256-bit (32-byte) entropy
- Store production secrets in vault services (AWS Secrets Manager, Azure Key Vault, etc.)
- Use different secrets per environment
- Rotate secrets every 90 days (or per compliance requirements)
- Revoke secrets immediately if compromised

❌ **DON'T:**
- Hardcode secrets in code or config files
- Commit `.env` file to version control
- Reuse secrets across environments
- Share secrets via email or chat
- Use weak or predictable secrets

### 2. Environment Isolation

```
Development:   dev-api-key-xxx, weak security, local-only
    ↓
Staging:       staging-api-key-xxx, production-like, isolated
    ↓
Production:    prod-api-key-xxx, maximum security, vault-stored
```

### 3. Access Control

- Limit secret access to minimum required personnel
- Use role-based access control (RBAC)
- Enable audit logging for secret access
- Implement just-in-time (JIT) access
- Require MFA for secret management operations

### 4. Rotation Strategy

**Regular Rotation:**
```bash
# Every 90 days
1. Generate new secrets
2. Update vault/secret manager
3. Deploy new secrets to staging
4. Test thoroughly
5. Deploy to production with zero downtime
6. Revoke old secrets after grace period
```

**Emergency Rotation:**
```bash
# Immediately if compromised
1. Generate new secrets IMMEDIATELY
2. Deploy to all environments
3. Revoke compromised secrets
4. Investigate breach source
5. Review access logs
6. Update incident response docs
```

### 5. Monitoring & Auditing

**Enable logging for:**
- Secret access events
- Failed authentication attempts
- Secret rotation events
- Configuration changes
- API key usage patterns

**Alert on:**
- Multiple failed auth attempts
- Secret access from unknown IPs
- Unusual API key usage patterns
- Secrets approaching rotation deadline

### 6. Zero-Trust Principles

- Never trust, always verify
- Assume breach mentality
- Principle of least privilege
- Defense in depth (multiple security layers)
- Continuous verification

---

## Troubleshooting

### Secrets Not Loading

**Symptom:** Server starts but uses placeholder values

**Check:**

```powershell
# Verify .env file exists
ls .env

# Check file contents (be careful with sensitive data!)
Get-Content .env

# Verify environment variables loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API_KEYS:', os.getenv('API_KEYS'))"
```

**Solutions:**
1. Ensure `.env` file is in project root
2. Check for syntax errors in `.env` file
3. Verify `python-dotenv` is installed: `pip install python-dotenv`
4. Check loader logs for "Loaded environment variables from..."

---

### Authentication Failures

**Symptom:** API returns 401 Unauthorized

**Check:**

```bash
# Test API key
curl -H "X-API-Key: your-key-here" http://localhost:8000/api/health
```

**Solutions:**
1. Verify `API_KEYS` environment variable is set correctly
2. Check for extra spaces or quotes in `.env` file
3. Ensure API key matches exactly (case-sensitive)
4. Check logs for "API keys overridden from environment"
5. Verify API key is in comma-separated list

---

### JWT Token Issues

**Symptom:** Token validation fails or tokens expire immediately

**Check:**

```python
# Verify JWT secret loaded
import os
print("JWT Secret:", os.getenv('JWT_SECRET_KEY')[:10] + "...")  # First 10 chars only

# Check token expiry
import jwt
token = "your-token-here"
decoded = jwt.decode(token, options={"verify_signature": False})
print("Expires:", decoded.get('exp'))
```

**Solutions:**
1. Ensure `JWT_SECRET_KEY` is set and minimum 64 bytes
2. Check `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` setting
3. Verify system time is synchronized (NTP)
4. Don't rotate JWT secret while active tokens exist
5. Check logs for "JWT secret key overridden from environment"

---

### LLM Judge Not Working

**Symptom:** LLM validation doesn't run or fails

**Check:**

```python
# Test LLM API key
import os
import openai

openai.api_key = os.getenv('LLM_API_KEY')
print("API Key set:", bool(openai.api_key))

# Try simple completion
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "test"}]
)
print("LLM accessible:", response.choices[0].message.content)
```

**Solutions:**
1. Set `LLM_API_KEY` environment variable
2. Verify API key is valid (check provider dashboard)
3. Ensure `llm_judge.enabled: true` in config.yaml
4. Check API key has sufficient credits/quota
5. Verify network connectivity to LLM provider
6. Check logs for "LLM API key overridden from environment"

---

### Docker/Container Issues

**Symptom:** Environment variables not available in container

**Check:**

```bash
# Inspect container environment
docker exec <container-id> env | grep API_KEYS

# Check container logs
docker logs <container-id>
```

**Solutions:**
1. Use `--env-file .env` when running docker
2. Or use `-e VAR=value` for each variable
3. In docker-compose, use `env_file:` or `environment:`
4. Ensure `.env` file is accessible to Docker
5. Check file permissions on `.env`
6. Don't mount `.env` in .dockerignore

---

### Kubernetes Secrets Issues

**Symptom:** Pods can't access secrets

**Check:**

```bash
# Verify secret exists
kubectl get secret gateway-secrets

# Check secret contents
kubectl get secret gateway-secrets -o yaml

# Check pod environment
kubectl exec <pod-name> -- env | grep API_KEYS
```

**Solutions:**
1. Ensure secret created: `kubectl create secret generic ...`
2. Verify secret referenced in deployment manifest
3. Check `envFrom.secretRef.name` matches secret name
4. Ensure pod has permission to access secrets
5. Verify secret in same namespace as pod

---

### Permission Denied Errors

**Symptom:** Cannot read .env file or secrets

**Solutions:**

```powershell
# PowerShell - Set file permissions
icacls .env /grant:r "$env:USERNAME:(R)"

# Linux/Mac - Set file permissions
chmod 600 .env  # Owner read/write only
```

---

## Additional Resources

- [12-Factor App - Config](https://12factor.net/config)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)
- [NIST Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Azure Key Vault Best Practices](https://docs.microsoft.com/en-us/azure/key-vault/general/best-practices)

---

## Support

For issues or questions:

1. Check this guide and troubleshooting section
2. Review application logs for error messages
3. Consult main README.md for general setup
4. Check GitHub issues for known problems

---

**Last Updated:** November 9, 2025  
**Version:** 1.0.0
