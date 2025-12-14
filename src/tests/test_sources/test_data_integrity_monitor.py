"""
Tests for DataIntegrityMonitor - Phase 10.5C Data Integrity Monitor

TDD: Tests written FIRST before implementation.

The DataIntegrityMonitor tracks data integrity issues and triggers
monitor mode when thresholds are exceeded.

Triggers:
- WebSocket connection loss/reconnect
- Data gaps (missing ticks in sequence)
- Abnormal game end (no proper rug/crash event)

Thresholds (mutually exclusive):
- Ticks: Consecutive ticks of data loss
- Games: Number of dropped/corrupted games

Tests cover:
- Initialization with threshold config
- Tick tracking and gap detection
- Connection event handling
- Game completion tracking
- Threshold exceeded detection
- Reset on clean game
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

# These imports will FAIL until we create the module (TDD RED phase)
from sources.data_integrity_monitor import (
    DataIntegrityMonitor,
    ThresholdType,
    IntegrityIssue,
)
from models.recording_config import MonitorThresholdType


class TestEnumValues:
    """Tests for enum values"""

    @pytest.mark.parametrize("enum_val,expected", [
        (ThresholdType.TICKS, "ticks"),
        (ThresholdType.GAMES, "games"),
        (IntegrityIssue.TICK_GAP, "tick_gap"),
        (IntegrityIssue.CONNECTION_LOST, "connection_lost"),
        (IntegrityIssue.ABNORMAL_GAME_END, "abnormal_game_end"),
    ])
    def test_enum_values(self, enum_val, expected):
        """Test all enum values are correct"""
        assert enum_val.value == expected


class TestDataIntegrityMonitorInitialization:
    """Tests for DataIntegrityMonitor initialization"""

    @pytest.mark.parametrize("attr,expected", [
        ("threshold_type", ThresholdType.TICKS),
        ("threshold_value", 20),
        ("consecutive_tick_gaps", 0),
        ("consecutive_bad_games", 0),
        ("is_triggered", False),
    ])
    def test_default_values(self, attr, expected):
        """Test all default values are correct"""
        monitor = DataIntegrityMonitor()
        assert getattr(monitor, attr) == expected

    @pytest.mark.parametrize("threshold_type,threshold_value", [
        (ThresholdType.TICKS, 45),
        (ThresholdType.GAMES, 3),
    ])
    def test_custom_threshold(self, threshold_type, threshold_value):
        """Test custom threshold configuration"""
        monitor = DataIntegrityMonitor(
            threshold_type=threshold_type,
            threshold_value=threshold_value
        )
        assert monitor.threshold_type == threshold_type
        assert monitor.threshold_value == threshold_value


class TestDataIntegrityMonitorTickTracking:
    """Tests for tick tracking and gap detection"""

    def test_on_tick_updates_last_tick(self):
        """Test on_tick updates last seen tick"""
        monitor = DataIntegrityMonitor()
        monitor.on_tick(tick=5)
        assert monitor.last_tick == 5

    def test_on_tick_sequential_no_gap(self):
        """Test sequential ticks don't trigger gap"""
        monitor = DataIntegrityMonitor()
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=1)
        monitor.on_tick(tick=2)
        assert monitor.consecutive_tick_gaps == 0

    def test_on_tick_gap_detected(self):
        """Test gap in tick sequence detected"""
        monitor = DataIntegrityMonitor()
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=1)
        monitor.on_tick(tick=5)  # Gap: 2, 3, 4 missing
        assert monitor.consecutive_tick_gaps == 3

    def test_on_tick_gap_accumulates(self):
        """Test gaps accumulate"""
        monitor = DataIntegrityMonitor()
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=3)  # Gap of 2
        monitor.on_tick(tick=7)  # Gap of 3
        assert monitor.consecutive_tick_gaps == 5

    def test_on_tick_resets_gap_on_sequential(self):
        """Test gap counter resets on sequential tick after gap"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=10)
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=5)  # Gap of 4
        assert monitor.consecutive_tick_gaps == 4
        monitor.on_tick(tick=6)  # Sequential
        assert monitor.consecutive_tick_gaps == 0

    def test_on_tick_triggers_at_threshold(self):
        """Test monitor triggers when tick gap threshold reached"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.TICKS,
            threshold_value=5
        )
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        monitor.on_tick(tick=0)
        monitor.on_tick(tick=10)  # Gap of 9, exceeds threshold of 5

        assert monitor.is_triggered is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == IntegrityIssue.TICK_GAP

    def test_on_tick_game_start_resets_last_tick(self):
        """Test starting new game resets last tick tracking"""
        monitor = DataIntegrityMonitor()
        monitor.on_tick(tick=100)
        monitor.on_game_start(game_id="game-2")
        monitor.on_tick(tick=0)  # New game starts at 0
        assert monitor.consecutive_tick_gaps == 0


