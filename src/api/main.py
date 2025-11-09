"""
Main FastAPI application factory and configuration.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_config, get_config_loader
from ..policy import get_policy_loader
from ..proxy import get_proxy_config, validate_proxy_config
from ..middleware.proxy import ProxyMiddleware
from ..middleware.content import content_processing_middleware
from ..observability import MetricsCollector
from ..security.rate_limiter import rate_limit_middleware
from .routers import (
    redaction_router,
    health_router,
    metrics_router,
    policy_router,
    streaming_router,
)

logger = logging.getLogger(__name__)

# Import new security routers
try:
    from .routers.auth import router as auth_router
    from .routers.audit import router as audit_router
    from .routers.rate_limit import router as rate_limit_router
    SECURITY_ROUTERS_AVAILABLE = True
except ImportError:
    SECURITY_ROUTERS_AVAILABLE = False
    logger.warning("Security routers not available - some features disabled")

from .middleware import add_process_time_header, sanitize_logs_middleware

# Application state
app_state: Dict[str, any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    config = get_config()
    logger.info(f"Starting {config.name}...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Version: {config.version}")
    
    # Initialize application state
    app_state.update({
        'start_time': datetime.utcnow(),
        'metrics': MetricsCollector(
            max_history=config.observability.metrics.history_size
        ),
        'config': config
    })
    
    # Load and validate proxy configuration
    proxy_config = get_proxy_config()
    proxy_validation = validate_proxy_config(proxy_config)
    
    if not proxy_validation['valid']:
        logger.error("Proxy configuration validation failed:")
        for error in proxy_validation['errors']:
            logger.error(f"  - {error}")
    
    if proxy_validation['warnings']:
        for warning in proxy_validation['warnings']:
            logger.warning(f"Proxy config warning: {warning}")
    
    # Initialize proxy middleware if enabled
    if proxy_config.proxy_mode:
        proxy_middleware = ProxyMiddleware(proxy_config)
        app_state['proxy_middleware'] = proxy_middleware
        logger.info("Proxy mode enabled - gateway will act as reverse proxy")
    else:
        logger.info("Proxy mode disabled - gateway will act as service only")
    
    policy_loader = get_policy_loader()
    logger.info(f"Loaded policy version: {policy_loader.get_policy_version()}")
    
    # Validate configuration
    config_loader = get_config_loader()
    validation = config_loader.validate_config()
    
    if not validation['valid']:
        logger.error("Configuration validation failed:")
        for error in validation['errors']:
            logger.error(f"  - {error}")
    
    if validation['warnings']:
        logger.warning("Configuration warnings:")
        for warning in validation['warnings']:
            logger.warning(f"  - {warning}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {config.name}...")
    
    # Cleanup proxy middleware
    if 'proxy_middleware' in app_state:
        await app_state['proxy_middleware'].cleanup()
        logger.info("Proxy middleware cleaned up")
    
    # Shutdown
    logger.info(f"Shutting down {config.name}...")


def create_app() -> FastAPI:
    """
    Create FastAPI application with all routes and middleware.
    
    Returns:
        Configured FastAPI application
    """
    # Load configuration
    config = get_config()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.server.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create FastAPI app with configuration
    app = FastAPI(
        title=config.name,
        description="Real-time API gateway for detecting and redacting sensitive PII and PCI data",
        version=config.version,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.middleware("http")(add_process_time_header)
    app.middleware("http")(sanitize_logs_middleware)
    app.middleware("http")(content_processing_middleware)
    
    # Add rate limiting middleware
    app.middleware("http")(rate_limit_middleware)
    
    # Add proxy middleware (highest priority - processes requests first)
    @app.middleware("http")
    async def proxy_middleware(request: Request, call_next):
        """Proxy middleware to intercept and route requests to upstream services."""
        # Check if proxy middleware is configured
        if 'proxy_middleware' in app_state:
            proxy_response = await app_state['proxy_middleware'](request)
            if proxy_response:
                return proxy_response
        
        # If no proxy route matches, continue with normal FastAPI routing
        return await call_next(request)
    
    # Include routers
    app.include_router(health_router)
    app.include_router(redaction_router)
    app.include_router(streaming_router)
    app.include_router(metrics_router)
    app.include_router(policy_router)
    
    # Include security routers if available
    if SECURITY_ROUTERS_AVAILABLE:
        app.include_router(auth_router)
        app.include_router(audit_router)
        app.include_router(rate_limit_router)
        logger.info("Security routers enabled: JWT auth, audit logging, rate limiting")
    
    return app


# Create app instance
app = create_app()


def get_app_state() -> Dict[str, any]:
    """
    Get application state.
    
    Returns:
        Application state dictionary
    """
    return app_state


__all__ = ["create_app", "app", "get_app_state"]