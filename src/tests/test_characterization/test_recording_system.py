"""
Recording System Characterization Tests - Issue #18

Documents CURRENT behavior of the dual recording systems:
1. Legacy: ReplayEngine.auto_recording + RecorderSink
2. Phase 10.5: RecordingController + UnifiedRecorder + RecordingStateMachine

These tests capture existing behavior as a safety net.
DO NOT modify expected values to make tests pass.

Key Finding: Two independent recording state machines exist.
The UI may show state from one system while logs show another.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from pathlib import Path


@pytest.fixture
def mock_config():
    """Provide mock config for ReplayEngine tests."""
    mock_cfg = MagicMock()
    mock_cfg.LIVE_FEED = {
        'ring_buffer_size': 100,
        'recording_buffer_size': 100,
        'auto_recording': False
    }
    mock_cfg.FILES = {
        'recordings_dir': '/tmp/recordings'
    }
    return mock_cfg


@pytest.fixture
def mock_game_state():
    """Provide mock GameState for ReplayEngine tests."""
    state = MagicMock()
    state.get_current_tick.return_value = None
    state.add_observer = MagicMock()
    state.remove_observer = MagicMock()
    return state


class TestRecordingStateSources:
    """Document all sources of 'is recording?' truth."""

    def test_legacy_replay_engine_has_auto_recording_flag(self, mock_config, mock_game_state):
        """
        Document: ReplayEngine has auto_recording attribute.

        ReplayEngine.auto_recording controls whether new games
        are automatically recorded. Default is False.
        """
        from core.replay_engine import ReplayEngine

        with patch('config.config', mock_config):
            engine = ReplayEngine(mock_game_state)

            # Document: auto_recording defaults to False
            assert engine.auto_recording == False

            # Document: Can be enabled via method
            engine.enable_recording()
            assert engine.auto_recording == True

            # Cleanup
            engine.cleanup()

    def test_legacy_recorder_sink_has_is_recording_method(self):
        """
        Document: RecorderSink.is_recording() tracks active recording.

        This is separate from ReplayEngine.auto_recording.
        auto_recording = True doesn't mean is_recording() = True.
        """
        from core.recorder_sink import RecorderSink

        sink = RecorderSink(
            recordings_dir='/tmp/recordings',
            buffer_size=10
        )

        # Document: Initially not recording
        assert sink.is_recording() == False

        # Document: start_recording changes state
        sink.start_recording(game_id='test123')
        assert sink.is_recording() == True

        # Document: stop_recording changes state back
        sink.stop_recording()
        assert sink.is_recording() == False

    def test_phase105_state_machine_has_multiple_states(self):
        """
        Document: RecordingStateMachine has 4 distinct states.

        States: IDLE, MONITORING, RECORDING, FINISHING_GAME
        This is more granular than the legacy boolean flags.
        """
        from services.recording_state_machine import RecordingStateMachine, RecordingState

        sm = RecordingStateMachine()

        # Document: Initial state is IDLE
        assert sm.state == RecordingState.IDLE

        # Document: start_session transitions to MONITORING (not RECORDING)
        sm.start_session(game_in_progress=False)
        assert sm.state == RecordingState.MONITORING

        # Document: Game start transitions to RECORDING
        sm.on_game_start('test123')
        assert sm.state == RecordingState.RECORDING

        # Document: is_recording() only True in RECORDING state
        assert sm.is_recording() == True

        # Document: is_active() True for all non-IDLE states
        assert sm.is_active() == True

    def test_recording_controller_wraps_state_machine(self):
        """
        Document: RecordingController.is_recording delegates to UnifiedRecorder.

        When _recorder is None, is_recording returns False.
        """
        from ui.controllers.recording_controller import RecordingController

        with patch('ui.controllers.recording_controller.RecordingConfig') as mock_cfg:
            mock_cfg.load.return_value = Mock(
                capture_mode=Mock(value='market'),
                audio_cues=False,
                game_count=10
            )

            root = MagicMock()
            controller = RecordingController(
                root=root,
                recordings_path='/tmp/recordings',
                game_state=None
            )

            # Document: Without starting session, is_recording is False
            assert controller.is_recording == False
            assert controller.is_active == False

            # Document: current_state is None when no recorder
            assert controller.current_state is None


class TestStateMismatchScenarios:
    """
    Document scenarios where state sources can disagree.

    Issue #18: Logs show 'disabled' but UI shows 'enabled'
    """

    def test_legacy_and_phase105_are_independent(self):
        """
        Document: Legacy ReplayEngine and Phase 10.5 RecordingController
        are completely independent systems.

        Neither knows about the other's state.
        """
        from services.recording_state_machine import RecordingStateMachine, RecordingState
        from core.recorder_sink import RecorderSink

        # Legacy system
        legacy_sink = RecorderSink(
            recordings_dir='/tmp/recordings',
            buffer_size=10
        )

        # Phase 10.5 system
        phase105_sm = RecordingStateMachine()

        # Document: Can have legacy recording while phase105 is idle
        legacy_sink.start_recording('game1')
        assert legacy_sink.is_recording() == True
        assert phase105_sm.state == RecordingState.IDLE

        # Document: Can have phase105 recording while legacy is not
        legacy_sink.stop_recording()
        phase105_sm.start_session()
        phase105_sm.on_game_start('game2')

        assert legacy_sink.is_recording() == False
        assert phase105_sm.is_recording() == True

    def test_replay_engine_get_recording_info_shows_legacy_state(self, mock_config, mock_game_state):
        """
        Document: ReplayEngine.get_recording_info() only shows legacy state.

        This is what some UI/log code may use, unaware of Phase 10.5.
        """
        from core.replay_engine import ReplayEngine

        with patch('config.config', mock_config):
            engine = ReplayEngine(mock_game_state)

            info = engine.get_recording_info()

            # Document: Returns legacy system state only
            assert 'enabled' in info  # auto_recording flag
            assert 'active' in info   # recorder_sink.is_recording()
            assert info['enabled'] == False
            assert info['active'] == False

            engine.cleanup()


class TestLogMessageTriggers:
    """Document when 'recording disabled' appears in logs."""

    def test_disable_recording_logs_when_auto_recording_was_true(self, mock_config, mock_game_state):
        """
        Document: disable_recording() logs 'Recording already disabled'
        when auto_recording is False.
        """
        from core.replay_engine import ReplayEngine
        import logging

        with patch('config.config', mock_config):
            engine = ReplayEngine(mock_game_state)

            # Document: Calling disable when already disabled logs this
            with patch('core.replay_engine.logger') as mock_logger:
                engine.disable_recording()
                mock_logger.info.assert_called_with("Recording already disabled")

            engine.cleanup()

    def test_on_live_tick_logs_recording_disabled(self, mock_config, mock_game_state):
        """
        Document: on_live_tick logs 'recording disabled' when
        auto_recording is False and a new game starts.

        This is one source of the 'disabled' log message.
        """
        from core.replay_engine import ReplayEngine
        from models import GameTick
        from decimal import Decimal

        with patch('config.config', mock_config):
            engine = ReplayEngine(mock_game_state)
            engine.is_live_mode = False  # Will be set to True on first tick
            engine.game_id = None  # No current game

            # Create a tick for a new game
            tick = GameTick(
                game_id='test_game_123',
                tick=1,
                timestamp='2025-01-01T00:00:00',
                price=Decimal('1.5'),
                phase='ACTIVE',
                active=True,
                rugged=False,
                cooldown_timer=0,
                trade_count=0
            )

            with patch('core.replay_engine.logger') as mock_logger:
                engine.push_tick(tick)

                # Document: This logs "Started live game: ... (recording disabled)"
                # Find the call that contains 'recording disabled'
                calls = [str(c) for c in mock_logger.info.call_args_list]
                found_recording_disabled = any('recording disabled' in c for c in calls)
                assert found_recording_disabled, f"Expected 'recording disabled' in logs, got: {calls}"

            engine.cleanup()


class TestUIStateVariables:
    """Document UI state variable behavior."""

    def test_recording_controller_get_status_returns_dict(self):
        """
        Document: RecordingController.get_status() returns status dict.

        This is what UI should use to display recording state.
        """
        from ui.controllers.recording_controller import RecordingController

        with patch('ui.controllers.recording_controller.RecordingConfig') as mock_cfg:
            mock_cfg.load.return_value = Mock(
                capture_mode=Mock(value='market'),
                audio_cues=False,
                game_count=10
            )

            root = MagicMock()
            controller = RecordingController(
                root=root,
                recordings_path='/tmp/recordings',
                game_state=None
            )

            status = controller.get_status()

            # Document: Status structure when not recording
            assert status['state'] == 'idle'
            assert status['games_recorded'] == 0
            assert status['capture_mode'] == 'market'
            assert status['is_healthy'] == True
