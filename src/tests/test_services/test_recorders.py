"""
Tests for recorders.py - Phase 10.4F

TDD: Tests written FIRST before implementation.

Tests cover:
- GameStateRecorder: game state recording and file saving
- PlayerSessionRecorder: player action recording and file saving
"""

import pytest
import json
import tempfile
import shutil
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# This import will FAIL until we create the module (TDD RED phase)
from services.recorders import GameStateRecorder, PlayerSessionRecorder
from models.recording_models import PlayerAction


class TestGameStateRecorder:
    """Tests for GameStateRecorder"""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for test files"""
        tmp = tempfile.mkdtemp()
        yield tmp
        shutil.rmtree(tmp)

    def test_initialization(self, temp_dir):
        """Test default initialization"""
        recorder = GameStateRecorder(base_path=temp_dir)
        assert recorder.base_path == Path(temp_dir)
        assert recorder.current_game is None
        assert recorder.game_start_time is None

    def test_start_game(self, temp_dir):
        """Test starting game recording"""
        recorder = GameStateRecorder(base_path=temp_dir)

        recorder.start_game("game-123")

        assert recorder.current_game is not None
        assert recorder.current_game.meta.game_id == "game-123"
        assert recorder.game_start_time is not None

    def test_record_prices(self, temp_dir):
        """Test recording price data"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-123")

        prices = [Decimal("1.0"), Decimal("1.5"), Decimal("2.0")]
        recorder.record_prices(
            prices=prices,
            peak=Decimal("2.5"),
            seed_data={'server_seed': 'abc', 'server_seed_hash': 'hash123'}
        )

        assert recorder.current_game.prices == prices
        assert recorder.current_game.meta.peak_multiplier == Decimal("2.5")
        assert recorder.current_game.meta.duration_ticks == 3
        assert recorder.current_game.meta.server_seed == 'abc'
        assert recorder.current_game.meta.server_seed_hash == 'hash123'

    def test_save_creates_file(self, temp_dir):
        """Test save creates game file"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-123")
        recorder.record_prices(
            prices=[Decimal("1.0"), Decimal("1.5")],
            peak=Decimal("1.5")
        )

        filepath = recorder.save()

        assert filepath is not None
        assert Path(filepath).exists()
        assert "game.json" in filepath

    def test_save_without_game_returns_none(self, temp_dir):
        """Test save with no game returns None"""
        recorder = GameStateRecorder(base_path=temp_dir)

        result = recorder.save()

        assert result is None

    def test_save_file_content(self, temp_dir):
        """Test saved file has correct content"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-test-abc")
        recorder.record_prices(
            prices=[Decimal("1.0"), Decimal("2.0")],
            peak=Decimal("2.0")
        )

        filepath = recorder.save()

        with open(filepath, 'r') as f:
            data = json.load(f)

        assert data['meta']['game_id'] == "game-test-abc"
        assert data['meta']['duration_ticks'] == 2
        assert len(data['prices']) == 2

    def test_save_clears_current_game(self, temp_dir):
        """Test save clears current game"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-123")
        recorder.record_prices([Decimal("1.0")], Decimal("1.0"))

        recorder.save()

        assert recorder.current_game is None

    def test_creates_directory_structure(self, temp_dir):
        """Test creates date/games directory structure"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-123")
        recorder.record_prices([Decimal("1.0")], Decimal("1.0"))

        recorder.save()

        # Should have date/games directory
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        games_dir = Path(temp_dir) / date_str / "games"
        assert games_dir.exists()

    def test_updates_index(self, temp_dir):
        """Test save updates index.json"""
        recorder = GameStateRecorder(base_path=temp_dir)
        recorder.start_game("game-123")
        recorder.record_prices([Decimal("1.0")], Decimal("1.0"))

        recorder.save()

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        index_path = Path(temp_dir) / date_str / "index.json"
        assert index_path.exists()

        with open(index_path, 'r') as f:
            index = json.load(f)

        assert len(index['games']) == 1
        assert index['games'][0]['game_id'] == "game-123"

    def test_multiple_games_update_index(self, temp_dir):
        """Test multiple games are added to index"""
        recorder = GameStateRecorder(base_path=temp_dir)

        # Record first game
        recorder.start_game("game-1")
        recorder.record_prices([Decimal("1.0")], Decimal("1.0"))
        recorder.save()

        # Record second game
        recorder.start_game("game-2")
        recorder.record_prices([Decimal("1.5")], Decimal("1.5"))
        recorder.save()

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        index_path = Path(temp_dir) / date_str / "index.json"

        with open(index_path, 'r') as f:
            index = json.load(f)

        assert len(index['games']) == 2


