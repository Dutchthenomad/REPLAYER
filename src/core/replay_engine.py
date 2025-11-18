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

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Manages game replay playback with production-ready features:
    - Proper resource management and cleanup
    - Thread-safe operations with correct lock ordering
    - Memory-bounded live feed handling
    - Graceful error handling and recovery
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

        # Playback control
        self.is_playing = False
        self.playback_speed = 1.0
        self.playback_thread: Optional[threading.Thread] = None
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
        self.auto_recording = config.LIVE_FEED.get('auto_recording', True)

        # Thread safety with proper initialization
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._cleanup_registered = False

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

    def cleanup(self):
        """Clean up resources (called on shutdown)"""
        try:
            # Signal threads to stop
            self._stop_event.set()

            # Stop playback
            if self.is_playing:
                self.stop()

            # Wait for playback thread to finish
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=2.0)

            # Stop recording if active
            if self.recorder_sink.is_recording():
                summary = self.recorder_sink.stop_recording()
                try:
                    logger.info(f"Stopped recording on cleanup: {summary}")
                except (ValueError, OSError):
                    pass  # Logging may be shutdown at exit

            # Clear buffers
            self.live_ring_buffer.clear()

            try:
                logger.info("ReplayEngine cleanup completed")
            except (ValueError, OSError):
                pass  # Logging may be shutdown at exit
        except Exception as e:
            try:
                logger.error(f"Error during cleanup: {e}", exc_info=True)
            except (ValueError, OSError):
                pass  # Logging may be shutdown at exit

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
    # PLAYBACK CONTROL
    # ========================================================================

    def play(self):
        """Start auto-playback"""
        with self._acquire_lock():
            if self.is_playing:
                logger.warning("Already playing")
                return

            if not self.ticks:
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

            event_bus.publish(Events.REPLAY_STARTED, {'game_id': self.game_id})
            logger.info("Playback started")

    def pause(self):
        """Pause auto-playback"""
        with self._acquire_lock():
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

        event_bus.publish(Events.REPLAY_PAUSED, {'game_id': self.game_id})
        logger.info("Playback paused")

    def stop(self):
        """Stop playback and reset to start"""
        # First pause playback
        self.pause()

        with self._acquire_lock():
            self.current_index = 0

        # Display first tick
        if self.ticks:
            self.display_tick(0)

        event_bus.publish(Events.REPLAY_STOPPED, {'game_id': self.game_id})
        logger.info("Playback stopped")

    def reset(self):
        """Reset game to initial state (stop playback, reset state, go to beginning)"""
        # Stop playback
        self.pause()

        with self._acquire_lock():
            self.current_index = 0

        # Reset game state
        self.state.reset()

        # Update state with first tick if available
        if self.ticks:
            first_tick = self.ticks[0]
            self.state.update(
                game_id=self.game_id,
                current_tick=first_tick.tick,
                current_price=first_tick.price,
                current_phase=first_tick.phase,
                game_active=first_tick.active,
                rugged=first_tick.rugged
            )
            self.display_tick(0)

        event_bus.publish(Events.REPLAY_RESET, {'game_id': self.game_id})
        logger.info("Game reset to initial state")

    def step_forward(self) -> bool:
        """Step forward one tick"""
        with self._acquire_lock():
            if not self.ticks:
                return False

            if self.current_index >= len(self.ticks) - 1:
                self._handle_game_end()
                return False

            self.current_index += 1

        self.display_tick(self.current_index)
        return True

    def step_backward(self) -> bool:
        """Step backward one tick (not available in live mode)"""
        if self.is_live_mode:
            logger.warning("Cannot step backward in live mode")
            return False

        with self._acquire_lock():
            if not self.ticks or self.current_index <= 0:
                return False

            self.current_index -= 1

        self.display_tick(self.current_index)
        return True

    def jump_to_tick(self, tick_number: int) -> bool:
        """Jump to specific tick number (not available in live mode)"""
        if self.is_live_mode:
            logger.warning("Cannot jump to tick in live mode")
            return False

        with self._acquire_lock():
            if not self.ticks:
                return False

            # Find tick with matching number
            for i, tick in enumerate(self.ticks):
                if tick.tick == tick_number:
                    self.current_index = i
                    self.display_tick(i)
                    return True

        logger.warning(f"Tick {tick_number} not found")
        return False

    def jump_to_index(self, index: int) -> bool:
        """Jump to specific index in tick list"""
        with self._acquire_lock():
            if not self.ticks or index < 0 or index >= len(self.ticks):
                return False

            self.current_index = index

        self.display_tick(index)
        return True

    def set_tick_index(self, index: int) -> bool:
        """Backwards-compatible alias for jump_to_index()"""
        return self.jump_to_index(index)

    def set_speed(self, speed: float):
        """Set playback speed multiplier"""
        with self._acquire_lock():
            self.playback_speed = max(0.1, min(10.0, speed))
            new_speed = self.playback_speed

        event_bus.publish(Events.REPLAY_SPEED_CHANGED, {'speed': new_speed})
        logger.info(f"Playback speed set to {new_speed}x")

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

        # Store current tick reference
        self.state.current_tick = tick

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
        except:
            pass
