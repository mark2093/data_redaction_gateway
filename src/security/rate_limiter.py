"""
Rate Limiting implementation.

Provides request rate limiting per user, API key, or IP address.
"""
import time
import logging
from typing import Dict, Optional, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    enabled: bool = True


@dataclass
class RateLimitStatus:
    """Rate limit status for a client."""
    requests_in_minute: int
    requests_in_hour: int
    requests_in_day: int
    limit_minute: int
    limit_hour: int
    limit_day: int
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_minute: int
    reset_hour: int
    reset_day: int
    blocked: bool = False


class TokenBucket:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now
    
    def get_tokens(self) -> float:
        """Get current token count."""
        with self._lock:
            self._refill()
            return self.tokens


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int):
        """
        Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.requests: deque = deque()
        self._lock = threading.Lock()
    
    def add_request(self, timestamp: Optional[float] = None):
        """
        Add a request to the window.
        
        Args:
            timestamp: Request timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self._cleanup(timestamp)
            self.requests.append(timestamp)
    
    def count(self, timestamp: Optional[float] = None) -> int:
        """
        Count requests in current window.
        
        Args:
            timestamp: Current timestamp (defaults to now)
            
        Returns:
            Number of requests in window
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self._cleanup(timestamp)
            return len(self.requests)
    
    def _cleanup(self, current_time: float):
        """Remove expired requests from window."""
        cutoff = current_time - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        
        # Track requests per client (key: client_id, value: counters)
        self._minute_counters: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(60)
        )
        self._hour_counters: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(3600)
        )
        self._day_counters: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(86400)
        )
        
        # Token buckets for burst control
        self._token_buckets: Dict[str, TokenBucket] = {}
        
        # Blocked clients
        self._blocked_clients: Dict[str, float] = {}  # client_id -> unblock_time
        
        self._lock = threading.Lock()
    
    def check_rate_limit(self, client_id: str) -> Tuple[bool, RateLimitStatus]:
        """
        Check if client is within rate limits.
        
        Args:
            client_id: Client identifier (user_id, API key, or IP)
            
        Returns:
            Tuple of (allowed, status)
        """
        if not self.config.enabled:
            return True, self._get_unlimited_status()
        
        # Check if client is blocked
        if self._is_blocked(client_id):
            return False, self._get_blocked_status(client_id)
        
        current_time = time.time()
        
        # Get current counts
        minute_count = self._minute_counters[client_id].count(current_time)
        hour_count = self._hour_counters[client_id].count(current_time)
        day_count = self._day_counters[client_id].count(current_time)
        
        # Check limits
        minute_allowed = minute_count < self.config.requests_per_minute
        hour_allowed = hour_count < self.config.requests_per_hour
        day_allowed = day_count < self.config.requests_per_day
        
        # Check burst control
        burst_allowed = self._check_burst(client_id)
        
        allowed = minute_allowed and hour_allowed and day_allowed and burst_allowed
        
        # Create status
        status = RateLimitStatus(
            requests_in_minute=minute_count,
            requests_in_hour=hour_count,
            requests_in_day=day_count,
            limit_minute=self.config.requests_per_minute,
            limit_hour=self.config.requests_per_hour,
            limit_day=self.config.requests_per_day,
            remaining_minute=max(0, self.config.requests_per_minute - minute_count),
            remaining_hour=max(0, self.config.requests_per_hour - hour_count),
            remaining_day=max(0, self.config.requests_per_day - day_count),
            reset_minute=int(current_time + 60),
            reset_hour=int(current_time + 3600),
            reset_day=int(current_time + 86400),
            blocked=False
        )
        
        return allowed, status
    
    def record_request(self, client_id: str):
        """
        Record a request for a client.
        
        Args:
            client_id: Client identifier
        """
        if not self.config.enabled:
            return
        
        current_time = time.time()
        
        self._minute_counters[client_id].add_request(current_time)
        self._hour_counters[client_id].add_request(current_time)
        self._day_counters[client_id].add_request(current_time)
        
        # Consume token from bucket
        self._get_token_bucket(client_id).consume(1)
    
    def block_client(self, client_id: str, duration_seconds: int = 300):
        """
        Block a client for a duration.
        
        Args:
            client_id: Client identifier
            duration_seconds: Block duration in seconds
        """
        with self._lock:
            unblock_time = time.time() + duration_seconds
            self._blocked_clients[client_id] = unblock_time
            logger.warning(f"Client {client_id} blocked for {duration_seconds}s")
    
    def unblock_client(self, client_id: str):
        """
        Unblock a client.
        
        Args:
            client_id: Client identifier
        """
        with self._lock:
            if client_id in self._blocked_clients:
                del self._blocked_clients[client_id]
                logger.info(f"Client {client_id} unblocked")
    
    def _is_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked."""
        if client_id not in self._blocked_clients:
            return False
        
        current_time = time.time()
        unblock_time = self._blocked_clients[client_id]
        
        if current_time >= unblock_time:
            # Automatically unblock
            self.unblock_client(client_id)
            return False
        
        return True
    
    def _check_burst(self, client_id: str) -> bool:
        """Check burst control using token bucket."""
        bucket = self._get_token_bucket(client_id)
        return bucket.get_tokens() >= 1
    
    def _get_token_bucket(self, client_id: str) -> TokenBucket:
        """Get or create token bucket for client."""
        if client_id not in self._token_buckets:
            # Refill rate: requests_per_minute / 60 tokens per second
            refill_rate = self.config.requests_per_minute / 60.0
            self._token_buckets[client_id] = TokenBucket(
                capacity=self.config.burst_size,
                refill_rate=refill_rate
            )
        return self._token_buckets[client_id]
    
    def _get_unlimited_status(self) -> RateLimitStatus:
        """Get status for unlimited access."""
        return RateLimitStatus(
            requests_in_minute=0,
            requests_in_hour=0,
            requests_in_day=0,
            limit_minute=999999,
            limit_hour=999999,
            limit_day=999999,
            remaining_minute=999999,
            remaining_hour=999999,
            remaining_day=999999,
            reset_minute=0,
            reset_hour=0,
            reset_day=0,
            blocked=False
        )
    
    def _get_blocked_status(self, client_id: str) -> RateLimitStatus:
        """Get status for blocked client."""
        unblock_time = self._blocked_clients.get(client_id, 0)
        return RateLimitStatus(
            requests_in_minute=0,
            requests_in_hour=0,
            requests_in_day=0,
            limit_minute=self.config.requests_per_minute,
            limit_hour=self.config.requests_per_hour,
            limit_day=self.config.requests_per_day,
            remaining_minute=0,
            remaining_hour=0,
            remaining_day=0,
            reset_minute=int(unblock_time),
            reset_hour=int(unblock_time),
            reset_day=int(unblock_time),
            blocked=True
        )
    
    def get_stats(self) -> Dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "enabled": self.config.enabled,
            "limits": {
                "per_minute": self.config.requests_per_minute,
                "per_hour": self.config.requests_per_hour,
                "per_day": self.config.requests_per_day,
                "burst_size": self.config.burst_size
            },
            "tracked_clients": len(self._minute_counters),
            "blocked_clients": len(self._blocked_clients)
        }


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get singleton rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.
    
    Args:
        request: FastAPI request
        call_next: Next middleware
        
    Returns:
        Response
    """
    rate_limiter = get_rate_limiter()
    
    # Get client identifier (prefer user ID, fallback to API key or IP)
    client_id = None
    
    # Try to get from token (if authenticated)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from .jwt_auth import get_jwt_manager
            jwt_manager = get_jwt_manager()
            token = auth_header.replace("Bearer ", "")
            token_data = jwt_manager.verify_token(token)
            client_id = token_data.user_id or token_data.username
        except:
            pass
    
    # Fallback to API key
    if not client_id:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            client_id = f"apikey:{api_key}"
    
    # Fallback to IP address
    if not client_id:
        client_id = f"ip:{request.client.host}"
    
    # Check rate limit
    allowed, status = rate_limiter.check_rate_limit(client_id)
    
    if not allowed:
        # Rate limit exceeded
        logger.warning(f"Rate limit exceeded for {client_id}")
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "blocked": status.blocked,
                "reset_at": status.reset_minute,
                "limits": {
                    "minute": {
                        "limit": status.limit_minute,
                        "remaining": status.remaining_minute,
                        "reset": status.reset_minute
                    },
                    "hour": {
                        "limit": status.limit_hour,
                        "remaining": status.remaining_hour,
                        "reset": status.reset_hour
                    },
                    "day": {
                        "limit": status.limit_day,
                        "remaining": status.remaining_day,
                        "reset": status.reset_day
                    }
                }
            },
            headers={
                "X-RateLimit-Limit-Minute": str(status.limit_minute),
                "X-RateLimit-Remaining-Minute": str(status.remaining_minute),
                "X-RateLimit-Reset-Minute": str(status.reset_minute),
                "Retry-After": str(60)
            }
        )
    
    # Record request
    rate_limiter.record_request(client_id)
    
    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit-Minute"] = str(status.limit_minute)
    response.headers["X-RateLimit-Remaining-Minute"] = str(status.remaining_minute)
    response.headers["X-RateLimit-Reset-Minute"] = str(status.reset_minute)
    
    return response


__all__ = [
    "RateLimitConfig",
    "RateLimitStatus",
    "RateLimiter",
    "TokenBucket",
    "SlidingWindowCounter",
    "get_rate_limiter",
    "rate_limit_middleware",
]
