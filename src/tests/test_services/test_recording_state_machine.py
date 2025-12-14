"""
Tests for RecordingStateMachine - Phase 10.5B Recording State Machine

TDD: Tests written FIRST before implementation.

State Machine:
    IDLE → MONITORING → RECORDING → FINISHING_GAME → IDLE
                ↑            │
                └────────────┘ (data integrity issue)

Tests cover:
- RecordingState enum values
- Initial state is IDLE
- State transitions (valid and invalid)
- Event callbacks for state changes
- Session limit tracking
- Data integrity issue handling
"""

import pytest
from unittest.mock import Mock, call
from datetime import datetime

# These imports will FAIL until we create the module (TDD RED phase)
from services.recording_state_machine import (
    RecordingState,
    RecordingStateMachine,
)


class TestRecordingState:
    """Tests for RecordingState enum"""

    @pytest.mark.parametrize("state,expected", [
        (RecordingState.IDLE, "idle"),
        (RecordingState.MONITORING, "monitoring"),
        (RecordingState.RECORDING, "recording"),
        (RecordingState.FINISHING_GAME, "finishing_game"),
    ])
    def test_state_values(self, state, expected):
        """Test all state values are correct"""
        assert state.value == expected


class TestRecordingStateMachineInitialization:
    """Tests for RecordingStateMachine initialization"""

    def test_initial_state_is_idle(self):
        """Test that initial state is IDLE"""
        sm = RecordingStateMachine()
        assert sm.state == RecordingState.IDLE

    def test_games_recorded_starts_at_zero(self):
        """Test that games recorded counter starts at 0"""
        sm = RecordingStateMachine()
        assert sm.games_recorded == 0

    def test_session_start_time_is_none_initially(self):
        """Test that session start time is None initially"""
        sm = RecordingStateMachine()
        assert sm.session_start_time is None

    def test_game_in_progress_is_false_initially(self):
        """Test that game_in_progress flag is False initially"""
        sm = RecordingStateMachine()
        assert sm.game_in_progress is False


