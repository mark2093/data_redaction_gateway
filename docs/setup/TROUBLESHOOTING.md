# Troubleshooting Guide
## Runtime PII/PCI Data Redaction Gateway

This guide helps resolve common issues during setup and operation.

---

## Installation Issues

### Issue: spaCy model not found

**Error Message:**
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**Solution:**
```powershell
python -m spacy download en_core_web_sm
```

If that fails, try:
```powershell
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl
```

### Issue: Module not found errors

**Error Message:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
Ensure virtual environment is activated and dependencies are installed:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: Virtual environment activation fails

**Error Message:**
```
.\venv\Scripts\Activate.ps1 : File cannot be loaded because running scripts is disabled
```

**Solution:**
Enable script execution (run PowerShell as Administrator):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Runtime Issues

### Issue: Port already in use

**Error Message:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
Use a different port:
```powershell
python -m src.cli serve --port 8001
```

Or find and kill the process using port 8000:
```powershell
# Find process
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Issue: API key authentication fails

**Error Message:**
```
403 Forbidden: Invalid API key
```

**Solution:**
Ensure you're using a valid API key from `.env`:
```bash
curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/health
```

Check `.env` file for configured keys:
```env
API_KEYS=dev-api-key-12345,test-api-key-67890
```

### Issue: Policy file not found

**Error Message:**
```
FileNotFoundError: Policy file not found: input/redaction_rules.yaml
```

**Solution:**
Ensure you're running from the project root directory:
```powershell
cd c:\Users\swapnilj1\Documents\hackathon\data_redaction_gateway
python -m src.cli serve
```

Verify file exists:
```powershell
Test-Path input/redaction_rules.yaml
```

---

## Data Stream Simulator Issues

### Issue: Connection refused

**Error Message:**
```
httpx.ConnectError: [Errno 111] Connection refused
```

**Solution:**
Ensure the server is running:
```powershell
# Terminal 1: Start server
python -m src.cli serve --port 8000

# Terminal 2: Run simulator
python utils/data_stream_simulator.py --mode mixed --count 10
```

### Issue: Timeout errors

**Error Message:**
```
httpx.ReadTimeout: Read timeout
```

**Solution:**
- Check if server is responsive: `curl http://localhost:8000/health`
- Increase simulator timeout (edit `data_stream_simulator.py`)
- Reduce load: use lower `--count` or `--rps`

---

## Performance Issues

### Issue: High latency

**Symptoms:**
- Processing time > 100ms consistently
- Slow response times

**Solutions:**

1. Check metrics:
```powershell
python -m src.cli metrics
```

2. Enable caching (check `.env`):
```env
CACHE_TTL=300
CACHE_SIZE=1000
```

3. Disable NER if not needed (edit `input/redaction_rules.yaml`):
```yaml
- id: NAME_NER
  enabled: false
```

4. Use batch endpoint for multiple records:
```bash
curl -X POST http://localhost:8000/redact/batch
```

### Issue: High memory usage

**Symptoms:**
- Memory consumption growing over time
- Server becomes unresponsive

**Solutions:**

1. Restart the server periodically
2. Reduce cache size in `.env`:
```env
CACHE_SIZE=100
```

3. Limit NER processing by disabling the rule
4. Monitor with:
```powershell
python -m src.cli metrics
```

---

## Data Processing Issues

### Issue: Some PII not being redacted

**Symptoms:**
- Expected redactions not happening
- Inconsistent redaction behavior

**Solutions:**

1. Validate policy:
```powershell
python -m src.cli validate
```

2. Check rule patterns in `input/redaction_rules.yaml`
3. Test with dry-run:
```powershell
python -m src.cli dryrun input/test_order.json
```

4. Enable debug logging (edit `src/main.py`):
```python
logging.basicConfig(level=logging.DEBUG)
```

### Issue: False positives (over-redaction)

**Symptoms:**
- Non-sensitive data being redacted
- Legitimate numbers/text masked

**Solutions:**

1. Adjust regex patterns in `input/redaction_rules.yaml`
2. Add word boundaries (`\b`) to patterns
3. Increase pattern specificity
4. Disable rules that are too aggressive:
```yaml
- id: ACCOUNT_REGEX
  enabled: false
```

### Issue: JSON structure changes after redaction

**Symptoms:**
- Output structure different from input
- Missing fields or changed types

**Solutions:**

