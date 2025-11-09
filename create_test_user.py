#!/usr/bin/env python3
"""
Quick script to create an admin user in the running server.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.security.jwt_auth import get_jwt_manager
from src.security.rbac import Role

def create_admin_user():
    """Create admin user."""
    jwt_manager = get_jwt_manager()
    
    try:
        # Use shorter password to avoid bcrypt 72-byte limit
        admin = jwt_manager.create_user(
            username="admin",
            password="admin123",  # Simple password for testing
            email="admin@example.com",
            full_name="System Administrator",
            roles=[Role.ADMIN]
        )
        print(f"✓ Created admin user: {admin.username}")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Roles: {admin.roles}")
        print(f"\nYou can now login via:")
        print(f'curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d \'{{"username": "admin", "password": "admin123"}}\'')
        return True
    except ValueError as e:
        print(f"Note: User may already exist - {e}")
        print(f"\nTry logging in with:")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        return False

if __name__ == "__main__":
    create_admin_user()
