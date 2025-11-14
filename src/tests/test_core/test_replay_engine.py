"""
Tests for ReplayEngine integration with GameState
"""

import json
from decimal import Decimal
from pathlib import Path

from core import ReplayEngine, GameState


def _write_game_file(path: Path, game_id: str = "test-game"):
    ticks = [
        {
            "game_id": game_id,
            "tick": 0,
            "timestamp": "2025-01-01T00:00:00",
            "price": 1.0,
            "phase": "ACTIVE",
            "active": True,
            "rugged": False,
            "cooldown_timer": 0,
            "trade_count": 0
        },
        {
            "game_id": game_id,
            "tick": 1,
            "timestamp": "2025-01-01T00:00:01",
            "price": 1.2,
            "phase": "ACTIVE",
            "active": True,
            "rugged": False,
            "cooldown_timer": 0,
            "trade_count": 1
        }
    ]
    with path.open("w") as fh:
        for tick in ticks:
            fh.write(json.dumps(tick) + "\n")


def test_load_file_resets_state(tmp_path):
    """Loading a file should reset state and set the game_id"""
    game_state = GameState(Decimal("0.100"))
    engine = ReplayEngine(game_state)

    # Simulate an open position that should be cleared
    game_state.open_position({
        'entry_price': Decimal('1.0'),
        'amount': Decimal('0.01'),
        'entry_tick': 0,
        'status': 'active'
    })

    game_file = tmp_path / "game.jsonl"
    _write_game_file(game_file, game_id="game-live")

    assert engine.load_file(game_file) is True
    assert game_state.current_game_id == "game-live"
    assert game_state.has_active_position() is False
