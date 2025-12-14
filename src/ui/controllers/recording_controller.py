"""
Recording Controller - Phase 10.5H

Integrates all Phase 10.5 components:
- RecordingConfigDialog (UI)
- UnifiedRecorder (recording logic)
- ToastNotification (feedback)
- AudioCuePlayer (audio feedback)

Provides a clean interface for MainWindow to control recording sessions.
"""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

from models.recording_config import RecordingConfig, CaptureMode
from models.recording_models import (
    PlayerAction,
    ServerState,
    LocalStateSnapshot,
    RecordedAction,
)
from services.unified_recorder import UnifiedRecorder
from services.recording_state_machine import RecordingState
from ui.recording_config_dialog import RecordingConfigDialog
from ui.toast_notification import RecordingToastManager
from ui.audio_cue_player import AudioCuePlayer

if TYPE_CHECKING:
    import tkinter as tk
    from core import GameState

logger = logging.getLogger(__name__)


class RecordingController:
    """
    Controller for recording sessions.

    Orchestrates:
    - Config dialog presentation
    - Unified recorder management
    - Toast notifications
    - Audio cues

    Usage:
        controller = RecordingController(root, recordings_path, game_state)

        # Show config and start recording
        controller.show_config_dialog()

        # Or start with defaults
        controller.start_session()

        # Stop recording
        controller.stop_session()
    """

    def __init__(
        self,
        root: "tk.Tk",
        recordings_path: str,
        game_state: Optional["GameState"] = None,
        player_id: Optional[str] = None,
        username: Optional[str] = None
    ):
        """
        Initialize the recording controller.

        Args:
            root: Tkinter root window
            recordings_path: Base path for recordings
            game_state: GameState instance for state observation
            player_id: Player ID for player state recording
            username: Username for player state recording
        """
        self.root = root
        self.recordings_path = Path(recordings_path)
        self.game_state = game_state
        self._player_id = player_id
        self._username = username

        # Load saved config
        self._config = RecordingConfig.load()

        # Components (initialized lazily)
        self._recorder: Optional[UnifiedRecorder] = None
        self._toast: Optional[RecordingToastManager] = None
        self._audio: Optional[AudioCuePlayer] = None

        # Initialize toast manager
        self._toast = RecordingToastManager(root)

        # Initialize audio player
        self._audio = AudioCuePlayer(enabled=self._config.audio_cues)

    @property
    def is_recording(self) -> bool:
        """Whether currently recording a game."""
        return self._recorder is not None and self._recorder.is_recording

    @property
    def is_active(self) -> bool:
        """Whether a recording session is active."""
        return self._recorder is not None and self._recorder.is_active

    @property
    def games_recorded(self) -> int:
        """Number of games recorded in current session."""
        if self._recorder:
            return self._recorder.games_recorded
        return 0

    @property
    def current_state(self) -> Optional[RecordingState]:
        """Current recording state."""
        if self._recorder:
            return self._recorder.state_machine.state
        return None

    def show_config_dialog(self) -> bool:
        """
        Show the recording configuration dialog.

        Returns:
            True if user clicked Start, False if cancelled
        """
        dialog = RecordingConfigDialog(
            self.root,
            config=self._config,
            on_start=self._on_config_start,
            on_cancel=self._on_config_cancel
        )

        result = dialog.show()

        if result:
            self._config = result
            return True
        return False

    def start_session(self, config: Optional[RecordingConfig] = None) -> None:
        """
        Start a recording session.

        Args:
            config: Configuration to use (defaults to saved config)
        """
        if self.is_active:
            logger.warning("Recording session already active")
            return

        config = config or self._config

        # Create recorder
        self._recorder = UnifiedRecorder(
            base_path=str(self.recordings_path),
            config=config,
            player_id=self._player_id,
            username=self._username
        )

        # Wire up callbacks
        self._recorder.on_state_change = self._on_state_change
        self._recorder.on_game_recorded = self._on_game_recorded
        self._recorder.on_session_complete = self._on_session_complete

        # Update audio setting
        self._audio.enabled = config.audio_cues

        # Check if game is in progress
        game_in_progress = False
        if self.game_state:
            game_in_progress = self.game_state.get_current_tick() is not None

        # Start session
        self._recorder.start_session(game_in_progress=game_in_progress)

        # Feedback
        self._toast.recording_started()
        self._audio.play_recording_started()

        logger.info(f"Recording session started (mode={config.capture_mode.value})")

    def stop_session(self) -> None:
        """Stop the current recording session."""
        if not self.is_active:
            logger.debug("No active recording session to stop")
            return

        games = self.games_recorded

        self._recorder.stop_session()
        self._recorder = None

        # Feedback
        self._toast.recording_stopped(games)
        self._audio.play_recording_stopped()

        logger.info(f"Recording session stopped ({games} games)")

    def on_game_start(self, game_id: str) -> None:
        """
        Handle game start event.

        Args:
            game_id: Game identifier
        """
        if self._recorder:
            self._recorder.on_game_start(game_id)

    def on_tick(self, tick: int, price: Decimal) -> None:
        """
        Handle tick event.

        Args:
            tick: Tick number
            price: Price at this tick
        """
        if self._recorder:
            self._recorder.on_tick(tick, price)

    def on_game_end(
        self,
        game_id: str,
        prices: Optional[list] = None,
        peak: Optional[Decimal] = None,
        clean: bool = True,
        seed_data: Optional[dict] = None
    ) -> None:
        """
        Handle game end event.

        Args:
            game_id: Game identifier
            prices: Price list (optional - calculated from ticks if not provided)
            peak: Peak multiplier (optional - calculated from prices if not provided)
            clean: Whether game ended cleanly
            seed_data: Optional seed data
        """
        if self._recorder:
            self._recorder.on_game_end(game_id, prices, peak, clean, seed_data)

    def on_player_action(self, action: PlayerAction) -> None:
        """
        Record a player action.

        Args:
            action: Player action to record
        """
        if self._recorder:
            self._recorder.on_player_action(action)

    # =========================================================================
    # Phase 10.6: Button Recording with Validation
    # =========================================================================

    def on_button_press(
        self,
        button: str,
        local_state: LocalStateSnapshot,
        amount: Optional[Decimal] = None,
        server_state: Optional[ServerState] = None
    ) -> Optional[RecordedAction]:
        """
        Record a button press with dual-state validation.

        Phase 10.6: Called by TradingController for ALL button presses.

        Args:
            button: Button text (e.g., 'BUY', '+0.01', '25%', 'X')
            local_state: REPLAYER's calculated state at action time
            amount: Trade amount (for BUY/SELL/SIDEBET)
            server_state: Server state from WebSocket (optional)

        Returns:
            RecordedAction if recorded, None otherwise
        """
        if self._recorder:
            return self._recorder.record_button_press(
                button=button,
                local_state=local_state,
                amount=amount,
                server_state=server_state
            )
        return None

    def update_server_state(self, server_state: ServerState) -> None:
        """
        Update the latest server state for validation.

        Called when WebSocket playerUpdate is received.

        Args:
            server_state: Latest server state from WebSocket
        """
        if self._recorder:
            self._recorder.update_server_state(server_state)

    def record_trade_confirmation(self, action_id: str, timestamp_ms: int) -> Optional[float]:
        """
        Record trade confirmation and calculate latency.

        Args:
            action_id: ID of the action to confirm
            timestamp_ms: Confirmation timestamp in milliseconds

        Returns:
            Latency in ms if found, None otherwise
        """
        if self._recorder:
            return self._recorder.record_trade_confirmation(action_id, timestamp_ms)
        return None

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection loss."""
        if self._recorder:
            self._recorder.on_connection_lost()
            self._toast.data_integrity_issue("Connection lost")
            self._audio.play_recording_paused()

    def on_connection_restored(self) -> None:
        """Handle WebSocket connection restored."""
        if self._recorder:
            self._recorder.on_connection_restored()

    def get_status(self) -> dict:
        """Get recording status."""
        if self._recorder:
            return self._recorder.get_status()
        return {
            "state": "idle",
            "games_recorded": 0,
            "capture_mode": self._config.capture_mode.value,
            "game_limit": self._config.game_count,
            "is_healthy": True,
        }

    def set_player_info(self, player_id: str, username: str) -> None:
        """
        Set player information for player state recording.

        Args:
            player_id: Player ID
            username: Username
        """
        self._player_id = player_id
        self._username = username

    # Callback handlers

    def _on_config_start(self, config: RecordingConfig) -> None:
        """Handle config dialog Start button."""
        self._config = config
        self.start_session(config)

    def _on_config_cancel(self) -> None:
        """Handle config dialog Cancel button."""
        logger.debug("Recording config dialog cancelled")

    def _on_state_change(
        self,
        old_state: RecordingState,
        new_state: RecordingState
    ) -> None:
        """Handle recording state change."""
        logger.debug(f"Recording state: {old_state.value} -> {new_state.value}")

        if new_state == RecordingState.MONITORING and old_state == RecordingState.RECORDING:
            # Entered monitor mode (data integrity issue)
            self._toast.recording_paused("Monitor Mode active")
            self._audio.play_recording_paused()

        elif new_state == RecordingState.RECORDING and old_state == RecordingState.MONITORING:
            # Recovered from monitor mode
            if self.games_recorded > 0:  # Not first game
                self._toast.recording_resumed()
                self._audio.play_recording_resumed()

        elif new_state == RecordingState.FINISHING_GAME:
            # Limit reached, finishing current game
            self._toast.session_limit_reached()

    def _on_game_recorded(self, filepath: str) -> None:
        """Handle game recorded event."""
        logger.info(f"Game recorded: {filepath}")
        self._audio.play_game_recorded()

    def _on_session_complete(self, games_recorded: int) -> None:
        """Handle session complete event."""
        logger.info(f"Recording session complete: {games_recorded} games")
        self._toast.recording_stopped(games_recorded)
        self._audio.play_recording_stopped()
        self._recorder = None
