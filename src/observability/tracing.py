"""
Tracing utilities for observability.
"""
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


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
    
    def start_span(self, name: str) -> Dict[str, Any]:
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
    
    def end_span(self, span: Dict[str, Any], attributes: Optional[Dict[str, Any]] = None):
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
    
    def get_recent_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent spans.
        
        Args:
            limit: Maximum number of spans to return
            
        Returns:
            List of recent spans
        """
        return self.spans[-limit:]
    
    def clear_spans(self):
        """Clear all stored spans."""
        self.spans.clear()
        logger.debug("Cleared all spans")


# Global tracer instance
_tracer: Optional[OpenTelemetryTracer] = None


def get_tracer(service_name: str = "pii-redaction-gateway") -> OpenTelemetryTracer:
    """
    Get global tracer instance.
    
    Args:
        service_name: Name of the service
        
    Returns:
        OpenTelemetryTracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = OpenTelemetryTracer(service_name)
    return _tracer


__all__ = ["OpenTelemetryTracer", "get_tracer"]