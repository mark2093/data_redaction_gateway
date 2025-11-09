"""
Enhanced metrics collection and observability utilities.
"""
import time
import logging
from typing import List, Dict, Optional, Any
from collections import deque, defaultdict
from datetime import datetime, timedelta
import statistics
import threading

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Enhanced metrics collector with advanced observability features."""
    
    def __init__(self, max_history: int = 10000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of latency measurements to keep
        """
        self.total_requests = 0
        self.total_redactions = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.judge_fallbacks = 0
        self.judge_calls = 0
        
        # Use deque for efficient FIFO operations
        self.latencies = deque(maxlen=max_history)
        self.start_time = time.time()
        
        # Enhanced metrics
        self._lock = threading.Lock()
        self.error_counts = defaultdict(int)
        self.endpoint_metrics = defaultdict(lambda: {
            'count': 0,
            'errors': 0,
            'latencies': deque(maxlen=1000),
            'last_error': None
        })
        self.rule_metrics = defaultdict(lambda: {
            'triggers': 0,
            'actions': defaultdict(int)
        })
        
        # Time-based metrics (per minute)
        self.requests_per_minute = deque(maxlen=60)
        self.errors_per_minute = deque(maxlen=60)
        self.last_minute_update = datetime.utcnow()
        
        # Alerting thresholds
        self.thresholds = {
            'latency_p95_ms': 1000,  # Alert if P95 > 1 second
            'error_rate': 5.0,  # Alert if error rate > 5%
            'cache_hit_rate': 80.0,  # Alert if cache hit rate < 80%
        }
        
        # Alert history
        self.alerts = deque(maxlen=100)
        
        logger.info("Enhanced metrics collector initialized")
    
    def record_request(self, latency_ms: float, endpoint: Optional[str] = None, error: Optional[str] = None):
        """
        Record a request with enhanced tracking.
        
        Args:
            latency_ms: Request latency in milliseconds
            endpoint: API endpoint path
            error: Error message if request failed
        """
        with self._lock:
            self.total_requests += 1
            self.latencies.append(latency_ms)
            
            # Update time-based metrics
            self._update_time_metrics()
            
            # Track per-endpoint metrics
            if endpoint:
                self.endpoint_metrics[endpoint]['count'] += 1
                self.endpoint_metrics[endpoint]['latencies'].append(latency_ms)
                
                if error:
                    self.endpoint_metrics[endpoint]['errors'] += 1
                    self.endpoint_metrics[endpoint]['last_error'] = {
                        'message': error,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    self.error_counts[error] += 1
                    self._check_alert_conditions()
    
    def record_rule_trigger(self, rule_id: str, action: str):
        """
        Record a rule trigger.
        
        Args:
            rule_id: Rule identifier
            action: Action taken (mask, fpe, hash, etc.)
        """
        with self._lock:
            self.rule_metrics[rule_id]['triggers'] += 1
            self.rule_metrics[rule_id]['actions'][action] += 1
    
    def _update_time_metrics(self):
        """Update time-based rolling metrics."""
        current_time = datetime.utcnow()
        
        # Check if a minute has passed
        if (current_time - self.last_minute_update).total_seconds() >= 60:
            # Push current minute's request count
            minute_requests = self.total_requests - sum(self.requests_per_minute)
            self.requests_per_minute.append(minute_requests)
            
            # Update error tracking
            total_errors = sum(self.error_counts.values())
            minute_errors = total_errors - sum(self.errors_per_minute)
            self.errors_per_minute.append(minute_errors)
            
            self.last_minute_update = current_time
    
    def _check_alert_conditions(self):
        """Check if any alert thresholds have been exceeded."""
        # Check latency threshold
        p95 = self.get_percentile_latency(95)
        if p95 > self.thresholds['latency_p95_ms']:
            self._record_alert(
                'high_latency',
                f"P95 latency ({p95:.2f}ms) exceeds threshold ({self.thresholds['latency_p95_ms']}ms)"
            )
        
        # Check error rate
        error_rate = self.get_error_rate()
        if error_rate > self.thresholds['error_rate']:
            self._record_alert(
                'high_error_rate',
                f"Error rate ({error_rate:.2f}%) exceeds threshold ({self.thresholds['error_rate']}%)"
            )
        
        # Check cache hit rate
        cache_hit_rate = self.get_cache_hit_rate()
        if cache_hit_rate > 0 and cache_hit_rate < self.thresholds['cache_hit_rate']:
            self._record_alert(
                'low_cache_hit_rate',
                f"Cache hit rate ({cache_hit_rate:.2f}%) below threshold ({self.thresholds['cache_hit_rate']}%)"
            )
    
    def _record_alert(self, alert_type: str, message: str):
        """Record an alert."""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.alerts.append(alert)
        logger.warning(f"ALERT [{alert_type}]: {message}")
    
    def get_error_rate(self) -> float:
        """
        Calculate error rate.
        
        Returns:
            Error rate as percentage (0-100)
        """
        if self.total_requests == 0:
            return 0.0
        
        total_errors = sum(self.error_counts.values())
        return (total_errors / self.total_requests) * 100
    
    def get_requests_per_second(self) -> float:
        """
        Calculate current requests per second.
        
        Returns:
            Requests per second (averaged over last minute)
        """
        if not self.requests_per_minute:
            return 0.0
        
        # Average over available minutes
        return sum(self.requests_per_minute) / len(self.requests_per_minute) / 60
    
    def record_redactions(self, count: int):
        """
        Record redactions performed.
        
        Args:
            count: Number of redactions
        """
        self.total_redactions += count
    
    def record_proxy_request(self, route: str, upstream: str, latency: float, success: bool):
        """
        Record proxy request metrics.
        
        Args:
            route: Route pattern that was matched
            upstream: Upstream service name
            latency: Request latency in milliseconds
            success: Whether the request was successful
        """
        self.total_requests += 1
        self.latencies.append(latency)
        
        # Initialize proxy metrics if not exists
        if not hasattr(self, 'proxy_metrics'):
            self.proxy_metrics = {
                'routes': {},
                'upstreams': {},
                'success_count': 0,
                'error_count': 0
            }
        
        # Record route metrics
        if route not in self.proxy_metrics['routes']:
            self.proxy_metrics['routes'][route] = {'count': 0, 'latencies': deque(maxlen=1000)}
        self.proxy_metrics['routes'][route]['count'] += 1
        self.proxy_metrics['routes'][route]['latencies'].append(latency)
        
        # Record upstream metrics
        if upstream not in self.proxy_metrics['upstreams']:
            self.proxy_metrics['upstreams'][upstream] = {'count': 0, 'latencies': deque(maxlen=1000)}
        self.proxy_metrics['upstreams'][upstream]['count'] += 1
        self.proxy_metrics['upstreams'][upstream]['latencies'].append(latency)
        
        # Record success/error
        if success:
            self.proxy_metrics['success_count'] += 1
        else:
            self.proxy_metrics['error_count'] += 1
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1
    
    def record_judge_call(self, fallback: bool = False):
        """
        Record an LLM judge call.
        
        Args:
            fallback: Whether the call resulted in fallback
        """
        self.judge_calls += 1
        if fallback:
            self.judge_fallbacks += 1
    
    def get_average_latency(self) -> float:
        """
        Get average latency.
        
        Returns:
            Average latency in milliseconds
        """
        if not self.latencies:
            return 0.0
        
        return statistics.mean(self.latencies)
    
    def get_percentile_latency(self, percentile: int) -> float:
        """
        Get percentile latency.
        
        Args:
            percentile: Percentile to calculate (e.g., 95, 99)
            
        Returns:
            Latency at specified percentile in milliseconds
        """
        if not self.latencies:
            return 0.0
        
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * (percentile / 100.0))
        
        if index >= len(sorted_latencies):
            index = len(sorted_latencies) - 1
        
        return sorted_latencies[index]
    
    def get_cache_hit_rate(self) -> float:
        """
        Get cache hit rate.
        
        Returns:
            Cache hit rate as percentage (0-100)
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        
        return (self.cache_hits / total) * 100
    
    def get_redaction_coverage(self) -> float:
        """
        Get redaction coverage (redactions per request).
        
        Returns:
            Average number of redactions per request
        """
        if self.total_requests == 0:
            return 0.0
        
        return self.total_redactions / self.total_requests
    
    @property
    def judge_fallback_rate(self) -> float:
        """
        Get LLM judge fallback rate.
        
        Returns:
            Fallback rate as percentage (0-100)
        """
        if self.judge_calls == 0:
            return 0.0
        
        return (self.judge_fallbacks / self.judge_calls) * 100
    
    def get_uptime_seconds(self) -> float:
        """
        Get service uptime.
        
        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time
    
    def get_summary(self) -> dict:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary with all metrics including enhanced observability data
        """
        with self._lock:
            summary = {
                # Basic metrics
                'total_requests': self.total_requests,
                'total_redactions': self.total_redactions,
                'total_errors': sum(self.error_counts.values()),
                
                # Latency metrics
                'avg_processing_time_ms': self.get_average_latency(),
                'p50_latency_ms': self.get_percentile_latency(50),
                'p95_latency_ms': self.get_percentile_latency(95),
                'p99_latency_ms': self.get_percentile_latency(99),
                'min_latency_ms': min(self.latencies) if self.latencies else 0,
                'max_latency_ms': max(self.latencies) if self.latencies else 0,
                
                # Cache metrics
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_hit_rate': self.get_cache_hit_rate(),
                
                # Redaction metrics
                'redaction_coverage': self.get_redaction_coverage(),
                'avg_redactions_per_request': self.get_redaction_coverage(),
                
                # LLM Judge metrics
                'judge_calls_total': self.judge_calls,
                'judge_fallbacks': self.judge_fallbacks,
                'judge_fallback_rate': self.judge_fallback_rate,
                
                # Performance metrics
                'requests_per_second': self.get_requests_per_second(),
                'error_rate': self.get_error_rate(),
                'uptime_seconds': self.get_uptime_seconds(),
                
                # Health status
                'health_status': self._get_health_status(),
                
                # Top errors
                'top_errors': self._get_top_errors(5),
                
                # Endpoint breakdown
                'endpoint_stats': self._get_endpoint_stats(),
                
                # Rule statistics
                'rule_stats': self._get_rule_stats(),
                
                # Recent alerts
                'recent_alerts': list(self.alerts)[-10:] if self.alerts else [],
                
                # Proxy metrics (if available)
                'proxy_metrics': getattr(self, 'proxy_metrics', None)
            }
            
            return summary
    
    def _get_health_status(self) -> str:
        """
        Determine overall health status.
        
        Returns:
            Health status: 'healthy', 'degraded', or 'unhealthy'
        """
        error_rate = self.get_error_rate()
        p95_latency = self.get_percentile_latency(95)
        
        # Unhealthy conditions
        if error_rate > 10.0 or p95_latency > 2000:
            return 'unhealthy'
        
        # Degraded conditions
        if error_rate > 5.0 or p95_latency > 1000:
            return 'degraded'
        
        return 'healthy'
    
    def _get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        sorted_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'error': error, 'count': count}
            for error, count in sorted_errors[:limit]
        ]
    
    def _get_endpoint_stats(self) -> Dict[str, Any]:
        """Get per-endpoint statistics."""
        stats = {}
        
        for endpoint, metrics in self.endpoint_metrics.items():
            if metrics['latencies']:
                stats[endpoint] = {
                    'requests': metrics['count'],
                    'errors': metrics['errors'],
                    'error_rate': (metrics['errors'] / metrics['count'] * 100) if metrics['count'] > 0 else 0,
                    'avg_latency_ms': statistics.mean(metrics['latencies']),
                    'p95_latency_ms': self._calculate_percentile(metrics['latencies'], 95),
                    'last_error': metrics['last_error']
                }
        
        return stats
    
    def _get_rule_stats(self) -> Dict[str, Any]:
        """Get rule trigger statistics."""
        stats = {}
        
        for rule_id, metrics in self.rule_metrics.items():
            stats[rule_id] = {
                'total_triggers': metrics['triggers'],
                'actions': dict(metrics['actions'])
            }
        
        # Sort by trigger count
        return dict(sorted(stats.items(), key=lambda x: x[1]['total_triggers'], reverse=True))
    
    def _calculate_percentile(self, data: deque, percentile: int) -> float:
        """Calculate percentile from deque."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100.0))
        
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        metrics = []
        
        # Counter metrics
        metrics.append(f'# HELP redaction_requests_total Total number of requests processed')
        metrics.append(f'# TYPE redaction_requests_total counter')
        metrics.append(f'redaction_requests_total {self.total_requests}')
        
        metrics.append(f'# HELP redaction_redactions_total Total number of redactions performed')
        metrics.append(f'# TYPE redaction_redactions_total counter')
        metrics.append(f'redaction_redactions_total {self.total_redactions}')
        
        # Gauge metrics
        metrics.append(f'# HELP redaction_latency_p95_ms 95th percentile latency in milliseconds')
        metrics.append(f'# TYPE redaction_latency_p95_ms gauge')
        metrics.append(f'redaction_latency_p95_ms {self.get_percentile_latency(95)}')
        
        metrics.append(f'# HELP redaction_cache_hit_rate Cache hit rate percentage')
        metrics.append(f'# TYPE redaction_cache_hit_rate gauge')
        metrics.append(f'redaction_cache_hit_rate {self.get_cache_hit_rate()}')
        
        metrics.append(f'# HELP redaction_error_rate Error rate percentage')
        metrics.append(f'# TYPE redaction_error_rate gauge')
        metrics.append(f'redaction_error_rate {self.get_error_rate()}')
        
        return '\n'.join(metrics)
    
    def reset(self):
        """Reset all metrics."""
        self.total_requests = 0
        self.total_redactions = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.judge_fallbacks = 0
        self.judge_calls = 0
        self.latencies.clear()
        self.start_time = time.time()
        
        logger.info("Metrics reset")


# Global singleton instance
_metrics_instance = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global singleton metrics collector instance.
    
    Returns:
        Shared MetricsCollector instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = MetricsCollector()
                logger.info("Enhanced metrics collector initialized")
    return _metrics_instance

__all__ = ["MetricsCollector"]