"""
ReplaySource Interface - Abstract base for tick data sources

Defines the interface for providing tick data to ReplayEngine from various sources:
- Files (JSONL)
- WebSocket (live feeds)
- Simulation/testing
- Recording playback
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from models import GameTick


class ReplaySource(ABC):
    """
    Abstract base class for replay data sources

    Implementations must provide a way to load game ticks either:
    - All at once (batch loading for files)
    - Incrementally (streaming for WebSocket/live feeds)
    """

    @abstractmethod
    def load(self, identifier: str) -> tuple[List[GameTick], str]:
        """
        Load game data from source

        Args:
            identifier: Source-specific identifier (filepath, game ID, etc.)

        Returns:
            Tuple of (ticks list, game_id)

        Raises:
            FileNotFoundError: If source not found
            ValueError: If data is invalid
        """
        pass

    @abstractmethod
    def is_available(self, identifier: str) -> bool:
        """
        Check if source is available

        Args:
            identifier: Source-specific identifier

        Returns:
            True if source exists and is accessible
        """
        pass

    @abstractmethod
    def list_available(self) -> List[str]:
        """
        List all available sources

        Returns:
            List of source identifiers (filepaths, game IDs, etc.)
        """
        pass

    def get_metadata(self, identifier: str) -> dict:
        """
        Get metadata about a source (optional)

        Args:
            identifier: Source-specific identifier

        Returns:
            Dictionary with metadata (tick_count, duration, etc.)
        """
        return {}


class FileDirectorySource(ReplaySource):
    """
    File-based replay source

    Loads game ticks from JSONL files in a directory
    """

    def __init__(self, directory: Path):
        """
        Initialize file directory source

        Args:
            directory: Path to directory containing JSONL files
        """
        self.directory = Path(directory)
        if not self.directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

    def load(self, identifier: str) -> tuple[List[GameTick], str]:
        """
        Load game from JSONL file

        Args:
            identifier: Filename or path to JSONL file

        Returns:
            Tuple of (ticks list, game_id)
        """
        filepath = self._resolve_path(identifier)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        ticks = []
        game_id = None

        import json

        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    tick = GameTick.from_dict(data)
                    ticks.append(tick)

                    # Extract game_id from first tick
                    if game_id is None:
                        game_id = tick.game_id

                except Exception as e:
                    raise ValueError(f"Invalid tick data at line {line_num}: {e}")

        if not ticks:
            raise ValueError(f"No valid ticks found in {filepath}")

        if game_id is None:
            game_id = filepath.stem  # Use filename as fallback

        return ticks, game_id

    def is_available(self, identifier: str) -> bool:
        """Check if file exists"""
        try:
            filepath = self._resolve_path(identifier)
            return filepath.exists()
        except (OSError, ValueError):
            # AUDIT FIX: Catch specific exceptions for path resolution
            return False

    def list_available(self) -> List[str]:
        """List all JSONL files in directory"""
        return sorted([
            f.name for f in self.directory.glob("*.jsonl")
        ])

    def get_metadata(self, identifier: str) -> dict:
        """Get file metadata"""
        filepath = self._resolve_path(identifier)

        if not filepath.exists():
            return {}

        # Count lines without loading full file
        line_count = 0
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    line_count += 1

        return {
            'filepath': str(filepath),
            'tick_count': line_count,
            'file_size': filepath.stat().st_size,
            'modified': filepath.stat().st_mtime
        }

    def _resolve_path(self, identifier: str) -> Path:
        """Resolve identifier to full file path"""
        path = Path(identifier)

        # If absolute path provided, use as-is
        if path.is_absolute():
            return path

        # Otherwise, resolve relative to directory
        return self.directory / identifier
