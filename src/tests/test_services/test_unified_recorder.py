"""
Tests for UnifiedRecorder - Phase 10.5D Unified Recorder

TDD: Tests written FIRST before implementation.

The UnifiedRecorder orchestrates GameStateRecorder + PlayerSessionRecorder,
respects capture mode settings, and integrates with the state machine
and data integrity monitor.

Tests cover:
- Initialization with config
- Game state only mode
- Game + player state mode
- Integration with RecordingStateMachine
- Integration with DataIntegrityMonitor
- File organization (games/ + demonstrations/)
- Session lifecycle
"""

import json
import os
import pytest
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# These imports will FAIL until we create the module (TDD RED phase)
from services.unified_recorder import UnifiedRecorder
from models.recording_config import RecordingConfig, CaptureMode
from models.recording_models import PlayerAction
from services.recording_state_machine import RecordingState, RecordingStateMachine
from sources.data_integrity_monitor import DataIntegrityMonitor, ThresholdType


class TestUnifiedRecorderInitialization:
    """Tests for UnifiedRecorder initialization"""

    def test_initialization_with_default_config(self):
        """Test initialization with default config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            assert recorder.config.capture_mode == CaptureMode.GAME_STATE_ONLY
            assert recorder.is_recording is False

    def test_initialization_with_custom_config(self):
        """Test initialization with custom config"""
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=10
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            assert recorder.config.capture_mode == CaptureMode.GAME_AND_PLAYER
            assert recorder.config.game_count == 10

    def test_initialization_creates_state_machine(self):
        """Test that initialization creates a state machine"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            assert recorder.state_machine is not None
            assert recorder.state_machine.state == RecordingState.IDLE

    def test_initialization_creates_integrity_monitor(self):
        """Test that initialization creates an integrity monitor"""
        config = RecordingConfig(
            monitor_threshold_type=ThresholdType.GAMES,
            monitor_threshold_value=5
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            assert recorder.integrity_monitor is not None
            assert recorder.integrity_monitor.threshold_type == ThresholdType.GAMES
            assert recorder.integrity_monitor.threshold_value == 5


class TestUnifiedRecorderSessionLifecycle:
    """Tests for session start/stop lifecycle"""

    def test_start_session_transitions_to_monitoring(self):
        """Test start_session transitions state machine to MONITORING"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            recorder.start_session()
            assert recorder.state_machine.state == RecordingState.MONITORING
            assert recorder.is_active is True

    def test_start_session_with_game_in_progress(self):
        """Test start_session with game already in progress"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            recorder.start_session(game_in_progress=True)
            assert recorder.state_machine.state == RecordingState.MONITORING

    def test_stop_session_returns_to_idle(self):
        """Test stop_session returns to IDLE"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            recorder.start_session()
            recorder.stop_session()
            assert recorder.state_machine.state == RecordingState.IDLE
            assert recorder.is_active is False

    def test_stop_session_mid_game_finishes_game(self):
        """Test stop_session mid-game goes to FINISHING_GAME"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")
            recorder.stop_session()
            assert recorder.state_machine.state == RecordingState.FINISHING_GAME