class TestRecordingStateMachineStartSession:
    """Tests for starting a recording session"""

    def test_start_session_when_no_game_in_progress_goes_to_monitoring(self):
        """Test start_session goes to MONITORING when no game in progress"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        assert sm.state == RecordingState.MONITORING

    def test_start_session_when_game_in_progress_goes_to_monitoring(self):
        """Test start_session goes to MONITORING when game is in progress"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=True)
        assert sm.state == RecordingState.MONITORING

    def test_start_session_sets_session_start_time(self):
        """Test that start_session sets session start time"""
        sm = RecordingStateMachine()
        before = datetime.now()
        sm.start_session(game_in_progress=False)
        after = datetime.now()
        assert sm.session_start_time is not None
        assert before <= sm.session_start_time <= after

    def test_start_session_resets_games_recorded(self):
        """Test that start_session resets games recorded counter"""
        sm = RecordingStateMachine()
        sm._games_recorded = 5  # Simulate previous session
        sm.start_session(game_in_progress=False)
        assert sm.games_recorded == 0

    def test_start_session_from_non_idle_raises_error(self):
        """Test that start_session from non-IDLE state raises error"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)  # Now in MONITORING
        with pytest.raises(ValueError, match="Cannot start session"):
            sm.start_session(game_in_progress=False)

    def test_start_session_with_game_limit(self):
        """Test start_session with game limit"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=10)
        assert sm.game_limit == 10

    def test_start_session_with_infinite_game_limit(self):
        """Test start_session with infinite game limit (None)"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=None)
        assert sm.game_limit is None


class TestRecordingStateMachineGameEvents:
    """Tests for game start/end events"""

    def test_on_game_start_from_monitoring_goes_to_recording(self):
        """Test on_game_start from MONITORING goes to RECORDING"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        assert sm.state == RecordingState.MONITORING

        sm.on_game_start(game_id="game-123")
        assert sm.state == RecordingState.RECORDING

    def test_on_game_start_sets_current_game_id(self):
        """Test on_game_start sets current game ID"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        assert sm.current_game_id == "game-123"

    def test_on_game_start_from_idle_is_ignored(self):
        """Test on_game_start from IDLE is ignored"""
        sm = RecordingStateMachine()
        sm.on_game_start(game_id="game-123")
        assert sm.state == RecordingState.IDLE

    def test_on_game_end_from_recording_goes_to_monitoring(self):
        """Test on_game_end from RECORDING goes to MONITORING"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        assert sm.state == RecordingState.RECORDING

        sm.on_game_end(game_id="game-123")
        assert sm.state == RecordingState.MONITORING

    def test_on_game_end_increments_games_recorded(self):
        """Test on_game_end increments games recorded counter"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        assert sm.games_recorded == 0

        sm.on_game_end(game_id="game-123")
        assert sm.games_recorded == 1

    def test_on_game_end_clears_current_game_id(self):
        """Test on_game_end clears current game ID"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.on_game_end(game_id="game-123")
        assert sm.current_game_id is None

    def test_on_game_end_from_finishing_game_goes_to_idle(self):
        """Test on_game_end from FINISHING_GAME goes to IDLE"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=1)
        sm.on_game_start(game_id="game-123")
        # Manually trigger limit reached (normally done by on_game_end)
        sm._state = RecordingState.FINISHING_GAME

        sm.on_game_end(game_id="game-123")
        assert sm.state == RecordingState.IDLE

    def test_on_game_end_from_idle_is_ignored(self):
        """Test on_game_end from IDLE is ignored"""
        sm = RecordingStateMachine()
        sm.on_game_end(game_id="game-123")
        assert sm.state == RecordingState.IDLE
        assert sm.games_recorded == 0


class TestRecordingStateMachineSessionLimits:
    """Tests for session limit handling"""

    def test_game_limit_reached_goes_to_finishing_game_mid_game(self):
        """Test limit reached mid-game goes to FINISHING_GAME"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=1)
        sm.on_game_start(game_id="game-1")

        # Simulate reaching limit by external check
        assert sm.is_limit_reached() is False  # Not yet, game not ended

        sm.on_game_end(game_id="game-1")
        # After 1 game, limit of 1 is reached, should go to IDLE
        assert sm.state == RecordingState.IDLE
        assert sm.games_recorded == 1

    def test_limit_reached_after_multiple_games(self):
        """Test limit reached after multiple games"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=3)

        # Game 1
        sm.on_game_start(game_id="game-1")
        sm.on_game_end(game_id="game-1")
        assert sm.state == RecordingState.MONITORING
        assert sm.games_recorded == 1

        # Game 2
        sm.on_game_start(game_id="game-2")
        sm.on_game_end(game_id="game-2")
        assert sm.state == RecordingState.MONITORING
        assert sm.games_recorded == 2

        # Game 3 - should trigger limit
        sm.on_game_start(game_id="game-3")
        sm.on_game_end(game_id="game-3")
        assert sm.state == RecordingState.IDLE
        assert sm.games_recorded == 3

    def test_infinite_limit_never_triggers(self):
        """Test infinite limit (None) never triggers"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=None)

        # Record many games
        for i in range(100):
            sm.on_game_start(game_id=f"game-{i}")
            sm.on_game_end(game_id=f"game-{i}")

        assert sm.state == RecordingState.MONITORING
        assert sm.games_recorded == 100

    def test_is_limit_reached_with_game_limit(self):
        """Test is_limit_reached helper method"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False, game_limit=2)

        assert sm.is_limit_reached() is False

        sm.on_game_start(game_id="game-1")
        sm.on_game_end(game_id="game-1")
        assert sm.is_limit_reached() is False

        sm.on_game_start(game_id="game-2")
        sm.on_game_end(game_id="game-2")
        assert sm.is_limit_reached() is True


class TestRecordingStateMachineDataIntegrity:
    """Tests for data integrity issue handling"""

    def test_on_data_integrity_issue_from_recording_goes_to_monitoring(self):
        """Test data integrity issue from RECORDING goes to MONITORING"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        assert sm.state == RecordingState.RECORDING

        sm.on_data_integrity_issue(reason="connection_lost")
        assert sm.state == RecordingState.MONITORING

    def test_on_data_integrity_issue_clears_current_game(self):
        """Test data integrity issue clears current game (discard partial)"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")

        sm.on_data_integrity_issue(reason="data_gap")
        assert sm.current_game_id is None

    def test_on_data_integrity_issue_does_not_increment_games_recorded(self):
        """Test data integrity issue does not increment games recorded"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        assert sm.games_recorded == 0

        sm.on_data_integrity_issue(reason="abnormal_end")
        assert sm.games_recorded == 0  # Not incremented - game was discarded

    def test_on_data_integrity_issue_from_idle_is_ignored(self):
        """Test data integrity issue from IDLE is ignored"""
        sm = RecordingStateMachine()
        sm.on_data_integrity_issue(reason="test")
        assert sm.state == RecordingState.IDLE

    def test_on_data_integrity_issue_from_monitoring_is_ignored(self):
        """Test data integrity issue from MONITORING is ignored"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_data_integrity_issue(reason="test")
        assert sm.state == RecordingState.MONITORING


class TestRecordingStateMachineStopSession:
    """Tests for stopping a recording session"""

    def test_stop_session_from_idle_does_nothing(self):
        """Test stop_session from IDLE does nothing"""
        sm = RecordingStateMachine()
        sm.stop_session()
        assert sm.state == RecordingState.IDLE

    def test_stop_session_from_monitoring_goes_to_idle(self):
        """Test stop_session from MONITORING goes to IDLE"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.stop_session()
        assert sm.state == RecordingState.IDLE

    def test_stop_session_from_recording_goes_to_finishing_game(self):
        """Test stop_session from RECORDING goes to FINISHING_GAME"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.stop_session()
        assert sm.state == RecordingState.FINISHING_GAME

    def test_stop_session_preserves_current_game(self):
        """Test stop_session preserves current game for finishing"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.stop_session()
        assert sm.current_game_id == "game-123"

    def test_stop_session_from_finishing_game_is_ignored(self):
        """Test stop_session from FINISHING_GAME is ignored (already stopping)"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.stop_session()
        assert sm.state == RecordingState.FINISHING_GAME

        sm.stop_session()  # Second call
        assert sm.state == RecordingState.FINISHING_GAME  # Still finishing


class TestRecordingStateMachineCallbacks:
    """Tests for state change callbacks"""

    def test_on_state_change_callback_called(self):
        """Test on_state_change callback is called on transitions"""
        sm = RecordingStateMachine()
        callback = Mock()
        sm.on_state_change = callback

        sm.start_session(game_in_progress=False)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == RecordingState.IDLE  # old state
        assert args[1] == RecordingState.MONITORING  # new state

    def test_on_state_change_callback_called_multiple_times(self):
        """Test callback called for each state transition"""
        sm = RecordingStateMachine()
        callback = Mock()
        sm.on_state_change = callback

        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-1")
        sm.on_game_end(game_id="game-1")

        assert callback.call_count == 3
        calls = callback.call_args_list
        # IDLE -> MONITORING
        assert calls[0][0] == (RecordingState.IDLE, RecordingState.MONITORING)
        # MONITORING -> RECORDING
        assert calls[1][0] == (RecordingState.MONITORING, RecordingState.RECORDING)
        # RECORDING -> MONITORING
        assert calls[2][0] == (RecordingState.RECORDING, RecordingState.MONITORING)

    def test_on_game_recorded_callback_called(self):
        """Test on_game_recorded callback is called when game ends successfully"""
        sm = RecordingStateMachine()
        callback = Mock()
        sm.on_game_recorded = callback

        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.on_game_end(game_id="game-123")

        callback.assert_called_once_with("game-123")

    def test_on_game_recorded_not_called_on_integrity_issue(self):
        """Test on_game_recorded NOT called when data integrity issue occurs"""
        sm = RecordingStateMachine()
        callback = Mock()
        sm.on_game_recorded = callback

        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")
        sm.on_data_integrity_issue(reason="test")

        callback.assert_not_called()

    def test_on_session_complete_callback_called(self):
        """Test on_session_complete callback is called when session ends"""
        sm = RecordingStateMachine()
        callback = Mock()
        sm.on_session_complete = callback

        sm.start_session(game_in_progress=False, game_limit=1)
        sm.on_game_start(game_id="game-1")
        sm.on_game_end(game_id="game-1")

        callback.assert_called_once_with(1)  # 1 game recorded


class TestRecordingStateMachineEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_game_end_with_wrong_game_id_is_ignored(self):
        """Test game end with wrong game ID is ignored"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-123")

        sm.on_game_end(game_id="wrong-game-id")

        assert sm.state == RecordingState.RECORDING
        assert sm.current_game_id == "game-123"

    def test_game_start_while_recording_is_ignored(self):
        """Test game start while already recording is ignored"""
        sm = RecordingStateMachine()
        sm.start_session(game_in_progress=False)
        sm.on_game_start(game_id="game-1")

        sm.on_game_start(game_id="game-2")

        assert sm.state == RecordingState.RECORDING
        assert sm.current_game_id == "game-1"  # Still first game

    def test_is_recording_helper(self):
        """Test is_recording helper method"""
        sm = RecordingStateMachine()
        assert sm.is_recording() is False

        sm.start_session(game_in_progress=False)
        assert sm.is_recording() is False

        sm.on_game_start(game_id="game-1")
        assert sm.is_recording() is True

        sm.on_game_end(game_id="game-1")
        assert sm.is_recording() is False

    def test_is_active_helper(self):
        """Test is_active helper (session in progress but not necessarily recording)"""
        sm = RecordingStateMachine()
        assert sm.is_active() is False

        sm.start_session(game_in_progress=False)
        assert sm.is_active() is True

        sm.on_game_start(game_id="game-1")
        assert sm.is_active() is True

        sm.stop_session()
        assert sm.is_active() is True  # Still finishing game

        sm.on_game_end(game_id="game-1")
        assert sm.is_active() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
