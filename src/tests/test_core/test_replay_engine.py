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
    assert game_state.get('game_id') == "game-live"
    assert game_state.get('position') is None


def test_progress_reaches_100_percent_at_final_tick(tmp_path):
    """
    Regression test for Bug 2: Playback progress never reaches 100%

    The bug was that progress used index/len, which tops out at 99.x% when
    index = len-1. This test verifies progress reaches exactly 100.0% at the
    final tick.
    """
    game_state = GameState(Decimal("0.100"))
    engine = ReplayEngine(game_state)

    # Create a game file with exactly 5 ticks
    game_file = tmp_path / "game.jsonl"
    ticks = []
    for i in range(5):
        ticks.append({
            "game_id": "test-game",
            "tick": i,
            "timestamp": f"2025-01-01T00:00:{i:02d}",
            "price": 1.0 + (i * 0.1),
            "phase": "ACTIVE",
            "active": True,
            "rugged": False,
            "cooldown_timer": 0,
            "trade_count": i
        })

    with game_file.open("w") as fh:
        for tick in ticks:
            fh.write(json.dumps(tick) + "\n")

    # Load the file
    assert engine.load_file(game_file) is True
    assert len(engine.ticks) == 5

    # Progress at start (index 0)
    assert engine.current_index == 0
    progress_start = engine.get_progress()
    assert progress_start == 0.2  # (0 + 1) / 5 = 0.2 = 20%

    # Advance to index 3 (4th tick)
    engine.current_index = 3
    progress_mid = engine.get_progress()
    assert progress_mid == 0.8  # (3 + 1) / 5 = 0.8 = 80%

    # Advance to final tick (index 4)
    engine.current_index = 4
    progress_final = engine.get_progress()
    assert progress_final == 1.0, f"Expected progress=1.0 at final tick, got {progress_final}"

    # Verify get_info() also returns 100%
    info = engine.get_info()
    assert info['progress'] == 100.0, f"Expected info progress=100.0, got {info['progress']}"
    assert info['total_ticks'] == 5
    assert info['current_tick'] == 4
