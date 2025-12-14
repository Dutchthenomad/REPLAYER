"""
Tests for feed_rate_limiter.py - Extracted from websocket_feed.py

Phase 10.4A TDD: Tests written FIRST before extraction.

Tests cover:
- TokenBucketRateLimiter: token bucket algorithm, statistics
- PriorityRateLimiter: critical signal bypass
"""

import pytest
import time
from unittest.mock import MagicMock

# These imports will FAIL until we create the module (TDD RED phase)
from sources.feed_rate_limiter import (
    TokenBucketRateLimiter,
    PriorityRateLimiter
)


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter"""

    def test_initialization_defaults(self):
        """Test default initialization"""
        limiter = TokenBucketRateLimiter()
        assert limiter.rate == 20.0
        assert limiter.burst == 40  # 2x rate
        assert limiter.total_requests == 0
        assert limiter.total_allowed == 0
        assert limiter.total_dropped == 0

    def test_initialization_custom(self):
        """Test custom initialization"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=15)
        assert limiter.rate == 10.0
        assert limiter.burst == 15

    def test_acquire_allows_within_burst(self):
        """Test acquire allows requests within burst capacity"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # Should allow up to burst capacity
        results = [limiter.acquire() for _ in range(5)]
        assert all(results)
        assert limiter.total_allowed == 5
        assert limiter.total_dropped == 0

    def test_acquire_drops_over_burst(self):
        """Test acquire drops requests over burst capacity"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # Exhaust burst
        for _ in range(5):
            limiter.acquire()

        # Next request should be dropped (no time for refill)
        result = limiter.acquire()
        assert result is False
        assert limiter.total_dropped == 1

    def test_token_refill_over_time(self):
        """Test tokens refill over time"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # Exhaust burst
        for _ in range(5):
            limiter.acquire()

        # Wait for refill (100ms = 1 token at 10 tokens/sec)
        time.sleep(0.15)

        # Should allow another request
        result = limiter.acquire()
        assert result is True

    def test_get_stats(self):
        """Test statistics collection"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # Make some requests
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        stats = limiter.get_stats()

        assert 'rate' in stats
        assert 'burst' in stats
        assert 'tokens_available' in stats
        assert 'total_requests' in stats
        assert 'total_allowed' in stats
        assert 'total_dropped' in stats
        assert 'drop_rate' in stats
        assert stats['total_requests'] == 3
        assert stats['total_allowed'] == 3


class TestPriorityRateLimiter:
    """Tests for PriorityRateLimiter"""

    def test_inheritance(self):
        """Test PriorityRateLimiter inherits from TokenBucketRateLimiter"""
        limiter = PriorityRateLimiter()
        assert isinstance(limiter, TokenBucketRateLimiter)

    def test_critical_phases_defined(self):
        """Test critical phases are defined"""
        assert hasattr(PriorityRateLimiter, 'CRITICAL_PHASES')
        assert 'RUG_EVENT' in PriorityRateLimiter.CRITICAL_PHASES
        assert 'RUG_EVENT_1' in PriorityRateLimiter.CRITICAL_PHASES
        assert 'RUG_EVENT_2' in PriorityRateLimiter.CRITICAL_PHASES

    def test_should_process_critical_rugged(self):
        """Test critical signals with rugged=True always pass"""
        limiter = PriorityRateLimiter(rate=1.0, burst=1)

        # Exhaust burst
        limiter.acquire()

        # Create mock signal with rugged=True
        signal = MagicMock()
        signal.rugged = True
        signal.phase = ''

        # Should always allow critical signals
        result = limiter.should_process(signal)
        assert result is True

    def test_should_process_critical_phase(self):
        """Test critical phase signals always pass"""
        limiter = PriorityRateLimiter(rate=1.0, burst=1)

        # Exhaust burst
        limiter.acquire()

        # Create mock signal with critical phase
        signal = MagicMock()
        signal.rugged = False
        signal.phase = 'RUG_EVENT_1'

        # Should always allow critical phase signals
        result = limiter.should_process(signal)
        assert result is True

    def test_should_process_non_critical_rate_limited(self):
        """Test non-critical signals are rate limited"""
        limiter = PriorityRateLimiter(rate=1.0, burst=1)

        # Exhaust burst
        limiter.acquire()

        # Create mock non-critical signal
        signal = MagicMock()
        signal.rugged = False
        signal.phase = 'ACTIVE_GAMEPLAY'

        # Should be rate limited
        result = limiter.should_process(signal)
        assert result is False

    def test_should_process_non_critical_allowed(self):
        """Test non-critical signals pass when tokens available"""
        limiter = PriorityRateLimiter(rate=10.0, burst=5)

        # Create mock non-critical signal
        signal = MagicMock()
        signal.rugged = False
        signal.phase = 'ACTIVE_GAMEPLAY'

        # Should be allowed
        result = limiter.should_process(signal)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
