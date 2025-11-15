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
from .recorder_sink import RecorderSink
from .live_ring_buffer import LiveRingBuffer

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

    def __init__(self, game_state: GameState, replay_source=None):
        from core.replay_source import FileDirectorySource
        from config import config

        self.state = game_state

        # Replay source (defaults to file directory)
        if replay_source is None:
            replay_source = FileDirectorySource(config.FILES['recordings_dir'])
        self.replay_source = replay_source

        # Game data
        self.ticks: List[GameTick] = []
        self.current_index = 0
        self.game_id: Optional[str] = None

        # Playback control
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 = normal speed
        self.playback_thread: Optional[threading.Thread] = None
        self.multi_game_mode = False  # NEW: Multi-game auto-advance mode

        # Live feed infrastructure (Phase 5)
        self.live_ring_buffer = LiveRingBuffer(
            max_size=config.LIVE_FEED['ring_buffer_size']
        )
        self.recorder_sink = RecorderSink(
            recordings_dir=config.FILES['recordings_dir'],
            buffer_size=config.LIVE_FEED['recording_buffer_size']
        )
        self.auto_recording = config.LIVE_FEED['auto_recording']

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
        Load game recording from JSONL file using replay source

        Args:
            filepath: Path to .jsonl file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading game file: {filepath}")

            # Use replay source to load ticks
            loaded_ticks, game_id = self.replay_source.load(str(filepath))

            # AUDIT FIX: Assign to instance variables under lock
            with self._lock:
                self.ticks = loaded_ticks
                self.current_index = 0
                self.game_id = game_id

            # Reset state for new game session
            self.state.reset()
            self.state.update(game_id=self.game_id, game_active=False)

            event_bus.publish(Events.GAME_START, {
                'game_id': self.game_id,
                'tick_count': len(self.ticks),
                'filepath': str(filepath)
            })

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

    def load_game(self, ticks: List[GameTick], game_id: str) -> bool:
        """
        Load game data from a list of ticks (for testing)

        Args:
            ticks: List of GameTick objects
            game_id: Game identifier

        Returns:
            True if loaded successfully
        """
        with self._lock:
            try:
                self.ticks = ticks
                self.game_id = game_id
                self.current_index = 0

                # Initialize game state
                if ticks:
                    first_tick = ticks[0]
                    self.state.update(
                        game_id=game_id,
                        game_active=True,
                        current_tick=first_tick.tick,
                        current_price=first_tick.price,
                        current_phase=first_tick.phase
                    )

                logger.info(f"Loaded game {game_id} with {len(ticks)} ticks")
                event_bus.publish(Events.FILE_LOADED, {'game_id': game_id, 'tick_count': len(ticks)})
                return True

            except Exception as e:
                logger.error(f"Failed to load game: {e}", exc_info=True)
                return False

    def push_tick(self, tick: GameTick) -> bool:
        """
        Push a single tick to the replay engine (for live feeds)

        This method is designed for WebSocket/live feed integration where ticks
        arrive one at a time rather than being loaded from a file in batch.

        Features (Phase 5):
        - Stores tick in ring buffer (prevents unbounded memory growth)
        - Auto-records to disk if auto_recording enabled
        - Initializes game state on first tick

        Args:
            tick: GameTick to add

        Returns:
            True if tick was added successfully
        """
        with self._lock:
            # Initialize game on first tick
            if not self.ticks:
                self.game_id = tick.game_id
                self.state.reset()
                self.state.update(
                    game_id=self.game_id,
                    game_active=True,
                    current_tick=tick.tick,
                    current_price=tick.price,
                    current_phase=tick.phase
                )

                event_bus.publish(Events.GAME_START, {
                    'game_id': self.game_id,
                    'tick_count': 0,
                    'live_mode': True
                })

                # Start recording if auto-recording enabled
                if self.auto_recording:
                    recording_file = self.recorder_sink.start_recording(self.game_id)
                    logger.info(f"Started live game: {self.game_id}, recording to {recording_file.name}")
                else:
                    logger.info(f"Started live game: {self.game_id} (recording disabled)")

            # Add tick to ring buffer (bounded memory)
            self.live_ring_buffer.append(tick)

            # Record tick to disk if recording enabled
            if self.auto_recording:
                self.recorder_sink.record_tick(tick)

            # Add tick to end of list (for backward compatibility)
            self.ticks.append(tick)

            # Auto-advance to latest tick (for live mode)
            self.current_index = len(self.ticks) - 1

        # Display new tick outside lock
        self.display_tick(self.current_index)

        logger.debug(f"Pushed tick {tick.tick} for game {tick.game_id}")
        return True

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

    def set_tick_index(self, index: int) -> bool:
        """
        Set current tick by index (for testing)

        Args:
            index: Target tick index

        Returns:
            True if set successfully
        """
        if not self.ticks or index < 0 or index >= len(self.ticks):
            return False

        with self._lock:
            self.current_index = index

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
            game_active=tick.active,
            game_id=tick.game_id
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
        # Only pause if NOT in multi-game mode (instant advance for multi-game)
        if not self.multi_game_mode:
            self.pause()

        # Calculate final metrics
        metrics = self.state.calculate_metrics()

        event_bus.publish(Events.GAME_END, {
            'game_id': self.game_id,
            'metrics': metrics
        })
        self.state.update(game_active=False)

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

    # ========================================================================
    # LIVE FEED CONTROL (Phase 5)
    # ========================================================================

    def enable_recording(self) -> bool:
        """
        Enable auto-recording of live feeds

        Returns:
            True if recording was enabled
        """
        with self._lock:
            if self.auto_recording:
                logger.info("Recording already enabled")
                return False

            self.auto_recording = True

            # Start recording if game is in progress
            if self.ticks and not self.recorder_sink.is_recording():
                self.recorder_sink.start_recording(self.game_id)
                logger.info("Recording enabled and started for current game")
            else:
                logger.info("Recording enabled (will start on next game)")

            return True

    def disable_recording(self) -> bool:
        """
        Disable auto-recording of live feeds

        Returns:
            True if recording was disabled
        """
        with self._lock:
            if not self.auto_recording:
                logger.info("Recording already disabled")
                return False

            self.auto_recording = False

            # Stop current recording if active
            if self.recorder_sink.is_recording():
                summary = self.recorder_sink.stop_recording()
                logger.info(f"Recording disabled and stopped: {summary}")
            else:
                logger.info("Recording disabled")

            return True

    def is_recording(self) -> bool:
        """
        Check if currently recording

        Returns:
            True if recording is active
        """
        return self.recorder_sink.is_recording()

    def get_recording_info(self) -> dict:
        """
        Get current recording status

        Returns:
            Dict with recording info (enabled, active, filepath, tick_count)
        """
        with self._lock:
            return {
                'enabled': self.auto_recording,
                'active': self.recorder_sink.is_recording(),
                'filepath': str(self.recorder_sink.get_current_file()) if self.recorder_sink.get_current_file() else None,
                'tick_count': self.recorder_sink.get_tick_count()
            }

    def get_ring_buffer_info(self) -> dict:
        """
        Get ring buffer status

        Returns:
            Dict with buffer info (size, max_size, oldest_tick, newest_tick)
        """
        return {
            'size': self.live_ring_buffer.get_size(),
            'max_size': self.live_ring_buffer.get_max_size(),
            'is_full': self.live_ring_buffer.is_full(),
            'oldest_tick': self.live_ring_buffer.get_oldest_tick().tick if self.live_ring_buffer.get_oldest_tick() else None,
            'newest_tick': self.live_ring_buffer.get_newest_tick().tick if self.live_ring_buffer.get_newest_tick() else None
        }
