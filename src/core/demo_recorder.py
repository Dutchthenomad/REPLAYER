"""
DemoRecorderSink - Human Demonstration Recording for Imitation Learning

Records human gameplay demonstrations to JSONL files, capturing:
- All button presses (bet increments, percentages, trades)
- Full state context at each action
- Round-trip latency for trade confirmations

File Organization:
- demonstrations/
    session_YYYYMMDD_HHMMSS/
        game_001_gameId.jsonl
        game_002_gameId.jsonl
        session_metadata.json
"""

import json
import logging
import threading
import atexit
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

from models import (
    StateSnapshot,
    DemoAction,
    get_category_for_button,
    is_trade_action,
)

logger = logging.getLogger(__name__)


class DemoRecordingError(Exception):
    """Custom exception for demo recording-related errors."""


class DemoRecorderSink:
    """
    Production-ready recorder for human demonstration actions.

    Two-level hierarchy:
    - Session: A demonstration session spanning multiple consecutive games
    - Game: Individual game recordings with per-game JSONL files

    Thread-safe with RLock for concurrent access from UI and WebSocket threads.
    """

    # Class-level lock for managing multiple instances
    _instances_lock = threading.Lock()
    _active_instances: List['DemoRecorderSink'] = []
    _shutting_down = False

    def __init__(self, base_dir: Path, buffer_size: int = 100):
        """
        Initialize DemoRecorderSink.

        Args:
            base_dir: Base directory for demonstration recordings
            buffer_size: Number of actions to buffer before flush
        """
        self.base_dir = Path(base_dir)
        self.buffer_size = max(1, buffer_size)

        # Create base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self._session_id: Optional[str] = None
        self._session_dir: Optional[Path] = None
        self._session_start_time: Optional[datetime] = None
        self._games_played: int = 0
        self._total_actions: int = 0

        # Game state
        self._game_id: Optional[str] = None
        self._game_number: int = 0
        self._game_file: Optional[Path] = None
        self._file_handle = None
        self._game_start_time: Optional[datetime] = None

        # Action tracking
        self._buffer: List[str] = []
        self._action_count: int = 0
        self._pending_actions: Dict[str, DemoAction] = {}

        # Thread safety
        self._lock = threading.RLock()
        self._closed = False

        # Register for cleanup
        self._register_instance()

        logger.info(f"DemoRecorderSink initialized: {self.base_dir} (buffer_size={buffer_size})")

    def _register_instance(self):
        """Register this instance for cleanup on exit"""
        with self._instances_lock:
            self._active_instances.append(self)
            if len(self._active_instances) == 1:
                atexit.register(self._cleanup_all_instances)

    @classmethod
    def _cleanup_all_instances(cls):
        """Clean up all active recorder instances on exit"""
        # Avoid deadlock: `instance.close()` also acquires `_instances_lock`.
        cls._shutting_down = True
        with cls._instances_lock:
            instances = list(cls._active_instances)
            cls._active_instances.clear()

        for instance in instances:
            try:
                instance.close()
            except Exception:
                # Avoid noisy/logging failures during interpreter shutdown.
                pass

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(self) -> str:
        """
        Start a new demonstration session.

        Creates session directory with naming: session_YYYYMMDD_HHMMSS

        Returns:
            Session ID string
        """
        with self._lock:
            # End previous session if active
            if self._session_id is not None:
                self.end_session()

            # Generate session ID from timestamp
            now = datetime.now()
            self._session_id = f"session_{now.strftime('%Y%m%d_%H%M%S')}"
            self._session_dir = self.base_dir / self._session_id
            self._session_start_time = now

            # Create session directory
            self._session_dir.mkdir(parents=True, exist_ok=True)

            # Reset session counters
            self._games_played = 0
            self._total_actions = 0
            self._game_number = 0

            logger.info(f"Started demonstration session: {self._session_id}")
            return self._session_id

    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        End the current demonstration session.

        Creates session_metadata.json with session summary.

        Returns:
            Summary dict with session_id, games_played, total_actions
        """
        with self._lock:
            if self._session_id is None:
                return None

            # End active game if any
            if self._game_id is not None:
                self.end_game()

            # Build summary
            summary = {
                'session_id': self._session_id,
                'games_played': self._games_played,
                'total_actions': self._total_actions,
            }

            # Write session metadata
            if self._session_dir is not None:
                metadata_file = self._session_dir / "session_metadata.json"
                metadata = {
                    '_metadata': {
                        'session_id': self._session_id,
                        'start_time': self._session_start_time.isoformat() if self._session_start_time else None,
                        'end_time': datetime.now().isoformat(),
                        'games_played': self._games_played,
                        'total_actions': self._total_actions,
                    }
                }
                try:
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2)
                except Exception as e:
                    logger.error(f"Failed to write session metadata: {e}")

            logger.info(f"Ended session {self._session_id}: {self._games_played} games, {self._total_actions} actions")

            # Reset session state
            self._session_id = None
            self._session_dir = None
            self._session_start_time = None

            return summary

    # -------------------------------------------------------------------------
    # Game Management
    # -------------------------------------------------------------------------

    def start_game(self, game_id: str) -> Path:
        """
        Start recording a new game.

        Creates JSONL file: game_NNN_gameId.jsonl

        Args:
            game_id: Game identifier from server

        Returns:
            Path to the game recording file

        Raises:
            RuntimeError: If no session is active
        """
        with self._lock:
            if self._session_id is None:
                raise RuntimeError("No session active. Call start_session() first.")

            # End previous game if active
            if self._game_id is not None:
                self.end_game()

            # Increment game number
            self._game_number += 1
            self._game_id = game_id
            self._game_start_time = datetime.now()

            # Create filename: game_001_gameId.jsonl
            filename = f"game_{self._game_number:03d}_{game_id}.jsonl"
            self._game_file = self._session_dir / filename

            # Open file and write header
            try:
                self._file_handle = open(self._game_file, 'w', encoding='utf-8', buffering=8192)
                header = {
                    '_header': {
                        'game_id': game_id,
                        'session_id': self._session_id,
                        'game_number': self._game_number,
                        'start_time': self._game_start_time.isoformat(),
                    }
                }
                self._file_handle.write(json.dumps(header) + '\n')
                self._file_handle.flush()
            except Exception as e:
                if self._file_handle:
                    try:
                        self._file_handle.close()
                    except (OSError, IOError):
                        pass
                    self._file_handle = None
                raise DemoRecordingError(f"Failed to start game recording: {e}")

            # Reset game counters
            self._buffer = []
            self._action_count = 0
            self._pending_actions = {}

            logger.info(f"Started game recording: {filename}")
            return self._game_file

    def end_game(self) -> Optional[Dict[str, Any]]:
        """
        End the current game recording.

        Flushes buffer, writes footer, closes file.

        Returns:
            Summary dict with game_id, action_count, filepath
        """
        with self._lock:
            if self._game_id is None:
                return None

            # Flush buffer (force=True to include unconfirmed trade actions)
            self._flush(force=True)

            # Write footer
            if self._file_handle:
                footer = {
                    '_footer': {
                        'game_id': self._game_id,
                        'session_id': self._session_id,
                        'game_number': self._game_number,
                        'end_time': datetime.now().isoformat(),
                        'action_count': self._action_count,
                    }
                }
                try:
                    self._file_handle.write(json.dumps(footer) + '\n')
                    self._file_handle.flush()
                    os.fsync(self._file_handle.fileno())
                except Exception as e:
                    logger.error(f"Error writing game footer: {e}")

                # Close file
                try:
                    self._file_handle.close()
                except (OSError, IOError):
                    pass
                self._file_handle = None

            # Build summary
            summary = {
                'game_id': self._game_id,
                'action_count': self._action_count,
                'filepath': self._game_file,
            }

            # Update session counters
            self._games_played += 1
            self._total_actions += self._action_count

            logger.info(f"Ended game {self._game_id}: {self._action_count} actions")

            # Reset game state
            self._game_id = None
            self._game_file = None
            self._game_start_time = None
            self._buffer = []
            self._action_count = 0
            self._pending_actions = {}

            return summary

    # -------------------------------------------------------------------------
    # Action Recording
    # -------------------------------------------------------------------------

    def record_button_press(
        self,
        button: str,
        state_before: StateSnapshot,
        amount: Optional[Decimal] = None,
        state_after: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a button press action.

        Args:
            button: Button text (e.g., '+0.01', 'BUY', '25%')
            state_before: Game state snapshot at time of action
            amount: Trade amount (for BUY/SELL/SIDEBET)
            state_after: Optional state changes after action

        Returns:
            Action ID for confirmation tracking
        """
        with self._lock:
            # Get category for button
            category = get_category_for_button(button)

            # Create action with factory method if trade, else directly
            if is_trade_action(category):
                action = DemoAction.create_trade_action(
                    button=button,
                    amount=amount or Decimal('0'),
                    state_before=state_before
                )
            else:
                action = DemoAction.create_bet_action(
                    button=button,
                    state_before=state_before,
                    state_after=state_after
                )

            # Track pending trade actions for confirmation
            if is_trade_action(category):
                self._pending_actions[action.action_id] = action

            # Serialize to JSON
            action_json = json.dumps(action.to_jsonl_dict())
            self._buffer.append(action_json)
            self._action_count += 1

            # Flush if buffer full
            if len(self._buffer) >= self.buffer_size:
                self._flush()

            return action.action_id

    def record_confirmation(
        self,
        action_id: str,
        server_data: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """
        Record trade confirmation from server.

        Args:
            action_id: Action ID returned from record_button_press
            server_data: Server confirmation data

        Returns:
            Latency in milliseconds, or None if action not found
        """
        with self._lock:
            # Find pending action
            action = self._pending_actions.get(action_id)
            if action is None:
                logger.warning(f"Confirmation for unknown action: {action_id}")
                return None

            # Record confirmation timestamp and calculate latency
            timestamp_confirmed = int(time.time() * 1000)
            latency_ms = action.record_confirmation(timestamp_confirmed, server_data)

            # Update the buffered action with confirmation data
            # Find and replace in buffer
            for i, action_json in enumerate(self._buffer):
                action_dict = json.loads(action_json)
                if action_dict.get('action_id') == action_id:
                    # Update with confirmation
                    action_dict['timestamp_confirmed'] = timestamp_confirmed
                    action_dict['latency_ms'] = latency_ms
                    action_dict['confirmation'] = server_data
                    self._buffer[i] = json.dumps(action_dict)
                    break

            # Remove from pending
            del self._pending_actions[action_id]

            logger.debug(f"Recorded confirmation for {action_id}: {latency_ms:.1f}ms")
            return latency_ms

    # -------------------------------------------------------------------------
    # Buffer Management
    # -------------------------------------------------------------------------

    def _flush(self, force: bool = False):
        """
        Flush buffer to disk. Called with lock held.

        Args:
            force: If True, flush all actions including pending confirmations.
                   Used on game end to ensure all data is written.
        """
        if not self._buffer or not self._file_handle:
            return

        try:
            pending_ids = set(self._pending_actions.keys())
            remaining_buffer = []

            for action_json in self._buffer:
                action_dict = json.loads(action_json)
                action_id = action_dict.get('action_id')

                # If forcing or action is not pending confirmation, write it
                if force or action_id not in pending_ids:
                    self._file_handle.write(action_json + '\n')
                else:
                    # Keep pending actions in buffer
                    remaining_buffer.append(action_json)

            self._file_handle.flush()
            self._buffer = remaining_buffer
        except Exception as e:
            logger.error(f"Failed to flush buffer: {e}")
            raise

    # -------------------------------------------------------------------------
    # Status Methods
    # -------------------------------------------------------------------------

    @property
    def action_count(self) -> int:
        """Get number of actions recorded in current game"""
        with self._lock:
            return self._action_count

    def is_session_active(self) -> bool:
        """Check if a session is currently active"""
        with self._lock:
            return self._session_id is not None

    def is_game_active(self) -> bool:
        """Check if a game is currently being recorded"""
        with self._lock:
            return self._game_id is not None

    def get_status(self) -> Dict[str, Any]:
        """Get complete recorder status"""
        with self._lock:
            return {
                'session_id': self._session_id,
                'session_active': self._session_id is not None,
                'game_id': self._game_id,
                'game_active': self._game_id is not None,
                'games_played': self._games_played,
                'total_actions': self._total_actions,
                'current_game_actions': self._action_count,
                'buffer_size': len(self._buffer),
                'pending_confirmations': len(self._pending_actions),
            }

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def close(self):
        """Close recorder and clean up resources"""
        with self._lock:
            if self._closed:
                return

            # End active session (which ends active game)
            if self._session_id is not None and not self.__class__._shutting_down:
                self.end_session()
            elif self.__class__._shutting_down:
                try:
                    if self._file_handle:
                        self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None
                self._buffer = []
                self._pending_actions.clear()

            self._closed = True

            # Remove from active instances
            with self._instances_lock:
                if self in self._active_instances:
                    self._active_instances.remove(self)

            if not self.__class__._shutting_down:
                logger.info("DemoRecorderSink closed")

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()

    def __del__(self):
        """Destructor for cleanup (fallback only)"""
        try:
            if not self._closed:
                self.close()
        except Exception:
            pass
