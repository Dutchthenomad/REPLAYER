"""
Tests for recording_models.py - Phase 10.4 Foundation Layer

TDD: Tests written FIRST before implementation.

Tests cover:
- GameStateMeta: Game recording metadata
- GameStateRecord: Complete game state with prices
- PlayerAction: Single player action with state snapshot
- PlayerSessionMeta: Session metadata
- PlayerSession: Complete player session
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Optional

# These imports will FAIL until we create the module (TDD RED phase)
from models.recording_models import (
    GameStateMeta,
    GameStateRecord,
    PlayerAction,
    PlayerSessionMeta,
    PlayerSession
)


class TestGameStateMeta:
    """Tests for GameStateMeta dataclass"""

    def test_creation_minimal(self):
        """Test creation with minimal required fields"""
        meta = GameStateMeta(
            game_id="20251207-abc123",
            start_time=datetime(2025, 12, 7, 14, 30, 22)
        )
        assert meta.game_id == "20251207-abc123"
        assert meta.start_time == datetime(2025, 12, 7, 14, 30, 22)
        assert meta.end_time is None
        assert meta.duration_ticks == 0
        assert meta.peak_multiplier == Decimal("1.0")
        assert meta.server_seed_hash is None
        assert meta.server_seed is None

    def test_creation_full(self):
        """Test creation with all fields"""
        meta = GameStateMeta(
            game_id="20251207-abc123",
            start_time=datetime(2025, 12, 7, 14, 30, 22),
            end_time=datetime(2025, 12, 7, 14, 32, 45),
            duration_ticks=143,
            peak_multiplier=Decimal("45.23"),
            server_seed_hash="abc123hash",
            server_seed="xyz789seed"
        )
        assert meta.duration_ticks == 143
        assert meta.peak_multiplier == Decimal("45.23")
        assert meta.server_seed_hash == "abc123hash"
        assert meta.server_seed == "xyz789seed"


class TestGameStateRecord:
    """Tests for GameStateRecord dataclass"""

    def test_creation(self):
        """Test creation with meta"""
        meta = GameStateMeta(
            game_id="test-123",
            start_time=datetime.utcnow()
        )
        record = GameStateRecord(meta=meta)
        assert record.meta == meta
        assert record.prices == []

    def test_add_price(self):
        """Test adding prices at specific ticks"""
        meta = GameStateMeta(game_id="test", start_time=datetime.utcnow())
        record = GameStateRecord(meta=meta)

        record.add_price(0, Decimal("1.0"))
        record.add_price(1, Decimal("1.01"))
        record.add_price(2, Decimal("1.03"))

        assert len(record.prices) == 3
        assert record.prices[0] == Decimal("1.0")
        assert record.prices[1] == Decimal("1.01")
        assert record.prices[2] == Decimal("1.03")

    def test_add_price_extends_array(self):
        """Test adding price at index beyond current length extends array"""
        meta = GameStateMeta(game_id="test", start_time=datetime.utcnow())
        record = GameStateRecord(meta=meta)

        record.add_price(5, Decimal("1.5"))

        assert len(record.prices) == 6
        assert record.prices[5] == Decimal("1.5")
        # Gaps should be None
        assert record.prices[0] is None
        assert record.prices[4] is None

    def test_fill_gaps(self):
        """Test filling gaps with partial prices"""
        meta = GameStateMeta(game_id="test", start_time=datetime.utcnow())
        record = GameStateRecord(meta=meta)

        # Create array with gaps
        record.add_price(0, Decimal("1.0"))
        record.add_price(3, Decimal("1.1"))  # Gap at 1, 2

        # Fill gaps
        record.fill_gaps({"1": "1.02", "2": "1.05"})

        assert record.prices[1] == Decimal("1.02")
        assert record.prices[2] == Decimal("1.05")

    def test_has_gaps(self):
        """Test gap detection"""
        meta = GameStateMeta(game_id="test", start_time=datetime.utcnow())
        record = GameStateRecord(meta=meta)

        # No gaps initially
        record.add_price(0, Decimal("1.0"))
        record.add_price(1, Decimal("1.01"))
        assert record.has_gaps() is False

        # Create gap
        record.add_price(3, Decimal("1.03"))
        assert record.has_gaps() is True

    def test_to_dict(self):
        """Test JSON serialization"""
        meta = GameStateMeta(
            game_id="20251207-abc123",
            start_time=datetime(2025, 12, 7, 14, 30, 22),
            end_time=datetime(2025, 12, 7, 14, 32, 45),
            duration_ticks=3,
            peak_multiplier=Decimal("2.5")
        )
        record = GameStateRecord(meta=meta)
        record.add_price(0, Decimal("1.0"))
        record.add_price(1, Decimal("1.5"))
        record.add_price(2, Decimal("2.5"))

        result = record.to_dict()

        assert result["meta"]["game_id"] == "20251207-abc123"
        assert result["meta"]["duration_ticks"] == 3
        assert result["meta"]["peak_multiplier"] == "2.5"
        assert result["prices"] == ["1.0", "1.5", "2.5"]


class TestPlayerAction:
    """Tests for PlayerAction dataclass"""

    def test_creation(self):
        """Test creation with all fields"""
        action = PlayerAction(
            game_id="20251207-abc123",
            tick=12,
            timestamp=datetime(2025, 12, 7, 14, 30, 34),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.234"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001"),
            entry_price=Decimal("1.234"),
            pnl=None
        )
        assert action.game_id == "20251207-abc123"
        assert action.tick == 12
        assert action.action == "BUY"
        assert action.amount == Decimal("0.001")
        assert action.entry_price == Decimal("1.234")
        assert action.pnl is None

    def test_to_dict(self):
        """Test JSON serialization"""
        action = PlayerAction(
            game_id="test-123",
            tick=5,
            timestamp=datetime(2025, 12, 7, 14, 30, 0),
            action="SELL",
            amount=Decimal("0.001"),
            price=Decimal("2.0"),
            balance_after=Decimal("1.002"),
            position_qty_after=Decimal("0"),
            entry_price=Decimal("1.5"),
            pnl=Decimal("0.0005")
        )

        result = action.to_dict()

        assert result["game_id"] == "test-123"
        assert result["tick"] == 5
        assert result["action"] == "SELL"
        assert result["amount"] == "0.001"
        assert result["pnl"] == "0.0005"


class TestPlayerSessionMeta:
    """Tests for PlayerSessionMeta dataclass"""

    def test_creation(self):
        """Test creation"""
        meta = PlayerSessionMeta(
            player_id="did:privy:cm3xxx",
            username="Dutch",
            session_start=datetime(2025, 12, 7, 14, 30, 0)
        )
        assert meta.player_id == "did:privy:cm3xxx"
        assert meta.username == "Dutch"
        assert meta.session_end is None


class TestPlayerSession:
    """Tests for PlayerSession dataclass"""

    def test_creation(self):
        """Test creation"""
        meta = PlayerSessionMeta(
            player_id="test-player",
            username="TestUser",
            session_start=datetime.utcnow()
        )
        session = PlayerSession(meta=meta)
        assert session.meta == meta
        assert session.actions == []

    def test_add_action(self):
        """Test adding actions"""
        meta = PlayerSessionMeta(
            player_id="test-player",
            username="TestUser",
            session_start=datetime.utcnow()
        )
        session = PlayerSession(meta=meta)

        action = PlayerAction(
            game_id="game-1",
            tick=5,
            timestamp=datetime.utcnow(),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        session.add_action(action)

        assert len(session.actions) == 1
        assert session.actions[0] == action

    def test_get_games_played(self):
        """Test getting unique game IDs"""
        meta = PlayerSessionMeta(
            player_id="test-player",
            username="TestUser",
            session_start=datetime.utcnow()
        )
        session = PlayerSession(meta=meta)

        # Add actions from multiple games
        for game_id in ["game-1", "game-1", "game-2", "game-3", "game-2"]:
            action = PlayerAction(
                game_id=game_id,
                tick=1,
                timestamp=datetime.utcnow(),
                action="BUY",
                amount=Decimal("0.001"),
                price=Decimal("1.0"),
                balance_after=Decimal("0.999"),
                position_qty_after=Decimal("0.001")
            )
            session.add_action(action)

        games = session.get_games_played()
        assert games == {"game-1", "game-2", "game-3"}

    def test_to_dict(self):
        """Test JSON serialization"""
        meta = PlayerSessionMeta(
            player_id="did:privy:test",
            username="TestUser",
            session_start=datetime(2025, 12, 7, 14, 30, 0),
            session_end=datetime(2025, 12, 7, 15, 45, 0)
        )
        session = PlayerSession(meta=meta)

        action = PlayerAction(
            game_id="game-1",
            tick=5,
            timestamp=datetime(2025, 12, 7, 14, 35, 0),
            action="BUY",
            amount=Decimal("0.001"),
            price=Decimal("1.5"),
            balance_after=Decimal("0.999"),
            position_qty_after=Decimal("0.001")
        )
        session.add_action(action)

        result = session.to_dict()

        assert result["meta"]["player_id"] == "did:privy:test"
        assert result["meta"]["username"] == "TestUser"
        assert result["meta"]["session_end"] == "2025-12-07T15:45:00"
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "BUY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
