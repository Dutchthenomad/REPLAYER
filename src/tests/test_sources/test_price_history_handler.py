"""
Tests for price_history_handler.py - Phase 10.4D

TDD: Tests written FIRST before implementation.

Tests cover:
- PriceHistoryHandler: tick processing, gap filling, game completion
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

# This import will FAIL until we create the module (TDD RED phase)
from sources.price_history_handler import PriceHistoryHandler


class TestPriceHistoryHandler:
    """Tests for PriceHistoryHandler"""

    def test_initialization(self):
        """Test default initialization"""
        handler = PriceHistoryHandler()
        assert handler.current_game_id is None
        assert handler.prices == []
        assert handler.peak_multiplier == Decimal("1.0")

    def test_handle_tick_starts_game(self):
        """Test handling first tick starts new game"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))

        assert handler.current_game_id == "game-123"
        assert len(handler.prices) == 1
        assert handler.prices[0] == Decimal("1.0")

    def test_handle_tick_sequential(self):
        """Test handling sequential ticks"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 1, Decimal("1.01"))
        handler.handle_tick("game-123", 2, Decimal("1.03"))

        assert len(handler.prices) == 3
        assert handler.prices[0] == Decimal("1.0")
        assert handler.prices[1] == Decimal("1.01")
        assert handler.prices[2] == Decimal("1.03")

    def test_handle_tick_tracks_peak(self):
        """Test peak multiplier tracking"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 1, Decimal("2.5"))
        handler.handle_tick("game-123", 2, Decimal("1.8"))

        assert handler.peak_multiplier == Decimal("2.5")

    def test_handle_tick_skipped_creates_gap(self):
        """Test skipped ticks create gaps (None)"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 3, Decimal("1.5"))  # Skip 1, 2

        assert len(handler.prices) == 4
        assert handler.prices[0] == Decimal("1.0")
        assert handler.prices[1] is None
        assert handler.prices[2] is None
        assert handler.prices[3] == Decimal("1.5")

    def test_handle_partial_prices_fills_gaps(self):
        """Test partialPrices fills gaps"""
        handler = PriceHistoryHandler()

        # Create prices with gaps
        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 3, Decimal("1.5"))

        # Fill gaps
        handler.handle_partial_prices({
            'values': {'1': 1.1, '2': 1.3}
        })

        assert handler.prices[1] == Decimal("1.1")
        assert handler.prices[2] == Decimal("1.3")

    def test_handle_partial_prices_no_overwrite(self):
        """Test partialPrices doesn't overwrite existing values"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 1, Decimal("1.1"))

        # Try to overwrite
        handler.handle_partial_prices({
            'values': {'1': 9.9}  # Different value
        })

        # Should keep original value
        assert handler.prices[1] == Decimal("1.1")

    def test_handle_game_end_emits_event(self):
        """Test game end emits game_prices_complete event"""
        handler = PriceHistoryHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('game_prices_complete', callback)

        # Start game
        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 1, Decimal("2.0"))

        # End game
        handler.handle_game_end("game-123", [])

        assert len(received) == 1
        assert received[0]['game_id'] == "game-123"
        assert len(received[0]['prices']) == 2
        assert received[0]['peak_multiplier'] == Decimal("2.0")

    def test_handle_game_end_with_seed_data(self):
        """Test game end extracts seed data from history"""
        handler = PriceHistoryHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('game_prices_complete', callback)

        handler.handle_tick("game-123", 0, Decimal("1.0"))

        # End with game history containing seed
        handler.handle_game_end("game-123", [{
            'id': 'game-123',
            'peakMultiplier': 5.0,
            'provablyFair': {
                'serverSeed': 'abc123',
                'serverSeedHash': 'hash456'
            }
        }])

        assert received[0]['seed_data']['server_seed'] == 'abc123'
        assert received[0]['seed_data']['server_seed_hash'] == 'hash456'

    def test_new_game_finalizes_previous(self):
        """Test starting new game finalizes previous one"""
        handler = PriceHistoryHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('game_prices_complete', callback)

        # Start game 1
        handler.handle_tick("game-1", 0, Decimal("1.0"))
        handler.handle_tick("game-1", 1, Decimal("1.5"))

        # Start game 2 (should finalize game 1)
        handler.handle_tick("game-2", 0, Decimal("1.0"))

        assert len(received) == 1
        assert received[0]['game_id'] == "game-1"

    def test_has_gaps(self):
        """Test gap detection"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))
        handler.handle_tick("game-123", 1, Decimal("1.1"))
        assert handler.has_gaps() is False

        handler.handle_tick("game-123", 3, Decimal("1.3"))
        assert handler.has_gaps() is True

    def test_get_prices_returns_copy(self):
        """Test get_prices returns a copy"""
        handler = PriceHistoryHandler()

        handler.handle_tick("game-123", 0, Decimal("1.0"))

        prices = handler.get_prices()
        prices[0] = Decimal("9.9")

        # Original should be unchanged
        assert handler.prices[0] == Decimal("1.0")

    def test_event_handler_registration(self):
        """Test event handler can be registered"""
        handler = PriceHistoryHandler()
        callback = MagicMock()

        handler.on('game_prices_complete', callback)

        assert 'game_prices_complete' in handler._event_handlers

    def test_game_end_wrong_game_ignored(self):
        """Test game end for wrong game is ignored"""
        handler = PriceHistoryHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('game_prices_complete', callback)

        handler.handle_tick("game-1", 0, Decimal("1.0"))

        # Try to end different game
        handler.handle_game_end("game-2", [])

        # Should not emit
        assert len(received) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
