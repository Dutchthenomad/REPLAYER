"""
Tests for Phase 3 Audit Components

Tests cover:
- TokenBucketRateLimiter: Rate limiting and burst capacity
- ConnectionHealthMonitor: Health status tracking
- LatencySpikeDetector: Latency spike detection
- GracefulDegradationManager: Operating mode transitions
- GameStateMachine recovery: Disconnect recovery and state summary

PHASE 4 AUDIT: Testing Infrastructure Improvements
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from sources.websocket_feed import (
    TokenBucketRateLimiter,
    ConnectionHealth,
    ConnectionHealthMonitor,
    LatencySpikeDetector,
    OperatingMode,
    GracefulDegradationManager
)
from sources.game_state_machine import GameStateMachine


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter rate limiting"""

    def test_rate_limiter_creation(self):
        """Test rate limiter initializes correctly"""
        limiter = TokenBucketRateLimiter(rate=10.0)

        assert limiter.rate == 10.0
        assert limiter.burst == 20  # Default 2x rate
        assert limiter.tokens == 20.0  # Starts at burst capacity
        assert limiter.total_requests == 0

    def test_rate_limiter_custom_burst(self):
        """Test rate limiter with custom burst"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=50)

        assert limiter.rate == 10.0
        assert limiter.burst == 50
        assert limiter.tokens == 50.0

    def test_acquire_consumes_token(self):
        """Test acquire decrements token count"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        initial_tokens = limiter.tokens
        result = limiter.acquire()

        assert result is True
        assert limiter.tokens == initial_tokens - 1.0
        assert limiter.total_allowed == 1
        assert limiter.total_requests == 1

    def test_acquire_fails_when_empty(self):
        """Test acquire returns False when no tokens available"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=3)

        # Consume all tokens
        for _ in range(3):
            limiter.acquire()

        # Next should fail
        result = limiter.acquire()

        assert result is False
        assert limiter.total_dropped == 1
        assert limiter.total_requests == 4

    def test_tokens_refill_over_time(self):
        """Test tokens refill based on elapsed time"""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=10)

        # Consume all tokens
        for _ in range(10):
            limiter.acquire()

        assert limiter.tokens < 1.0

        # Wait for refill (100 tokens/sec = 1 token per 10ms)
        time.sleep(0.05)  # 50ms = 5 tokens

        result = limiter.acquire()
        assert result is True

    def test_tokens_cap_at_burst(self):
        """Test tokens don't exceed burst capacity"""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=10)

        # Wait (tokens should cap at burst)
        time.sleep(0.1)

        # Force an acquire to trigger refill calculation
        limiter.acquire()

        assert limiter.tokens <= limiter.burst

    def test_get_stats(self):
        """Test get_stats returns correct statistics"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # Perform some operations
        for _ in range(3):
            limiter.acquire()

        stats = limiter.get_stats()

        assert stats['rate'] == 10.0
        assert stats['burst'] == 5
        assert stats['total_requests'] == 3
        assert stats['total_allowed'] == 3
        assert stats['total_dropped'] == 0
        assert stats['drop_rate'] == 0.0

    def test_drop_rate_calculation(self):
        """Test drop rate is calculated correctly"""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=2)

        # 2 allowed, 2 dropped
        for _ in range(4):
            limiter.acquire()

        stats = limiter.get_stats()

        assert stats['total_requests'] == 4
        assert stats['total_allowed'] == 2
        assert stats['total_dropped'] == 2
        assert stats['drop_rate'] == 50.0

    def test_thread_safety(self):
        """Test rate limiter is thread-safe under concurrent access"""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=50)
        results = []

        def acquire_many():
            local_results = []
            for _ in range(20):
                local_results.append(limiter.acquire())
            results.append(sum(local_results))

        threads = [threading.Thread(target=acquire_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All requests should be accounted for
        assert limiter.total_requests == 100
        assert limiter.total_allowed + limiter.total_dropped == 100


class TestConnectionHealthMonitor:
    """Tests for ConnectionHealthMonitor health tracking"""

    def test_monitor_creation(self):
        """Test health monitor initializes correctly"""
        monitor = ConnectionHealthMonitor()

        assert monitor.stale_threshold_sec == 10.0
        assert monitor.latency_threshold_ms == 1000.0
        assert monitor.error_rate_threshold == 5.0
        assert monitor.is_connected is False

    def test_disconnected_status(self):
        """Test DISCONNECTED status when not connected"""
        monitor = ConnectionHealthMonitor()

        health = monitor.check_health()

        assert health['status'] == ConnectionHealth.DISCONNECTED
        assert 'Not connected to server' in health['issues']

    def test_healthy_status(self):
        """Test HEALTHY status when all is well"""
        monitor = ConnectionHealthMonitor()
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(avg_latency_ms=100.0, error_rate=0.0)

        assert health['status'] == ConnectionHealth.HEALTHY
        assert len(health['issues']) == 0

    def test_stale_status(self):
        """Test STALE status when no recent signals"""
        monitor = ConnectionHealthMonitor(stale_threshold_sec=0.1)
        monitor.set_connected(True)
        monitor.record_signal()

        # Wait for stale threshold
        time.sleep(0.15)

        health = monitor.check_health()

        assert health['status'] == ConnectionHealth.STALE
        assert any('No signals' in issue for issue in health['issues'])

    def test_degraded_high_latency(self):
        """Test DEGRADED status on high latency"""
        monitor = ConnectionHealthMonitor(latency_threshold_ms=500.0)
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(avg_latency_ms=800.0)

        assert health['status'] == ConnectionHealth.DEGRADED
        assert any('High latency' in issue for issue in health['issues'])

    def test_degraded_high_error_rate(self):
        """Test DEGRADED status on high error rate"""
        monitor = ConnectionHealthMonitor(error_rate_threshold=5.0)
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(error_rate=10.0)

        assert health['status'] == ConnectionHealth.DEGRADED
        assert any('High error rate' in issue for issue in health['issues'])

    def test_degraded_high_drop_rate(self):
        """Test DEGRADED status on high drop rate"""
        monitor = ConnectionHealthMonitor()
        monitor.set_connected(True)
        monitor.record_signal()

        health = monitor.check_health(drop_rate=15.0)

        assert health['status'] == ConnectionHealth.DEGRADED
        assert any('High drop rate' in issue for issue in health['issues'])

    def test_signal_age_tracking(self):
        """Test signal age is tracked correctly"""
        monitor = ConnectionHealthMonitor()
        monitor.set_connected(True)
        monitor.record_signal()

        time.sleep(0.1)

        age = monitor.get_signal_age()
        assert age is not None
        assert age >= 0.1

    def test_signal_age_none_initially(self):
        """Test signal age is None before any signals"""
        monitor = ConnectionHealthMonitor()

        assert monitor.get_signal_age() is None


class TestLatencySpikeDetector:
    """Tests for LatencySpikeDetector spike detection"""

    def test_detector_creation(self):
        """Test spike detector initializes correctly"""
        detector = LatencySpikeDetector(
            window_size=50,
            spike_threshold_std=2.0,
            absolute_threshold_ms=1000.0
        )

        assert detector.window_size == 50
        assert detector.spike_threshold_std == 2.0
        assert detector.absolute_threshold_ms == 1000.0
        assert detector.total_samples == 0

    def test_no_spike_on_normal_latency(self):
        """Test no spike detected for normal latency values"""
        detector = LatencySpikeDetector()

        # Record normal latencies
        for _ in range(20):
            result = detector.record(100.0)

        # Last record should not be a spike
        assert result is None

    def test_spike_on_absolute_threshold(self):
        """Test spike detected when absolute threshold exceeded"""
        detector = LatencySpikeDetector(absolute_threshold_ms=500.0)

        # Record some normal latencies first
        for _ in range(15):
            detector.record(100.0)

        # Record spike
        result = detector.record(600.0)

        assert result is not None
        assert 'Absolute threshold' in result['reason']
        assert result['latency_ms'] == 600.0

    def test_spike_on_statistical_threshold(self):
        """Test spike detected when z-score threshold exceeded"""
        detector = LatencySpikeDetector(
            spike_threshold_std=2.0,
            absolute_threshold_ms=10000.0  # High to not trigger
        )

        # Record consistent low latencies
        for _ in range(20):
            detector.record(100.0)

        # Record spike (much higher than mean)
        result = detector.record(500.0)

        assert result is not None
        assert 'Statistical spike' in result['reason']

    def test_needs_minimum_samples(self):
        """Test no spike detection with insufficient samples"""
        detector = LatencySpikeDetector()

        # Only 5 samples
        for _ in range(5):
            result = detector.record(1000.0)

        assert result is None  # Need 10 samples minimum

    def test_get_stats(self):
        """Test get_stats returns correct statistics"""
        detector = LatencySpikeDetector(absolute_threshold_ms=200.0)

        # Record some latencies including one spike
        for i in range(15):
            detector.record(100.0)
        detector.record(300.0)  # This is a spike

        stats = detector.get_stats()

        assert stats['total_samples'] == 16
        assert stats['total_spikes'] == 1
        assert stats['spike_rate'] > 0
        assert stats['mean_latency_ms'] > 0
        assert stats['max_latency_ms'] == 300.0
        assert stats['min_latency_ms'] == 100.0

    def test_spike_count_increments(self):
        """Test spike count increments on each spike"""
        detector = LatencySpikeDetector(absolute_threshold_ms=200.0)

        # Record samples
        for _ in range(15):
            detector.record(100.0)

        # Record multiple spikes
        detector.record(300.0)
        detector.record(400.0)
        detector.record(500.0)

        assert detector.total_spikes == 3

    def test_thread_safety(self):
        """Test spike detector is thread-safe"""
        detector = LatencySpikeDetector()
        spike_count = [0]

        def record_many():
            for i in range(50):
                result = detector.record(100.0 + i)
                if result:
                    spike_count[0] += 1

        threads = [threading.Thread(target=record_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert detector.total_samples == 250


class TestGracefulDegradationManager:
    """Tests for GracefulDegradationManager mode transitions"""

    def test_manager_creation(self):
        """Test degradation manager initializes correctly"""
        manager = GracefulDegradationManager()

        assert manager.current_mode == OperatingMode.NORMAL
        assert manager.error_threshold == 10
        assert manager.spike_threshold == 5

    def test_starts_in_normal_mode(self):
        """Test manager starts in NORMAL mode"""
        manager = GracefulDegradationManager()

        assert manager.current_mode == OperatingMode.NORMAL
        assert not manager.should_skip_non_critical()
        assert not manager.should_buffer_aggressively()

    def test_disconnect_sets_offline(self):
        """Test disconnect event sets OFFLINE mode"""
        manager = GracefulDegradationManager()

        manager.record_disconnect()

        assert manager.current_mode == OperatingMode.OFFLINE

    def test_reconnect_sets_degraded(self):
        """Test reconnect after offline sets DEGRADED mode"""
        manager = GracefulDegradationManager()

        manager.record_disconnect()
        manager.record_reconnect()

        assert manager.current_mode == OperatingMode.DEGRADED
        assert manager.should_skip_non_critical()

    def test_errors_trigger_degradation(self):
        """Test errors above threshold trigger degradation"""
        manager = GracefulDegradationManager(error_threshold=5)

        for _ in range(5):
            manager.record_error()

        assert manager.current_mode == OperatingMode.DEGRADED

    def test_spikes_trigger_degradation(self):
        """Test spikes above threshold trigger degradation"""
        manager = GracefulDegradationManager(spike_threshold=3)

        for _ in range(3):
            manager.record_spike()

        assert manager.current_mode == OperatingMode.DEGRADED

    def test_severe_errors_trigger_minimal(self):
        """Test severe errors (2x threshold) trigger MINIMAL mode"""
        manager = GracefulDegradationManager(error_threshold=5)

        for _ in range(10):  # 2x threshold
            manager.record_error()

        assert manager.current_mode == OperatingMode.MINIMAL
        assert manager.should_buffer_aggressively()

    def test_recovery_after_window(self):
        """Test recovery to NORMAL after recovery window"""
        manager = GracefulDegradationManager(
            error_threshold=3,
            recovery_window_sec=0.1
        )

        # Trigger degradation
        for _ in range(3):
            manager.record_error()

        assert manager.current_mode == OperatingMode.DEGRADED

        # Wait for recovery window
        time.sleep(0.15)
        manager.check_recovery()

        assert manager.current_mode == OperatingMode.NORMAL

    def test_no_recovery_from_offline(self):
        """Test cannot recover from OFFLINE without reconnect"""
        manager = GracefulDegradationManager(recovery_window_sec=0.1)

        manager.record_disconnect()
        time.sleep(0.15)
        manager.check_recovery()

        # Should still be offline
        assert manager.current_mode == OperatingMode.OFFLINE

    def test_mode_change_callback(self):
        """Test mode change callback is called"""
        manager = GracefulDegradationManager(error_threshold=2)

        callback_calls = []
        manager.on_mode_change = lambda old, new: callback_calls.append((old, new))

        for _ in range(2):
            manager.record_error()

        assert len(callback_calls) == 1
        assert callback_calls[0] == (OperatingMode.NORMAL, OperatingMode.DEGRADED)

    def test_get_status(self):
        """Test get_status returns correct information"""
        manager = GracefulDegradationManager()

        manager.record_error()
        manager.record_spike()

        status = manager.get_status()

        assert status['mode'] == OperatingMode.NORMAL  # Below thresholds
        assert status['errors_in_window'] == 1
        assert status['spikes_in_window'] == 1

    def test_mode_history_tracking(self):
        """Test mode transitions are recorded in history"""
        manager = GracefulDegradationManager(error_threshold=2)

        for _ in range(2):
            manager.record_error()

        status = manager.get_status()

        assert len(status['recent_transitions']) > 0
        assert status['recent_transitions'][-1]['to'] == OperatingMode.DEGRADED


class TestGameStateMachineRecovery:
    """Tests for GameStateMachine recovery methods"""

    def test_recover_from_disconnect(self):
        """Test recover_from_disconnect preserves context"""
        machine = GameStateMachine()

        # Process some states
        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-123'
        })

        recovery_info = machine.recover_from_disconnect()

        assert recovery_info['previous_phase'] == 'ACTIVE_GAMEPLAY'
        assert recovery_info['previous_game_id'] == 'game-123'
        assert recovery_info['previous_tick'] == 50
        assert recovery_info['recovered'] is True

    def test_recover_resets_to_unknown(self):
        """Test recovery resets phase to UNKNOWN"""
        machine = GameStateMachine()

        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-123'
        })

        machine.recover_from_disconnect()

        assert machine.current_phase == 'UNKNOWN'

    def test_recover_preserves_game_id(self):
        """Test recovery preserves game ID for comparison"""
        machine = GameStateMachine()

        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-123'
        })

        machine.recover_from_disconnect()

        # Game ID should still be set for comparison after reconnect
        assert machine.current_game_id == 'game-123'

    def test_recover_adds_transition_history(self):
        """Test recovery adds DISCONNECT_RECOVERY to history"""
        machine = GameStateMachine()

        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-123'
        })

        machine.recover_from_disconnect()

        assert len(machine.transition_history) >= 1
        last_transition = machine.transition_history[-1]
        assert last_transition['to'] == 'DISCONNECT_RECOVERY'

    def test_get_state_summary(self):
        """Test get_state_summary returns correct info"""
        machine = GameStateMachine()

        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-123'
        })

        summary = machine.get_state_summary()

        assert summary['phase'] == 'ACTIVE_GAMEPLAY'
        assert summary['game_id'] == 'game-123'
        assert summary['tick'] == 50
        assert 'anomaly_count' in summary
        assert 'recent_transitions' in summary

    def test_get_state_summary_includes_recent_transitions(self):
        """Test get_state_summary includes recent transitions"""
        machine = GameStateMachine()

        # Create multiple transitions
        machine.process({'active': True, 'tickCount': 0, 'rugged': False, 'gameId': 'g1'})
        machine.process({'active': True, 'tickCount': 1, 'rugged': False, 'gameId': 'g1'})
        machine.process({'active': True, 'rugged': True, 'gameId': 'g1', 'gameHistory': [{}]})

        summary = machine.get_state_summary()

        assert len(summary['recent_transitions']) > 0
        assert len(summary['recent_transitions']) <= 5  # Max 5


class TestWebSocketFeedIntegration:
    """Integration tests for WebSocketFeed with Phase 3 components"""

    @pytest.fixture
    def mock_socketio(self):
        """Mock Socket.IO client"""
        with patch('sources.websocket_feed.socketio.Client') as mock:
            client_instance = MagicMock()
            client_instance.sid = 'test-socket-id'
            mock.return_value = client_instance
            yield client_instance

    def test_feed_has_rate_limiter(self, mock_socketio):
        """Test WebSocketFeed initializes with rate limiter"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert hasattr(feed, 'rate_limiter')
        assert isinstance(feed.rate_limiter, TokenBucketRateLimiter)

    def test_feed_has_health_monitor(self, mock_socketio):
        """Test WebSocketFeed initializes with health monitor"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert hasattr(feed, 'health_monitor')
        assert isinstance(feed.health_monitor, ConnectionHealthMonitor)

    def test_feed_has_spike_detector(self, mock_socketio):
        """Test WebSocketFeed initializes with spike detector"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert hasattr(feed, 'spike_detector')
        assert isinstance(feed.spike_detector, LatencySpikeDetector)

    def test_feed_has_degradation_manager(self, mock_socketio):
        """Test WebSocketFeed initializes with degradation manager"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert hasattr(feed, 'degradation_manager')
        assert isinstance(feed.degradation_manager, GracefulDegradationManager)

    def test_feed_tracks_rate_limited_signals(self, mock_socketio):
        """Test WebSocketFeed tracks rate-limited signals in metrics"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert 'rate_limited' in feed.metrics
        assert feed.metrics['rate_limited'] == 0

    def test_feed_tracks_latency_spikes(self, mock_socketio):
        """Test WebSocketFeed tracks latency spikes in metrics"""
        from sources import WebSocketFeed

        feed = WebSocketFeed(log_level='ERROR')

        assert 'latency_spikes' in feed.metrics
        assert feed.metrics['latency_spikes'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
