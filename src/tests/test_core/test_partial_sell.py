"""
Tests for Phase 8.1: Partial Sell Infrastructure

Tests cover:
- Sell percentage state management in GameState
- Position.reduce_amount() method
- GameState.partial_close_position() method
- GameState.set_sell_percentage() validation
- TradeManager.execute_sell() with partial sell support
- Event emission for SELL_PERCENTAGE_CHANGED and POSITION_REDUCED
"""

import pytest
import time
from decimal import Decimal
from models import Position
from core import GameState, TradeManager
from core.game_state import StateEvents
from services import Events, event_bus


class TestSellPercentageState:
    """Tests for sell_percentage state management"""

    def test_initial_sell_percentage_is_100(self, game_state):
        """Test sell_percentage defaults to 100% (1.0)"""
        assert game_state.get_sell_percentage() == Decimal('1.0')

    def test_set_sell_percentage_valid(self, game_state):
        """Test setting sell_percentage to valid values"""
        valid_percentages = [Decimal('0.1'), Decimal('0.25'), Decimal('0.5'), Decimal('1.0')]

        for percentage in valid_percentages:
            result = game_state.set_sell_percentage(percentage)
            assert result == True
            assert game_state.get_sell_percentage() == percentage

    def test_set_sell_percentage_invalid(self, game_state):
        """Test setting sell_percentage to invalid values"""
        invalid_percentages = [Decimal('0.05'), Decimal('0.33'), Decimal('0.75'), Decimal('2.0')]

        for percentage in invalid_percentages:
            result = game_state.set_sell_percentage(percentage)
            assert result == False
            # Percentage should remain unchanged
            assert game_state.get_sell_percentage() == Decimal('1.0')

    def test_set_sell_percentage_emits_event(self, game_state):
        """Test that set_sell_percentage emits SELL_PERCENTAGE_CHANGED event"""
        event_received = []

        def handler(data):
            event_received.append(data)

        game_state.subscribe(StateEvents.SELL_PERCENTAGE_CHANGED, handler)
        game_state.set_sell_percentage(Decimal('0.5'))

        assert len(event_received) == 1
        assert event_received[0]['old'] == Decimal('1.0')
        assert event_received[0]['new'] == Decimal('0.5')


class TestPositionReduceAmount:
    """Tests for Position.reduce_amount() method"""

    def test_reduce_amount_10_percent(self):
        """Test reducing position by 10%"""
        position = Position(
            entry_price=Decimal('1.5'),
            amount=Decimal('0.010'),
            entry_time=123456789.0,
            entry_tick=10
        )

        reduced = position.reduce_amount(Decimal('0.1'))

        assert reduced == Decimal('0.001')
        assert position.amount == Decimal('0.009')

    def test_reduce_amount_25_percent(self):
        """Test reducing position by 25%"""
        position = Position(
            entry_price=Decimal('2.0'),
            amount=Decimal('0.020'),
            entry_time=123456789.0,
            entry_tick=10
        )

        reduced = position.reduce_amount(Decimal('0.25'))

        assert reduced == Decimal('0.005')
        assert position.amount == Decimal('0.015')

    def test_reduce_amount_50_percent(self):
        """Test reducing position by 50%"""
        position = Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.100'),
            entry_time=123456789.0,
            entry_tick=10
        )

        reduced = position.reduce_amount(Decimal('0.5'))

        assert reduced == Decimal('0.050')
        assert position.amount == Decimal('0.050')

    def test_reduce_amount_invalid_percentage(self):
        """Test reducing position with invalid percentage raises ValueError"""
        position = Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.010'),
            entry_time=123456789.0,
            entry_tick=10
        )

        with pytest.raises(ValueError, match="Invalid percentage"):
            position.reduce_amount(Decimal('0.33'))

    def test_reduce_amount_100_percent_raises_error(self):
        """Test reducing position by 100% raises ValueError (should use close() instead)"""
        position = Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.010'),
            entry_time=123456789.0,
            entry_tick=10
        )

        with pytest.raises(ValueError, match="Cannot reduce by 100%"):
            position.reduce_amount(Decimal('1.0'))

    def test_reduce_amount_closed_position_raises_error(self):
        """Test reducing closed position raises ValueError"""
        position = Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.010'),
            entry_time=123456789.0,
            entry_tick=10
        )
        position.close(Decimal('1.5'), 123456800.0, 20)

        with pytest.raises(ValueError, match="Cannot reduce closed position"):
            position.reduce_amount(Decimal('0.5'))


