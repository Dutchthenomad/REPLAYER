"""
RecorderSink - Records live game ticks to disk

Writes incoming ticks to JSONL files with timestamp-based naming for
chronological ordering (critical for pattern analysis and ML training).
"""

import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from models import GameTick

logger = logging.getLogger(__name__)


class RecorderSink:
    """
    Records game ticks to JSONL files

    Features:
    - Timestamp-based file naming (game_YYYYMMDD_HHMMSS.jsonl)
    - Buffered writes for performance
    - Thread-safe operations
    - Auto-creates recording directory
    """

    def __init__(self, recordings_dir: Path, buffer_size: int = 100):
        """
        Initialize recorder

        Args:
            recordings_dir: Directory to save recordings
            buffer_size: Number of ticks to buffer before flush (default: 100)
        """
        self.recordings_dir = Path(recordings_dir)
        self.buffer_size = buffer_size

        # Ensure directory exists
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Recording state
        self.current_file: Optional[Path] = None
        self.file_handle = None
        self.buffer = []
        self.tick_count = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.info(f"RecorderSink initialized: {self.recordings_dir}")

    def start_recording(self, game_id: Optional[str] = None) -> Path:
        """
        Start recording a new game

        Args:
            game_id: Optional game identifier (included in data, not filename)

        Returns:
            Path to recording file
        """
        with self._lock:
            # Close previous recording if open
            if self.file_handle:
                self.stop_recording()

            # Generate timestamp-based filename for chronological ordering
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"game_{timestamp}.jsonl"
            self.current_file = self.recordings_dir / filename

            # Open file for writing
            self.file_handle = open(self.current_file, 'w')
            self.buffer = []
            self.tick_count = 0

            logger.info(f"Started recording: {filename}")
            return self.current_file

    def record_tick(self, tick: GameTick) -> bool:
        """
        Record a single tick

        Args:
            tick: GameTick to record

        Returns:
            True if recorded successfully
        """
        with self._lock:
            if not self.file_handle:
                logger.warning("No recording in progress, auto-starting")
                self.start_recording(tick.game_id)

            # Convert tick to JSON and add to buffer
            tick_json = json.dumps(tick.to_dict())
            self.buffer.append(tick_json)
            self.tick_count += 1

            # Flush buffer if full
            if len(self.buffer) >= self.buffer_size:
                self._flush()

            return True

    def stop_recording(self) -> Optional[dict]:
        """
        Stop recording and close file

        Returns:
            Summary dict with filepath, tick_count, etc.
        """
        with self._lock:
            if not self.file_handle:
                return None

            # Flush remaining buffer
            self._flush()

            # Close file
            self.file_handle.close()

            summary = {
                'filepath': str(self.current_file),
                'tick_count': self.tick_count,
                'file_size': self.current_file.stat().st_size if self.current_file else 0
            }

            logger.info(
                f"Stopped recording: {self.current_file.name} "
                f"({self.tick_count} ticks, {summary['file_size']} bytes)"
            )

            # Reset state
            self.file_handle = None
            self.current_file = None
            self.buffer = []
            self.tick_count = 0

            return summary

    def _flush(self):
        """Flush buffer to disk (called with lock held)"""
        if not self.buffer or not self.file_handle:
            return

        # Write all buffered ticks
        for tick_json in self.buffer:
            self.file_handle.write(tick_json + '\n')

        self.file_handle.flush()
        self.buffer = []

    def is_recording(self) -> bool:
        """Check if currently recording"""
        with self._lock:
            return self.file_handle is not None

    def get_current_file(self) -> Optional[Path]:
        """Get path to current recording file"""
        with self._lock:
            return self.current_file

    def get_tick_count(self) -> int:
        """Get number of ticks recorded in current session"""
        with self._lock:
            return self.tick_count

    def __del__(self):
        """Cleanup: ensure file is closed"""
        if self.file_handle:
            try:
                self.stop_recording()
            except:
                pass
