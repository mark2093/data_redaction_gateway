"""
Metrics collection and observability utilities.
"""
import time
import logging
from typing import List
from collections import deque
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and tracks service metrics."""
    
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
    
    def record_request(self, latency_ms: float):
        """
        Record a request.
        
        Args:
            latency_ms: Request latency in milliseconds
        """
        self.total_requests += 1
        self.latencies.append(latency_ms)
    
    def record_redactions(self, count: int):
        """
        Record redactions performed.
        
        Args:
            count: Number of redactions
        """
        self.total_redactions += count
    
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
    
    def get_uptime_seconds(self) -> float:
        """
        Get service uptime.
        
        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time
    
    def get_summary(self) -> dict:
        """
        Get metrics summary.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'total_requests': self.total_requests,
            'total_redactions': self.total_redactions,
            'average_latency_ms': self.get_average_latency(),
            'p50_latency_ms': self.get_percentile_latency(50),
            'p95_latency_ms': self.get_percentile_latency(95),
            'p99_latency_ms': self.get_percentile_latency(99),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.get_cache_hit_rate(),
            'redaction_coverage': self.get_redaction_coverage(),
            'judge_calls': self.judge_calls,
            'judge_fallbacks': self.judge_fallbacks,
            'judge_fallback_rate': (
                (self.judge_fallbacks / self.judge_calls * 100) 
                if self.judge_calls > 0 else 0.0
            ),
            'uptime_seconds': self.get_uptime_seconds()
        }
    
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


class OpenTelemetryTracer:
    """Simplified OpenTelemetry tracing wrapper."""
    
    def __init__(self, service_name: str = "pii-redaction-gateway"):
        """
        Initialize tracer.
        
        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self.spans = []
    
    def start_span(self, name: str) -> dict:
        """
        Start a new span.
        
        Args:
            name: Span name
            
        Returns:
            Span context
        """
        span = {
            'name': name,
            'start_time': time.time(),
            'service': self.service_name
        }
        return span
    
    def end_span(self, span: dict, attributes: dict = None):
        """
        End a span.
        
        Args:
            span: Span context
            attributes: Additional attributes
        """
        span['end_time'] = time.time()
        span['duration_ms'] = (span['end_time'] - span['start_time']) * 1000
        
        if attributes:
            span['attributes'] = attributes
        
        self.spans.append(span)
        
        # Keep only recent spans
        if len(self.spans) > 1000:
            self.spans = self.spans[-1000:]
        
        logger.debug(
            f"Span: {span['name']} - Duration: {span['duration_ms']:.2f}ms"
        )
    
    def get_recent_spans(self, limit: int = 100) -> List[dict]:
        """
        Get recent spans.
        
        Args:
            limit: Maximum number of spans to return
            
        Returns:
            List of recent spans
        """
        return self.spans[-limit:]


# Global tracer instance
_tracer: OpenTelemetryTracer = OpenTelemetryTracer()


def get_tracer() -> OpenTelemetryTracer:
    """
    Get global tracer instance.
    
    Returns:
        OpenTelemetryTracer instance
    """
    return _tracer
