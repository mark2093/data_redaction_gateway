"""
Authentication API endpoints.

Provides endpoints for user authentication, token management, and user operations.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, Field

from ...security.jwt_auth import (
    JWTManager,
    Token,
    User,
    TokenData,
    get_jwt_manager,
    get_current_user,
    get_current_active_user,
)
from ...security.rbac import (
    Permission,
    Role,
    require_permission,
    require_role,
)
from ...security.audit import (
    log_auth_event,
    AuditEventType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class CreateUserRequest(BaseModel):
    """Create user request model."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    email: Optional[str] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    roles: list[str] = Field(default_factory=list, description="User roles")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")


class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []
    tenant_id: Optional[str] = None
    disabled: bool = False


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/login", response_model=Token)
async def login(request: Request, credentials: LoginRequest):
    """
    Authenticate user and return access token.
    
    Args:
        request: FastAPI request
        credentials: Login credentials
        
    Returns:
        Access and refresh tokens
    """
    jwt_manager = get_jwt_manager()
    
    try:
        # Authenticate user
        token = jwt_manager.login(credentials.username, credentials.password)
        
        # Log successful login
        log_auth_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            username=credentials.username,
            client_ip=request.client.host,
            success=True,
            message=f"User {credentials.username} logged in successfully"
        )
        
        return token
    
    except HTTPException as e:
        # Log failed login
        log_auth_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            username=credentials.username,
            client_ip=request.client.host,
            success=False,
            message=f"Failed login attempt for user {credentials.username}"
        )
        raise


@router.post("/logout")
async def logout(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Logout user (invalidate token).
    
    Args:
        request: FastAPI request
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # Note: In a production system, you would revoke the token here
    # For now, we just log the event
    
    log_auth_event(
        event_type=AuditEventType.AUTH_LOGOUT,
        user_id=current_user.user_id,
        username=current_user.username,
        client_ip=request.client.host,
        success=True,
        message=f"User {current_user.username} logged out"
    )
    
    return {"message": "Logged out successfully"}


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: CreateUserRequest,
    current_user: TokenData = Depends(require_permission(Permission.USER_WRITE))
):
    """
    Create a new user (requires user:write permission).
    
    Args:
        user_data: User creation data
        current_user: Current authenticated user (with permission check)
        
    Returns:
        Created user
    """
    jwt_manager = get_jwt_manager()
    
    try:
        # Create user
        user = jwt_manager.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            full_name=user_data.full_name,
            roles=user_data.roles,
            tenant_id=user_data.tenant_id
        )
        
        # Log user creation
        log_auth_event(
            event_type=AuditEventType.USER_CREATED,
            user_id=current_user.user_id,
            username=current_user.username,
            success=True,
            message=f"User {user.username} created by {current_user.username}",
            details={"created_user": user.username}
        )
        
        # Return user without password
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            permissions=user.permissions,
            tenant_id=user.tenant_id,
            disabled=user.disabled
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    jwt_manager = get_jwt_manager()
    user = jwt_manager.get_user(current_user.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        permissions=user.permissions,
        tenant_id=user.tenant_id,
        disabled=user.disabled
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: TokenRefreshRequest,
    request: Request
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_request: Refresh token request
        request: FastAPI request
        
    Returns:
        New access token
    """
    jwt_manager = get_jwt_manager()
    
    try:
        # Verify refresh token
        token_data = jwt_manager.verify_token(refresh_request.refresh_token)
        
        # Get user
        user = jwt_manager.get_user(token_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new access token
        new_token_data = {
            "sub": user.username,
            "user_id": user.user_id,
            "roles": user.roles,
            "permissions": user.permissions,
            "tenant_id": user.tenant_id
        }
        
        access_token = jwt_manager.create_access_token(new_token_data)
        
        # Log token refresh
        log_auth_event(
            event_type=AuditEventType.AUTH_TOKEN_CREATED,
            user_id=user.user_id,
            username=user.username,
            client_ip=request.client.host,
            success=True,
            message=f"Token refreshed for user {user.username}"
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=jwt_manager.access_token_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/verify")
async def verify_current_token(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Verify current access token.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Token validity status
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "roles": current_user.roles,
        "tenant_id": current_user.tenant_id
    }


__all__ = ["router"]
