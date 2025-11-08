"""
Main FastAPI application for PII/PCI Data Redaction Gateway.
Configuration-driven application using YAML settings.
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.models import (
    RedactionRequest,
    RedactionResponse,
    DryRunResponse,
    HealthResponse,
    MetricsResponse
)
from src.redaction_engine import RedactionEngine
from src.policy_loader import get_policy_loader
from src.security import verify_api_key, sanitize_log
from src.metrics import MetricsCollector
from src.config_loader import get_config
from src.llm_judge import get_llm_judge

# Load configuration
app_config = get_config()

# Configure logging from config
logging.basicConfig(
    level=getattr(logging, app_config.server.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application state
app_state = {
    'start_time': datetime.utcnow(),
    'metrics': MetricsCollector(
        max_history=app_config.observability.metrics.history_size
    ),
    'config': app_config
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    logger.info(f"Starting {app_config.name}...")
    logger.info(f"Environment: {app_config.environment}")
    logger.info(f"Version: {app_config.version}")
    
    policy_loader = get_policy_loader()
    logger.info(f"Loaded policy version: {policy_loader.get_policy_version()}")
    
    # Validate configuration
    from src.config_loader import get_config_loader
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
    logger.info(f"Shutting down {app_config.name}...")


# Create FastAPI app with configuration
app = FastAPI(
    title=app_config.name,
    description="Real-time API gateway for detecting and redacting sensitive PII and PCI data",
    version=app_config.version,
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


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time-Ms"] = str(process_time)
    
    # Add policy headers
    policy_loader = get_policy_loader()
    response.headers["X-Redaction-Policy"] = "PII-PCI-Redaction"
    response.headers["X-Policy-Version"] = policy_loader.get_policy_version()
    
    return response


@app.middleware("http")
async def sanitize_logs_middleware(request: Request, call_next):
    """Ensure no PII is logged."""
    # Log sanitized request info
    sanitized_path = sanitize_log(request.url.path)
    logger.info(f"Request: {request.method} {sanitized_path}")
    
    response = await call_next(request)
    return response


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": app_config.name,
        "version": app_config.version,
        "environment": app_config.environment,
        "status": "operational"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    policy_loader = get_policy_loader()
    uptime = (datetime.utcnow() - app_state['start_time']).total_seconds()
    
    return HealthResponse(
        status="healthy",
        version=app_config.version,
        policy_version=policy_loader.get_policy_version(),
        uptime_seconds=uptime,
        cache_size=policy_loader.get_cache_stats()['size']
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get service metrics."""
    metrics = app_state['metrics']
    
    return MetricsResponse(
        total_requests=metrics.total_requests,
        total_redactions=metrics.total_redactions,
        average_latency_ms=metrics.get_average_latency(),
        p95_latency_ms=metrics.get_percentile_latency(95),
        p99_latency_ms=metrics.get_percentile_latency(99),
        cache_hit_rate=metrics.get_cache_hit_rate(),
        redaction_coverage=metrics.get_redaction_coverage(),
        judge_fallback_rate=metrics.judge_fallback_rate
    )


