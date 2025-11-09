"""
Audit log API endpoints.

Provides endpoints for querying and managing audit logs.
"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ...security.jwt_auth import TokenData, get_current_user
from ...security.rbac import Permission, require_permission
from ...security.audit import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    get_audit_logger,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditEventResponse(BaseModel):
    """Audit event response model."""
    timestamp: str
    event_type: str
    severity: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    tenant_id: Optional[str] = None
    client_ip: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    message: str
    details: dict = {}
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None


class AuditQueryResponse(BaseModel):
    """Audit query response."""
    total: int = Field(..., description="Total events returned")
    events: List[AuditEventResponse] = Field(..., description="Audit events")


class AuditStatisticsResponse(BaseModel):
    """Audit statistics response."""
    total_events: int
    events_in_memory: int
    max_memory_events: int
    event_type_counts: dict
    log_file: Optional[str]
    console_output: bool


@router.get("/events", response_model=AuditQueryResponse)
async def query_audit_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
):
    """
    Query audit events (requires audit:read permission).
    
    Args:
        event_type: Filter by event type
        user_id: Filter by user ID
        tenant_id: Filter by tenant ID
        severity: Filter by severity
        limit: Maximum number of events
        current_user: Current authenticated user (with permission check)
        
    Returns:
        Matching audit events
    """
    audit = get_audit_logger()
    
    # Apply tenant isolation if not admin
    if current_user.tenant_id and tenant_id != current_user.tenant_id:
        # Only allow users to see their own tenant's events
        tenant_id = current_user.tenant_id
    
    # Query events
    events = audit.query_events(
        event_type=event_type,
        user_id=user_id,
        tenant_id=tenant_id,
        severity=severity,
        limit=limit
    )
    
    # Convert to response models
    event_responses = [
        AuditEventResponse(
            timestamp=event.timestamp,
            event_type=event.event_type,
            severity=event.severity,
            user_id=event.user_id,
            username=event.username,
            tenant_id=event.tenant_id,
            client_ip=event.client_ip,
            endpoint=event.endpoint,
            method=event.method,
            status_code=event.status_code,
            message=event.message,
            details=event.details,
            request_id=event.request_id,
            session_id=event.session_id,
            resource=event.resource,
            action=event.action,
            result=event.result
        )
        for event in events
    ]
    
    return AuditQueryResponse(
        total=len(event_responses),
        events=event_responses
    )


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
):
    """
    Get audit log statistics (requires audit:read permission).
    
    Args:
        current_user: Current authenticated user (with permission check)
        
    Returns:
        Audit statistics
    """
    audit = get_audit_logger()
    stats = audit.get_statistics()
    
    return AuditStatisticsResponse(**stats)


@router.get("/event-types")
async def get_event_types(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
):
    """
    Get list of available event types (requires audit:read permission).
    
    Args:
        current_user: Current authenticated user (with permission check)
        
    Returns:
        List of event types
    """
    event_types = [e.value for e in AuditEventType]
    
    return {
        "event_types": event_types,
        "total": len(event_types)
    }


@router.get("/severities")
async def get_severities(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
):
    """
    Get list of severity levels (requires audit:read permission).
    
    Args:
        current_user: Current authenticated user (with permission check)
        
    Returns:
        List of severity levels
    """
    severities = [s.value for s in AuditSeverity]
    
    return {
        "severities": severities,
        "total": len(severities)
    }


@router.delete("/events")
async def clear_audit_events(
    current_user: TokenData = Depends(require_permission(Permission.ADMIN_ALL))
):
    """
    Clear audit events from memory (requires admin permission).
    
    Warning: This only clears in-memory events, not the log file.
    
    Args:
        current_user: Current authenticated user (with admin permission check)
        
    Returns:
        Success message
    """
    audit = get_audit_logger()
    audit.clear_events()
    
    logger.warning(f"Audit events cleared by user {current_user.username}")
    
    return {
        "message": "Audit events cleared from memory",
        "note": "Events in log file are preserved"
    }


__all__ = ["router"]