class TestUnifiedRecorderGameStateOnly:
    """Tests for GAME_STATE_ONLY capture mode"""

    def test_records_game_state(self):
        """Test that game state is recorded"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            # Simulate ticks
            for tick in range(10):
                recorder.on_tick(tick=tick, price=Decimal("1.0") + Decimal(tick) / 100)

            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0") + Decimal(i) / 100 for i in range(10)],
                peak=Decimal("1.09")
            )

            # Verify game was recorded
            assert recorder.games_recorded == 1

    def test_does_not_record_player_state(self):
        """Test that player state is NOT recorded in GAME_STATE_ONLY mode"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            # Record an action - should be ignored
            action = PlayerAction(
                game_id="game-123",
                tick=5,
                timestamp=datetime.utcnow(),
                action="BUY",
                amount=Decimal("0.001"),
                price=Decimal("1.05"),
                balance_after=Decimal("0.999"),
                position_qty_after=Decimal("0.001")
            )
            recorder.on_player_action(action)

            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            # Check no player file exists
            demonstrations_dir = Path(tmpdir) / "demonstrations"
            assert not demonstrations_dir.exists() or not any(demonstrations_dir.iterdir())

    def test_on_game_end_without_prices_calculates_from_ticks(self):
        """Test that on_game_end can calculate prices and peak from collected ticks"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-456")

            # Simulate ticks - prices go up then down
            prices = [Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("1.8"), Decimal("1.2")]
            for tick, price in enumerate(prices):
                recorder.on_tick(tick=tick, price=price)

            # Call on_game_end WITHOUT prices and peak - should calculate internally
            recorder.on_game_end(game_id="game-456")

            # Verify game was recorded
            assert recorder.games_recorded == 1

            # Verify the saved file has correct data
            games_dir = Path(tmpdir) / "games"
            game_files = list(games_dir.glob("*.game.json"))
            assert len(game_files) == 1

            with open(game_files[0]) as f:
                game_data = json.load(f)

            # Check peak was calculated correctly (max of prices = 2.0)
            assert Decimal(str(game_data["meta"]["peak_multiplier"])) == Decimal("2.0")
            # Check prices were stored
            assert len(game_data["prices"]) == 5


class TestUnifiedRecorderGameAndPlayer:
    """Tests for GAME_AND_PLAYER capture mode"""

    def test_records_both_game_and_player(self):
        """Test that both game and player state are recorded"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_AND_PLAYER)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(
                base_path=tmpdir,
                config=config,
                player_id="player-123",
                username="TestUser"
            )
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            # Record an action
            action = PlayerAction(
                game_id="game-123",
                tick=5,
                timestamp=datetime.utcnow(),
                action="BUY",
                amount=Decimal("0.001"),
                price=Decimal("1.05"),
                balance_after=Decimal("0.999"),
                position_qty_after=Decimal("0.001")
            )
            recorder.on_player_action(action)

            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            recorder.stop_session()

            # Verify files exist
            games_dir = Path(tmpdir) / "games"
            demonstrations_dir = Path(tmpdir) / "demonstrations"

            assert games_dir.exists()
            # Player file should exist since we had actions
            assert demonstrations_dir.exists()

    def test_game_file_has_player_input_flag(self):
        """Test that game file has has_player_input flag when player data exists"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_AND_PLAYER)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(
                base_path=tmpdir,
                config=config,
                player_id="player-123",
                username="TestUser"
            )
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            action = PlayerAction(
                game_id="game-123",
                tick=5,
                timestamp=datetime.utcnow(),
                action="BUY",
                amount=Decimal("0.001"),
                price=Decimal("1.05"),
                balance_after=Decimal("0.999"),
                position_qty_after=Decimal("0.001")
            )
            recorder.on_player_action(action)

            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            # Find and check game file
            games_dir = Path(tmpdir) / "games"
            game_files = list(games_dir.glob("*.json"))
            assert len(game_files) == 1

            with open(game_files[0]) as f:
                game_data = json.load(f)
            assert game_data["meta"]["has_player_input"] is True


class TestUnifiedRecorderIntegrityMonitor:
    """Tests for DataIntegrityMonitor integration"""

    def test_tick_gaps_trigger_monitor_mode(self):
        """Test that tick gaps trigger monitor mode"""
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_STATE_ONLY,
            monitor_threshold_type=ThresholdType.TICKS,
            monitor_threshold_value=5
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            # Create tick gap exceeding threshold
            recorder.on_tick(tick=0, price=Decimal("1.0"))
            recorder.on_tick(tick=10, price=Decimal("1.1"))  # Gap of 9

            # Should have triggered and discarded game
            assert recorder.state_machine.state == RecordingState.MONITORING
            assert recorder.integrity_monitor.is_triggered is True

    def test_connection_lost_triggers_monitor_mode(self):
        """Test that connection loss triggers monitor mode"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            recorder.on_connection_lost()

            assert recorder.state_machine.state == RecordingState.MONITORING
            assert recorder.integrity_monitor.is_triggered is True

    def test_clean_game_resets_triggered_state(self):
        """Test that clean game observation resets triggered state"""
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_STATE_ONLY,
            monitor_threshold_type=ThresholdType.TICKS,
            monitor_threshold_value=5
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()

            # Trigger via connection loss
            recorder.on_connection_lost()
            assert recorder.integrity_monitor.is_triggered is True

            # Observe clean game
            recorder.on_game_start(game_id="game-clean")
            for tick in range(5):
                recorder.on_tick(tick=tick, price=Decimal("1.0"))
            recorder.on_game_end(
                game_id="game-clean",
                prices=[Decimal("1.0")] * 5,
                peak=Decimal("1.0"),
                clean=True
            )

            # Should be recovered
            assert recorder.integrity_monitor.is_triggered is False