@app.post("/redact", response_model=RedactionResponse, tags=["Redaction"])
async def redact_data(
    request: RedactionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Redact sensitive PII/PCI data from input.
    
    This endpoint processes incoming data and redacts sensitive information
    according to configured policies. Approximately 10-20% of requests are
    sampled for LLM-based validation to ensure redaction quality.
    """
    start_time = time.time()
    
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Store original data for judge (if sampled)
        original_data = request.data
        
        # Perform redaction
        redacted_data = engine.redact(request.data)
        redaction_meta = engine.get_redaction_meta() if request.include_meta else None
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics
        metrics = app_state['metrics']
        metrics.record_request(processing_time)
        metrics.record_redactions(len(redaction_meta) if redaction_meta else 0)
        
        # LLM-as-Judge validation (sampled)
        judge_result = None
        llm_judge = get_llm_judge()
        
        if llm_judge.should_sample() and redaction_meta:
            try:
                judge_result = await llm_judge.validate_redaction(
                    original_data=original_data,
                    redacted_data=redacted_data,
                    redaction_meta=redaction_meta
                )
                
                # Record judge call in metrics
                if judge_result is None:
                    metrics.record_judge_call(fallback=True)
                    logger.info("LLM judge validation fell back to rules-only mode")
                else:
                    metrics.record_judge_call(fallback=False)
                    logger.info(
                        f"LLM judge validation: coverage={judge_result.coverage_complete}, "
                        f"confidence={judge_result.confidence}%"
                    )
                    
            except Exception as judge_error:
                # Gracefully handle judge errors
                logger.error(f"LLM judge error: {judge_error}", exc_info=True)
                metrics.record_judge_call(fallback=True)
                judge_result = None
        
        # Build response
        response = RedactionResponse(
            redacted_data=redacted_data,
            redaction_meta=redaction_meta,
            policy_version=policy_loader.get_policy_version(),
            processing_time_ms=processing_time,
            judge_result=judge_result
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Redaction error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redaction processing failed"
        )


@app.post("/redact/dry-run", response_model=DryRunResponse, tags=["Redaction"])
async def dry_run_redaction(
    request: RedactionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Perform dry-run redaction showing before/after comparison.
    
    This endpoint shows what would be redacted without actually applying the changes.
    Useful for testing and validation.
    """
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Perform redaction
        redacted_data = engine.redact(request.data)
        redaction_meta = engine.get_redaction_meta()
        
        # Calculate diff
        diff = {
            'redaction_count': len(redaction_meta),
            'fields_affected': list(set([meta.field for meta in redaction_meta])),
            'rules_triggered': list(set([meta.rule for meta in redaction_meta]))
        }
        
        # Build response
        response = DryRunResponse(
            original_data=request.data,
            redacted_data=redacted_data,
            diff=diff,
            redaction_meta=redaction_meta,
            policy_version=policy_loader.get_policy_version()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Dry-run error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dry-run processing failed"
        )


@app.post("/redact/batch", tags=["Redaction"])
async def redact_batch(
    requests: list[RedactionRequest],
    api_key: str = Depends(verify_api_key)
):
    """
    Batch redaction endpoint for processing multiple items.
    
    Processes multiple redaction requests in a single API call.
    """
    start_time = time.time()
    
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Process each request
        results = []
        total_redactions = 0
        
        for req in requests:
            redacted_data = engine.redact(req.data)
            redaction_meta = engine.get_redaction_meta() if req.include_meta else None
            
            results.append({
                'redacted_data': redacted_data,
                'redaction_meta': redaction_meta
            })
            
            total_redactions += len(redaction_meta) if redaction_meta else 0
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics
        metrics = app_state['metrics']
        metrics.record_request(processing_time)
        metrics.record_redactions(total_redactions)
        
        return {
            'results': results,
            'total_processed': len(requests),
            'total_redactions': total_redactions,
            'policy_version': policy_loader.get_policy_version(),
            'processing_time_ms': processing_time
        }
        
    except Exception as e:
        logger.error(f"Batch redaction error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch redaction processing failed"
        )


@app.get("/policy/version", tags=["Policy"])
async def get_policy_version(api_key: str = Depends(verify_api_key)):
    """Get current policy version."""
    policy_loader = get_policy_loader()
    
    return {
        'version': policy_loader.get_policy_version(),
        'loaded_at': app_state['start_time'].isoformat(),
        'rule_count': len(policy_loader.get_rules())
    }


@app.post("/policy/reload", tags=["Policy"])
async def reload_policy(api_key: str = Depends(verify_api_key)):
    """Reload policy from YAML file."""
    try:
        policy_loader = get_policy_loader()
        policy = policy_loader.reload_policy()
        
        return {
            'status': 'success',
            'version': policy.version,
            'rule_count': len(policy.rules),
            'reloaded_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Policy reload error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload policy: {str(e)}"
        )


@app.get("/policy/validate", tags=["Policy"])
async def validate_policy(api_key: str = Depends(verify_api_key)):
    """Validate current policy configuration."""
    policy_loader = get_policy_loader()
    validation = policy_loader.validate_policy()
    
    return validation


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