class TestPartialClosePosition:
    """Tests for GameState.partial_close_position() method"""

    def test_partial_close_10_percent(self, game_state, sample_position):
        """Test partially closing 10% of position"""
        # Open position
        game_state.open_position(sample_position)
        initial_balance = game_state.get('balance')

        # Partially close 10% at 2.0x (100% profit)
        result = game_state.partial_close_position(
            percentage=Decimal('0.1'),
            exit_price=Decimal('2.0'),
            exit_tick=20
        )

        assert result is not None
        assert result['percentage'] == Decimal('0.1')
        assert result['amount_sold'] == Decimal('0.001')  # 10% of 0.01
        assert result['remaining_amount'] == Decimal('0.009')
        assert game_state.get('position') is not None
        assert game_state.get('position')['amount'] == Decimal('0.009')

        # Check P&L calculation (10% of position, 100% profit)
        assert result['pnl_sol'] == Decimal('0.001')  # 0.001 SOL profit
        assert result['pnl_percent'] == Decimal('100.0')

    def test_partial_close_50_percent(self, game_state, sample_position):
        """Test partially closing 50% of position"""
        game_state.open_position(sample_position)

        result = game_state.partial_close_position(
            percentage=Decimal('0.5'),
            exit_price=Decimal('1.5'),
            exit_tick=15
        )

        assert result is not None
        assert result['percentage'] == Decimal('0.5')
        assert result['amount_sold'] == Decimal('0.005')  # 50% of 0.01
        assert result['remaining_amount'] == Decimal('0.005')
        assert game_state.get('position')['amount'] == Decimal('0.005')

        # Check P&L (50% of position, 50% profit)
        assert result['pnl_sol'] == Decimal('0.0025')
        assert result['pnl_percent'] == Decimal('50.0')

    def test_partial_close_100_percent_uses_close_position(self, game_state, sample_position):
        """Test that 100% partial close delegates to close_position()"""
        game_state.open_position(sample_position)

        result = game_state.partial_close_position(
            percentage=Decimal('1.0'),
            exit_price=Decimal('2.0'),
            exit_tick=20
        )

        # Should fully close position
        assert result is not None
        assert game_state.get('position') is None

    def test_partial_close_no_active_position_returns_none(self, game_state):
        """Test partial close with no active position returns None"""
        result = game_state.partial_close_position(
            percentage=Decimal('0.5'),
            exit_price=Decimal('1.5'),
            exit_tick=10
        )

        assert result is None

    def test_partial_close_invalid_percentage_returns_none(self, game_state, sample_position):
        """Test partial close with invalid percentage returns None"""
        game_state.open_position(sample_position)

        result = game_state.partial_close_position(
            percentage=Decimal('0.33'),
            exit_price=Decimal('1.5'),
            exit_tick=10
        )

        assert result is None
        # Position should remain unchanged
        assert game_state.get('position')['amount'] == sample_position.amount

    def test_partial_close_updates_balance(self, game_state, sample_position):
        """Test partial close updates balance correctly"""
        game_state.open_position(sample_position)
        balance_before = game_state.get('balance')

        # Partial close 50% at 2.0x (100% profit)
        game_state.partial_close_position(
            percentage=Decimal('0.5'),
            exit_price=Decimal('2.0'),
            exit_tick=10
        )

        # Expected proceeds: 0.005 SOL * 2.0x = 0.01 SOL
        expected_balance = balance_before + Decimal('0.01')
        assert game_state.get('balance') == expected_balance

    def test_partial_close_emits_position_reduced_event(self, game_state, sample_position):
        """Test partial close emits POSITION_REDUCED event"""
        event_received = []

        def handler(data):
            event_received.append(data)

        game_state.subscribe(StateEvents.POSITION_REDUCED, handler)
        game_state.open_position(sample_position)
        game_state.partial_close_position(
            percentage=Decimal('0.25'),
            exit_price=Decimal('1.5'),
            exit_tick=15
        )

        assert len(event_received) == 1
        assert event_received[0]['percentage'] == Decimal('0.25')
        assert event_received[0]['amount_sold'] == Decimal('0.0025')