class TestUnifiedRecorderFileOrganization:
    """Tests for file organization"""

    def test_games_saved_to_games_directory(self):
        """Test that games are saved to games/ directory"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")
            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            games_dir = Path(tmpdir) / "games"
            assert games_dir.exists()
            assert len(list(games_dir.glob("*.json"))) == 1

    def test_demonstrations_saved_to_demonstrations_directory(self):
        """Test that player data saved to demonstrations/ directory"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_AND_PLAYER)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(
                base_path=tmpdir,
                config=config,
                player_id="player-123",
                username="TestUser"
            )
            recorder.start_session()
            recorder.on_game_start(game_id="game-123")

            action = PlayerAction(
                game_id="game-123",
                tick=5,
                timestamp=datetime.utcnow(),
                action="BUY",
                amount=Decimal("0.001"),
                price=Decimal("1.05"),
                balance_after=Decimal("0.999"),
                position_qty_after=Decimal("0.001")
            )
            recorder.on_player_action(action)

            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )
            recorder.stop_session()

            demonstrations_dir = Path(tmpdir) / "demonstrations"
            assert demonstrations_dir.exists()


class TestUnifiedRecorderCallbacks:
    """Tests for callbacks"""

    def test_on_game_recorded_callback(self):
        """Test on_game_recorded callback is called"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            callback = Mock()
            recorder.on_game_recorded = callback

            recorder.start_session()
            recorder.on_game_start(game_id="game-123")
            recorder.on_game_end(
                game_id="game-123",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            callback.assert_called_once()
            args = callback.call_args[0]
            # game_id shortened: game-123 -> 123 in filename
            assert "123" in args[0]  # game_id suffix in filepath

    def test_on_session_complete_callback(self):
        """Test on_session_complete callback is called"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_STATE_ONLY, game_count=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            callback = Mock()
            recorder.on_session_complete = callback

            recorder.start_session()
            recorder.on_game_start(game_id="game-1")
            recorder.on_game_end(
                game_id="game-1",
                prices=[Decimal("1.0")],
                peak=Decimal("1.0")
            )

            callback.assert_called_once_with(1)  # 1 game recorded

    def test_on_state_change_callback(self):
        """Test on_state_change callback is called"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            callback = Mock()
            recorder.on_state_change = callback

            recorder.start_session()

            callback.assert_called()
            # Should have IDLE -> MONITORING transition
            args = callback.call_args[0]
            assert args[0] == RecordingState.IDLE
            assert args[1] == RecordingState.MONITORING


class TestUnifiedRecorderHelpers:
    """Tests for helper methods"""

    def test_is_recording_property(self):
        """Test is_recording property"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            assert recorder.is_recording is False

            recorder.start_session()
            assert recorder.is_recording is False  # Monitoring, not recording

            recorder.on_game_start(game_id="game-1")
            assert recorder.is_recording is True

            recorder.on_game_end(game_id="game-1", prices=[], peak=Decimal("1.0"))
            assert recorder.is_recording is False

    def test_is_active_property(self):
        """Test is_active property"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            assert recorder.is_active is False

            recorder.start_session()
            assert recorder.is_active is True

            recorder.stop_session()
            assert recorder.is_active is False

    def test_games_recorded_counter(self):
        """Test games_recorded counter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir)
            recorder.start_session()

            assert recorder.games_recorded == 0

            for i in range(3):
                recorder.on_game_start(game_id=f"game-{i}")
                recorder.on_game_end(
                    game_id=f"game-{i}",
                    prices=[Decimal("1.0")],
                    peak=Decimal("1.0")
                )

            assert recorder.games_recorded == 3

    def test_get_status(self):
        """Test get_status returns comprehensive status"""
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=10
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = UnifiedRecorder(base_path=tmpdir, config=config)
            recorder.start_session()

            status = recorder.get_status()

            assert "state" in status
            assert "games_recorded" in status
            assert "capture_mode" in status
            assert "game_limit" in status
            assert "is_healthy" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
