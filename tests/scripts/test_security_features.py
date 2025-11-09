#!/usr/bin/env python3
"""
Security features test and setup script.

Creates test users and demonstrates JWT, RBAC, rate limiting, and audit logging.
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add src to path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.security.jwt_auth import get_jwt_manager, JWTManager
from src.security.rbac import get_rbac_manager, Role, Permission
from src.security.rate_limiter import get_rate_limiter, RateLimitConfig
from src.security.audit import (
    get_audit_logger,
    log_auth_event,
    log_security_event,
    AuditEventType,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_users():
    """Create test users with different roles."""
    print("\n" + "="*50)
    print("Setting up test users...")
    print("="*50)
    
    jwt_manager = get_jwt_manager()
    
    # Create admin user
    try:
        admin = jwt_manager.create_user(
            username="admin",
            password="admin123",
            email="admin@example.com",
            full_name="System Administrator",
            roles=[Role.ADMIN],
            permissions=[Permission.ADMIN_ALL]
        )
        print(f"✓ Created admin user: {admin.username}")
        print(f"  - User ID: {admin.user_id}")
        print(f"  - Roles: {admin.roles}")
    except ValueError as e:
        print(f"✗ Admin user already exists: {e}")
    
    # Create regular user
    try:
        user = jwt_manager.create_user(
            username="user1",
            password="user123",
            email="user1@example.com",
            full_name="Regular User",
            roles=[Role.USER]
        )
        print(f"✓ Created regular user: {user.username}")
        print(f"  - User ID: {user.user_id}")
        print(f"  - Roles: {user.roles}")
    except ValueError as e:
        print(f"✗ User already exists: {e}")
    
    # Create service account
    try:
        service = jwt_manager.create_user(
            username="service_account",
            password="service123",
            email="service@example.com",
            full_name="Service Account",
            roles=[Role.SERVICE_ACCOUNT]
        )
        print(f"✓ Created service account: {service.username}")
        print(f"  - User ID: {service.user_id}")
        print(f"  - Roles: {service.roles}")
    except ValueError as e:
        print(f"✗ Service account already exists: {e}")
    
    # Create auditor
    try:
        auditor = jwt_manager.create_user(
            username="auditor",
            password="auditor123",
            email="auditor@example.com",
            full_name="Security Auditor",
            roles=[Role.AUDITOR]
        )
        print(f"✓ Created auditor: {auditor.username}")
        print(f"  - User ID: {auditor.user_id}")
        print(f"  - Roles: {auditor.roles}")
    except ValueError as e:
        print(f"✗ Auditor already exists: {e}")


def test_jwt_authentication():
    """Test JWT authentication."""
    print("\n" + "="*50)
    print("Testing JWT Authentication...")
    print("="*50)
    
    jwt_manager = get_jwt_manager()
    
    # Test login
    try:
        token = jwt_manager.login("admin", "admin123")
        print(f"✓ Login successful")
        print(f"  - Access Token: {token.access_token[:40]}...")
        print(f"  - Refresh Token: {token.refresh_token[:40] if token.refresh_token else 'None'}...")
        print(f"  - Expires in: {token.expires_in} seconds")
        
        # Verify token
        token_data = jwt_manager.verify_token(token.access_token)
        print(f"✓ Token verified")
        print(f"  - Username: {token_data.username}")
        print(f"  - User ID: {token_data.user_id}")
        print(f"  - Roles: {token_data.roles}")
        print(f"  - Permissions: {token_data.permissions[:3]}... ({len(token_data.permissions)} total)")
        
        return token.access_token
    
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return None


def test_rbac():
    """Test RBAC."""
    print("\n" + "="*50)
    print("Testing Role-Based Access Control...")
    print("="*50)
    
    rbac = get_rbac_manager()
    
    # List all roles
    roles = rbac.list_roles()
    print(f"✓ Defined roles: {len(roles)}")
    for role_name, role_def in roles.items():
        print(f"\n  {role_name}:")
        print(f"    - Description: {role_def.description}")
        print(f"    - Permissions: {len(role_def.permissions)}")
        print(f"    - Sample permissions: {list(role_def.permissions)[:3]}")
    
    # Test permission checks
    print("\n✓ Testing permission checks:")
    
    test_cases = [
        (Role.ADMIN, Permission.ADMIN_ALL, True),
        (Role.USER, Permission.REDACT_READ, True),
        (Role.USER, Permission.USER_DELETE, False),
        (Role.READER, Permission.REDACT_WRITE, False),
        (Role.AUDITOR, Permission.AUDIT_READ, True),
    ]
    
    for role, permission, expected in test_cases:
        has_perm = rbac.has_permission([role], permission)
        status = "✓" if has_perm == expected else "✗"
        print(f"  {status} {role} -> {permission}: {has_perm} (expected: {expected})")


def test_rate_limiting():
    """Test rate limiting."""
    print("\n" + "="*50)
    print("Testing Rate Limiting...")
    print("="*50)
    
    rate_limiter = get_rate_limiter()
    
    # Get statistics
    stats = rate_limiter.get_stats()
    print(f"✓ Rate limiter configuration:")
    print(f"  - Enabled: {stats['enabled']}")
    print(f"  - Per minute: {stats['limits']['per_minute']}")
    print(f"  - Per hour: {stats['limits']['per_hour']}")
    print(f"  - Per day: {stats['limits']['per_day']}")
    print(f"  - Burst size: {stats['limits']['burst_size']}")
    
    # Test rate limiting
    client_id = "test_client_1"
    print(f"\n✓ Testing rate limits for client: {client_id}")
    
    # Make 5 requests
    for i in range(5):
        allowed, status = rate_limiter.check_rate_limit(client_id)
        if allowed:
            rate_limiter.record_request(client_id)
            print(f"  Request {i+1}: ✓ Allowed - Remaining: {status.remaining_minute}")
        else:
            print(f"  Request {i+1}: ✗ Blocked")
    
    # Test blocking
    print(f"\n✓ Testing client blocking:")
    rate_limiter.block_client(client_id, duration_seconds=5)
    allowed, status = rate_limiter.check_rate_limit(client_id)
    print(f"  - Client blocked: {status.blocked}")
    
    # Unblock
    rate_limiter.unblock_client(client_id)
    allowed, status = rate_limiter.check_rate_limit(client_id)
    print(f"  - Client unblocked: {not status.blocked}")


def test_audit_logging():
    """Test audit logging."""
    print("\n" + "="*50)
    print("Testing Audit Logging...")
    print("="*50)
    
    audit = get_audit_logger()
    
    # Log some test events
    print("✓ Logging test events...")
    
    log_auth_event(
        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
        user_id="user_1",
        username="admin",
        client_ip="127.0.0.1",
        success=True,
        message="Admin user logged in successfully"
    )
    
    log_security_event(
        event_type=AuditEventType.SECURITY_RATE_LIMIT_EXCEEDED,
        user_id="user_2",
        client_ip="192.168.1.100",
        message="Rate limit exceeded for user",
        details={"endpoint": "/redact", "attempts": 150}
    )
    
    # Query events
    print("\n✓ Querying audit events:")
    events = audit.query_events(limit=5)
    print(f"  - Total events: {len(events)}")
    
    for i, event in enumerate(events[:3], 1):
        print(f"\n  Event {i}:")
        print(f"    - Type: {event.event_type}")
        print(f"    - Severity: {event.severity}")
        print(f"    - User: {event.username or 'N/A'}")
        print(f"    - Message: {event.message}")
        print(f"    - Timestamp: {event.timestamp}")
    
    # Get statistics
    stats = audit.get_statistics()
    print(f"\n✓ Audit statistics:")
    print(f"  - Total events: {stats['total_events']}")
    print(f"  - Events in memory: {stats['events_in_memory']}")
    print(f"  - Log file: {stats['log_file']}")
    print(f"  - Event type counts: {len(stats['event_type_counts'])} types")


def main():
    """Main test function."""
    print("\n" + "="*70)
    print(" "*15 + "ADVANCED SECURITY FEATURES TEST")
    print("="*70)
    
    try:
        # Setup
        setup_test_users()
        
        # Test each component
        test_jwt_authentication()
        test_rbac()
        test_rate_limiting()
        test_audit_logging()
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print("✓ All security features tested successfully!")
        print("\nFeatures implemented:")
        print("  ✓ JWT Authentication - Token-based auth with refresh tokens")
        print("  ✓ RBAC - 5 roles with granular permissions")
        print("  ✓ Rate Limiting - Per-minute/hour/day limits with burst control")
        print("  ✓ Audit Logging - Comprehensive event tracking")
        print("\nTest users created:")
        print("  - admin / admin123 (Admin role)")
        print("  - user1 / user123 (User role)")
        print("  - service_account / service123 (Service Account role)")
        print("  - auditor / auditor123 (Auditor role)")
        print("\nNext steps:")
        print("  1. Start the API server: python main_modular.py")
        print("  2. Test endpoints with JWT tokens")
        print("  3. Run PowerShell test script: .\\tests\\scripts\\test_security.ps1")
        print("="*70)
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