This shouldn't happen with the current implementation. If it does:

1. Test with dry-run to compare:
```powershell
python -m src.cli dryrun input/test_order.json
```

2. Check for errors in logs
3. Verify input is valid JSON:
```powershell
Get-Content input/test_order.json | python -m json.tool
```

---

## CLI Issues

### Issue: Rich library not rendering colors

**Symptoms:**
- CLI output shows escape codes instead of colors
- Messy terminal output

**Solutions:**

1. Update terminal (use Windows Terminal instead of cmd.exe)
2. Install/update Rich:
```powershell
pip install --upgrade rich
```

3. Disable colors (set environment variable):
```powershell
$env:NO_COLOR = "1"
python -m src.cli health
```

---

## Testing Issues

### Issue: pytest not found

**Error Message:**
```
pytest: The term 'pytest' is not recognized
```

**Solution:**
Install test dependencies:
```powershell
pip install pytest pytest-asyncio pytest-cov
```

Run tests:
```powershell
pytest tests/test_redaction.py -v
```

### Issue: Tests failing

**Solutions:**

1. Ensure dependencies are installed:
```powershell
pip install -r requirements.txt
```

2. Check if policy file exists:
```powershell
Test-Path input/redaction_rules.yaml
```

3. Run specific test:
```powershell
pytest tests/test_redaction.py::TestLuhnValidator::test_valid_credit_cards -v
```

---

## Configuration Issues

### Issue: .env file not being read

**Symptoms:**
- Default values being used
- Configuration changes not taking effect

**Solutions:**

1. Ensure `.env` file is in project root
2. Check file name (must be exactly `.env`, not `.env.txt`)
3. Restart the server after changes
4. Verify with:
```powershell
Get-Content .env
```

### Issue: YAML parsing errors

**Error Message:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solutions:**

1. Validate YAML syntax:
```powershell
python -c "import yaml; yaml.safe_load(open('input/redaction_rules.yaml'))"
```

2. Check for proper indentation (use spaces, not tabs)
3. Validate with CLI:
```powershell
python -m src.cli validate
```

---

## Network Issues

### Issue: Cannot access API from other machines

**Symptoms:**
- API works on localhost but not from network
- Connection timeout from other machines

**Solutions:**

1. Ensure server binds to 0.0.0.0:
```powershell
python -m src.cli serve --host 0.0.0.0 --port 8000
```

2. Check Windows Firewall:
```powershell
# Add firewall rule
New-NetFirewallRule -DisplayName "Redaction Gateway" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

3. Use machine's IP address:
```bash
curl http://192.168.1.100:8000/health
```

---

## Common Workflow Issues

### Issue: Can't see API documentation

**Solution:**
Navigate to: `http://localhost:8000/docs`

If server is on different port:
```
http://localhost:8001/docs
```

### Issue: How to test without simulator

**Solution:**
Use curl or PowerShell:

```powershell
# PowerShell
$headers = @{"X-API-Key"="dev-api-key-12345"}
$body = @{data=@{email="test@example.com"}} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/redact" -Method Post -Headers $headers -Body $body -ContentType "application/json"

# Or use test files
python -m src.cli redact input/test_order.json
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs**: Server output shows detailed error messages
2. **Run validation**: `python -m src.cli validate`
3. **Test health**: `python -m src.cli health`
4. **Review documentation**: See `USAGE_GUIDE.md`
5. **Check conversation log**: See `conversation.log` for development notes

---

## Quick Diagnostic Commands

Run these to diagnose issues:

```powershell
# 1. Check Python version (need 3.8+)
python --version

# 2. Check if virtual environment is active
Get-Command python

# 3. Check if dependencies are installed
pip list | Select-String -Pattern "fastapi|spacy|pydantic"

# 4. Check if policy file exists
Test-Path input/redaction_rules.yaml

# 5. Validate policy
python -m src.cli validate

# 6. Check server health
python -m src.cli health

# 7. Test redaction locally
python -m src.cli dryrun input/test_order.json

# 8. Check if port is available
netstat -ano | findstr :8000
```

---

## Emergency Reset

If nothing works, start fresh:

```powershell
# 1. Deactivate virtual environment
deactivate

# 2. Remove virtual environment
Remove-Item -Recurse -Force venv

# 3. Run quick start
.\quickstart.ps1

# 4. Test
python -m src.cli serve --port 8000
```

---

**Last Updated:** November 8, 2025
