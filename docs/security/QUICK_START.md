# Security Features - Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

### 2. Set Environment Variables
```bash
# Windows PowerShell
$env:JWT_SECRET_KEY="your-super-secret-key-here-change-in-production"

# Linux/Mac
export JWT_SECRET_KEY="your-super-secret-key-here-change-in-production"
```

### 3. Create Test Users
```bash
python tests/scripts/test_security_features.py
```

This creates:
- `admin` / `admin123` (Admin role)
- `user1` / `user123` (User role)
- `service_account` / `service123` (Service Account)
- `auditor` / `auditor123` (Auditor role)

### 4. Start Server
```bash
python main_modular.py
```

## Quick Examples

### Login and Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Use Token for Protected Endpoint
```bash
# Save token
TOKEN="eyJhbGc..."

# Use in request
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Check Rate Limit Status
```bash
curl http://localhost:8000/rate-limit/status \
  -H "Authorization: Bearer $TOKEN"
```

### Query Audit Logs
```bash
curl "http://localhost:8000/audit/events?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

## Protecting Your Endpoints

### Require Authentication
```python
from fastapi import Depends
from src.security.jwt_auth import get_current_user, TokenData

@router.get("/protected")
async def protected_endpoint(
    current_user: TokenData = Depends(get_current_user)
):
    return {"user": current_user.username}
```

### Require Specific Permission
```python
from src.security.rbac import require_permission, Permission

@router.post("/admin-action")
async def admin_action(
    current_user: TokenData = Depends(require_permission(Permission.ADMIN_ALL))
):
    # Only admins can access
    return {"status": "success"}
```

### Require Specific Role
```python
from src.security.rbac import require_role, Role

@router.get("/auditor-only")
async def auditor_endpoint(
    current_user: TokenData = Depends(require_role(Role.AUDITOR))
):
    # Only auditors can access
    return {"status": "success"}
```

## Roles and Permissions

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Admin** | All (15) | System administration |
| **User** | redact:*, policy:read, metrics:read, health:read | Standard API users |
| **Reader** | redact:read, policy:read, metrics:read, health:read | Read-only access |
| **Service Account** | redact:*, health:read | Programmatic access |
| **Auditor** | audit:read, metrics:read, policy:read, health:read | Compliance/monitoring |

## Rate Limits (Default)

| Window | Limit | Burst |
|--------|-------|-------|
| Per Minute | 60 | 10 |
| Per Hour | 1,000 | - |
| Per Day | 10,000 | - |

## Common Tasks

### Create New User (Admin Only)
```bash
curl -X POST http://localhost:8000/auth/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepassword",
    "email": "user@company.com",
    "roles": ["user"]
  }'
```

### Refresh Expired Token
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

### Block Abusive Client (Admin Only)
```bash
curl -X POST http://localhost:8000/rate-limit/block \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "user_123", "duration_seconds": 300}'
```

### Search Audit Logs
```bash
# Failed logins
curl "http://localhost:8000/audit/events?event_type=auth.login.failed" \
  -H "Authorization: Bearer $TOKEN"

# Rate limit violations
curl "http://localhost:8000/audit/events?event_type=security.rate_limit.exceeded" \
  -H "Authorization: Bearer $TOKEN"
```

## Configuration

Edit `config/config.yaml`:

```yaml
security:
  # JWT
  jwt:
    enabled: true
    access_token_expire_minutes: 30
    refresh_token_expire_days: 7
  
  # Rate Limiting
  rate_limit:
    enabled: true
    requests_per_minute: 60
    requests_per_hour: 1000
    requests_per_day: 10000
  
  # Audit Logging
  audit:
    enabled: true
    log_file: "logs/audit.log"
```

## Troubleshooting

### "Not authenticated" Error
- Check if token is included: `-H "Authorization: Bearer TOKEN"`
- Verify token hasn't expired (30 min default)
- Use refresh token to get new access token

### "Permission denied" Error
- Check user's roles: `GET /auth/me`
- Verify endpoint requires permission user has
- Use admin account for testing

### Rate Limit Exceeded (429)
- Check status: `GET /rate-limit/status`
- Wait for reset time or adjust limits in config
- Admin can unblock: `POST /rate-limit/unblock/{client_id}`

### Audit Logs Not Showing
- Verify audit logging is enabled in config
- Check file permissions on `logs/audit.log`
- Query in-memory events: `GET /audit/events`

## Security Best Practices

✅ **DO**:
- Change JWT_SECRET_KEY in production
- Use HTTPS/TLS for all requests
- Rotate tokens regularly
- Monitor audit logs for suspicious activity
- Set appropriate rate limits for your use case
- Use service accounts for API integrations
- Review audit logs regularly

❌ **DON'T**:
- Commit JWT_SECRET_KEY to version control
- Share tokens between users
- Use default passwords in production
- Disable audit logging
- Ignore rate limit violations
- Grant admin role unnecessarily
- Log tokens/passwords

## Production Checklist

- [ ] Set strong JWT_SECRET_KEY
- [ ] Change all default passwords
- [ ] Remove test API keys
- [ ] Configure appropriate rate limits
- [ ] Enable TLS/HTTPS
- [ ] Set up log rotation for audit.log
- [ ] Configure monitoring alerts
- [ ] Document custom roles/permissions
- [ ] Test authentication flow
- [ ] Test rate limiting behavior
- [ ] Verify audit logging works
- [ ] Set up backup for audit logs

## Further Reading

- [Full Documentation](./ADVANCED_SECURITY.md)
- [Implementation Summary](./SECURITY_IMPLEMENTATION_SUMMARY.md)
- [JWT RFC](https://tools.ietf.org/html/rfc7519)
- [RBAC Best Practices](https://en.wikipedia.org/wiki/Role-based_access_control)
