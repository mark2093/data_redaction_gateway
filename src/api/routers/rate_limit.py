"""
Rate limit management API endpoints.

Provides endpoints for checking and managing rate limits.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...security.jwt_auth import TokenData, get_current_user
from ...security.rbac import Permission, require_permission, require_any_role, Role
from ...security.rate_limiter import (
    RateLimitStatus,
    get_rate_limiter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rate-limit", tags=["Rate Limiting"])


class RateLimitStatusResponse(BaseModel):
    """Rate limit status response."""
    client_id: str
    requests_in_minute: int
    requests_in_hour: int
    requests_in_day: int
    limit_minute: int
    limit_hour: int
    limit_day: int
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_minute: int
    reset_hour: int
    reset_day: int
    blocked: bool


class RateLimitStatsResponse(BaseModel):
    """Rate limit statistics response."""
    enabled: bool
    limits: dict
    tracked_clients: int
    blocked_clients: int


class BlockClientRequest(BaseModel):
    """Block client request."""
    client_id: str = Field(..., description="Client ID to block")
    duration_seconds: int = Field(300, ge=1, le=86400, description="Block duration in seconds")


@router.get("/status", response_model=RateLimitStatusResponse)
async def get_my_rate_limit_status(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get rate limit status for current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Rate limit status
    """
    rate_limiter = get_rate_limiter()
    client_id = current_user.user_id or current_user.username
    
    allowed, status_info = rate_limiter.check_rate_limit(client_id)
    
    return RateLimitStatusResponse(
        client_id=client_id,
        requests_in_minute=status_info.requests_in_minute,
        requests_in_hour=status_info.requests_in_hour,
        requests_in_day=status_info.requests_in_day,
        limit_minute=status_info.limit_minute,
        limit_hour=status_info.limit_hour,
        limit_day=status_info.limit_day,
        remaining_minute=status_info.remaining_minute,
        remaining_hour=status_info.remaining_hour,
        remaining_day=status_info.remaining_day,
        reset_minute=status_info.reset_minute,
        reset_hour=status_info.reset_hour,
        reset_day=status_info.reset_day,
        blocked=status_info.blocked
    )


@router.get("/status/{client_id}", response_model=RateLimitStatusResponse)
async def get_client_rate_limit_status(
    client_id: str,
    current_user: TokenData = Depends(require_any_role(Role.ADMIN, Role.AUDITOR))
):
    """
    Get rate limit status for specific client (requires admin or auditor role).
    
    Args:
        client_id: Client ID
        current_user: Current authenticated user (with role check)
        
    Returns:
        Rate limit status
    """
    rate_limiter = get_rate_limiter()
    
    allowed, status_info = rate_limiter.check_rate_limit(client_id)
    
    return RateLimitStatusResponse(
        client_id=client_id,
        requests_in_minute=status_info.requests_in_minute,
        requests_in_hour=status_info.requests_in_hour,
        requests_in_day=status_info.requests_in_day,
        limit_minute=status_info.limit_minute,
        limit_hour=status_info.limit_hour,
        limit_day=status_info.limit_day,
        remaining_minute=status_info.remaining_minute,
        remaining_hour=status_info.remaining_hour,
        remaining_day=status_info.remaining_day,
        reset_minute=status_info.reset_minute,
        reset_hour=status_info.reset_hour,
        reset_day=status_info.reset_day,
        blocked=status_info.blocked
    )


@router.get("/stats", response_model=RateLimitStatsResponse)
async def get_rate_limit_stats(
    current_user: TokenData = Depends(require_any_role(Role.ADMIN, Role.AUDITOR))
):
    """
    Get rate limiter statistics (requires admin or auditor role).
    
    Args:
        current_user: Current authenticated user (with role check)
        
    Returns:
        Rate limiter statistics
    """
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats()
    
    return RateLimitStatsResponse(**stats)


@router.post("/block")
async def block_client(
    request: BlockClientRequest,
    current_user: TokenData = Depends(require_permission(Permission.ADMIN_ALL))
):
    """
    Block a client (requires admin permission).
    
    Args:
        request: Block client request
        current_user: Current authenticated user (with admin permission check)
        
    Returns:
        Success message
    """
    rate_limiter = get_rate_limiter()
    
    rate_limiter.block_client(request.client_id, request.duration_seconds)
    
    logger.warning(
        f"Client {request.client_id} blocked for {request.duration_seconds}s by {current_user.username}"
    )
    
    return {
        "message": f"Client {request.client_id} blocked",
        "duration_seconds": request.duration_seconds,
        "blocked_by": current_user.username
    }


@router.post("/unblock/{client_id}")
async def unblock_client(
    client_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ADMIN_ALL))
):
    """
    Unblock a client (requires admin permission).
    
    Args:
        client_id: Client ID to unblock
        current_user: Current authenticated user (with admin permission check)
        
    Returns:
        Success message
    """
    rate_limiter = get_rate_limiter()
    
    rate_limiter.unblock_client(client_id)
    
    logger.info(f"Client {client_id} unblocked by {current_user.username}")
    
    return {
        "message": f"Client {client_id} unblocked",
        "unblocked_by": current_user.username
    }


__all__ = ["router"]
