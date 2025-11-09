"""
API Gateway proxy middleware for intercepting and transforming requests.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
import httpx
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import fnmatch

from ..core.models.proxy import ProxyConfig, RouteConfig, UpstreamService
from ..engines.base import RedactionEngine
from ..policy import get_policy_loader
from ..observability import MetricsCollector

logger = logging.getLogger(__name__)


class ProxyMiddleware:
    """Middleware for proxying requests to upstream services with redaction."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize proxy middleware."""
        self.config = config
        self.metrics = MetricsCollector()
        self.upstream_clients: Dict[str, httpx.AsyncClient] = {}
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup HTTP clients for upstream services."""
        for name, service in self.config.upstream_services.items():
            client_kwargs = {
                "timeout": service.timeout_seconds,
                "verify": service.verify_ssl,
                "headers": service.headers or {}
            }
            
            # Add API key authentication if configured
            if service.api_key_header and service.api_key_value:
                client_kwargs["headers"][service.api_key_header] = service.api_key_value
            
            # Add client certificates for mTLS
            if service.client_cert_path and service.client_key_path:
                client_kwargs["cert"] = (service.client_cert_path, service.client_key_path)
            
            self.upstream_clients[name] = httpx.AsyncClient(**client_kwargs)
            logger.info(f"Configured upstream client for {name}: {service.base_url}")
    
    async def __call__(self, request: Request) -> Optional[Response]:
        """Process request through proxy if route matches."""
        start_time = time.time()
        
        # Check if proxy mode is enabled
        if not self.config.proxy_mode:
            return None  # Let FastAPI handle normally
        
        # Find matching route
        route_config = self._find_matching_route(request)
        if not route_config:
            return None  # No proxy route matches
        
        # Get upstream service
        upstream_service = self.config.upstream_services.get(route_config.upstream_service)
        if not upstream_service:
            logger.error(f"Upstream service not found: {route_config.upstream_service}")
            raise HTTPException(status_code=502, detail="Upstream service not configured")
        
        try:
            # Process request
            response = await self._proxy_request(request, route_config, upstream_service)
            
            # Record metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.record_proxy_request(
                route=route_config.path_pattern,
                upstream=route_config.upstream_service,
                latency=processing_time,
                success=200 <= response.status_code < 400
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Proxy error for {request.url.path}: {e}")
            processing_time = (time.time() - start_time) * 1000
            self.metrics.record_proxy_request(
                route=route_config.path_pattern,
                upstream=route_config.upstream_service,
                latency=processing_time,
                success=False
            )
            raise HTTPException(status_code=502, detail="Upstream service error")
    
    def _find_matching_route(self, request: Request) -> Optional[RouteConfig]:
        """Find matching route configuration for request."""
        method = request.method
        path = str(request.url.path)
        
        for route in self.config.routes:
            if not route.enabled:
                continue
            
            # Check HTTP method
            if method not in [m.value for m in route.methods]:
                continue
            
            # Check path pattern (supports wildcards)
            if fnmatch.fnmatch(path, route.path_pattern):
                logger.debug(f"Route matched: {route.path_pattern} for {method} {path}")
                return route
        
        return None
    
    async def _proxy_request(
        self, 
        request: Request, 
        route_config: RouteConfig, 
        upstream_service: UpstreamService
    ) -> Response:
        """Proxy request to upstream service with redaction."""
        
        # Build upstream URL
        upstream_path = route_config.upstream_path or str(request.url.path)
        upstream_url = urljoin(str(upstream_service.base_url), upstream_path.lstrip('/'))
        
        # Add query parameters
        if request.url.query:
            upstream_url += f"?{request.url.query}"
        
        logger.debug(f"Proxying {request.method} {request.url.path} -> {upstream_url}")
        
        # Get request body
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            request_body = await request.body()
        
        # Redact request if enabled
        redacted_request_body = request_body
        request_redaction_meta = []
        
        if route_config.redact_request and request_body:
            redacted_request_body, request_redaction_meta = await self._redact_body(
                request_body, route_config
            )
        
        # Prepare headers
        headers = await self._prepare_headers(request, route_config, request_redaction_meta)
        
        # Get upstream client
        client = self.upstream_clients[route_config.upstream_service]
        
        # Make upstream request
        try:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                content=redacted_request_body,
                headers=headers,
                timeout=route_config.timeout_override or upstream_service.timeout_seconds
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout calling upstream service: {upstream_url}")
            raise HTTPException(status_code=504, detail="Upstream service timeout")
        except Exception as e:
            logger.error(f"Error calling upstream service {upstream_url}: {e}")
            raise HTTPException(status_code=502, detail="Upstream service error")
        
        # Get response body
        response_body = upstream_response.content
        
        # Redact response if enabled
        redacted_response_body = response_body
        response_redaction_meta = []
        
        if route_config.redact_response and response_body:
            redacted_response_body, response_redaction_meta = await self._redact_body(
                response_body, route_config
            )
        
        # Prepare response headers
        response_headers = self._prepare_response_headers(
            upstream_response.headers, 
            route_config,
            request_redaction_meta + response_redaction_meta
        )
        
        # Create response
        return Response(
            content=redacted_response_body,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type")
        )
    
    async def _redact_body(
        self, 
        body: bytes, 
        route_config: RouteConfig
    ) -> Tuple[bytes, list]:
        """Redact request or response body."""
        try:
            # Try to decode as JSON
            import json
            data = json.loads(body.decode('utf-8'))
            
            # Load policy for route
            policy_loader = get_policy_loader()
            rules = policy_loader.get_rules()
            
            # Filter rules based on route configuration
            if route_config.redaction_policy and route_config.redaction_policy.rules:
                rules = [r for r in rules if r.id in route_config.redaction_policy.rules]
            elif route_config.redaction_policy and route_config.redaction_policy.exclude_rules:
                rules = [r for r in rules if r.id not in route_config.redaction_policy.exclude_rules]
            
            # Apply redaction
            engine = RedactionEngine(rules)
            redacted_data = engine.redact(data)
            redaction_meta = engine.get_redaction_meta()
            
            # Convert back to bytes
            redacted_json = json.dumps(redacted_data, separators=(',', ':')).encode('utf-8')
            
            return redacted_json, redaction_meta
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON or can't decode, return as-is
            logger.debug("Body is not JSON, skipping redaction")
            return body, []
        except Exception as e:
            logger.error(f"Error redacting body: {e}")
            return body, []
    
    async def _prepare_headers(
        self, 
        request: Request, 
        route_config: RouteConfig,
        redaction_meta: list
    ) -> Dict[str, str]:
        """Prepare headers for upstream request."""
        headers = {}
        
        # Copy preserved headers
        for header_name in route_config.preserve_headers:
            if header_name.lower() in request.headers:
                headers[header_name] = request.headers[header_name.lower()]
        
        # Copy content-related headers
        content_headers = ["content-type", "content-encoding", "content-length"]
        for header_name in content_headers:
            if header_name in request.headers:
                headers[header_name] = request.headers[header_name]
        
        # Add redaction headers if enabled
        if self.config.add_redaction_headers:
            policy_loader = get_policy_loader()
            headers["X-Redaction-Policy"] = policy_loader.get_policy_version()
            headers["X-Redacted-Fields"] = str(len(redaction_meta))
        
        # Add correlation ID if configured
        correlation_id = request.headers.get(self.config.correlation_header)
        if correlation_id:
            headers[self.config.correlation_header] = correlation_id
        
        return headers
    
    def _prepare_response_headers(
        self, 
        upstream_headers: Dict[str, str],
        route_config: RouteConfig,
        redaction_meta: list
    ) -> Dict[str, str]:
        """Prepare headers for client response."""
        headers = dict(upstream_headers)
        
        # Add redaction headers if enabled
        if self.config.add_redaction_headers:
            policy_loader = get_policy_loader()
            headers["X-Redaction-Policy"] = policy_loader.get_policy_version()
            headers["X-Policy-Version"] = policy_loader.get_policy_version()
            headers["X-Total-Redactions"] = str(len(redaction_meta))
            
            if redaction_meta:
                fields_affected = list(set([meta.field for meta in redaction_meta]))
                headers["X-Redacted-Fields"] = ",".join(fields_affected)
        
        # Remove hop-by-hop headers
        hop_by_hop = [
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"
        ]
        for header in hop_by_hop:
            headers.pop(header, None)
        
        return headers
    
    async def cleanup(self):
        """Clean up resources."""
        for client in self.upstream_clients.values():
            await client.aclose()


__all__ = ["ProxyMiddleware"]