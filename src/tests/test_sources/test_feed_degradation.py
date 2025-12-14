"""
Tests for feed_degradation.py - Extracted from websocket_feed.py

Phase 10.4A TDD: Tests written FIRST before extraction.

Tests cover:
- OperatingMode: enum values
- GracefulDegradationManager: mode transitions, recovery, callbacks
"""

import pytest
import time
from unittest.mock import MagicMock

# These imports will FAIL until we create the module (TDD RED phase)
from sources.feed_degradation import (
    OperatingMode,
    GracefulDegradationManager
)


class TestOperatingMode:
    """Tests for OperatingMode enum-like class"""

    @pytest.mark.parametrize("mode,expected", [
        (OperatingMode.NORMAL, "NORMAL"),
        (OperatingMode.DEGRADED, "DEGRADED"),
        (OperatingMode.MINIMAL, "MINIMAL"),
        (OperatingMode.OFFLINE, "OFFLINE"),
    ])
    def test_mode_values(self, mode, expected):
        """Test all mode values are correct strings"""
        assert mode == expected


class TestGracefulDegradationManager:
    """Tests for GracefulDegradationManager"""

    @pytest.mark.parametrize("attr,expected", [
        ("error_threshold", 10),
        ("spike_threshold", 5),
        ("recovery_window_sec", 60.0),
        ("current_mode", OperatingMode.NORMAL),
        ("errors_in_window", 0),
        ("spikes_in_window", 0),
    ])
    def test_initialization_defaults(self, attr, expected):
        """Test all default values are correct"""
        manager = GracefulDegradationManager()
        assert getattr(manager, attr) == expected

    def test_initialization_custom(self):
        """Test custom initialization"""
        manager = GracefulDegradationManager(
            error_threshold=5,
            spike_threshold=3,
            recovery_window_sec=30.0
        )
        assert manager.error_threshold == 5
        assert manager.spike_threshold == 3
        assert manager.recovery_window_sec == 30.0

    def test_record_error(self):
        """Test error recording increments counter"""
        manager = GracefulDegradationManager()

        manager.record_error()

        assert manager.errors_in_window == 1
        assert manager.last_issue_time is not None

    def test_record_spike(self):
        """Test spike recording increments counter"""
        manager = GracefulDegradationManager()

        manager.record_spike()

        assert manager.spikes_in_window == 1
        assert manager.last_issue_time is not None

    def test_degraded_on_error_threshold(self):
        """Test mode degrades when error threshold reached"""
        manager = GracefulDegradationManager(error_threshold=3)

        # Record errors up to threshold
        for _ in range(3):
            manager.record_error()

        assert manager.current_mode == OperatingMode.DEGRADED

    def test_degraded_on_spike_threshold(self):
        """Test mode degrades when spike threshold reached"""
        manager = GracefulDegradationManager(spike_threshold=3)

        # Record spikes up to threshold
        for _ in range(3):
            manager.record_spike()

        assert manager.current_mode == OperatingMode.DEGRADED

    def test_minimal_on_severe_errors(self):
        """Test mode goes MINIMAL on severe errors (2x threshold)"""
        manager = GracefulDegradationManager(error_threshold=3)

        # Record errors to 2x threshold
        for _ in range(6):
            manager.record_error()

        assert manager.current_mode == OperatingMode.MINIMAL

    def test_record_disconnect(self):
        """Test disconnect sets OFFLINE mode"""
        manager = GracefulDegradationManager()

        manager.record_disconnect()

        assert manager.current_mode == OperatingMode.OFFLINE

    def test_record_reconnect(self):
        """Test reconnect transitions from OFFLINE to DEGRADED"""
        manager = GracefulDegradationManager()

        manager.record_disconnect()
        assert manager.current_mode == OperatingMode.OFFLINE

        manager.record_reconnect()
        assert manager.current_mode == OperatingMode.DEGRADED

    def test_check_recovery_from_degraded(self):
        """Test recovery from DEGRADED to NORMAL"""
        # Set low error threshold so we can trigger degradation
        manager = GracefulDegradationManager(
            error_threshold=3,
            recovery_window_sec=0.1
        )

        # Degrade by exceeding error threshold
        manager.record_error()
        manager.record_error()
        manager.record_error()

        # Verify we're degraded
        assert manager.current_mode == OperatingMode.DEGRADED

        # Wait for recovery window
        time.sleep(0.15)

        manager.check_recovery()

        assert manager.current_mode == OperatingMode.NORMAL
        assert manager.errors_in_window == 0

    def test_no_recovery_while_offline(self):
        """Test no recovery while in OFFLINE mode"""
        manager = GracefulDegradationManager(recovery_window_sec=0.1)

        manager.record_disconnect()

        time.sleep(0.15)

        manager.check_recovery()

        # Should still be offline
        assert manager.current_mode == OperatingMode.OFFLINE

    def test_should_skip_non_critical(self):
        """Test should_skip_non_critical returns correct values"""
        manager = GracefulDegradationManager()

        # NORMAL - don't skip
        assert manager.should_skip_non_critical() is False

        # DEGRADED - skip
        manager.current_mode = OperatingMode.DEGRADED
        assert manager.should_skip_non_critical() is True

        # MINIMAL - skip
        manager.current_mode = OperatingMode.MINIMAL
        assert manager.should_skip_non_critical() is True

    def test_should_buffer_aggressively(self):
        """Test should_buffer_aggressively returns correct values"""
        manager = GracefulDegradationManager()

        # NORMAL - don't buffer
        assert manager.should_buffer_aggressively() is False

        # DEGRADED - don't buffer aggressively
        manager.current_mode = OperatingMode.DEGRADED
        assert manager.should_buffer_aggressively() is False

        # MINIMAL - buffer aggressively
        manager.current_mode = OperatingMode.MINIMAL
        assert manager.should_buffer_aggressively() is True

    def test_on_mode_change_callback(self):
        """Test mode change callback is called"""
        manager = GracefulDegradationManager(error_threshold=1)

        callback_calls = []

        def callback(old_mode, new_mode):
            callback_calls.append((old_mode, new_mode))

        manager.on_mode_change = callback

        # Trigger mode change
        manager.record_error()

        assert len(callback_calls) == 1
        assert callback_calls[0] == (OperatingMode.NORMAL, OperatingMode.DEGRADED)

    def test_get_status(self):
        """Test get_status returns correct structure"""
        manager = GracefulDegradationManager()

        status = manager.get_status()

        assert 'mode' in status
        assert 'errors_in_window' in status
        assert 'spikes_in_window' in status
        assert 'last_issue_time' in status
        assert 'degradation_duration_sec' in status
        assert 'recent_transitions' in status
        assert status['mode'] == OperatingMode.NORMAL

    def test_mode_history_tracked(self):
        """Test mode transitions are tracked in history"""
        manager = GracefulDegradationManager(error_threshold=1)

        # Trigger transitions
        manager.record_error()  # NORMAL -> DEGRADED

        assert len(manager.mode_history) >= 1

        last_transition = manager.mode_history[-1]
        assert last_transition['from'] == OperatingMode.NORMAL
        assert last_transition['to'] == OperatingMode.DEGRADED
        assert 'timestamp' in last_transition

    def test_mode_history_bounded(self):
        """Test mode history is limited to 20 entries"""
        manager = GracefulDegradationManager(error_threshold=1, recovery_window_sec=0.01)

        # Create many transitions
        for i in range(25):
            manager.record_error()
            time.sleep(0.02)
            manager.check_recovery()

        assert len(manager.mode_history) <= 20


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