class TestPlayerSessionRecorder:
    """Tests for PlayerSessionRecorder"""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for test files"""
        tmp = tempfile.mkdtemp()
        yield tmp
        shutil.rmtree(tmp)

    def test_initialization(self, temp_dir):
        """Test default initialization"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        assert recorder.base_path == Path(temp_dir)
        assert recorder.session is None
        assert recorder.session_start is None

    def test_start_session(self, temp_dir):
        """Test starting session"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)

        recorder.start_session("player-123", "testuser")

        assert recorder.session is not None
        assert recorder.session.meta.player_id == "player-123"
        assert recorder.session.meta.username == "testuser"

    def test_record_action(self, temp_dir):
        """Test recording action"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)

        assert len(recorder.session.actions) == 1
        assert recorder.session.actions[0].action == "BUY"

    def test_record_action_without_session(self, temp_dir):
        """Test recording action without session does nothing"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)

        # Should not raise, just do nothing
        assert recorder.session is None

    def test_save_creates_file(self, temp_dir):
        """Test save creates session file"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)

        filepath = recorder.save()

        assert filepath is not None
        assert Path(filepath).exists()
        assert "_session.json" in filepath

    def test_save_without_actions_returns_none(self, temp_dir):
        """Test save with no actions returns None"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        result = recorder.save()

        assert result is None

    def test_save_without_session_returns_none(self, temp_dir):
        """Test save without session returns None"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)

        result = recorder.save()

        assert result is None

    def test_save_file_content(self, temp_dir):
        """Test saved file has correct content"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="SELL",
            amount=Decimal("0.001"),
            price=Decimal("2.0"),
            balance_after=Decimal("1.001"),
            position_qty_after=Decimal("0"),
            pnl=Decimal("0.0005")
        )
        recorder.record_action(action)

        filepath = recorder.save()

        with open(filepath, 'r') as f:
            data = json.load(f)

        assert data['meta']['player_id'] == "player-123"
        assert data['meta']['username'] == "testuser"
        assert len(data['actions']) == 1
        assert data['actions'][0]['action'] == "SELL"

    def test_creates_directory_structure(self, temp_dir):
        """Test creates date/sessions directory structure"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)
        recorder.save()

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        sessions_dir = Path(temp_dir) / date_str / "sessions"
        assert sessions_dir.exists()

    def test_updates_index(self, temp_dir):
        """Test save updates index.json"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)
        recorder.save()

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        index_path = Path(temp_dir) / date_str / "index.json"
        assert index_path.exists()

        with open(index_path, 'r') as f:
            index = json.load(f)

        assert len(index['sessions']) == 1
        assert index['sessions'][0]['username'] == "testuser"
        assert index['sessions'][0]['total_actions'] == 1

    def test_multiple_actions_recorded(self, temp_dir):
        """Test multiple actions are recorded"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        # Record multiple actions
        for i in range(5):
            action = PlayerAction(
                game_id="game-1",
                tick=50 + i,
                timestamp=datetime.utcnow(),
                action="BUY" if i % 2 == 0 else "SELL",
                amount=Decimal("0.001"),
                price=Decimal(f"1.{i}"),
                balance_after=Decimal("1.0"),
                position_qty_after=Decimal("0.001")
            )
            recorder.record_action(action)

        assert len(recorder.session.actions) == 5

    def test_session_end_time_set_on_save(self, temp_dir):
        """Test session_end is set when saving"""
        recorder = PlayerSessionRecorder(base_path=temp_dir)
        recorder.start_session("player-123", "testuser")

        action = PlayerAction(
            game_id="game-1",
            tick=50,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        recorder.record_action(action)

        assert recorder.session.meta.session_end is None

        recorder.save()

        # After save, session is cleared, so we check the saved file
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        sessions_dir = Path(temp_dir) / date_str / "sessions"
        files = list(sessions_dir.glob("*.json"))
        assert len(files) == 1

        with open(files[0], 'r') as f:
            data = json.load(f)

        assert data['meta']['session_end'] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
