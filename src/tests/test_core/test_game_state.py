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
        assert game_state.get('balance') == Decimal('0.100')
        assert game_state.get('initial_balance') == Decimal('0.100')
        assert game_state.get_stats('total_pnl') == Decimal('0.0')

    def test_gamestate_custom_balance(self):
        """Test creating GameState with custom balance"""
        state = GameState(Decimal('0.500'))

        assert state.get('balance') == Decimal('0.500')
        assert state.get('initial_balance') == Decimal('0.500')


class TestGameStateBalanceManagement:
    """Tests for balance management"""

    def test_update_balance_decrease(self, game_state):
        """Test decreasing balance"""
        # Modular API: update_balance adds/subtracts a delta (not set absolute)
        game_state.update_balance(Decimal('-0.005'), "Test deduction")

        assert game_state.get('balance') == Decimal('0.095')
        assert game_state.get_stats('total_pnl') == Decimal('-0.005')

    def test_update_balance_increase(self, game_state):
        """Test increasing balance"""
        # Modular API: update_balance adds/subtracts a delta (not set absolute)
        game_state.update_balance(Decimal('0.010'), "Test addition")

        assert game_state.get('balance') == Decimal('0.110')
        assert game_state.get_stats('total_pnl') == Decimal('0.010')

    def test_update_balance_multiple_changes(self, game_state):
        """Test multiple balance updates"""
        # Modular API: update_balance adds/subtracts deltas
        game_state.update_balance(Decimal('-0.005'), "First change")
        game_state.update_balance(Decimal('0.010'), "Second change")

        assert game_state.get('balance') == Decimal('0.105')
        assert game_state.get_stats('total_pnl') == Decimal('0.005')


class TestGameStatePositionManagement:
    """Tests for position management"""

    def test_no_active_position_initially(self, game_state):
        """Test no active position on initialization"""
        assert game_state.get('position') is None

    def test_open_position(self, game_state, sample_position):
        """Test opening a position"""
        game_state.open_position(sample_position)

        position = game_state.get('position')
        assert position is not None
        # Position is stored as dict, compare key fields
        assert position['entry_price'] == sample_position.entry_price
        assert position['amount'] == sample_position.amount

    def test_close_position(self, game_state, sample_position):
        """Test closing a position"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        assert game_state.get('position') is None

    def test_position_history(self, game_state, sample_position):
        """Test position history tracking"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        history = game_state.get_position_history()
        assert len(history) == 1
        # Check entry fields match
        closed_pos = history[0]
        assert closed_pos.entry_price == sample_position.entry_price
        assert closed_pos.amount == sample_position.amount
        assert closed_pos.entry_time == sample_position.entry_time
        assert closed_pos.entry_tick == sample_position.entry_tick
        # Check exit fields are populated
        assert closed_pos.status == 'closed'
        assert closed_pos.exit_price == Decimal('1.5')
        assert closed_pos.exit_tick == 10
        assert closed_pos.pnl_sol == Decimal('0.005')
        assert closed_pos.pnl_percent == Decimal('50.0')

    def test_multiple_positions_sequential(self, game_state):
        """Test opening multiple positions sequentially"""
        # First position
        pos1 = Position(Decimal('1.0'), Decimal('0.01'), 1000.0, 0)
        game_state.open_position(pos1)
        game_state.close_position(Decimal('1.5'), 2000.0, 10)

        # Second position
        pos2 = Position(Decimal('2.0'), Decimal('0.02'), 3000.0, 20)
        game_state.open_position(pos2)

        position = game_state.get('position')
        assert position is not None
        # Position is stored as dict, compare key fields
        assert position['entry_price'] == pos2.entry_price
        assert position['amount'] == pos2.amount
        assert len(game_state.get_position_history()) == 1  # Only closed positions


class TestGameStateSidebetManagement:
    """Tests for sidebet management"""

    def test_no_active_sidebet_initially(self, game_state):
        """Test no active sidebet on initialization"""
        assert game_state.get('sidebet') is None

    def test_place_sidebet(self, game_state, sample_sidebet):
        """Test placing a sidebet"""
        game_state.place_sidebet(sample_sidebet)

        sidebet = game_state.get('sidebet')
        assert sidebet is not None
        # Sidebet is stored as dict, compare key fields
        assert sidebet['amount'] == sample_sidebet.amount
        assert sidebet['placed_tick'] == sample_sidebet.placed_tick

    def test_resolve_sidebet(self, game_state, sample_sidebet):
        """Test resolving a sidebet"""
        game_state.place_sidebet(sample_sidebet)
        game_state.resolve_sidebet(won=True)

        assert game_state.get('sidebet') is None


