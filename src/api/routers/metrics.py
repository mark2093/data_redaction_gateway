"""
Enhanced metrics API router with detailed observability endpoints.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query

from ...core.models.api import MetricsResponse
from ...security import verify_api_key
from ...observability import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Monitoring"])

# Global metrics instance (shared singleton)
_metrics = get_metrics_collector()


@router.get("/", response_model=MetricsResponse)
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get basic service metrics (backward compatible)."""
    return MetricsResponse(
        total_requests=_metrics.total_requests,
        total_redactions=_metrics.total_redactions,
        avg_processing_time_ms=_metrics.get_average_latency(),
        p95_latency_ms=_metrics.get_percentile_latency(95),
        p99_latency_ms=_metrics.get_percentile_latency(99),
        cache_hit_rate=_metrics.get_cache_hit_rate(),
        redaction_coverage=_metrics.get_redaction_coverage(),
        judge_fallback_rate=_metrics.judge_fallback_rate,
        judge_calls_total=_metrics.judge_calls,
        judge_fallbacks=_metrics.judge_fallbacks
    )


@router.get("/detailed")
async def get_detailed_metrics(api_key: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """
    Get comprehensive metrics with full observability data.
    
    Includes endpoint breakdowns, rule statistics, error analysis, and alerts.
    """
    return _metrics.get_summary()


@router.get("/endpoints")
async def get_endpoint_metrics(
    api_key: str = Depends(verify_api_key),
    sort_by: Optional[str] = Query("requests", description="Sort by: requests, errors, latency")
) -> Dict[str, Any]:
    """
    Get per-endpoint performance metrics.
    
    Shows request counts, error rates, and latency statistics for each endpoint.
    """
    summary = _metrics.get_summary()
    endpoint_stats = summary.get('endpoint_stats', {})
    
    # Sort endpoints
    if sort_by == "errors":
        sorted_stats = dict(sorted(
            endpoint_stats.items(),
            key=lambda x: x[1].get('errors', 0),
            reverse=True
        ))
    elif sort_by == "latency":
        sorted_stats = dict(sorted(
            endpoint_stats.items(),
            key=lambda x: x[1].get('avg_latency_ms', 0),
            reverse=True
        ))
    else:  # sort by requests
        sorted_stats = dict(sorted(
            endpoint_stats.items(),
            key=lambda x: x[1].get('requests', 0),
            reverse=True
        ))
    
    return {
        'total_endpoints': len(sorted_stats),
        'sort_by': sort_by,
        'endpoints': sorted_stats
    }


@router.get("/rules")
async def get_rule_metrics(
    api_key: str = Depends(verify_api_key),
    min_triggers: Optional[int] = Query(0, description="Minimum trigger count")
) -> Dict[str, Any]:
    """
    Get redaction rule trigger statistics.
    
    Shows which rules are being triggered most frequently and what actions are taken.
    """
    summary = _metrics.get_summary()
    rule_stats = summary.get('rule_stats', {})
    
    # Filter by minimum triggers
    if min_triggers > 0:
        rule_stats = {
            rule_id: stats
            for rule_id, stats in rule_stats.items()
            if stats['total_triggers'] >= min_triggers
        }
    
    return {
        'total_rules': len(rule_stats),
        'min_triggers_filter': min_triggers,
        'rules': rule_stats
    }


@router.get("/alerts")
async def get_recent_alerts(
    api_key: str = Depends(verify_api_key),
    limit: Optional[int] = Query(10, description="Number of recent alerts to return")
) -> Dict[str, Any]:
    """
    Get recent system alerts.
    
    Returns alerts triggered by threshold violations (high latency, error rates, etc.).
    """
    summary = _metrics.get_summary()
    all_alerts = summary.get('recent_alerts', [])
    
    return {
        'total_alerts': len(all_alerts),
        'recent_alerts': all_alerts[-limit:] if all_alerts else []
    }


@router.get("/performance")
async def get_performance_metrics(api_key: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """
    Get real-time performance metrics.
    
    Includes throughput, latency percentiles, and error rates.
    """
    summary = _metrics.get_summary()
    
    return {
        'throughput': {
            'requests_per_second': summary.get('requests_per_second', 0),
            'total_requests': summary.get('total_requests', 0)
        },
        'latency': {
            'avg_ms': summary.get('avg_processing_time_ms', 0),
            'min_ms': summary.get('min_latency_ms', 0),
            'max_ms': summary.get('max_latency_ms', 0),
            'p50_ms': summary.get('p50_latency_ms', 0),
            'p95_ms': summary.get('p95_latency_ms', 0),
            'p99_ms': summary.get('p99_latency_ms', 0)
        },
        'reliability': {
            'error_rate': summary.get('error_rate', 0),
            'total_errors': summary.get('total_errors', 0),
            'health_status': summary.get('health_status', 'unknown')
        }
    }


@router.post("/reset")
async def reset_metrics(api_key: str = Depends(verify_api_key)) -> Dict[str, str]:
    """
    Reset all metrics counters.
    
    WARNING: This will clear all collected metrics data.
    """
    _metrics.reset()
    logger.warning(f"Metrics reset by API key: {api_key[:8]}...")
    
    return {
        'status': 'success',
        'message': 'All metrics have been reset'
    }


__all__ = ["router", "_metrics"]