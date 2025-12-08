"""
Recording State Machine - Phase 10.5B

Manages recording session state transitions.

State Machine:
    IDLE → MONITORING → RECORDING → FINISHING_GAME → IDLE
                ↑            │
                └────────────┘ (data integrity issue)

States:
- IDLE: Not recording, waiting for user to start session
- MONITORING: Watching feed, waiting for clean game to begin recording
- RECORDING: Actively capturing game data
- FINISHING_GAME: Limit reached, completing current game before stopping
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class RecordingState(Enum):
    """Recording session state."""
    IDLE = "idle"
    MONITORING = "monitoring"
    RECORDING = "recording"
    FINISHING_GAME = "finishing_game"


class RecordingStateMachine:
    """
    State machine for recording sessions.

    Handles transitions between states and tracks session metrics.

    Usage:
        sm = RecordingStateMachine()
        sm.on_state_change = lambda old, new: print(f"{old} -> {new}")
        sm.on_game_recorded = lambda game_id: print(f"Recorded: {game_id}")
        sm.on_session_complete = lambda count: print(f"Session done: {count} games")

        sm.start_session(game_in_progress=False, game_limit=10)
        # ... receive game events ...
        sm.on_game_start(game_id="abc123")
        sm.on_game_end(game_id="abc123")
    """

    def __init__(self):
        self._state = RecordingState.IDLE
        self._games_recorded = 0
        self._session_start_time: Optional[datetime] = None
        self._game_in_progress = False
        self._current_game_id: Optional[str] = None
        self._game_limit: Optional[int] = None

        # Callbacks
        self.on_state_change: Optional[Callable[[RecordingState, RecordingState], None]] = None
        self.on_game_recorded: Optional[Callable[[str], None]] = None
        self.on_session_complete: Optional[Callable[[int], None]] = None

    @property
    def state(self) -> RecordingState:
        """Current state of the state machine."""
        return self._state

    @property
    def games_recorded(self) -> int:
        """Number of games recorded in current session."""
        return self._games_recorded

    @property
    def session_start_time(self) -> Optional[datetime]:
        """When the current session started."""
        return self._session_start_time

    @property
    def game_in_progress(self) -> bool:
        """Whether a game is currently in progress."""
        return self._game_in_progress

    @property
    def current_game_id(self) -> Optional[str]:
        """ID of the game currently being recorded."""
        return self._current_game_id

    @property
    def game_limit(self) -> Optional[int]:
        """Maximum number of games to record (None = infinite)."""
        return self._game_limit

    def _transition_to(self, new_state: RecordingState) -> None:
        """Transition to a new state, calling callback if set."""
        old_state = self._state
        if old_state != new_state:
            self._state = new_state
            logger.info(f"Recording state: {old_state.value} -> {new_state.value}")
            if self.on_state_change:
                self.on_state_change(old_state, new_state)

    def start_session(
        self,
        game_in_progress: bool = False,
        game_limit: Optional[int] = None
    ) -> None:
        """
        Start a new recording session.

        Args:
            game_in_progress: Whether a game is currently in progress
            game_limit: Maximum number of games to record (None = infinite)

        Raises:
            ValueError: If session already active (not in IDLE state)
        """
        if self._state != RecordingState.IDLE:
            raise ValueError(
                f"Cannot start session: already in {self._state.value} state. "
                "Stop current session first."
            )

        # Reset session state
        self._games_recorded = 0
        self._session_start_time = datetime.now()
        self._game_in_progress = game_in_progress
        self._current_game_id = None
        self._game_limit = game_limit

        # Always go to MONITORING first (wait for clean game start)
        self._transition_to(RecordingState.MONITORING)

        logger.info(
            f"Recording session started. "
            f"Game limit: {game_limit if game_limit else 'infinite'}, "
            f"Game in progress: {game_in_progress}"
        )

    def stop_session(self) -> None:
        """
        Stop the recording session.

        If currently recording a game, transitions to FINISHING_GAME
        to complete the current game before stopping.
        """
        if self._state == RecordingState.IDLE:
            logger.debug("stop_session called but already IDLE")
            return

        if self._state == RecordingState.FINISHING_GAME:
            logger.debug("stop_session called but already FINISHING_GAME")
            return

        if self._state == RecordingState.RECORDING:
            # Complete current game before stopping
            self._transition_to(RecordingState.FINISHING_GAME)
            logger.info("Recording session stopping after current game completes")
        else:
            # MONITORING - can stop immediately
            self._finish_session()

    def _finish_session(self) -> None:
        """Complete the session and return to IDLE."""
        games = self._games_recorded
        self._transition_to(RecordingState.IDLE)
        self._session_start_time = None
        self._current_game_id = None

        if self.on_session_complete:
            self.on_session_complete(games)

        logger.info(f"Recording session complete. Games recorded: {games}")

    def on_game_start(self, game_id: str) -> None:
        """
        Handle game start event.

        Args:
            game_id: Unique identifier for the game
        """
        if self._state == RecordingState.MONITORING:
            self._current_game_id = game_id
            self._game_in_progress = True
            self._transition_to(RecordingState.RECORDING)
            logger.info(f"Started recording game: {game_id}")

        elif self._state == RecordingState.RECORDING:
            # Already recording a game - ignore
            logger.warning(
                f"Game start received while already recording {self._current_game_id}, "
                f"ignoring {game_id}"
            )

        else:
            # IDLE or FINISHING_GAME - ignore
            logger.debug(f"Game start ignored in {self._state.value} state")

    def on_game_end(self, game_id: str) -> None:
        """
        Handle game end event.

        Args:
            game_id: Unique identifier for the game that ended
        """
        if self._state == RecordingState.IDLE:
            logger.debug("Game end ignored in IDLE state")
            return

        if self._state == RecordingState.MONITORING:
            # Game ended while we were waiting - good, now we can start fresh
            self._game_in_progress = False
            logger.debug("Game ended while monitoring, ready for next game")
            return

        # Verify game ID matches
        if self._current_game_id and game_id != self._current_game_id:
            logger.warning(
                f"Game end for {game_id} but currently recording {self._current_game_id}, "
                "ignoring"
            )
            return

        # RECORDING or FINISHING_GAME - complete the game
        self._games_recorded += 1
        recorded_game_id = self._current_game_id
        self._current_game_id = None
        self._game_in_progress = False

        if self.on_game_recorded and recorded_game_id:
            self.on_game_recorded(recorded_game_id)

        logger.info(f"Game recorded: {recorded_game_id} (total: {self._games_recorded})")

        # Check what to do next
        if self._state == RecordingState.FINISHING_GAME:
            # Was waiting to finish - now done
            self._finish_session()

        elif self.is_limit_reached():
            # Limit reached - finish session
            self._finish_session()

        else:
            # Continue recording - go back to monitoring for next game
            self._transition_to(RecordingState.MONITORING)

    def on_data_integrity_issue(self, reason: str) -> None:
        """
        Handle data integrity issue (discard current game, return to monitoring).

        Args:
            reason: Description of the issue (connection_lost, data_gap, abnormal_end)
        """
        if self._state != RecordingState.RECORDING:
            logger.debug(f"Data integrity issue ignored in {self._state.value} state")
            return

        logger.warning(f"Data integrity issue: {reason}. Discarding current game.")

        # Discard current game (don't increment counter)
        self._current_game_id = None
        self._game_in_progress = False

        # Go back to monitoring to wait for clean game
        self._transition_to(RecordingState.MONITORING)

    def is_limit_reached(self) -> bool:
        """Check if the session game limit has been reached."""
        if self._game_limit is None:
            return False
        return self._games_recorded >= self._game_limit

    def is_recording(self) -> bool:
        """Check if currently recording a game."""
        return self._state == RecordingState.RECORDING

    def is_active(self) -> bool:
        """Check if a recording session is active (not IDLE)."""
        return self._state != RecordingState.IDLE
