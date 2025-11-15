"""
LiveRingBuffer - Circular buffer for live game feeds

Prevents unbounded memory growth during long live games by maintaining
a fixed-size buffer that automatically discards oldest ticks when full.
"""

import logging
import threading
from collections import deque
from typing import List, Optional
from models import GameTick

logger = logging.getLogger(__name__)


class LiveRingBuffer:
    """
    Thread-safe circular buffer for live game ticks

    Features:
    - Fixed-size buffer (configurable, default: 5000 ticks)
    - Automatic eviction of oldest ticks when full
    - Thread-safe operations for concurrent access
    - Efficient memory usage for long-running games

    Design rationale:
    - Live games can run for extended periods
    - Full game history not needed for live display (just recent context)
    - Ring buffer prevents memory exhaustion while preserving recent state
    """

    def __init__(self, max_size: int = 5000):
        """
        Initialize ring buffer

        Args:
            max_size: Maximum number of ticks to store (default: 5000)
                     Can be increased in future if analysis requires more history
        """
        if max_size <= 0:
            raise ValueError(f"Buffer size must be positive, got {max_size}")

        self.max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.RLock()

        logger.info(f"LiveRingBuffer initialized: max_size={max_size}")

    def append(self, tick: GameTick) -> bool:
        """
        Append tick to buffer (evicts oldest if full)

        Args:
            tick: GameTick to append

        Returns:
            True if appended successfully
        """
        with self._lock:
            self._buffer.append(tick)
            return True

    def get_latest(self, n: Optional[int] = None) -> List[GameTick]:
        """
        Get latest N ticks (or all if n=None)

        Args:
            n: Number of latest ticks to retrieve (None = all)

        Returns:
            List of GameTick objects (newest last)
        """
        with self._lock:
            if n is None:
                return list(self._buffer)

            if n <= 0:
                return []

            # Get last n items (or fewer if buffer is smaller)
            return list(self._buffer)[-n:]

    def get_all(self) -> List[GameTick]:
        """
        Get all ticks in buffer

        Returns:
            List of all GameTick objects (oldest first, newest last)
        """
        with self._lock:
            return list(self._buffer)

    def clear(self):
        """Clear all ticks from buffer"""
        with self._lock:
            self._buffer.clear()
            logger.debug("LiveRingBuffer cleared")

    def is_full(self) -> bool:
        """
        Check if buffer is at maximum capacity

        Returns:
            True if buffer is full
        """
        with self._lock:
            return len(self._buffer) >= self.max_size

    def get_size(self) -> int:
        """
        Get current number of ticks in buffer

        Returns:
            Number of ticks currently stored
        """
        with self._lock:
            return len(self._buffer)

    def get_max_size(self) -> int:
        """
        Get maximum buffer capacity

        Returns:
            Maximum number of ticks buffer can hold
        """
        return self.max_size

    def get_oldest_tick(self) -> Optional[GameTick]:
        """
        Get oldest tick in buffer

        Returns:
            Oldest GameTick or None if buffer empty
        """
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[0]

    def get_newest_tick(self) -> Optional[GameTick]:
        """
        Get newest tick in buffer

        Returns:
            Newest GameTick or None if buffer empty
        """
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def get_tick_range(self, start_tick: int, end_tick: int) -> List[GameTick]:
        """
        Get ticks within a specific tick number range

        Args:
            start_tick: Starting tick number (inclusive)
            end_tick: Ending tick number (inclusive)

        Returns:
            List of GameTick objects within range
        """
        with self._lock:
            return [
                tick for tick in self._buffer
                if start_tick <= tick.tick <= end_tick
            ]

    def __len__(self) -> int:
        """Get current buffer size (supports len(buffer))"""
        return self.get_size()

    def __bool__(self) -> bool:
        """Check if buffer is non-empty (supports if buffer:)"""
        return self.get_size() > 0

    def __repr__(self) -> str:
        """String representation for debugging"""
        with self._lock:
            return (
                f"LiveRingBuffer(size={len(self._buffer)}/{self.max_size}, "
                f"oldest_tick={self._buffer[0].tick if self._buffer else None}, "
                f"newest_tick={self._buffer[-1].tick if self._buffer else None})"
            )
