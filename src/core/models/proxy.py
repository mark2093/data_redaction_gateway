"""
Proxy configuration for upstream services routing.
"""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, HttpUrl, validator
from enum import Enum


class ProxyMethod(str, Enum):
    """Supported HTTP methods for proxy routing."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class RedactionPolicy(BaseModel):
    """Redaction policy for specific routes."""
    policy_file: str = "input/redaction_rules.yaml"
    rules: Optional[List[str]] = None  # Specific rule IDs to apply
    exclude_rules: Optional[List[str]] = None  # Rule IDs to exclude
    tenant_id: Optional[str] = None
    region: Optional[str] = None


class UpstreamService(BaseModel):
    """Configuration for upstream service."""
    name: str
    base_url: HttpUrl
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Health check configuration
    health_check_path: str = "/health"
    health_check_interval: int = 30  # seconds
    
    # Security
    headers: Optional[Dict[str, str]] = None
    api_key_header: Optional[str] = None
    api_key_value: Optional[str] = None
    
    # TLS/mTLS
    verify_ssl: bool = True
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    

class RouteConfig(BaseModel):
    """Route-specific configuration."""
    path_pattern: str  # e.g., "/api/v1/users/*"
    methods: List[ProxyMethod] = [ProxyMethod.POST, ProxyMethod.PUT, ProxyMethod.PATCH]
    upstream_service: str  # Reference to UpstreamService.name
    upstream_path: Optional[str] = None  # Path rewrite, default is same as incoming
    
    # Redaction configuration
    redaction_policy: Optional[RedactionPolicy] = None
    
    # Request/Response transformation
    redact_request: bool = True
    redact_response: bool = True
    preserve_headers: List[str] = ["authorization", "x-correlation-id", "x-request-id"]
    
    # Route-specific overrides
    timeout_override: Optional[float] = None
    enabled: bool = True


class ProxyConfig(BaseModel):
    """Main proxy configuration."""
    
    # Proxy server settings
    proxy_mode: bool = False  # Enable proxy mode
    bind_host: str = "0.0.0.0"
    bind_port: int = 8000
    
    # Default policies
    default_redaction_policy: RedactionPolicy = RedactionPolicy()
    
    # Upstream services
    upstream_services: Dict[str, UpstreamService] = {}
    
    # Route configurations
    routes: List[RouteConfig] = []
    
    # Global proxy settings
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    default_timeout: float = 30.0
    enable_health_checks: bool = True
    
    # Headers
    add_redaction_headers: bool = True
    correlation_header: str = "x-correlation-id"
    
    @validator('routes')
    def validate_routes(cls, routes, values):
        """Validate route configurations."""
        if not routes and values.get('proxy_mode', False):
            raise ValueError("Proxy mode requires at least one route configuration")
        
        upstream_services = values.get('upstream_services', {})
        for route in routes:
            if route.upstream_service not in upstream_services:
                raise ValueError(f"Route {route.path_pattern} references unknown upstream service: {route.upstream_service}")
        
        return routes


# Default configuration
def get_default_proxy_config() -> ProxyConfig:
    """Get default proxy configuration with examples."""
    return ProxyConfig(
        proxy_mode=False,
        upstream_services={
            "users_api": UpstreamService(
                name="users_api",
                base_url="http://localhost:3000",
                headers={"User-Agent": "redaction-gateway/1.0"}
            ),
            "payments_api": UpstreamService(
                name="payments_api", 
                base_url="http://localhost:3001",
                api_key_header="X-API-Key",
                api_key_value="${PAYMENTS_API_KEY}"
            )
        },
        routes=[
            RouteConfig(
                path_pattern="/api/v1/users/*",
                methods=[ProxyMethod.POST, ProxyMethod.PUT],
                upstream_service="users_api",
                redaction_policy=RedactionPolicy(
                    rules=["EMAIL_REGEX", "PHONE_REGEX", "FIELD_NAMES"]
                )
            ),
            RouteConfig(
                path_pattern="/api/v1/payments/*", 
                methods=[ProxyMethod.POST],
                upstream_service="payments_api",
                redaction_policy=RedactionPolicy(
                    rules=["LUHN_PAN", "CVV_SPECIFIC", "EMAIL_REGEX"]
                )
            )
        ]
    )


__all__ = [
    "ProxyMethod", 
    "RedactionPolicy", 
    "UpstreamService", 
    "RouteConfig", 
    "ProxyConfig",
    "get_default_proxy_config"
]