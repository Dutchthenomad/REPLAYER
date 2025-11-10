"""
Replay Engine - Game playback controller
Loads JSONL files, manages playback, and publishes tick events
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable
from decimal import Decimal

from models import GameTick
from services import event_bus, Events
from .game_state import GameState

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Manages game replay playback

    Responsibilities:
    - Load game recordings from JSONL files
    - Step through ticks (manual or auto-play)
    - Control playback speed
    - Publish tick events
    - Track playback state
    """

    def __init__(self, game_state: GameState):
        self.state = game_state

        # Game data
        self.ticks: List[GameTick] = []
        self.current_index = 0
        self.game_id: Optional[str] = None

        # Playback control
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 = normal speed
        self.playback_thread: Optional[threading.Thread] = None

        # Thread safety (AUDIT FIX: Added _stop_event for clean shutdown)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        # Callbacks for UI updates
        self.on_tick_callback: Optional[Callable] = None
        self.on_game_end_callback: Optional[Callable] = None

        logger.info("ReplayEngine initialized")

    # ========================================================================
    # FILE LOADING
    # ========================================================================

    def load_file(self, filepath: Path) -> bool:
        """
        Load game recording from JSONL file

        Args:
            filepath: Path to .jsonl file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # AUDIT FIX: Load outside lock to prevent blocking
            loaded_ticks = []
            game_id = None

            logger.info(f"Loading game file: {filepath}")

            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # AUDIT FIX: Validate required fields before parsing
                        required_fields = ['tick', 'price', 'phase', 'active', 'rugged', 'game_id']
                        for field in required_fields:
                            if field not in data:
                                raise KeyError(f"Missing required field: {field}")

                        tick = GameTick.from_dict(data)
                        loaded_ticks.append(tick)

                        # Set game_id from first tick
                        if game_id is None:
                            game_id = tick.game_id

                    except Exception as e:
                        logger.warning(f"Skipped invalid line {line_num}: {e}")
                        continue

            if not loaded_ticks:
                logger.error("No valid ticks found in file")
                return False

            # AUDIT FIX: Assign to instance variables under lock
            with self._lock:
                self.ticks = loaded_ticks
                self.current_index = 0
                self.game_id = game_id

            logger.info(f"Loaded {len(self.ticks)} ticks from game {self.game_id}")

            # Publish file loaded event
            event_bus.publish(Events.FILE_LOADED, {
                'filepath': str(filepath),
                'game_id': self.game_id,
                'tick_count': len(self.ticks)
            })

            # Display first tick
            self.display_tick(0)

            return True

        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            return False
        except Exception as e:
            logger.error(f"Failed to load file: {e}", exc_info=True)
            return False

    # ========================================================================
    # PLAYBACK CONTROL
    # ========================================================================

    def play(self):
        """Start auto-playback (thread-safe)"""
        if not self.ticks:
            logger.warning("No game loaded")
            return

        # Thread-safe check-then-act pattern
        with self._lock:
            if self.is_playing:
                logger.warning("Already playing")
                return

            if self.is_at_end():
                logger.info("At end of game, resetting to start")
                self.reset()

            self.is_playing = True

        # Start playback thread outside lock (thread creation doesn't need protection)
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()

        event_bus.publish(Events.REPLAY_START)
        logger.info("Playback started")

    def pause(self):
        """Pause auto-playback (thread-safe)"""
        # Thread-safe check-then-act pattern
        with self._lock:
            if not self.is_playing:
                return

            self.is_playing = False

        # AUDIT FIX: Signal stop event for immediate shutdown
        self._stop_event.set()

        # Wait for thread to finish outside lock to avoid deadlock
        # Don't join if we're the playback thread itself
        if self.playback_thread and self.playback_thread != threading.current_thread():
            self.playback_thread.join(timeout=2)

        # AUDIT FIX: Clear stop event for next playback
        self._stop_event.clear()

        event_bus.publish(Events.REPLAY_PAUSE)
        logger.info("Playback paused")

    def step_forward(self) -> bool:
        """
        Step forward one tick (thread-safe)

        Returns:
            True if stepped successfully, False if at end
        """
        if not self.ticks:
            return False

        with self._lock:
            if self.current_index >= len(self.ticks) - 1:
                logger.info("Reached end of game")
                self._handle_game_end()
                return False

            self.current_index += 1
            index = self.current_index

        # Display tick outside lock (calls callbacks which may acquire other locks)
        self.display_tick(index)
        return True

    def step_backward(self) -> bool:
        """
        Step backward one tick (thread-safe)

        Returns:
            True if stepped successfully, False if at start
        """
        if not self.ticks:
            return False

        with self._lock:
            if self.current_index <= 0:
                return False

            self.current_index -= 1
            index = self.current_index

        # Display tick outside lock
        self.display_tick(index)
        return True

    def jump_to_tick(self, tick_number: int) -> bool:
        """
        Jump to specific tick number (thread-safe)

        Args:
            tick_number: Target tick number

        Returns:
            True if jumped successfully
        """
        if not self.ticks:
            return False

        # Find index for tick number
        with self._lock:
            for i, tick in enumerate(self.ticks):
                if tick.tick == tick_number:
                    self.current_index = i
                    index = i
                    break
            else:
                logger.warning(f"Tick {tick_number} not found")
                return False

        # Display tick outside lock
        self.display_tick(index)
        return True

    def reset(self):
        """Reset to beginning of game (thread-safe)"""
        self.pause()  # pause() is already thread-safe

        with self._lock:
            self.current_index = 0

        # Reset state and display outside lock
        self.state.reset()

        if self.ticks:
            self.display_tick(0)

        logger.info("Replay reset to start")

    def set_speed(self, speed: float):
        """
        Set playback speed (thread-safe)

        Args:
            speed: Speed multiplier (0.25, 0.5, 1.0, 2.0, 4.0, etc.)
        """
        with self._lock:
            self.playback_speed = max(0.1, min(10.0, speed))
            new_speed = self.playback_speed

        event_bus.publish(Events.REPLAY_SPEED_CHANGED, {'speed': new_speed})
        logger.info(f"Playback speed set to {new_speed}x")

    # ========================================================================
    # DISPLAY & UPDATES
    # ========================================================================

    def display_tick(self, index: int):
        """
        Display tick at given index
        Updates game state and publishes event
        """
        if not self.ticks or index < 0 or index >= len(self.ticks):
            return

        tick = self.ticks[index]

        # Update game state
        self.state.update(
            current_tick=tick.tick,
            current_price=tick.price,
            current_phase=tick.phase,
            rugged=tick.rugged,
            game_active=tick.active
        )

        # Store current tick reference
        self.state.current_tick = tick

        # Publish tick event
        event_bus.publish(Events.GAME_TICK, {
            'tick': tick,
            'index': index,
            'total': len(self.ticks),
            'progress': (index / len(self.ticks)) * 100 if self.ticks else 0
        })

        # Call UI callback if set
        if self.on_tick_callback:
            self.on_tick_callback(tick, index, len(self.ticks))

        # Check for rug event
        if tick.rugged and not self.state.get('rug_detected'):
            self._handle_rug_event(tick)

    def _handle_rug_event(self, tick: GameTick):
        """Handle rug event detection"""
        self.state.update(rug_detected=True)
        event_bus.publish(Events.GAME_RUG, {
            'tick': tick.tick,
            'price': float(tick.price),
            'game_id': tick.game_id
        })
        logger.warning(f"RUG EVENT detected at tick {tick.tick}")

    def _handle_game_end(self):
        """Handle reaching end of game"""
        self.pause()

        # Calculate final metrics
        metrics = self.state.calculate_metrics()

        event_bus.publish(Events.GAME_END, {
            'game_id': self.game_id,
            'metrics': metrics
        })

        if self.on_game_end_callback:
            self.on_game_end_callback(metrics)

        logger.info(f"Game ended. Final metrics: {metrics}")

    # ========================================================================
    # BACKGROUND PLAYBACK
    # ========================================================================

    def _playback_loop(self):
        """Background thread for auto-playback (thread-safe)"""
        # AUDIT FIX: Use stop_event for clean shutdown
        while not self._stop_event.is_set():
            # Check if still playing (thread-safe read)
            with self._lock:
                if not self.is_playing:
                    break
                speed = self.playback_speed

            # Step forward (already thread-safe)
            if not self.step_forward():
                break

            # Calculate delay based on speed
            # Base delay: 250ms per tick at 1x speed
            delay = 0.25 / speed

            # AUDIT FIX: Use wait with timeout instead of sleep for responsive shutdown
            if self._stop_event.wait(timeout=delay):
                break

        # Ensure flag is cleared (thread-safe)
        with self._lock:
            self.is_playing = False

    # ========================================================================
    # STATUS QUERIES
    # ========================================================================

    def is_loaded(self) -> bool:
        """Check if a game is loaded"""
        return len(self.ticks) > 0

    def is_at_start(self) -> bool:
        """Check if at start of game"""
        return self.current_index == 0

    def is_at_end(self) -> bool:
        """Check if at end of game"""
        return self.current_index >= len(self.ticks) - 1

    def get_current_tick(self) -> Optional[GameTick]:
        """Get current tick"""
        if not self.ticks or self.current_index >= len(self.ticks):
            return None
        return self.ticks[self.current_index]

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)"""
        if not self.ticks:
            return 0.0
        return self.current_index / len(self.ticks)

    def get_info(self) -> dict:
        """Get replay info"""
        return {
            'loaded': self.is_loaded(),
            'game_id': self.game_id,
            'total_ticks': len(self.ticks),
            'current_tick': self.current_index,
            'is_playing': self.is_playing,
            'speed': self.playback_speed,
            'progress': self.get_progress() * 100
        }
