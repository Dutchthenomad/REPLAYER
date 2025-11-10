"""
Game Queue Management
Handles sequential game loading for multi-game sessions
"""

from pathlib import Path
from typing import List, Optional
import random
import logging

logger = logging.getLogger(__name__)


class GameQueue:
    """
    Manages sequential game loading for multi-game sessions.

    Provides queue-based access to game recordings with support for:
    - Sequential playback
    - Shuffling
    - Queue reset
    - Progress tracking
    """

    def __init__(self, recordings_dir: Path, shuffle: bool = False):
        """
        Initialize game queue.

        Args:
            recordings_dir: Path to directory containing game recordings
            shuffle: Whether to randomize game order
        """
        self.recordings_dir = Path(recordings_dir)
        self.shuffle_enabled = shuffle
        self.games: List[Path] = []
        self.current_index = 0

        # Load games
        self._load_games()

        # Shuffle if requested
        if self.shuffle_enabled:
            self.shuffle()

        logger.info(f"GameQueue initialized with {len(self.games)} games")

    def _load_games(self) -> None:
        """Load all game recording files from directory."""
        if not self.recordings_dir.exists():
            logger.error(f"Recordings directory not found: {self.recordings_dir}")
            return

        # Load all .jsonl files
        self.games = sorted(self.recordings_dir.glob("game_*.jsonl"))

        if not self.games:
            logger.warning(f"No game files found in {self.recordings_dir}")
        else:
            logger.info(f"Loaded {len(self.games)} game files from {self.recordings_dir}")

    def next_game(self) -> Optional[Path]:
        """
        Get the next game file path.

        Returns:
            Path to next game file, or None if queue exhausted
        """
        if not self.has_next():
            logger.debug("Queue exhausted - no more games")
            return None

        game = self.games[self.current_index]
        self.current_index += 1

        logger.debug(f"Next game: {game.name} ({self.current_index}/{len(self.games)})")
        return game

    def has_next(self) -> bool:
        """
        Check if more games available in queue.

        Returns:
            True if more games available, False otherwise
        """
        return self.current_index < len(self.games)

    def reset(self) -> None:
        """Reset queue to beginning."""
        self.current_index = 0
        logger.info("Queue reset to beginning")

    def shuffle(self) -> None:
        """Randomize game order."""
        random.shuffle(self.games)
        logger.info(f"Queue shuffled ({len(self.games)} games)")

    def get_progress(self) -> tuple[int, int]:
        """
        Get current progress through queue.

        Returns:
            Tuple of (current_index, total_games)
        """
        return (self.current_index, len(self.games))

    def get_remaining_count(self) -> int:
        """
        Get number of games remaining in queue.

        Returns:
            Number of unplayed games
        """
        return len(self.games) - self.current_index

    def peek_next(self) -> Optional[Path]:
        """
        Peek at next game without advancing queue.

        Returns:
            Path to next game, or None if queue exhausted
        """
        if not self.has_next():
            return None
        return self.games[self.current_index]

    def __len__(self) -> int:
        """Return total number of games in queue."""
        return len(self.games)

    def __repr__(self) -> str:
        """String representation of queue state."""
        return (f"GameQueue({self.current_index}/{len(self.games)} games, "
                f"shuffle={self.shuffle_enabled})")
