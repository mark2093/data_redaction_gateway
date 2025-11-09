"""
Enhanced health check API router with detailed diagnostics.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Response
from typing import Dict, Any

from ...core.models.api import HealthResponse
from ...policy import get_policy_loader
from ...config import get_config
from ...observability import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Application state - will be moved to dependency injection
app_start_time = datetime.utcnow()
metrics_collector = MetricsCollector()


@router.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    config = get_config()
    return {
        "service": config.name,
        "version": config.version,
        "environment": config.environment,
        "status": "operational"
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint for load balancers."""
    config = get_config()
    policy_loader = get_policy_loader()
    uptime = (datetime.utcnow() - app_start_time).total_seconds()
    
    return HealthResponse(
        status="healthy",
        version=config.version,
        policy_version=policy_loader.get_policy_version(),
        uptime_seconds=uptime,
        cache_size=policy_loader.get_cache_stats()['size']
    )


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with comprehensive diagnostics.
    
    Returns detailed system status, performance metrics, and component health.
    """
    config = get_config()
    policy_loader = get_policy_loader()
    
    # Get metrics summary
    metrics = metrics_collector.get_summary()
    
    # Component health checks
    components = {
        'policy_loader': {
            'status': 'healthy',
            'version': policy_loader.get_policy_version(),
            'rules_loaded': len(policy_loader.get_rules()),
            'cache_stats': policy_loader.get_cache_stats()
        },
        'llm_judge': {
            'status': 'healthy' if config.llm_judge.enabled else 'disabled',
            'calls_total': metrics.get('judge_calls_total', 0),
            'fallback_rate': metrics.get('judge_fallback_rate', 0)
        },
        'proxy_mode': {
            'status': 'enabled' if hasattr(config, 'proxy') and config.proxy.proxy_mode else 'disabled',
            'metrics': metrics.get('proxy_metrics')
        }
    }
    
    # Overall health status
    health_status = metrics.get('health_status', 'unknown')
    
    return {
        'status': health_status,
        'timestamp': datetime.utcnow().isoformat(),
        'version': config.version,
        'environment': config.environment,
        'uptime_seconds': metrics.get('uptime_seconds', 0),
        'performance': {
            'requests_per_second': metrics.get('requests_per_second', 0),
            'avg_latency_ms': metrics.get('avg_processing_time_ms', 0),
            'p95_latency_ms': metrics.get('p95_latency_ms', 0),
            'p99_latency_ms': metrics.get('p99_latency_ms', 0),
            'error_rate': metrics.get('error_rate', 0)
        },
        'components': components,
        'metrics_summary': {
            'total_requests': metrics.get('total_requests', 0),
            'total_redactions': metrics.get('total_redactions', 0),
            'cache_hit_rate': metrics.get('cache_hit_rate', 0),
            'recent_alerts': metrics.get('recent_alerts', [])
        }
    }


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the application is running, regardless of health status.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the application is ready to serve traffic, 503 otherwise.
    """
    try:
        # Check critical components
        config = get_config()
        policy_loader = get_policy_loader()
        
        # Verify policy is loaded
        if len(policy_loader.get_rules()) == 0:
            return Response(
                content='{"status": "not ready", "reason": "no redaction rules loaded"}',
                status_code=503,
                media_type="application/json"
            )
        
        # Check error rate
        metrics = metrics_collector.get_summary()
        error_rate = metrics.get('error_rate', 0)
        
        if error_rate > 50:  # More than 50% errors
            return Response(
                content=f'{{"status": "not ready", "reason": "high error rate: {error_rate}%"}}',
                status_code=503,
                media_type="application/json"
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "rules_loaded": len(policy_loader.get_rules())
        }
        
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return Response(
            content=f'{{"status": "not ready", "reason": "{str(e)}"}}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    metrics_text = metrics_collector.get_prometheus_metrics()
    return Response(content=metrics_text, media_type="text/plain")


__all__ = ["router"]