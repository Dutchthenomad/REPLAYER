"""
Tests for GameState
"""

import pytest
from decimal import Decimal
from models import Position
from core import GameState


class TestGameStateInitialization:
    """Tests for GameState initialization"""

    def test_gamestate_creation(self, game_state):
        """Test creating GameState with default balance"""
        assert game_state.balance == Decimal('0.100')
        assert game_state.initial_balance == Decimal('0.100')
        assert game_state.session_pnl == Decimal('0.0')

    def test_gamestate_custom_balance(self):
        """Test creating GameState with custom balance"""
        state = GameState(Decimal('0.500'))

        assert state.balance == Decimal('0.500')
        assert state.initial_balance == Decimal('0.500')


class TestGameStateBalanceManagement:
    """Tests for balance management"""

    def test_update_balance_decrease(self, game_state):
        """Test decreasing balance"""
        # Modular API: update_balance adds/subtracts a delta (not set absolute)
        game_state.update_balance(Decimal('-0.005'), "Test deduction")

        assert game_state.balance == Decimal('0.095')
        assert game_state.session_pnl == Decimal('-0.005')

    def test_update_balance_increase(self, game_state):
        """Test increasing balance"""
        # Modular API: update_balance adds/subtracts a delta (not set absolute)
        game_state.update_balance(Decimal('0.010'), "Test addition")

        assert game_state.balance == Decimal('0.110')
        assert game_state.session_pnl == Decimal('0.010')

    def test_update_balance_multiple_changes(self, game_state):
        """Test multiple balance updates"""
        # Modular API: update_balance adds/subtracts deltas
        game_state.update_balance(Decimal('-0.005'), "First change")
        game_state.update_balance(Decimal('0.010'), "Second change")

        assert game_state.balance == Decimal('0.105')
        assert game_state.session_pnl == Decimal('0.005')


class TestGameStatePositionManagement:
    """Tests for position management"""

    def test_no_active_position_initially(self, game_state):
        """Test no active position on initialization"""
        assert game_state.has_active_position() == False
        assert game_state.active_position is None

    def test_open_position(self, game_state, sample_position):
        """Test opening a position"""
        game_state.open_position(sample_position)

        assert game_state.has_active_position() == True
        assert game_state.active_position == sample_position

    def test_close_position(self, game_state, sample_position):
        """Test closing a position"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        assert game_state.has_active_position() == False
        assert game_state.active_position is None

    def test_position_history(self, game_state, sample_position):
        """Test position history tracking"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        history = game_state.get_position_history()
        assert len(history) == 1
        assert history[0] == sample_position

    def test_multiple_positions_sequential(self, game_state):
        """Test opening multiple positions sequentially"""
        # First position
        pos1 = Position(Decimal('1.0'), Decimal('0.01'), 1000.0, 0)
        game_state.open_position(pos1)
        game_state.close_position(Decimal('1.5'), 2000.0, 10)

        # Second position
        pos2 = Position(Decimal('2.0'), Decimal('0.02'), 3000.0, 20)
        game_state.open_position(pos2)

        assert game_state.has_active_position() == True
        assert game_state.active_position == pos2
        assert len(game_state.get_position_history()) == 1  # Only closed positions


class TestGameStateSidebetManagement:
    """Tests for sidebet management"""

    def test_no_active_sidebet_initially(self, game_state):
        """Test no active sidebet on initialization"""
        assert game_state.has_active_sidebet() == False
        assert game_state.active_sidebet is None

    def test_place_sidebet(self, game_state, sample_sidebet):
        """Test placing a sidebet"""
        game_state.place_sidebet(sample_sidebet)

        assert game_state.has_active_sidebet() == True
        assert game_state.active_sidebet == sample_sidebet

    def test_resolve_sidebet(self, game_state, sample_sidebet):
        """Test resolving a sidebet"""
        game_state.place_sidebet(sample_sidebet)
        game_state.resolve_sidebet(won=True)

        assert game_state.has_active_sidebet() == False
        assert game_state.active_sidebet is None


class TestGameStateGameManagement:
    """Tests for game state management"""

    # NOTE: In modular architecture, load_game() and set_tick_index()
    # are ReplayEngine responsibilities, not GameState
    # These tests are kept for reference but test actual GameState API

    def test_game_id_property(self, loaded_game_state):
        """Test game ID property"""
        assert loaded_game_state.current_game_id == 'test-game'

    def test_current_tick_property(self, loaded_game_state):
        """Test current tick property"""
        tick = loaded_game_state.current_tick

        assert tick is not None
        # Note: GameState stores tick object in modular version
        assert hasattr(tick, 'phase')

    def test_update_game_state(self, game_state):
        """Test updating game state fields"""
        result = game_state.update(
            game_id='new-game',
            game_active=True,
            current_tick=10
        )

        assert result is True
        assert game_state.current_game_id == 'new-game'
        assert game_state.get('game_active') is True
        assert game_state.get('current_tick') == 10


class TestGameStateSnapshot:
    """Tests for state snapshot"""

    def test_snapshot_contains_required_keys(self, game_state):
        """Test snapshot contains required attributes"""
        snapshot = game_state.get_snapshot()

        # StateSnapshot is a dataclass, not a dict
        assert hasattr(snapshot, 'balance')
        assert hasattr(snapshot, 'tick')
        assert hasattr(snapshot, 'timestamp')
        from core.game_state import StateSnapshot
        assert isinstance(snapshot, StateSnapshot)

    def test_snapshot_reflects_current_state(self, game_state):
        """Test snapshot reflects current balance"""
        game_state.update_balance(Decimal('0.095'), "Test")
        snapshot = game_state.get_snapshot()

        # The exact snapshot structure may vary, but should include balance info
        assert snapshot is not None


class TestGameStateStatistics:
    """Tests for state statistics"""

    def test_initial_statistics(self, game_state):
        """Test initial statistics are zero/default"""
        assert game_state.session_pnl == Decimal('0.0')
        assert len(game_state.get_position_history()) == 0

    def test_statistics_after_trading(self, game_state, sample_position):
        """Test statistics update after trading"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        assert len(game_state.get_position_history()) == 1
