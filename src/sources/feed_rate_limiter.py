"""
Feed Rate Limiter - Phase 10.4A Modular Refactor

Extracted from websocket_feed.py:
- TokenBucketRateLimiter: Token bucket rate limiter for WebSocket flood protection
- PriorityRateLimiter: Rate limiter with priority bypass for critical signals

These classes handle rate limiting for the WebSocket feed without
containing any Socket.IO-specific code.
"""

import time
import threading
from typing import Dict, Any


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for WebSocket flood protection.

    PHASE 3.1 AUDIT FIX: Prevents data floods from overwhelming the system.

    Args:
        rate: Maximum tokens per second (signals/sec)
        burst: Maximum burst capacity (default: 2x rate)
    """

    def __init__(self, rate: float = 20.0, burst: int = None):
        self.rate = rate
        self.burst = burst if burst is not None else int(rate * 2)
        self.tokens = float(self.burst)
        self.last_update = time.time()
        self._lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.total_allowed = 0
        self.total_dropped = 0

    def acquire(self) -> bool:
        """
        Attempt to acquire a token.

        Returns:
            True if token acquired (request allowed), False if rate limited
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Refill tokens based on elapsed time
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

            self.total_requests += 1

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.total_allowed += 1
                return True
            else:
                self.total_dropped += 1
                return False

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self._lock:
            return {
                'rate': self.rate,
                'burst': self.burst,
                'tokens_available': self.tokens,
                'total_requests': self.total_requests,
                'total_allowed': self.total_allowed,
                'total_dropped': self.total_dropped,
                'drop_rate': (self.total_dropped / self.total_requests * 100)
                    if self.total_requests > 0 else 0.0
            }


class PriorityRateLimiter(TokenBucketRateLimiter):
    """Rate limiter with priority bypass for critical signals"""

    CRITICAL_PHASES = {'RUG_EVENT', 'RUG_EVENT_1', 'RUG_EVENT_2'}

    def __init__(self, rate: float = 20.0, burst: int = None):
        super().__init__(rate=rate, burst=burst)

    def should_process(self, signal: Any) -> bool:
        """Always allow critical signals; rate limit others"""
        if self._is_critical(signal):
            return True
        return self.acquire()

    def _is_critical(self, signal: Any) -> bool:
        return (
            getattr(signal, 'rugged', False) or
            getattr(signal, 'phase', '') in self.CRITICAL_PHASES
        )