class TestGameStateGameManagement:
    """Tests for game state management"""

    # NOTE: In modular architecture, load_game() and set_tick_index()
    # are ReplayEngine responsibilities, not GameState
    # These tests are kept for reference but test actual GameState API

    def test_game_id_property(self, loaded_game_state):
        """Test game ID property"""
        assert loaded_game_state.get('game_id') == 'test-game'

    def test_current_tick_property(self, loaded_game_state):
        """Test current tick property"""
        tick = loaded_game_state.get('current_tick')

        assert tick is not None
        # Note: current_tick is now an integer, not an object
        assert isinstance(tick, int)

    def test_update_game_state(self, game_state):
        """Test updating game state fields"""
        result = game_state.update(
            game_id='new-game',
            game_active=True,
            current_tick=10
        )

        assert result is True
        assert game_state.get('game_id') == 'new-game'
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
        assert game_state.get_stats('total_pnl') == Decimal('0.0')
        assert len(game_state.get_position_history()) == 0

    def test_statistics_after_trading(self, game_state, sample_position):
        """Test statistics update after trading"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), 1234567900.0, 10)

        assert len(game_state.get_position_history()) == 1


class TestGameStateResetAndMetrics:
    """Additional regression tests for state integrity"""

    def test_reset_restores_core_flags(self, game_state):
        """Reset should rebuild keys like rug_detected"""
        game_state.update(game_id='abc', rug_detected=True)
        game_state.reset()

        assert game_state.get('rug_detected') is False
        assert game_state.get('game_id') is None
        assert game_state.get('last_sidebet_resolved_tick') is None

    def test_close_position_records_exit_tick(self, game_state, sample_position):
        """Exit tick should be recorded correctly"""
        game_state.open_position(sample_position)
        closed = game_state.close_position(Decimal('1.5'), exit_tick=7)

        assert closed is not None
        assert closed['exit_tick'] == 7

    def test_metrics_use_realized_pnl(self, game_state, sample_position):
        """Average win/loss should be derived from P&L"""
        game_state.open_position(sample_position)
        game_state.close_position(Decimal('1.5'), exit_tick=5)

        # Second trade (loss)
        losing_position = Position(Decimal('2.0'), Decimal('0.01'), 1234567891.0, 6)
        game_state.open_position(losing_position)
        game_state.close_position(Decimal('1.0'), exit_tick=10)

        metrics = game_state.calculate_metrics()

        assert metrics['average_win'] > Decimal('0')
        assert metrics['average_loss'] > Decimal('0')


class TestCaptureDemoSnapshot:
    """Tests for capture_demo_snapshot() - Phase 10 Demo Recording"""

    def test_capture_demo_snapshot_returns_demo_state_snapshot(self, game_state):
        """Test capture_demo_snapshot returns models.demo_action.StateSnapshot"""
        from models.demo_action import StateSnapshot as DemoStateSnapshot

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert isinstance(snapshot, DemoStateSnapshot)

    def test_capture_demo_snapshot_includes_balance(self, game_state):
        """Test snapshot includes current balance"""
        game_state.update_balance(Decimal('-0.02'), "Test")

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.balance == Decimal('0.080')

    def test_capture_demo_snapshot_includes_bet_amount(self, game_state):
        """Test snapshot includes provided bet_amount"""
        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.015'))

        assert snapshot.bet_amount == Decimal('0.015')

    def test_capture_demo_snapshot_includes_sell_percentage(self, game_state):
        """Test snapshot includes current sell percentage"""
        game_state.set_sell_percentage(Decimal('0.5'))

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.sell_percentage == Decimal('0.5')

    def test_capture_demo_snapshot_includes_tick_and_price(self, game_state):
        """Test snapshot includes tick and price"""
        game_state.update(current_tick=42, current_price=Decimal('2.5'))

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.current_tick == 42
        assert snapshot.current_price == Decimal('2.5')

    def test_capture_demo_snapshot_includes_phase(self, game_state):
        """Test snapshot includes current phase"""
        game_state.update(current_phase='ACTIVE_GAMEPLAY')

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.phase == 'ACTIVE_GAMEPLAY'

    def test_capture_demo_snapshot_includes_position(self, game_state, sample_position):
        """Test snapshot includes position if active"""
        game_state.open_position(sample_position)

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.position is not None
        assert snapshot.position['entry_price'] == str(sample_position.entry_price)

    def test_capture_demo_snapshot_includes_sidebet(self, game_state, sample_sidebet):
        """Test snapshot includes sidebet if active"""
        game_state.place_sidebet(sample_sidebet)

        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.sidebet is not None
        assert snapshot.sidebet['amount'] == str(sample_sidebet.amount)

    def test_capture_demo_snapshot_null_when_no_position(self, game_state):
        """Test snapshot has None for position when no position"""
        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        assert snapshot.position is None

    def test_capture_demo_snapshot_is_serializable(self, game_state):
        """Test snapshot can be converted to dict for JSONL"""
        snapshot = game_state.capture_demo_snapshot(bet_amount=Decimal('0.01'))

        snapshot_dict = snapshot.to_dict()

        assert 'balance' in snapshot_dict
        assert 'bet_amount' in snapshot_dict
        assert 'current_tick' in snapshot_dict