class TestDataIntegrityMonitorConnectionEvents:
    """Tests for connection event handling"""

    def test_on_connection_lost_triggers_immediately(self):
        """Test connection lost triggers immediately"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.TICKS,
            threshold_value=5
        )
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        monitor.on_connection_lost()

        assert monitor.is_triggered is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == IntegrityIssue.CONNECTION_LOST

    def test_on_connection_restored_with_ticks_threshold(self):
        """Test connection restored doesn't auto-reset with ticks threshold"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        monitor.on_connection_lost()
        assert monitor.is_triggered is True

        monitor.on_connection_restored()
        # Still triggered - needs clean game to reset
        assert monitor.is_triggered is True


class TestDataIntegrityMonitorGameTracking:
    """Tests for game completion tracking"""

    def test_on_game_start_sets_current_game(self):
        """Test on_game_start sets current game ID"""
        monitor = DataIntegrityMonitor()
        monitor.on_game_start(game_id="game-123")
        assert monitor.current_game_id == "game-123"

    def test_on_game_end_clean_no_issues(self):
        """Test clean game end doesn't trigger issues"""
        monitor = DataIntegrityMonitor()
        monitor.on_game_start(game_id="game-1")
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=1)
        monitor.on_tick(tick=2)
        monitor.on_game_end(game_id="game-1", clean=True)

        assert monitor.consecutive_bad_games == 0
        assert monitor.is_triggered is False

    def test_on_game_end_abnormal_increments_counter(self):
        """Test abnormal game end increments bad games counter"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.GAMES,
            threshold_value=3
        )
        monitor.on_game_start(game_id="game-1")
        monitor.on_game_end(game_id="game-1", clean=False)

        assert monitor.consecutive_bad_games == 1

    def test_on_game_end_abnormal_triggers_at_threshold(self):
        """Test abnormal game ends trigger at threshold"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.GAMES,
            threshold_value=2
        )
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        # First bad game
        monitor.on_game_start(game_id="game-1")
        monitor.on_game_end(game_id="game-1", clean=False)
        assert monitor.is_triggered is False

        # Second bad game - triggers threshold
        monitor.on_game_start(game_id="game-2")
        monitor.on_game_end(game_id="game-2", clean=False)

        assert monitor.is_triggered is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == IntegrityIssue.ABNORMAL_GAME_END

    def test_on_game_end_clean_resets_bad_games_counter(self):
        """Test clean game end resets bad games counter"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.GAMES,
            threshold_value=3
        )
        # Two bad games
        monitor.on_game_start(game_id="game-1")
        monitor.on_game_end(game_id="game-1", clean=False)
        monitor.on_game_start(game_id="game-2")
        monitor.on_game_end(game_id="game-2", clean=False)
        assert monitor.consecutive_bad_games == 2

        # One clean game resets counter
        monitor.on_game_start(game_id="game-3")
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=1)
        monitor.on_game_end(game_id="game-3", clean=True)
        assert monitor.consecutive_bad_games == 0


class TestDataIntegrityMonitorReset:
    """Tests for reset behavior"""

    def test_reset_clears_triggered_state(self):
        """Test reset clears is_triggered"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        monitor.on_connection_lost()
        assert monitor.is_triggered is True

        monitor.reset()
        assert monitor.is_triggered is False

    def test_reset_clears_counters(self):
        """Test reset clears all counters"""
        monitor = DataIntegrityMonitor()
        monitor._consecutive_tick_gaps = 10
        monitor._consecutive_bad_games = 5

        monitor.reset()

        assert monitor.consecutive_tick_gaps == 0
        assert monitor.consecutive_bad_games == 0

    def test_on_clean_game_observed_resets_triggered(self):
        """Test observing clean game resets triggered state"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        monitor.on_connection_lost()
        assert monitor.is_triggered is True

        # Observe a clean game
        monitor.on_clean_game_observed()
        assert monitor.is_triggered is False

    def test_on_clean_game_observed_callback(self):
        """Test on_clean_game_observed triggers callback"""
        monitor = DataIntegrityMonitor()
        monitor.on_connection_lost()

        callback = Mock()
        monitor.on_recovery = callback

        monitor.on_clean_game_observed()

        callback.assert_called_once()


class TestDataIntegrityMonitorThresholdBehavior:
    """Tests for threshold-specific behavior"""

    def test_ticks_threshold_ignores_game_count(self):
        """Test ticks threshold doesn't trigger on bad games alone"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.TICKS,
            threshold_value=10
        )
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        # Many bad games but no tick gaps
        for i in range(20):
            monitor.on_game_start(game_id=f"game-{i}")
            monitor.on_tick(tick=0)
            monitor.on_tick(tick=1)
            monitor.on_game_end(game_id=f"game-{i}", clean=False)

        # Should not trigger - we're tracking ticks, not games
        assert monitor.is_triggered is False
        callback.assert_not_called()

    def test_games_threshold_ignores_tick_gaps(self):
        """Test games threshold doesn't trigger on tick gaps alone"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.GAMES,
            threshold_value=3
        )
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        # Large tick gaps but clean games
        monitor.on_game_start(game_id="game-1")
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=100)  # Huge gap
        monitor.on_game_end(game_id="game-1", clean=True)

        # Should not trigger - we're tracking games, not ticks
        assert monitor.is_triggered is False
        callback.assert_not_called()

    def test_connection_lost_always_triggers_regardless_of_type(self):
        """Test connection loss always triggers regardless of threshold type"""
        # With ticks threshold
        monitor1 = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=100)
        monitor1.on_connection_lost()
        assert monitor1.is_triggered is True

        # With games threshold
        monitor2 = DataIntegrityMonitor(threshold_type=ThresholdType.GAMES, threshold_value=100)
        monitor2.on_connection_lost()
        assert monitor2.is_triggered is True


class TestDataIntegrityMonitorCallbacks:
    """Tests for callbacks"""

    def test_on_threshold_exceeded_callback_receives_issue_type(self):
        """Test threshold exceeded callback receives issue type"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        monitor.on_tick(tick=0)
        monitor.on_tick(tick=10)

        callback.assert_called_once()
        issue_type = callback.call_args[0][0]
        assert issue_type == IntegrityIssue.TICK_GAP

    def test_on_threshold_exceeded_callback_receives_details(self):
        """Test threshold exceeded callback receives details dict"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        monitor.on_tick(tick=0)
        monitor.on_tick(tick=10)

        details = callback.call_args[0][1]
        assert "gap_size" in details
        assert details["gap_size"] == 9

    def test_callback_not_called_twice_once_triggered(self):
        """Test callback not called again once already triggered"""
        monitor = DataIntegrityMonitor(threshold_type=ThresholdType.TICKS, threshold_value=5)
        callback = Mock()
        monitor.on_threshold_exceeded = callback

        monitor.on_tick(tick=0)
        monitor.on_tick(tick=10)  # Triggers
        monitor.on_tick(tick=20)  # Should not trigger again

        assert callback.call_count == 1


class TestDataIntegrityMonitorHelpers:
    """Tests for helper methods"""

    def test_is_healthy_when_no_issues(self):
        """Test is_healthy returns True when no issues"""
        monitor = DataIntegrityMonitor()
        assert monitor.is_healthy() is True

    def test_is_healthy_false_when_triggered(self):
        """Test is_healthy returns False when triggered"""
        monitor = DataIntegrityMonitor()
        monitor.on_connection_lost()
        assert monitor.is_healthy() is False

    def test_get_status_returns_dict(self):
        """Test get_status returns status dictionary"""
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.TICKS,
            threshold_value=20
        )
        status = monitor.get_status()

        assert isinstance(status, dict)
        assert "is_triggered" in status
        assert "threshold_type" in status
        assert "threshold_value" in status
        assert "consecutive_tick_gaps" in status
        assert "consecutive_bad_games" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
