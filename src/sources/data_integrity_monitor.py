"""
Data Integrity Monitor - Phase 10.5C

Monitors data feed integrity and triggers monitor mode when thresholds exceeded.

Triggers:
- WebSocket connection loss/reconnect
- Data gaps (missing ticks in sequence)
- Abnormal game end (no proper rug/crash event)

Thresholds (mutually exclusive):
- Ticks: Consecutive ticks of data loss
- Games: Number of dropped/corrupted games

Recovery:
- Observe ONE full clean game to reset
"""

import logging
from enum import Enum
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


# Re-export MonitorThresholdType as ThresholdType for convenience
from models.recording_config import MonitorThresholdType as ThresholdType


class IntegrityIssue(Enum):
    """Type of data integrity issue detected."""
    TICK_GAP = "tick_gap"
    CONNECTION_LOST = "connection_lost"
    ABNORMAL_GAME_END = "abnormal_game_end"


class DataIntegrityMonitor:
    """
    Monitors data feed integrity and triggers when thresholds exceeded.

    Usage:
        monitor = DataIntegrityMonitor(
            threshold_type=ThresholdType.TICKS,
            threshold_value=20
        )
        monitor.on_threshold_exceeded = lambda issue, details: print(f"Issue: {issue}")
        monitor.on_recovery = lambda: print("Recovered!")

        # Feed events
        monitor.on_tick(tick=0)
        monitor.on_tick(tick=1)
        # ...
        monitor.on_game_end(game_id="abc", clean=True)
    """

    def __init__(
        self,
        threshold_type: ThresholdType = ThresholdType.TICKS,
        threshold_value: int = 20
    ):
        """
        Initialize the data integrity monitor.

        Args:
            threshold_type: Type of threshold (TICKS or GAMES)
            threshold_value: Threshold value (consecutive ticks or games)
        """
        self._threshold_type = threshold_type
        self._threshold_value = threshold_value

        # State
        self._is_triggered = False
        self._consecutive_tick_gaps = 0
        self._consecutive_bad_games = 0
        self._last_tick: Optional[int] = None
        self._current_game_id: Optional[str] = None

        # Callbacks
        self.on_threshold_exceeded: Optional[Callable[[IntegrityIssue, Dict[str, Any]], None]] = None
        self.on_recovery: Optional[Callable[[], None]] = None

    @property
    def threshold_type(self) -> ThresholdType:
        """Threshold type (TICKS or GAMES)."""
        return self._threshold_type

    @property
    def threshold_value(self) -> int:
        """Threshold value."""
        return self._threshold_value

    @property
    def is_triggered(self) -> bool:
        """Whether monitor mode has been triggered."""
        return self._is_triggered

    @property
    def consecutive_tick_gaps(self) -> int:
        """Consecutive tick gaps detected."""
        return self._consecutive_tick_gaps

    @property
    def consecutive_bad_games(self) -> int:
        """Consecutive bad games detected."""
        return self._consecutive_bad_games

    @property
    def last_tick(self) -> Optional[int]:
        """Last tick number seen."""
        return self._last_tick

    @property
    def current_game_id(self) -> Optional[str]:
        """Current game ID being monitored."""
        return self._current_game_id

    def on_tick(self, tick: int) -> None:
        """
        Process a tick event.

        Args:
            tick: Current tick number
        """
        if self._last_tick is not None:
            expected_tick = self._last_tick + 1
            if tick > expected_tick:
                # Gap detected
                gap_size = tick - expected_tick
                self._consecutive_tick_gaps += gap_size
                logger.debug(f"Tick gap detected: expected {expected_tick}, got {tick} (gap={gap_size})")

                # Check threshold (only for TICKS type)
                if self._threshold_type == ThresholdType.TICKS:
                    if self._consecutive_tick_gaps >= self._threshold_value:
                        self._trigger(IntegrityIssue.TICK_GAP, {"gap_size": gap_size})
            elif tick == expected_tick:
                # Sequential tick - reset gap counter
                self._consecutive_tick_gaps = 0

        self._last_tick = tick

    def on_game_start(self, game_id: str) -> None:
        """
        Process game start event.

        Args:
            game_id: Game identifier
        """
        self._current_game_id = game_id
        self._last_tick = None  # Reset tick tracking for new game
        logger.debug(f"Monitoring game: {game_id}")

    def on_game_end(self, game_id: str, clean: bool) -> None:
        """
        Process game end event.

        Args:
            game_id: Game identifier
            clean: Whether the game ended cleanly (proper rug/crash)
        """
        if clean:
            # Clean game - reset bad games counter
            self._consecutive_bad_games = 0
            logger.debug(f"Clean game end: {game_id}")
        else:
            # Abnormal end
            self._consecutive_bad_games += 1
            logger.warning(f"Abnormal game end: {game_id} (consecutive: {self._consecutive_bad_games})")

            # Check threshold (only for GAMES type)
            if self._threshold_type == ThresholdType.GAMES:
                if self._consecutive_bad_games >= self._threshold_value:
                    self._trigger(IntegrityIssue.ABNORMAL_GAME_END, {
                        "game_id": game_id,
                        "consecutive_bad_games": self._consecutive_bad_games
                    })

        self._current_game_id = None
        self._last_tick = None

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection loss - always triggers immediately."""
        logger.warning("Connection lost detected")
        self._trigger(IntegrityIssue.CONNECTION_LOST, {})

    def on_connection_restored(self) -> None:
        """Handle WebSocket connection restored."""
        logger.info("Connection restored - waiting for clean game to recover")
        # Don't auto-reset - need clean game observation

    def on_clean_game_observed(self) -> None:
        """
        Called when a clean game has been observed during monitor mode.
        Resets the triggered state.
        """
        if self._is_triggered:
            logger.info("Clean game observed - recovering from monitor mode")
            self._is_triggered = False
            self._consecutive_tick_gaps = 0
            self._consecutive_bad_games = 0

            if self.on_recovery:
                self.on_recovery()

    def reset(self) -> None:
        """Reset all state."""
        self._is_triggered = False
        self._consecutive_tick_gaps = 0
        self._consecutive_bad_games = 0
        self._last_tick = None
        self._current_game_id = None
        logger.debug("Data integrity monitor reset")

    def _trigger(self, issue: IntegrityIssue, details: Dict[str, Any]) -> None:
        """Trigger monitor mode."""
        if self._is_triggered:
            # Already triggered, don't call callback again
            return

        self._is_triggered = True
        logger.warning(f"Data integrity threshold exceeded: {issue.value}")

        if self.on_threshold_exceeded:
            self.on_threshold_exceeded(issue, details)

    def is_healthy(self) -> bool:
        """Check if data feed is healthy (not triggered)."""
        return not self._is_triggered

    def get_status(self) -> Dict[str, Any]:
        """Get current status as dictionary."""
        return {
            "is_triggered": self._is_triggered,
            "threshold_type": self._threshold_type.value,
            "threshold_value": self._threshold_value,
            "consecutive_tick_gaps": self._consecutive_tick_gaps,
            "consecutive_bad_games": self._consecutive_bad_games,
            "current_game_id": self._current_game_id,
            "last_tick": self._last_tick,
        }
