"""
Recorders - Phase 10.4F

GameStateRecorder: Records game state files (prices + metadata)
PlayerSessionRecorder: Records player actions to session files
"""

import json
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from typing import Optional
import logging

from models.recording_models import (
    GameStateRecord,
    GameStateMeta,
    PlayerSession,
    PlayerSessionMeta,
    PlayerAction
)

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class GameStateRecorder:
    """Records game state to JSON files."""

    def __init__(self, base_path: str = "recordings"):
        """
        Initialize recorder.

        Args:
            base_path: Base directory for recordings
        """
        self.base_path = Path(base_path)
        self.current_game: Optional[GameStateRecord] = None
        self.game_start_time: Optional[datetime] = None

    def start_game(self, game_id: str):
        """
        Start recording a new game.

        Args:
            game_id: Unique game identifier
        """
        self.game_start_time = datetime.utcnow()
        self.current_game = GameStateRecord(
            meta=GameStateMeta(
                game_id=game_id,
                start_time=self.game_start_time
            )
        )
        logger.info(f"Started recording game: {game_id}")

    def record_prices(
        self,
        prices: list,
        peak: Decimal,
        seed_data: Optional[dict] = None
    ):
        """
        Record completed price data.

        Args:
            prices: List of price values per tick
            peak: Peak multiplier reached
            seed_data: Optional dict with server_seed, server_seed_hash
        """
        if not self.current_game:
            return

        self.current_game.prices = prices
        self.current_game.meta.end_time = datetime.utcnow()
        self.current_game.meta.duration_ticks = len(prices)
        self.current_game.meta.peak_multiplier = peak

        if seed_data:
            self.current_game.meta.server_seed = seed_data.get('server_seed')
            self.current_game.meta.server_seed_hash = seed_data.get('server_seed_hash')

    def save(self) -> Optional[str]:
        """
        Save current game to file.

        Returns:
            Filepath if saved, None if no game to save
        """
        if not self.current_game:
            return None

        # Create directory structure
        date_str = self.game_start_time.strftime("%Y-%m-%d")
        games_dir = self.base_path / date_str / "games"
        games_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self.game_start_time.strftime("%Y%m%dT%H%M%S")
        game_id_short = self.current_game.meta.game_id.split('-')[-1][:8]
        filename = f"{time_str}_{game_id_short}.game.json"
        filepath = games_dir / filename

        # Write file
        with open(filepath, 'w') as f:
            json.dump(self.current_game.to_dict(), f, indent=2, cls=DecimalEncoder)

        logger.info(f"Saved game state: {filepath}")

        # Update index
        self._update_index(date_str, filename)

        self.current_game = None
        return str(filepath)

    def _update_index(self, date_str: str, filename: str):
        """
        Update daily index file.

        Args:
            date_str: Date string (YYYY-MM-DD)
            filename: Name of the game file
        """
        index_path = self.base_path / date_str / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {"date": date_str, "games": [], "sessions": []}

        # Add game entry
        index["games"].append({
            "file": filename,
            "game_id": self.current_game.meta.game_id,
            "start_time": self.current_game.meta.start_time.isoformat(),
            "duration_ticks": self.current_game.meta.duration_ticks,
            "peak_multiplier": str(self.current_game.meta.peak_multiplier)
        })

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)


class PlayerSessionRecorder:
    """Records player actions to JSON files."""

    def __init__(self, base_path: str = "recordings"):
        """
        Initialize recorder.

        Args:
            base_path: Base directory for recordings
        """
        self.base_path = Path(base_path)
        self.session: Optional[PlayerSession] = None
        self.session_start: Optional[datetime] = None

    def start_session(self, player_id: str, username: str):
        """
        Start new recording session.

        Args:
            player_id: Player's unique ID
            username: Player's username
        """
        self.session_start = datetime.utcnow()
        self.session = PlayerSession(
            meta=PlayerSessionMeta(
                player_id=player_id,
                username=username,
                session_start=self.session_start
            )
        )
        logger.info(f"Started session for: {username}")

    def record_action(self, action: PlayerAction):
        """
        Record player action.

        Args:
            action: PlayerAction to record
        """
        if not self.session:
            return
        self.session.add_action(action)

    def save(self) -> Optional[str]:
        """
        Save session to file.

        Returns:
            Filepath if saved, None if no session/actions to save
        """
        if not self.session or not self.session.actions:
            return None

        self.session.meta.session_end = datetime.utcnow()

        # Create directory
        date_str = self.session_start.strftime("%Y-%m-%d")
        sessions_dir = self.base_path / date_str / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self.session_start.strftime("%Y%m%dT%H%M%S")
        username = self.session.meta.username or "anonymous"
        filename = f"{time_str}_{username}_session.json"
        filepath = sessions_dir / filename

        # Write file
        with open(filepath, 'w') as f:
            json.dump(self.session.to_dict(), f, indent=2, cls=DecimalEncoder)

        logger.info(f"Saved session: {filepath}")

        # Update index
        self._update_index(date_str, filename)

        return str(filepath)

    def _update_index(self, date_str: str, filename: str):
        """
        Update daily index file.

        Args:
            date_str: Date string (YYYY-MM-DD)
            filename: Name of the session file
        """
        index_path = self.base_path / date_str / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {"date": date_str, "games": [], "sessions": []}

        index["sessions"].append({
            "file": filename,
            "player_id": self.session.meta.player_id,
            "username": self.session.meta.username,
            "games_played": len(self.session.get_games_played()),
            "total_actions": len(self.session.actions)
        })

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
