"""
Tests for feed_monitors.py - Extracted from websocket_feed.py

Phase 10.4A TDD: Tests written FIRST before extraction.

Tests cover:
- LatencySpikeDetector: spike detection, statistics, rate limiting
- ConnectionHealth: enum values
- ConnectionHealthMonitor: health checks, signal tracking
"""

import pytest
import time
from unittest.mock import MagicMock

# These imports will FAIL until we create the module (TDD RED phase)
from sources.feed_monitors import (
    LatencySpikeDetector,
    ConnectionHealth,
    ConnectionHealthMonitor
)


class TestLatencySpikeDetector:
    """Tests for LatencySpikeDetector"""

    def test_initialization_defaults(self):
        """Test default initialization"""
        detector = LatencySpikeDetector()
        assert detector.window_size == 100
        assert detector.spike_threshold_std == 10.0
        assert detector.absolute_threshold_ms == 10000.0
        assert detector.total_samples == 0
        assert detector.total_spikes == 0

    def test_initialization_custom(self):
        """Test custom initialization"""
        detector = LatencySpikeDetector(
            window_size=50,
            spike_threshold_std=5.0,
            absolute_threshold_ms=5000.0
        )
        assert detector.window_size == 50
        assert detector.spike_threshold_std == 5.0
        assert detector.absolute_threshold_ms == 5000.0

    def test_record_normal_latency(self):
        """Test recording normal latency doesn't trigger spike"""
        detector = LatencySpikeDetector()

        # Record normal latencies
        for _ in range(20):
            result = detector.record(100.0)  # 100ms - normal

        # No spike should be detected for normal latencies
        assert detector.total_spikes == 0
        assert detector.total_samples == 20

    def test_record_absolute_spike(self):
        """Test absolute threshold triggers spike"""
        detector = LatencySpikeDetector(absolute_threshold_ms=5000.0)

        # First, record some baseline samples
        for _ in range(20):
            detector.record(100.0)

        # Record spike exceeding absolute threshold
        result = detector.record(6000.0)  # 6 seconds - exceeds 5s threshold

        assert detector.total_spikes >= 1

    def test_get_stats(self):
        """Test statistics collection"""
        detector = LatencySpikeDetector()

        # Record some samples
        detector.record(100.0)
        detector.record(150.0)
        detector.record(120.0)

        stats = detector.get_stats()

        assert 'total_samples' in stats
        assert 'total_spikes' in stats
        assert 'spike_rate' in stats
        assert 'mean_latency_ms' in stats
        assert 'max_latency_ms' in stats
        assert 'min_latency_ms' in stats
        assert stats['total_samples'] == 3

    def test_latency_tiered_thresholds(self):
        """Test tiered threshold evaluation"""
        detector = LatencySpikeDetector()

        assert detector.check_latency(500.0) == 'OK'  # Normal
        assert detector.check_latency(2500.0) == 'WARNING'  # >= 2000ms
        assert detector.check_latency(6000.0) == 'ERROR'  # >= 5000ms
        assert detector.check_latency(15000.0) == 'CRITICAL'  # >= 10000ms


class TestConnectionHealth:
    """Tests for ConnectionHealth enum-like class"""

    @pytest.mark.parametrize("state,expected", [
        (ConnectionHealth.HEALTHY, "HEALTHY"),
        (ConnectionHealth.DEGRADED, "DEGRADED"),
        (ConnectionHealth.STALE, "STALE"),
        (ConnectionHealth.DISCONNECTED, "DISCONNECTED"),
        (ConnectionHealth.UNKNOWN, "UNKNOWN"),
    ])
    def test_health_state_values(self, state, expected):
        """Test all health state values are correct strings"""
        assert state == expected


class TestConnectionHealthMonitor:
    """Tests for ConnectionHealthMonitor"""

    def test_initialization(self):
        """Test default initialization"""
        monitor = ConnectionHealthMonitor()
        assert monitor.stale_threshold_sec == 10.0
        assert monitor.latency_threshold_ms == 1000.0
        assert monitor.error_rate_threshold == 5.0
        assert monitor.is_connected is False
        assert monitor.last_signal_time is None

    def test_set_connected(self):
        """Test connection state update"""
        monitor = ConnectionHealthMonitor()

        monitor.set_connected(True)
        assert monitor.is_connected is True
        assert monitor.last_signal_time is not None

        monitor.set_connected(False)
        assert monitor.is_connected is False

    def test_record_signal(self):
        """Test signal recording updates timestamp"""
        monitor = ConnectionHealthMonitor()

        before = time.time()
        monitor.record_signal()
        after = time.time()

        assert monitor.last_signal_time is not None
        assert before <= monitor.last_signal_time <= after

    def test_get_signal_age_none(self):
        """Test signal age returns None when no signal received"""
        monitor = ConnectionHealthMonitor()
        assert monitor.get_signal_age() is None

    def test_get_signal_age_value(self):
        """Test signal age returns correct value"""
        monitor = ConnectionHealthMonitor()
        monitor.record_signal()

        time.sleep(0.1)  # Wait 100ms

        age = monitor.get_signal_age()
        assert age is not None
        assert age >= 0.1

    def test_check_health_disconnected(self):
        """Test health check returns DISCONNECTED when not connected"""
        monitor = ConnectionHealthMonitor()

        health = monitor.check_health()

        assert health['status'] == ConnectionHealth.DISCONNECTED
        assert 'Not connected' in health['issues'][0]

    def test_check_health_healthy(self):
        """Test health check returns HEALTHY when all good"""
        monitor = ConnectionHealthMonitor()
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(avg_latency_ms=100.0, error_rate=0.0)

        assert health['status'] == ConnectionHealth.HEALTHY
        assert len(health['issues']) == 0

    def test_check_health_stale(self):
        """Test health check returns STALE after threshold"""
        monitor = ConnectionHealthMonitor(stale_threshold_sec=0.1)
        monitor.set_connected(True)
        monitor.record_signal()

        time.sleep(0.15)  # Exceed stale threshold

        health = monitor.check_health()

        assert health['status'] == ConnectionHealth.STALE
        assert any('No signals' in issue for issue in health['issues'])

    def test_check_health_degraded_latency(self):
        """Test health check returns DEGRADED on high latency"""
        monitor = ConnectionHealthMonitor(latency_threshold_ms=100.0)
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(avg_latency_ms=200.0)

        assert health['status'] == ConnectionHealth.DEGRADED
        assert any('High latency' in issue for issue in health['issues'])

    def test_check_health_degraded_errors(self):
        """Test health check returns DEGRADED on high error rate"""
        monitor = ConnectionHealthMonitor(error_rate_threshold=5.0)
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(error_rate=10.0)

        assert health['status'] == ConnectionHealth.DEGRADED
        assert any('High error rate' in issue for issue in health['issues'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