class TestTradeManagerPartialSell:
    """Tests for TradeManager.execute_sell() with partial sell support"""

    def test_execute_sell_with_100_percent(self, game_state, trade_manager, sample_tick):
        """Test execute_sell with 100% sell percentage (full close)"""
        # Setup
        game_state.open_position(Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.01'),
            entry_time=123456789.0,
            entry_tick=0
        ))

        # Execute sell at 2.0x (100% profit)
        game_state.update(current_tick=10, current_price=Decimal('2.0'), game_active=True)
        sample_tick.price = Decimal('2.0')
        game_state.set_sell_percentage(Decimal('1.0'))

        result = trade_manager.execute_sell()

        assert result['success'] == True
        assert result['partial'] == False
        assert result['amount'] == 0.01  # Float in result dict
        assert game_state.get('position') is None

    def test_execute_sell_with_50_percent(self, game_state, trade_manager, sample_tick):
        """Test execute_sell with 50% sell percentage"""
        # Setup
        game_state.open_position(Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.01'),
            entry_time=123456789.0,
            entry_tick=0
        ))

        # Execute partial sell
        game_state.update(current_tick=10, current_price=Decimal('2.0'), game_active=True)
        sample_tick.price = Decimal('2.0')
        game_state.set_sell_percentage(Decimal('0.5'))

        result = trade_manager.execute_sell()

        assert result['success'] == True
        assert result['partial'] == True
        assert result['percentage'] == Decimal('0.5')
        assert result['amount'] == 0.005  # Float in result dict (50% of 0.01)
        assert result['remaining_amount'] == Decimal('0.005')
        assert game_state.get('position') is not None

    def test_execute_sell_with_25_percent(self, game_state, trade_manager, sample_tick):
        """Test execute_sell with 25% sell percentage"""
        # Setup
        game_state.open_position(Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.020'),
            entry_time=123456789.0,
            entry_tick=0
        ))

        # Execute partial sell
        game_state.update(current_tick=10, current_price=Decimal('1.5'), game_active=True)
        sample_tick.price = Decimal('1.5')
        game_state.set_sell_percentage(Decimal('0.25'))

        result = trade_manager.execute_sell()

        assert result['success'] == True
        assert result['partial'] == True
        assert result['amount'] == 0.005  # Float in result dict (25% of 0.020)
        assert result['remaining_amount'] == Decimal('0.015')

    def test_execute_sell_publishes_event_with_partial_flag(self, game_state, trade_manager, sample_tick):
        """Test execute_sell publishes TRADE_SELL event with partial flag"""
        events_received = []

        def handler(event):
            events_received.append(event['data'])

        event_bus.subscribe(Events.TRADE_SELL, handler, weak=False)

        # Setup partial sell
        game_state.open_position(Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.01'),
            entry_time=123456789.0,
            entry_tick=0
        ))

        game_state.update(current_tick=10, current_price=Decimal('1.5'), game_active=True)
        sample_tick.price = Decimal('1.5')
        game_state.set_sell_percentage(Decimal('0.5'))

        trade_manager.execute_sell()

        # Give event bus time to process (async processing)
        time.sleep(0.1)

        assert len(events_received) == 1
        event_data = events_received[0]
        assert event_data['partial'] == True
        assert event_data['percentage'] == 0.5
        assert event_data['remaining_amount'] == 0.005


class TestPartialSellIntegration:
    """Integration tests for end-to-end partial sell workflow"""

    def test_multiple_partial_sells(self, game_state, trade_manager, sample_tick):
        """Test multiple sequential partial sells"""
        # Setup
        game_state.open_position(Position(
            entry_price=Decimal('1.0'),
            amount=Decimal('0.100'),
            entry_time=123456789.0,
            entry_tick=0
        ))

        # First partial sell: 25%
        game_state.update(current_tick=10, current_price=Decimal('1.5'), game_active=True)
        sample_tick.price = Decimal('1.5')
        game_state.set_sell_percentage(Decimal('0.25'))
        trade_manager.execute_sell()

        assert game_state.get('position')['amount'] == Decimal('0.075')

        # Second partial sell: 50% of remaining
        game_state.update(current_tick=20, current_price=Decimal('2.0'), game_active=True)
        sample_tick.price = Decimal('2.0')
        game_state.set_sell_percentage(Decimal('0.5'))
        trade_manager.execute_sell()

        assert game_state.get('position')['amount'] == Decimal('0.0375')

        # Third partial sell: 100% (close remaining)
        game_state.update(current_tick=30, current_price=Decimal('2.5'), game_active=True)
        sample_tick.price = Decimal('2.5')
        game_state.set_sell_percentage(Decimal('1.0'))
        trade_manager.execute_sell()

        assert game_state.get('position') is None

    def test_sell_percentage_persists_across_sells(self, game_state):
        """Test that sell_percentage persists until explicitly changed"""
        # Set to 50%
        game_state.set_sell_percentage(Decimal('0.5'))
        assert game_state.get_sell_percentage() == Decimal('0.5')

        # Should remain 50% until changed
        assert game_state.get_sell_percentage() == Decimal('0.5')

        # Change to 100%
        game_state.set_sell_percentage(Decimal('1.0'))
        assert game_state.get_sell_percentage() == Decimal('1.0')
