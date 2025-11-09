"""
Role-Based Access Control (RBAC) implementation.

Provides role and permission management for authorization.
"""
import logging
from typing import List, Set, Optional, Dict, Callable
from enum import Enum
from dataclasses import dataclass, field
from fastapi import HTTPException, Depends, status

from .jwt_auth import TokenData, get_current_user

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    # Redaction operations
    REDACT_READ = "redact:read"
    REDACT_WRITE = "redact:write"
    REDACT_STREAM = "redact:stream"
    
    # Policy management
    POLICY_READ = "policy:read"
    POLICY_WRITE = "policy:write"
    POLICY_DELETE = "policy:delete"
    
    # Metrics and monitoring
    METRICS_READ = "metrics:read"
    METRICS_WRITE = "metrics:write"
    
    # Health checks
    HEALTH_READ = "health:read"
    
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Audit logs
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"
    
    # Admin operations
    ADMIN_ALL = "admin:*"


class Role(str, Enum):
    """System roles."""
    ADMIN = "admin"
    USER = "user"
    READER = "reader"
    SERVICE_ACCOUNT = "service_account"
    AUDITOR = "auditor"


@dataclass
class RoleDefinition:
    """Role definition with permissions."""
    name: str
    description: str
    permissions: Set[str] = field(default_factory=set)
    inherits_from: List[str] = field(default_factory=list)


class RBACManager:
    """Role-Based Access Control manager."""
    
    def __init__(self):
        """Initialize RBAC manager with default roles and permissions."""
        self._roles: Dict[str, RoleDefinition] = {}
        self._setup_default_roles()
    
    def _setup_default_roles(self):
        """Setup default system roles."""
        # Admin role - full access
        self.define_role(
            name=Role.ADMIN,
            description="Administrator with full access",
            permissions={
                Permission.ADMIN_ALL,
                Permission.REDACT_READ,
                Permission.REDACT_WRITE,
                Permission.REDACT_STREAM,
                Permission.POLICY_READ,
                Permission.POLICY_WRITE,
                Permission.POLICY_DELETE,
                Permission.METRICS_READ,
                Permission.METRICS_WRITE,
                Permission.HEALTH_READ,
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.USER_DELETE,
                Permission.AUDIT_READ,
                Permission.AUDIT_WRITE,
            }
        )
        
        # User role - standard operations
        self.define_role(
            name=Role.USER,
            description="Standard user with redaction access",
            permissions={
                Permission.REDACT_READ,
                Permission.REDACT_WRITE,
                Permission.REDACT_STREAM,
                Permission.POLICY_READ,
                Permission.METRICS_READ,
                Permission.HEALTH_READ,
            }
        )
        
        # Reader role - read-only access
        self.define_role(
            name=Role.READER,
            description="Read-only access to redaction and metrics",
            permissions={
                Permission.REDACT_READ,
                Permission.POLICY_READ,
                Permission.METRICS_READ,
                Permission.HEALTH_READ,
            }
        )
        
        # Service account - API access
        self.define_role(
            name=Role.SERVICE_ACCOUNT,
            description="Service account for programmatic access",
            permissions={
                Permission.REDACT_READ,
                Permission.REDACT_WRITE,
                Permission.REDACT_STREAM,
                Permission.HEALTH_READ,
            }
        )
        
        # Auditor role - audit log access
        self.define_role(
            name=Role.AUDITOR,
            description="Auditor with access to logs and metrics",
            permissions={
                Permission.AUDIT_READ,
                Permission.METRICS_READ,
                Permission.POLICY_READ,
                Permission.HEALTH_READ,
            }
        )
    
    def define_role(
        self,
        name: str,
        description: str,
        permissions: Set[str],
        inherits_from: List[str] = None
    ):
        """
        Define a new role or update existing one.
        
        Args:
            name: Role name
            description: Role description
            permissions: Set of permissions
            inherits_from: List of roles to inherit from
        """
        role = RoleDefinition(
            name=name,
            description=description,
            permissions=set(permissions),
            inherits_from=inherits_from or []
        )
        
        # Add inherited permissions
        for parent_role in role.inherits_from:
            if parent_role in self._roles:
                role.permissions.update(self._roles[parent_role].permissions)
        
        self._roles[name] = role
        logger.info(f"Role defined: {name} with {len(role.permissions)} permissions")
    
    def get_role_permissions(self, role_name: str) -> Set[str]:
        """
        Get all permissions for a role.
        
        Args:
            role_name: Role name
            
        Returns:
            Set of permissions
        """
        role = self._roles.get(role_name)
        if not role:
            return set()
        return role.permissions.copy()
    
    def has_permission(
        self,
        user_roles: List[str],
        required_permission: str
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_roles: List of user's roles
            required_permission: Required permission
            
        Returns:
            True if user has permission
        """
        # Get all permissions from all roles
        user_permissions = set()
        for role_name in user_roles:
            user_permissions.update(self.get_role_permissions(role_name))
        
        # Check for admin wildcard
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        # Check for specific permission
        return required_permission in user_permissions
    
    def check_permission(
        self,
        user_roles: List[str],
        required_permission: str
    ):
        """
        Check permission and raise exception if not authorized.
        
        Args:
            user_roles: List of user's roles
            required_permission: Required permission
            
        Raises:
            HTTPException: If user lacks permission
        """
        if not self.has_permission(user_roles, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {required_permission}"
            )
    
    def list_roles(self) -> Dict[str, RoleDefinition]:
        """
        List all defined roles.
        
        Returns:
            Dictionary of role definitions
        """
        return self._roles.copy()


# Singleton instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """
    Get singleton RBAC manager instance.
    
    Returns:
        RBACManager instance
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: str) -> Callable:
    """
    Dependency to require a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user has required permission."""
        rbac = get_rbac_manager()
        rbac.check_permission(current_user.roles, permission)
        return current_user
    
    return permission_checker


def require_role(role: str) -> Callable:
    """
    Dependency to require a specific role.
    
    Args:
        role: Required role
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user has required role."""
        if role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires role '{role}'"
            )
        return current_user
    
    return role_checker


def require_any_role(*roles: str) -> Callable:
    """
    Dependency to require any of the specified roles.
    
    Args:
        roles: Required roles (any)
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user has any of the required roles."""
        if not any(role in current_user.roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of {roles}"
            )
        return current_user
    
    return role_checker


__all__ = [
    "Permission",
    "Role",
    "RoleDefinition",
    "RBACManager",
    "get_rbac_manager",
    "require_permission",
    "require_role",
    "require_any_role",
]
