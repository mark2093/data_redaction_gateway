"""
Security package for authentication and data protection.
"""

from .auth import verify_api_key, get_hmac_key, get_encryption_key, SecurityConfig
from .sanitization import sanitize_log
from .encryption import encrypt_value, decrypt_value
from .jwt_auth import (
    JWTManager,
    TokenData,
    Token,
    User,
    get_jwt_manager,
    get_current_user,
    get_current_active_user,
)
from .rbac import (
    Permission,
    Role,
    RoleDefinition,
    RBACManager,
    get_rbac_manager,
    require_permission,
    require_role,
    require_any_role,
)
from .rate_limiter import (
    RateLimitConfig,
    RateLimitStatus,
    RateLimiter,
    get_rate_limiter,
    rate_limit_middleware,
)
from .audit import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    AuditLogger,
    get_audit_logger,
    log_auth_event,
    log_redaction_event,
    log_security_event,
)

__all__ = [
    # Auth
    "verify_api_key",
    "get_hmac_key", 
    "get_encryption_key",
    "SecurityConfig",
    "sanitize_log",
    "encrypt_value",
    "decrypt_value",
    # JWT
    "JWTManager",
    "TokenData",
    "Token",
    "User",
    "get_jwt_manager",
    "get_current_user",
    "get_current_active_user",
    # RBAC
    "Permission",
    "Role",
    "RoleDefinition",
    "RBACManager",
    "get_rbac_manager",
    "require_permission",
    "require_role",
    "require_any_role",
    # Rate Limiting
    "RateLimitConfig",
    "RateLimitStatus",
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit_middleware",
    # Audit
    "AuditEventType",
    "AuditSeverity",
    "AuditEvent",
    "AuditLogger",
    "get_audit_logger",
    "log_auth_event",
    "log_redaction_event",
    "log_security_event",
]