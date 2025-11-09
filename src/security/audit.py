"""
Audit Logging implementation.

Provides comprehensive audit trail for security-sensitive operations.
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
from collections import deque

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types."""
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_CREATED = "auth.token.created"
    AUTH_TOKEN_REVOKED = "auth.token.revoked"
    AUTH_TOKEN_EXPIRED = "auth.token.expired"
    
    # Authorization events
    AUTHZ_ACCESS_GRANTED = "authz.access.granted"
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    
    # User management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_DISABLED = "user.disabled"
    USER_ENABLED = "user.enabled"
    
    # Redaction operations
    REDACT_REQUEST = "redact.request"
    REDACT_SUCCESS = "redact.success"
    REDACT_FAILED = "redact.failed"
    REDACT_STREAM = "redact.stream"
    
    # Policy management
    POLICY_LOADED = "policy.loaded"
    POLICY_UPDATED = "policy.updated"
    POLICY_DELETED = "policy.deleted"
    
    # Security events
    SECURITY_RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    SECURITY_CLIENT_BLOCKED = "security.client.blocked"
    SECURITY_CLIENT_UNBLOCKED = "security.client.unblocked"
    SECURITY_INVALID_TOKEN = "security.invalid_token"
    SECURITY_INVALID_API_KEY = "security.invalid_api_key"
    
    # Data events
    DATA_ENCRYPTED = "data.encrypted"
    DATA_DECRYPTED = "data.decrypted"
    DATA_TOKENIZED = "data.tokenized"
    DATA_DETOKENIZED = "data.detokenized"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG_CHANGED = "system.config.changed"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""
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
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Audit logging manager."""
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        console_output: bool = True,
        max_memory_events: int = 1000
    ):
        """
        Initialize audit logger.
        
        Args:
            log_file: Path to audit log file
            console_output: Enable console output
            max_memory_events: Maximum events to keep in memory
        """
        self.log_file = log_file
        self.console_output = console_output
        self.max_memory_events = max_memory_events
        
        # In-memory event storage
        self._events: deque = deque(maxlen=max_memory_events)
        self._lock = threading.Lock()
        
        # Statistics
        self._event_counts: Dict[str, int] = {}
        
        # Setup file logging if specified
        if self.log_file:
            self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging."""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(file_handler)
        audit_logger.setLevel(logging.INFO)
    
    def log_event(
        self,
        event_type: str,
        severity: str = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            severity: Event severity
            user_id: User ID
            username: Username
            tenant_id: Tenant ID
            client_ip: Client IP address
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            message: Event message
            details: Additional details
            request_id: Request ID
            session_id: Session ID
            resource: Resource being accessed
            action: Action performed
            result: Result of action
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            tenant_id=tenant_id,
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            message=message,
            details=details or {},
            request_id=request_id,
            session_id=session_id,
            resource=resource,
            action=action,
            result=result
        )
        
        with self._lock:
            # Store in memory
            self._events.append(event)
            
            # Update statistics
            self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1
        
        # Log to file
        if self.log_file:
            audit_logger = logging.getLogger("audit")
            audit_logger.info(event.to_json())
        
        # Log to console
        if self.console_output:
            log_level = self._get_log_level(severity)
            logger.log(
                log_level,
                f"AUDIT: {event_type} - {message}",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "client_ip": client_ip,
                    "endpoint": endpoint
                }
            )
    
    def _get_log_level(self, severity: str) -> int:
        """Map severity to log level."""
        mapping = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.INFO)
    
    def query_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit events.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            tenant_id: Filter by tenant ID
            severity: Filter by severity
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events
            
        Returns:
            List of matching events
        """
        with self._lock:
            events = list(self._events)
        
        # Apply filters
        filtered = []
        for event in events:
            # Event type filter
            if event_type and event.event_type != event_type:
                continue
            
            # User ID filter
            if user_id and event.user_id != user_id:
                continue
            
            # Tenant ID filter
            if tenant_id and event.tenant_id != tenant_id:
                continue
            
            # Severity filter
            if severity and event.severity != severity:
                continue
            
            # Time filters
            event_time = datetime.fromisoformat(event.timestamp)
            if start_time and event_time < start_time:
                continue
            if end_time and event_time > end_time:
                continue
            
            filtered.append(event)
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            total_events = len(self._events)
            event_counts = self._event_counts.copy()
        
        return {
            "total_events": total_events,
            "events_in_memory": total_events,
            "max_memory_events": self.max_memory_events,
            "event_type_counts": event_counts,
            "log_file": self.log_file,
            "console_output": self.console_output
        }
    
    def clear_events(self):
        """Clear all events from memory."""
        with self._lock:
            self._events.clear()
            self._event_counts.clear()
        logger.info("Audit events cleared from memory")


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get singleton audit logger instance.
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        # Default to logs/audit.log
        log_file = "logs/audit.log"
        _audit_logger = AuditLogger(log_file=log_file)
    return _audit_logger


def log_auth_event(
    event_type: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    message: str = "",
    details: Optional[Dict[str, Any]] = None
):
    """
    Log authentication event.
    
    Args:
        event_type: Authentication event type
        user_id: User ID
        username: Username
        client_ip: Client IP
        success: Whether operation was successful
        message: Event message
        details: Additional details
    """
    audit = get_audit_logger()
    severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
    result = "success" if success else "failed"
    
    audit.log_event(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        username=username,
        client_ip=client_ip,
        message=message,
        details=details,
        result=result
    )


def log_redaction_event(
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    fields_redacted: int = 0,
    processing_time_ms: float = 0,
    request_id: Optional[str] = None
):
    """
    Log redaction operation.
    
    Args:
        user_id: User ID
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        fields_redacted: Number of fields redacted
        processing_time_ms: Processing time
        request_id: Request ID
    """
    audit = get_audit_logger()
    
    audit.log_event(
        event_type=AuditEventType.REDACT_REQUEST,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        message=f"Redaction request processed: {fields_redacted} fields redacted",
        details={
            "fields_redacted": fields_redacted,
            "processing_time_ms": processing_time_ms
        },
        request_id=request_id,
        result="success" if status_code and status_code < 400 else "failed"
    )


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    message: str = "",
    details: Optional[Dict[str, Any]] = None
):
    """
    Log security event.
    
    Args:
        event_type: Security event type
        user_id: User ID
        client_ip: Client IP
        message: Event message
        details: Additional details
    """
    audit = get_audit_logger()
    
    audit.log_event(
        event_type=event_type,
        severity=AuditSeverity.WARNING,
        user_id=user_id,
        client_ip=client_ip,
        message=message,
        details=details
    )


__all__ = [
    "AuditEventType",
    "AuditSeverity",
    "AuditEvent",
    "AuditLogger",
    "get_audit_logger",
    "log_auth_event",
    "log_redaction_event",
    "log_security_event",
]
