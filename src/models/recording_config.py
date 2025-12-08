"""
Recording Configuration Model - Phase 10.5A Config Model & Persistence

Unified configuration for recording sessions.
Supports JSON persistence and sensible defaults.

Config File Location: ~/.replayer/recording_config.json (or src/recording_config.json fallback)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CaptureMode(Enum):
    """Recording capture mode - what data to record."""
    GAME_STATE_ONLY = "game_state_only"
    GAME_AND_PLAYER = "game_and_player"


class MonitorThresholdType(Enum):
    """Type of threshold for monitor mode activation."""
    TICKS = "ticks"
    GAMES = "games"


@dataclass
class RecordingConfig:
    """
    Unified recording configuration.

    Attributes:
        capture_mode: What to record (game state only or with player state)
        game_count: Max games to record (None = infinite)
        time_limit_minutes: Max time to record (None = no limit)
        monitor_threshold_type: Type of threshold for monitor mode
        monitor_threshold_value: Threshold value (ticks or games)
        audio_cues: Enable audio notifications
        auto_start_on_launch: Auto-start recording on app launch
        last_modified: When config was last saved
    """
    capture_mode: CaptureMode = CaptureMode.GAME_STATE_ONLY
    game_count: Optional[int] = None  # None = infinite
    time_limit_minutes: Optional[int] = None  # None = no limit
    monitor_threshold_type: MonitorThresholdType = MonitorThresholdType.TICKS
    monitor_threshold_value: int = 20
    audio_cues: bool = True
    auto_start_on_launch: bool = False
    last_modified: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize config to dictionary for JSON storage."""
        return {
            "capture_mode": self.capture_mode.value,
            "game_count": self.game_count,
            "time_limit_minutes": self.time_limit_minutes,
            "monitor_threshold_type": self.monitor_threshold_type.value,
            "monitor_threshold_value": self.monitor_threshold_value,
            "audio_cues": self.audio_cues,
            "auto_start_on_launch": self.auto_start_on_launch,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecordingConfig":
        """Deserialize config from dictionary."""
        last_modified = None
        if data.get("last_modified"):
            last_modified = datetime.fromisoformat(data["last_modified"])

        return cls(
            capture_mode=CaptureMode(data["capture_mode"]),
            game_count=data.get("game_count"),
            time_limit_minutes=data.get("time_limit_minutes"),
            monitor_threshold_type=MonitorThresholdType(data["monitor_threshold_type"]),
            monitor_threshold_value=data["monitor_threshold_value"],
            audio_cues=data.get("audio_cues", True),
            auto_start_on_launch=data.get("auto_start_on_launch", False),
            last_modified=last_modified,
        )

    def save(self, filepath: Optional[str] = None) -> None:
        """Save config to JSON file. Creates parent directories if needed.

        Args:
            filepath: Path to save config. Uses default path if not provided.
        """
        path = Path(filepath) if filepath else self.get_default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        logger.info(f"Recording config saved to {path}")

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> "RecordingConfig":
        """
        Load config from JSON file.

        Args:
            filepath: Path to config file. Uses default path if not provided.

        Returns default config if file doesn't exist or is invalid.
        """
        path = Path(filepath) if filepath else cls.get_default_config_path()

        if not path.exists():
            logger.info(f"Config file not found at {path}, using defaults")
            return cls()

        try:
            with open(path, 'r') as f:
                data = json.load(f)
            config = cls.from_dict(data)
            logger.info(f"Recording config loaded from {filepath}")
            return config
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid config file at {filepath}: {e}, using defaults")
            return cls()

    def is_game_count_infinite(self) -> bool:
        """Check if game count is infinite (no limit)."""
        return self.game_count is None

    def is_time_limit_off(self) -> bool:
        """Check if time limit is off (no limit)."""
        return self.time_limit_minutes is None

    @staticmethod
    def get_default_config_path() -> Path:
        """
        Get default config file path.

        Prefers ~/.replayer/recording_config.json if home dir accessible,
        falls back to src/recording_config.json
        """
        home = Path.home()
        replayer_dir = home / ".replayer"
        return replayer_dir / "recording_config.json"
