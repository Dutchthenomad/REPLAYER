"""
Replay Playback Controller

Manages playback state and navigation for replay engine.
Extracted from replay_engine.py during Phase 2 refactoring.

Classes:
    PlaybackController: Handles play/pause/stop, stepping, jumping, and speed control
"""

import logging
import threading
from typing import Optional, Callable, List, TYPE_CHECKING

from models import GameTick
from services import event_bus, Events

if TYPE_CHECKING:
    from core.replay_engine import ReplayEngine

logger = logging.getLogger(__name__)


class PlaybackController:
    """
    Controls playback state and navigation for replay engine.

    Responsibilities:
    - Play/pause/stop control
    - Step forward/backward
    - Jump to tick/index
    - Speed control
    - Background playback loop

    Usage:
        controller = PlaybackController(engine, state, lock, stop_event)
        controller.play()
        controller.set_speed(2.0)
        controller.pause()
    """

    def __init__(
        self,
        engine: 'ReplayEngine',
        lock: threading.RLock,
        stop_event: threading.Event
    ):
        """
        Initialize playback controller.

        Args:
            engine: Parent ReplayEngine instance
            lock: Shared lock for thread safety
            stop_event: Event for signaling shutdown
        """
        self.engine = engine
        self._lock = lock
        self._stop_event = stop_event

        # Playback state
        self.is_playing = False
        self.playback_speed = 1.0
        self.playback_thread: Optional[threading.Thread] = None

    # ========================================================================
    # PLAYBACK CONTROL
    # ========================================================================

    def play(self):
        """Start auto-playback"""
        with self._lock:
            if self.is_playing:
                logger.warning("Already playing")
                return

            if not self.engine.ticks:
                logger.warning("No game loaded")
                return

            self.is_playing = True
            self._stop_event.clear()

            # Start playback thread
            self.playback_thread = threading.Thread(
                target=self._playback_loop,
                name="ReplayEngine-Playback",
                daemon=True
            )
            self.playback_thread.start()

            event_bus.publish(Events.REPLAY_STARTED, {'game_id': self.engine.game_id})
            logger.info("Playback started")

    def pause(self):
        """Pause auto-playback"""
        with self._lock:
            if not self.is_playing:
                return

            self.is_playing = False

        # AUDIT FIX: Only join thread if NOT called from within the thread itself
        # (prevents deadlock when auto-play reaches end of game)
        current_thread = threading.current_thread()
        if self.playback_thread and self.playback_thread.is_alive():
            if current_thread != self.playback_thread:
                self.playback_thread.join(timeout=2.0)
            # else: We're in the playback thread - don't join, just return

        event_bus.publish(Events.REPLAY_PAUSED, {'game_id': self.engine.game_id})
        logger.info("Playback paused")

    def stop(self):
        """Stop playback and reset to start"""
        # First pause playback
        self.pause()

        with self._lock:
            self.engine.current_index = 0

        # Display first tick
        if self.engine.ticks:
            self.engine.display_tick(0)

        event_bus.publish(Events.REPLAY_STOPPED, {'game_id': self.engine.game_id})
        logger.info("Playback stopped")

    def reset(self):
        """Reset game to initial state (stop playback, reset state, go to beginning)"""
        # Stop playback
        self.pause()

        with self._lock:
            self.engine.current_index = 0

        # Reset game state
        self.engine.state.reset()

        # Update state with first tick if available
        if self.engine.ticks:
            first_tick = self.engine.ticks[0]
            self.engine.state.update(
                game_id=self.engine.game_id,
                current_tick=first_tick.tick,
                current_price=first_tick.price,
                current_phase=first_tick.phase,
                game_active=first_tick.active,
                rugged=first_tick.rugged
            )
            self.engine.display_tick(0)

        event_bus.publish(Events.REPLAY_RESET, {'game_id': self.engine.game_id})
        logger.info("Game reset to initial state")

    # ========================================================================
    # NAVIGATION
    # ========================================================================

    def step_forward(self) -> bool:
        """Step forward one tick"""
        with self._lock:
            if not self.engine.ticks:
                return False

            if self.engine.current_index >= len(self.engine.ticks) - 1:
                self.engine._handle_game_end()
                return False

            self.engine.current_index += 1

        self.engine.display_tick(self.engine.current_index)
        return True

    def step_backward(self) -> bool:
        """Step backward one tick (not available in live mode)"""
        if self.engine.is_live_mode:
            logger.warning("Cannot step backward in live mode")
            return False

        with self._lock:
            if not self.engine.ticks or self.engine.current_index <= 0:
                return False

            self.engine.current_index -= 1

        self.engine.display_tick(self.engine.current_index)
        return True

    def jump_to_tick(self, tick_number: int) -> bool:
        """Jump to specific tick number (not available in live mode)"""
        if self.engine.is_live_mode:
            logger.warning("Cannot jump to tick in live mode")
            return False

        with self._lock:
            if not self.engine.ticks:
                return False

            # Find tick with matching number
            for i, tick in enumerate(self.engine.ticks):
                if tick.tick == tick_number:
                    self.engine.current_index = i
                    self.engine.display_tick(i)
                    return True

        logger.warning(f"Tick {tick_number} not found")
        return False

    def jump_to_index(self, index: int) -> bool:
        """Jump to specific index in tick list"""
        with self._lock:
            if not self.engine.ticks or index < 0 or index >= len(self.engine.ticks):
                return False

            self.engine.current_index = index

        self.engine.display_tick(index)
        return True

    def set_tick_index(self, index: int) -> bool:
        """Backwards-compatible alias for jump_to_index()"""
        return self.jump_to_index(index)

    # ========================================================================
    # SPEED CONTROL
    # ========================================================================

    def set_speed(self, speed: float):
        """Set playback speed multiplier"""
        with self._lock:
            self.playback_speed = max(0.1, min(10.0, speed))
            new_speed = self.playback_speed

        event_bus.publish(Events.REPLAY_SPEED_CHANGED, {'speed': new_speed})
        logger.info(f"Playback speed set to {new_speed}x")

    def get_speed(self) -> float:
        """Get current playback speed"""
        with self._lock:
            return self.playback_speed

    # ========================================================================
    # BACKGROUND PLAYBACK
    # ========================================================================

    def _playback_loop(self):
        """Background thread for auto-playback"""
        logger.debug("Playback loop started")

        try:
            while not self._stop_event.is_set():
                # Check if still playing
                with self._lock:
                    if not self.is_playing:
                        break
                    speed = self.playback_speed

                # Step forward
                if not self.step_forward():
                    break

                # Calculate delay based on speed
                delay = 0.25 / speed

                # Wait with timeout for responsive shutdown
                if self._stop_event.wait(timeout=delay):
                    break

        except Exception as e:
            logger.error(f"Error in playback loop: {e}", exc_info=True)
        finally:
            # Ensure flag is cleared
            with self._lock:
                self.is_playing = False
            logger.debug("Playback loop ended")

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self):
        """Clean up playback resources"""
        # Signal threads to stop
        self._stop_event.set()

        # Stop playback
        if self.is_playing:
            self.is_playing = False

        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
