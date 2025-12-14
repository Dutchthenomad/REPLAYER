"""
Unified Recorder - Phase 10.5D

Orchestrates GameStateRecorder + PlayerSessionRecorder with unified
state machine and data integrity monitoring.

Respects capture mode:
- GAME_STATE_ONLY: Only records game state (prices)
- GAME_AND_PLAYER: Records both game state and player actions

File organization:
- games/ - Game state recordings
- demonstrations/ - Player session recordings (when has_player_input)
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional

from models.recording_config import RecordingConfig, CaptureMode
from models.recording_models import (
    GameStateRecord,
    GameStateMeta,
    PlayerSession,
    PlayerSessionMeta,
    PlayerAction,
    # Phase 10.6: Validation-aware models
    ServerState,
    LocalStateSnapshot,
    RecordedAction,
    validate_states,
)
from models.demo_action import ActionCategory, get_category_for_button, is_trade_action
from services.recording_state_machine import RecordingState, RecordingStateMachine
from sources.data_integrity_monitor import DataIntegrityMonitor, ThresholdType, IntegrityIssue

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class UnifiedRecorder:
    """
    Unified recording orchestrator for game state and player actions.

    Manages:
    - Recording state machine (IDLE -> MONITORING -> RECORDING -> FINISHING_GAME)
    - Data integrity monitoring (tick gaps, connection loss, abnormal endings)
    - Game state recording (prices, metadata)
    - Player session recording (actions, state snapshots)

    Usage:
        recorder = UnifiedRecorder(
            base_path="/path/to/recordings",
            config=RecordingConfig(capture_mode=CaptureMode.GAME_AND_PLAYER),
            player_id="player-123",
            username="TestUser"
        )
        recorder.start_session()

        # Handle game events
        recorder.on_game_start(game_id="abc")
        recorder.on_tick(tick=0, price=Decimal("1.0"))
        recorder.on_player_action(action)
        recorder.on_game_end(game_id="abc", prices=[...], peak=Decimal("1.5"))

        recorder.stop_session()
    """

    def __init__(
        self,
        base_path: str,
        config: Optional[RecordingConfig] = None,
        player_id: Optional[str] = None,
        username: Optional[str] = None
    ):
        """
        Initialize the unified recorder.

        Args:
            base_path: Base directory for recordings
            config: Recording configuration (defaults to GAME_STATE_ONLY)
            player_id: Player ID (required for GAME_AND_PLAYER mode)
            username: Player username (required for GAME_AND_PLAYER mode)
        """
        self.base_path = Path(base_path)
        self._config = config or RecordingConfig()
        self._player_id = player_id
        self._username = username

        # State machine
        self._state_machine = RecordingStateMachine()

        # Data integrity monitor
        self._integrity_monitor = DataIntegrityMonitor(
            threshold_type=self._config.monitor_threshold_type,
            threshold_value=self._config.monitor_threshold_value
        )

        # Current game state
        self._current_game: Optional[GameStateRecord] = None
        self._current_game_start: Optional[datetime] = None
        self._current_game_has_player_input = False
        self._current_game_ticks: List[Decimal] = []

        # Current player session
        self._player_session: Optional[PlayerSession] = None
        self._player_session_start: Optional[datetime] = None
        self._pending_actions: List[PlayerAction] = []

        # Phase 10.6: Button recording state
        self._current_game_actions: List[RecordedAction] = []
        self._action_file_handle = None
        self._last_server_state: Optional[ServerState] = None
        self._pending_trade_actions: Dict[str, RecordedAction] = {}  # action_id -> action

        # Callbacks
        self.on_game_recorded: Optional[Callable[[str], None]] = None
        self.on_session_complete: Optional[Callable[[int], None]] = None
        self.on_state_change: Optional[Callable[[RecordingState, RecordingState], None]] = None

        # Wire up internal callbacks
        self._state_machine.on_state_change = self._handle_state_change
        self._state_machine.on_game_recorded = self._handle_game_recorded
        self._state_machine.on_session_complete = self._handle_session_complete
        self._integrity_monitor.on_threshold_exceeded = self._handle_integrity_issue
        self._integrity_monitor.on_recovery = self._handle_integrity_recovery

    @property
    def config(self) -> RecordingConfig:
        """Recording configuration."""
        return self._config

    @property
    def state_machine(self) -> RecordingStateMachine:
        """Recording state machine."""
        return self._state_machine

    @property
    def integrity_monitor(self) -> DataIntegrityMonitor:
        """Data integrity monitor."""
        return self._integrity_monitor

    @property
    def is_recording(self) -> bool:
        """Whether currently recording a game."""
        return self._state_machine.state == RecordingState.RECORDING

    @property
    def is_active(self) -> bool:
        """Whether session is active (not IDLE)."""
        return self._state_machine.state != RecordingState.IDLE

    @property
    def games_recorded(self) -> int:
        """Number of games recorded in this session."""
        return self._state_machine.games_recorded

    def start_session(self, game_in_progress: bool = False) -> None:
        """
        Start a recording session.

        Args:
            game_in_progress: Whether a game is already in progress
        """
        self._state_machine.start_session(
            game_in_progress=game_in_progress,
            game_limit=self._config.game_count
        )

        # Start player session if in GAME_AND_PLAYER mode
        if self._config.capture_mode == CaptureMode.GAME_AND_PLAYER:
            self._start_player_session()

        logger.info(f"Started recording session (mode={self._config.capture_mode.value})")

    def stop_session(self) -> None:
        """Stop the recording session."""
        self._state_machine.stop_session()

        # Save player session if any actions recorded
        if self._player_session and self._pending_actions:
            self._save_player_session()

        logger.info(f"Stopped recording session (games_recorded={self.games_recorded})")

    def on_game_start(self, game_id: str) -> None:
        """
        Handle game start event.

        Args:
            game_id: Unique game identifier
        """
        # Notify state machine
        self._state_machine.on_game_start(game_id)

        # Notify integrity monitor
        self._integrity_monitor.on_game_start(game_id)

        # Only start recording if not triggered (integrity issue)
        if not self._integrity_monitor.is_triggered:
            self._start_game_recording(game_id)

        logger.debug(f"Game start: {game_id}")

    def on_tick(self, tick: int, price: Decimal) -> None:
        """
        Handle tick event.

        Args:
            tick: Tick number
            price: Price at this tick
        """
        # Feed to integrity monitor
        self._integrity_monitor.on_tick(tick)

        # If integrity triggered mid-game, discard current game
        if self._integrity_monitor.is_triggered:
            self._discard_current_game()
            return

        # Record tick if we have an active game
        if self._current_game:
            self._current_game.add_price(tick, price)
            self._current_game_ticks.append(price)

    def on_game_end(
        self,
        game_id: str,
        prices: Optional[List[Decimal]] = None,
        peak: Optional[Decimal] = None,
        clean: bool = True,
        seed_data: Optional[dict] = None
    ) -> None:
        """
        Handle game end event.

        Args:
            game_id: Game identifier
            prices: Complete price list (optional - calculated from ticks if not provided)
            peak: Peak multiplier reached (optional - calculated from prices if not provided)
            clean: Whether game ended cleanly (proper rug/crash)
            seed_data: Optional server seed data
        """
        # Notify integrity monitor of game end
        self._integrity_monitor.on_game_end(game_id, clean)

        # If triggered, we need to handle recovery first
        was_triggered = self._integrity_monitor.is_triggered

        # If clean game, try to recover from triggered state
        if clean and was_triggered:
            self._integrity_monitor.on_clean_game_observed()

        # If still triggered after recovery attempt, discard
        if self._integrity_monitor.is_triggered:
            self._discard_current_game()
            self._state_machine.on_data_integrity_issue("data_integrity")
            return

        # Calculate prices and peak from internal state if not provided
        if prices is None:
            prices = self._current_game_ticks.copy() if self._current_game_ticks else []

        if peak is None:
            peak = max(self._current_game_ticks) if self._current_game_ticks else Decimal("1.0")

        # Save the game if we have one
        if self._current_game:
            self._finalize_game(prices, peak, seed_data)
            filepath = self._save_game()

            if filepath:
                # Notify state machine
                self._state_machine.on_game_end(game_id)

    def on_player_action(self, action: PlayerAction) -> None:
        """
        Record a player action.

        Args:
            action: PlayerAction to record
        """
        # Only record in GAME_AND_PLAYER mode
        if self._config.capture_mode != CaptureMode.GAME_AND_PLAYER:
            return

        # Only record if we're actively recording a game
        if not self.is_recording:
            return

        self._pending_actions.append(action)
        self._current_game_has_player_input = True

        if self._player_session:
            self._player_session.add_action(action)

        logger.debug(f"Recorded player action: {action.action}")

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection loss."""
        self._integrity_monitor.on_connection_lost()
        self._discard_current_game()
        self._state_machine.on_data_integrity_issue("connection_lost")

    def on_connection_restored(self) -> None:
        """Handle WebSocket connection restored."""
        self._integrity_monitor.on_connection_restored()

    # =========================================================================
    # Phase 10.6: Button Recording with Validation
    # =========================================================================

    def update_server_state(self, server_state: ServerState) -> None:
        """
        Update the latest server state from WebSocket playerUpdate.

        Args:
            server_state: Latest server state from WebSocket
        """
        self._last_server_state = server_state

    def record_button_press(
        self,
        button: str,
        local_state: LocalStateSnapshot,
        amount: Optional[Decimal] = None,
        server_state: Optional[ServerState] = None
    ) -> Optional[RecordedAction]:
        """
        Record a button press with dual-state validation.

        Phase 10.6: Records ALL button presses (not just trades) with
        local vs server state validation.

        Args:
            button: Button text (e.g., 'BUY', '+0.01', '25%', 'X')
            local_state: REPLAYER's calculated state at action time
            amount: Trade amount (for BUY/SELL/SIDEBET)
            server_state: Server state (uses last cached if not provided)

        Returns:
            RecordedAction if recorded, None if not recording
        """
        # Only record if we're actively recording a game
        if not self.is_recording or not self._current_game:
            return None

        # Use provided server state or last cached
        server = server_state or self._last_server_state

        # Categorize the button
        try:
            category = get_category_for_button(button)
        except ValueError:
            logger.warning(f"Unknown button: {button}")
            category = ActionCategory.BET_INCREMENT

        # Validate states (zero tolerance)
        drift_detected = False
        drift_details = None
        if server:
            drift_detected, drift_details = validate_states(local_state, server)
            if drift_detected:
                logger.warning(f"Drift detected on {button}: {drift_details}")

        # Create recorded action
        action = RecordedAction(
            game_id=self._current_game.meta.game_id,
            tick=local_state.current_tick,
            timestamp=datetime.utcnow(),
            category=category.value,
            button=button,
            amount=amount,
            local_state=local_state,
            server_state=server,
            drift_detected=drift_detected,
            drift_details=drift_details,
        )

        # Store action
        self._current_game_actions.append(action)
        self._current_game_has_player_input = True

        # If it's a trade action, track for confirmation
        if is_trade_action(category):
            self._pending_trade_actions[action.action_id] = action

        # Write to JSONL file if open
        if self._action_file_handle:
            line = json.dumps(action.to_dict(), cls=DecimalEncoder) + "\n"
            self._action_file_handle.write(line)
            self._action_file_handle.flush()

        logger.debug(f"Recorded button: {button} (drift={drift_detected})")
        return action

    def record_trade_confirmation(
        self,
        action_id: str,
        timestamp_ms: int
    ) -> Optional[float]:
        """
        Record trade confirmation and calculate latency.

        Args:
            action_id: ID of the action to confirm
            timestamp_ms: Confirmation timestamp in milliseconds

        Returns:
            Latency in ms if found, None otherwise
        """
        action = self._pending_trade_actions.pop(action_id, None)
        if action:
            latency = action.record_confirmation(timestamp_ms)
            logger.debug(f"Trade confirmed: {action.button} latency={latency:.0f}ms")
            return latency
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        return {
            "state": self._state_machine.state.value,
            "games_recorded": self.games_recorded,
            "capture_mode": self._config.capture_mode.value,
            "game_limit": self._config.game_count,
            "is_healthy": self._integrity_monitor.is_healthy(),
            "current_game_id": self._state_machine.current_game_id,
            "integrity_status": self._integrity_monitor.get_status(),
        }

    # Internal methods

    def _start_game_recording(self, game_id: str) -> None:
        """Start recording a new game."""
        self._current_game_start = datetime.utcnow()
        self._current_game = GameStateRecord(
            meta=GameStateMeta(
                game_id=game_id,
                start_time=self._current_game_start
            )
        )
        self._current_game_has_player_input = False
        self._current_game_ticks = []
        self._current_game_actions = []
        self._pending_trade_actions = {}

        # Phase 10.6: Open JSONL file for player actions
        if self._config.capture_mode == CaptureMode.GAME_AND_PLAYER:
            player_dir = self.base_path / "player"
            player_dir.mkdir(parents=True, exist_ok=True)

            time_str = self._current_game_start.strftime("%Y%m%dT%H%M%S")
            game_id_short = game_id.split('-')[-1][:8] if '-' in game_id else game_id[:8]
            filename = f"{time_str}_{game_id_short}_player.jsonl"
            filepath = player_dir / filename

            try:
                self._action_file_handle = open(filepath, 'w')
                logger.debug(f"Opened player action file: {filepath}")
            except Exception as e:
                logger.error(f"Failed to open player action file: {e}")
                self._action_file_handle = None

        logger.debug(f"Started game recording: {game_id}")

    def _finalize_game(
        self,
        prices: List[Decimal],
        peak: Decimal,
        seed_data: Optional[dict] = None
    ) -> None:
        """Finalize game data before saving."""
        if not self._current_game:
            return

        # Use provided prices if current game has gaps
        if self._current_game.has_gaps() and prices:
            self._current_game.prices = prices

        self._current_game.meta.end_time = datetime.utcnow()
        self._current_game.meta.duration_ticks = len(self._current_game.prices)
        self._current_game.meta.peak_multiplier = peak

        if seed_data:
            self._current_game.meta.server_seed = seed_data.get('server_seed')
            self._current_game.meta.server_seed_hash = seed_data.get('server_seed_hash')

    def _save_game(self) -> Optional[str]:
        """Save current game to file."""
        if not self._current_game:
            return None

        # Phase 10.6: Close action file if open
        if self._action_file_handle:
            try:
                self._action_file_handle.close()
                logger.debug("Closed player action file")
            except Exception as e:
                logger.error(f"Error closing action file: {e}")
            self._action_file_handle = None

        # Create games directory
        games_dir = self.base_path / "games"
        games_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self._current_game_start.strftime("%Y%m%dT%H%M%S")
        game_id_short = self._current_game.meta.game_id.split('-')[-1][:8] if '-' in self._current_game.meta.game_id else self._current_game.meta.game_id[:8]
        filename = f"{time_str}_{game_id_short}.game.json"
        filepath = games_dir / filename

        # Build game data with has_player_input flag and action count
        game_data = self._current_game.to_dict()
        game_data["meta"]["has_player_input"] = self._current_game_has_player_input
        game_data["meta"]["action_count"] = len(self._current_game_actions)

        # Write file
        with open(filepath, 'w') as f:
            json.dump(game_data, f, indent=2, cls=DecimalEncoder)

        logger.info(f"Saved game: {filepath} (actions={len(self._current_game_actions)})")

        # Clear current game
        self._current_game = None
        self._current_game_start = None
        self._current_game_actions = []
        self._pending_trade_actions = {}

        return str(filepath)

    def _discard_current_game(self) -> None:
        """Discard current game recording (due to integrity issue)."""
        if self._current_game:
            game_id = self._current_game.meta.game_id
            logger.warning(f"Discarding game due to integrity issue: {game_id}")

            # Phase 10.6: Close and delete action file if open
            if self._action_file_handle:
                filepath = self._action_file_handle.name
                try:
                    self._action_file_handle.close()
                    # Delete the incomplete file
                    Path(filepath).unlink(missing_ok=True)
                    logger.debug(f"Deleted incomplete action file: {filepath}")
                except Exception as e:
                    logger.error(f"Error cleaning up action file: {e}")
                self._action_file_handle = None

            self._current_game = None
            self._current_game_start = None
            self._current_game_has_player_input = False
            self._current_game_ticks = []
            self._current_game_actions = []
            self._pending_trade_actions = {}

    def _start_player_session(self) -> None:
        """Start a new player session."""
        self._player_session_start = datetime.utcnow()
        self._player_session = PlayerSession(
            meta=PlayerSessionMeta(
                player_id=self._player_id or "unknown",
                username=self._username or "anonymous",
                session_start=self._player_session_start
            )
        )
        self._pending_actions = []

    def _save_player_session(self) -> Optional[str]:
        """Save player session to demonstrations directory."""
        if not self._player_session or not self._pending_actions:
            return None

        self._player_session.meta.session_end = datetime.utcnow()

        # Create demonstrations directory
        demos_dir = self.base_path / "demonstrations"
        demos_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self._player_session_start.strftime("%Y%m%dT%H%M%S")
        username = self._player_session.meta.username or "anonymous"
        filename = f"{time_str}_{username}_demo.json"
        filepath = demos_dir / filename

        # Write file
        with open(filepath, 'w') as f:
            json.dump(self._player_session.to_dict(), f, indent=2, cls=DecimalEncoder)

        logger.info(f"Saved player session: {filepath}")

        return str(filepath)

    # Internal callback handlers

    def _handle_state_change(
        self,
        old_state: RecordingState,
        new_state: RecordingState
    ) -> None:
        """Handle state machine state change."""
        logger.debug(f"State change: {old_state.value} -> {new_state.value}")

        if self.on_state_change:
            self.on_state_change(old_state, new_state)

    def _handle_game_recorded(self, game_id: str) -> None:
        """Handle game recorded event from state machine."""
        # This is called after we save - find the filepath
        games_dir = self.base_path / "games"
        if games_dir.exists():
            # Find most recent file matching game_id pattern
            game_id_short = game_id.split('-')[-1][:8]
            matches = list(games_dir.glob(f"*_{game_id_short}.game.json"))
            if matches and self.on_game_recorded:
                self.on_game_recorded(str(matches[-1]))

    def _handle_session_complete(self, games_recorded: int) -> None:
        """Handle session complete event from state machine."""
        if self.on_session_complete:
            self.on_session_complete(games_recorded)

    def _handle_integrity_issue(
        self,
        issue: IntegrityIssue,
        details: Dict[str, Any]
    ) -> None:
        """Handle data integrity issue."""
        logger.warning(f"Data integrity issue: {issue.value} - {details}")
        self._discard_current_game()
        self._state_machine.on_data_integrity_issue(issue.value)

    def _handle_integrity_recovery(self) -> None:
        """Handle recovery from integrity issue."""
        logger.info("Data integrity recovered - resuming recording")
