"""
Replay Engine - Game playback controller (PRODUCTION READY)
Loads JSONL files, manages playback, and publishes tick events
"""

import json
import logging
import threading
import time
import atexit
from pathlib import Path
from typing import List, Optional, Callable
from decimal import Decimal
from contextlib import contextmanager

from models import GameTick
from services import event_bus, Events
from .game_state import GameState
from .recorder_sink import RecorderSink
from .live_ring_buffer import LiveRingBuffer
from .replay_playback_controller import PlaybackController

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Manages game replay playback with production-ready features:
    - Proper resource management and cleanup
    - Thread-safe operations with correct lock ordering
    - Memory-bounded live feed handling
    - Graceful error handling and recovery

    Phase 2 Refactoring:
    - Playback control delegated to PlaybackController
    """

    def __init__(self, game_state: GameState, replay_source=None):
        from core.replay_source import FileDirectorySource
        from config import config

        self.state = game_state

        # Replay source (defaults to file directory)
        if replay_source is None:
            replay_source = FileDirectorySource(config.FILES['recordings_dir'])
        self.replay_source = replay_source

        # Game data - CRITICAL FIX: Remove unbounded ticks list for live mode
        self.file_mode_ticks: List[GameTick] = []  # Only used in file playback mode
        self.is_live_mode = False  # Track current mode
        self.current_index = 0
        self.game_id: Optional[str] = None

        # Multi-game mode flag
        self.multi_game_mode = False

        # Validate configuration before using
        ring_buffer_size = max(1, config.LIVE_FEED.get('ring_buffer_size', 5000))
        recording_buffer_size = max(1, config.LIVE_FEED.get('recording_buffer_size', 100))

        # Live feed infrastructure with validated settings
        self.live_ring_buffer = LiveRingBuffer(max_size=ring_buffer_size)
        self.recorder_sink = RecorderSink(
            recordings_dir=config.FILES['recordings_dir'],
            buffer_size=recording_buffer_size
        )
        # Default to disabled - user must explicitly enable recording from menu
        self.auto_recording = config.LIVE_FEED.get('auto_recording', False)

        # Thread safety with proper initialization
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._cleanup_registered = False
        self._shutting_down = False  # PHASE 3.3: Track shutdown state for logging safety

        # Phase 2 Refactoring: Delegate playback control to PlaybackController
        self._playback = PlaybackController(self, self._lock, self._stop_event)

        # Callbacks for UI updates
        self.on_tick_callback: Optional[Callable] = None
        self.on_game_end_callback: Optional[Callable] = None

        # Register cleanup handler
        self._register_cleanup()

        logger.info(f"ReplayEngine initialized (ring_buffer={ring_buffer_size}, recording_buffer={recording_buffer_size})")

    def _register_cleanup(self):
        """Register cleanup handler to ensure resources are freed"""
        if not self._cleanup_registered:
            atexit.register(self.cleanup)
            self._cleanup_registered = True

    def _safe_log(self, level: str, message: str, exc_info: bool = False):
        """
        PHASE 3.3 AUDIT FIX: Safe logging that handles shutdown state.

        During Python interpreter shutdown, logging streams may be closed
        before atexit handlers run. This method silently ignores logging
        errors during shutdown to prevent spurious error messages.

        Args:
            level: Log level ('info', 'warning', 'error', 'debug')
            message: Message to log
            exc_info: Whether to include exception info
        """
        if self._shutting_down:
            return  # Don't log during shutdown

        try:
            log_func = getattr(logger, level, logger.info)
            if exc_info:
                log_func(message, exc_info=True)
            else:
                log_func(message)
        except (ValueError, OSError, AttributeError):
            # Logging system is in an inconsistent state
            pass

    def cleanup(self):
        """Clean up resources (called on shutdown)"""
        # PHASE 3.3: Set shutdown flag to prevent logging errors
        self._shutting_down = True

        try:
            # Signal threads to stop
            self._stop_event.set()

            # Phase 2: Clean up playback controller
            if hasattr(self, '_playback'):
                self._playback.cleanup()

            # Stop recording if active
            if self.recorder_sink.is_recording():
                summary = self.recorder_sink.stop_recording()
                self._safe_log('info', f"Stopped recording on cleanup: {summary}")

            # Clear buffers
            self.live_ring_buffer.clear()

            self._safe_log('info', "ReplayEngine cleanup completed")
        except Exception as e:
            self._safe_log('error', f"Error during cleanup: {e}", exc_info=True)

    @contextmanager
    def _acquire_lock(self, timeout=5.0):
        """Context manager for acquiring lock with timeout"""
        acquired = self._lock.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError("Failed to acquire ReplayEngine lock")
        try:
            yield
        finally:
            self._lock.release()

    @property
    def ticks(self) -> List[GameTick]:
        """Get current tick list based on mode"""
        if self.is_live_mode:
            return self.live_ring_buffer.get_all()
        return self.file_mode_ticks

    # Phase 2 Refactoring: Properties for backwards compatibility
    @property
    def is_playing(self) -> bool:
        """Check if playback is active (delegates to PlaybackController)"""
        return self._playback.is_playing

    @is_playing.setter
    def is_playing(self, value: bool):
        """Set playback state (delegates to PlaybackController)"""
        self._playback.is_playing = value

    @property
    def playback_speed(self) -> float:
        """Get playback speed (delegates to PlaybackController)"""
        return self._playback.playback_speed

    @playback_speed.setter
    def playback_speed(self, value: float):
        """Set playback speed (delegates to PlaybackController)"""
        self._playback.playback_speed = value

    @property
    def playback_thread(self) -> Optional[threading.Thread]:
        """Get playback thread (delegates to PlaybackController)"""
        return self._playback.playback_thread

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
            logger.info(f"Loading game file: {filepath}")

            # Stop any current recording
            if self.recorder_sink.is_recording():
                self.recorder_sink.stop_recording()

            # Use replay source to load ticks
            loaded_ticks, game_id = self.replay_source.load(str(filepath))

            with self._acquire_lock():
                # Switch to file mode
                self.is_live_mode = False
                self.file_mode_ticks = loaded_ticks
                self.current_index = 0
                self.game_id = game_id
                
                # Clear live buffers when switching to file mode
                self.live_ring_buffer.clear()

            # Reset state for new game session
            self.state.reset()
            self.state.update(game_id=self.game_id, game_active=False)

            event_bus.publish(Events.GAME_START, {
                'game_id': self.game_id,
                'tick_count': len(loaded_ticks),
                'filepath': str(filepath),
                'mode': 'file'
            })

            logger.info(f"Loaded {len(loaded_ticks)} ticks from game {self.game_id}")

            # Publish file loaded event
            event_bus.publish(Events.FILE_LOADED, {
                'filepath': str(filepath),
                'game_id': self.game_id,
                'tick_count': len(loaded_ticks)
            })

            # Display first tick
            self.display_tick(0)

            return True

        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load file: {e}", exc_info=True)
            return False

    def load_game(self, ticks: List[GameTick], game_id: str) -> bool:
        """
        Load game data from a list of ticks (for testing)
        """
        with self._acquire_lock():
            try:
                # Switch to file mode for pre-loaded ticks
                self.is_live_mode = False
                self.file_mode_ticks = ticks
                self.game_id = game_id
                self.current_index = 0

                # Clear live buffers
                self.live_ring_buffer.clear()

                # AUDIT FIX: Reset state to prevent contamination between test runs
                self.state.reset()

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
                event_bus.publish(Events.FILE_LOADED, {
                    'game_id': game_id, 
                    'tick_count': len(ticks),
                    'mode': 'preloaded'
                })
                return True

            except Exception as e:
                logger.error(f"Failed to load game: {e}", exc_info=True)
                return False

    def push_tick(self, tick: GameTick) -> bool:
        """
        Push a single tick to the replay engine (for live feeds)
        CRITICAL FIX: Only use ring buffer in live mode, no unbounded list growth
        AUDIT FIX: Capture tick data inside lock to prevent race condition

        Args:
            tick: GameTick to add

        Returns:
            True if tick was added successfully
        """
        if not isinstance(tick, GameTick):
            logger.error(f"Invalid tick type: {type(tick)}")
            return False

        # AUDIT FIX: Capture display data inside lock to prevent race condition
        display_data = None

        try:
            with self._acquire_lock():
                # Initialize live mode on first tick
                if not self.is_live_mode or not self.game_id:
                    self.is_live_mode = True
                    self.game_id = tick.game_id
                    self.file_mode_ticks = []  # Clear file mode data
                    self.current_index = 0

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
                        try:
                            recording_file = self.recorder_sink.start_recording(self.game_id)
                            logger.info(f"Started live game: {self.game_id}, recording to {recording_file.name}")
                        except Exception as e:
                            logger.error(f"Failed to start recording: {e}")
                            # Continue without recording
                    else:
                        logger.info(f"Started live game: {self.game_id} (recording disabled)")

                # Detect new game starting (game_id changed) - LIVE FEED MULTI-GAME SUPPORT
                if tick.game_id != self.game_id:
                    logger.info(f"🔄 New game detected: {self.game_id} → {tick.game_id}")

                    # End current game gracefully
                    self._handle_game_end()

                    # Reset for new game
                    self.game_id = tick.game_id
                    self.current_index = 0
                    self.live_ring_buffer.clear()

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

                    # Start recording new game
                    if self.auto_recording:
                        try:
                            recording_file = self.recorder_sink.start_recording(self.game_id)
                            logger.info(f"Started live game: {self.game_id}, recording to {recording_file.name}")
                        except Exception as e:
                            logger.error(f"Failed to start recording: {e}")
                    else:
                        logger.info(f"Started live game: {self.game_id} (recording disabled)")

                # Add tick to ring buffer ONLY (no unbounded list growth)
                self.live_ring_buffer.append(tick)

                # Record tick to disk if recording enabled
                if self.auto_recording and self.recorder_sink.is_recording():
                    try:
                        self.recorder_sink.record_tick(tick)
                    except Exception as e:
                        logger.error(f"Failed to record tick: {e}")
                        # Continue processing even if recording fails

                # Update current index to latest
                self.current_index = self.live_ring_buffer.get_size() - 1

                # AUDIT FIX: Capture tick data and index inside lock to prevent race condition
                # This prevents the tick list from changing between lock release and display
                current_ticks = self.ticks  # Property call - gets current tick list based on mode
                if current_ticks and 0 <= self.current_index < len(current_ticks):
                    display_data = {
                        'tick': current_ticks[self.current_index],
                        'index': self.current_index,
                        'total': len(current_ticks)
                    }

            # AUDIT FIX: Display using captured tick data (safe - no race condition)
            if display_data is not None:
                self._display_tick_direct(display_data['tick'], display_data['index'], display_data['total'])

            logger.debug(f"Pushed tick {tick.tick} for game {tick.game_id}")
            return True

        except Exception as e:
            logger.error(f"Error pushing tick: {e}", exc_info=True)
            return False

    # ========================================================================
    # PLAYBACK CONTROL (Phase 2: Delegates to PlaybackController)
    # ========================================================================

    def play(self):
        """Start auto-playback (delegates to PlaybackController)"""
        self._playback.play()

    def pause(self):
        """Pause auto-playback (delegates to PlaybackController)"""
        self._playback.pause()

    def stop(self):
        """Stop playback and reset to start (delegates to PlaybackController)"""
        self._playback.stop()

    def reset(self):
        """Reset game to initial state (delegates to PlaybackController)"""
        self._playback.reset()

    def step_forward(self) -> bool:
        """Step forward one tick (delegates to PlaybackController)"""
        return self._playback.step_forward()

    def step_backward(self) -> bool:
        """Step backward one tick (delegates to PlaybackController)"""
        return self._playback.step_backward()

    def jump_to_tick(self, tick_number: int) -> bool:
        """Jump to specific tick number (delegates to PlaybackController)"""
        return self._playback.jump_to_tick(tick_number)

    def jump_to_index(self, index: int) -> bool:
        """Jump to specific index in tick list (delegates to PlaybackController)"""
        return self._playback.jump_to_index(index)

    def set_tick_index(self, index: int) -> bool:
        """Backwards-compatible alias for jump_to_index()"""
        return self._playback.set_tick_index(index)

    def set_speed(self, speed: float):
        """Set playback speed multiplier (delegates to PlaybackController)"""
        self._playback.set_speed(speed)

    # ========================================================================
    # DISPLAY & UPDATES
    # ========================================================================

    def display_tick(self, index: int):
        """Display tick at given index"""
        ticks = self.ticks  # Get current tick list based on mode

        if not ticks or index < 0 or index >= len(ticks):
            return

        tick = ticks[index]
        self._display_tick_direct(tick, index, len(ticks))

    def _display_tick_direct(self, tick: GameTick, index: int, total: int):
        """
        Display tick using pre-captured data (prevents race conditions)

        AUDIT FIX: This method accepts the tick directly instead of looking it up
        by index, preventing race conditions where the tick list changes between
        lock release and display.

        Args:
            tick: The GameTick to display
            index: The index of this tick
            total: Total number of ticks in the list
        """
        # Update game state
        self.state.update(
            current_tick=tick.tick,
            current_price=tick.price,
            current_phase=tick.phase,
            rugged=tick.rugged,
            game_active=tick.active,
            game_id=tick.game_id
        )

        # Publish tick event
        # Use (index + 1) so progress reaches 100% at final tick
        event_bus.publish(Events.GAME_TICK, {
            'tick': tick,
            'index': index,
            'total': total,
            'progress': ((index + 1) / total) * 100 if total else 0,
            'mode': 'live' if self.is_live_mode else 'file'
        })

        # Call UI callback if set
        if self.on_tick_callback:
            try:
                self.on_tick_callback(tick, index, total)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}")

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
        # Stop recording if in live mode
        if self.is_live_mode and self.recorder_sink.is_recording():
            summary = self.recorder_sink.stop_recording()
            logger.info(f"Live game ended, recording stopped: {summary}")

        # Only pause if NOT in multi-game mode
        if not self.multi_game_mode:
            self.pause()

        # Calculate final metrics
        metrics = self.state.calculate_metrics()

        event_bus.publish(Events.GAME_END, {
            'game_id': self.game_id,
            'metrics': metrics,
            'mode': 'live' if self.is_live_mode else 'file'
        })
        self.state.update(game_active=False)

        if self.on_game_end_callback:
            try:
                self.on_game_end_callback(metrics)
            except Exception as e:
                logger.error(f"Error in game end callback: {e}")

        logger.info(f"Game ended. Final metrics: {metrics}")

    # Note: _playback_loop moved to PlaybackController (Phase 2 refactoring)

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
        ticks = self.ticks
        return self.current_index >= len(ticks) - 1 if ticks else True

    def get_current_tick(self) -> Optional[GameTick]:
        """Get current tick"""
        ticks = self.ticks
        if not ticks or self.current_index >= len(ticks):
            return None
        return ticks[self.current_index]

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)"""
        ticks = self.ticks
        if not ticks:
            return 0.0
        # Use (index + 1) so progress reaches 100% at final tick
        return (self.current_index + 1) / len(ticks)

    def get_info(self) -> dict:
        """Get replay info"""
        ticks = self.ticks
        return {
            'loaded': self.is_loaded(),
            'game_id': self.game_id,
            'total_ticks': len(ticks),
            'current_tick': self.current_index,
            'is_playing': self.is_playing,
            'speed': self.playback_speed,
            'progress': self.get_progress() * 100,
            'mode': 'live' if self.is_live_mode else 'file',
            'ring_buffer_size': self.live_ring_buffer.get_size() if self.is_live_mode else 0
        }

    # ========================================================================
    # LIVE FEED CONTROL
    # ========================================================================

    def enable_recording(self) -> bool:
        """Enable auto-recording of live feeds"""
        with self._acquire_lock():
            if self.auto_recording:
                logger.info("Recording already enabled")
                return False

            self.auto_recording = True

            # Start recording if live game is in progress
            if self.is_live_mode and self.live_ring_buffer and not self.recorder_sink.is_recording():
                try:
                    self.recorder_sink.start_recording(self.game_id)
                    logger.info("Recording enabled and started for current game")
                except Exception as e:
                    logger.error(f"Failed to start recording: {e}")
                    return False
            else:
                logger.info("Recording enabled (will start on next game)")

            return True

    def disable_recording(self) -> bool:
        """Disable auto-recording of live feeds"""
        with self._acquire_lock():
            if not self.auto_recording:
                logger.info("Recording already disabled")
                return False

            self.auto_recording = False

            # Stop current recording if active
            if self.recorder_sink.is_recording():
                try:
                    summary = self.recorder_sink.stop_recording()
                    logger.info(f"Recording disabled and stopped: {summary}")
                except Exception as e:
                    logger.error(f"Failed to stop recording: {e}")
            else:
                logger.info("Recording disabled")

            return True

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.recorder_sink.is_recording()

    def get_recording_info(self) -> dict:
        """Get current recording status"""
        with self._acquire_lock():
            current_file = self.recorder_sink.get_current_file()
            return {
                'enabled': self.auto_recording,
                'active': self.recorder_sink.is_recording(),
                'filepath': str(current_file) if current_file else None,
                'tick_count': self.recorder_sink.get_tick_count(),
                'mode': 'live' if self.is_live_mode else 'file'
            }

    def get_ring_buffer_info(self) -> dict:
        """Get ring buffer status"""
        oldest = self.live_ring_buffer.get_oldest_tick()
        newest = self.live_ring_buffer.get_newest_tick()
        
        return {
            'size': self.live_ring_buffer.get_size(),
            'max_size': self.live_ring_buffer.get_max_size(),
            'is_full': self.live_ring_buffer.is_full(),
            'oldest_tick': oldest.tick if oldest else None,
            'newest_tick': newest.tick if newest else None,
            'memory_usage_estimate': self.live_ring_buffer.get_size() * 1024  # Rough estimate in bytes
        }

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception as e:
            # AUDIT FIX: Log error safely instead of silent pass
            self._safe_log('error', f"Error in destructor: {e}")
