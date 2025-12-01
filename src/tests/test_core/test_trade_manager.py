"""
Tests for TradeManager
"""

import pytest
from decimal import Decimal
from core import TradeManager


class TestTradeManagerInitialization:
    """Tests for TradeManager initialization"""

    def test_trade_manager_creation(self, trade_manager):
        """Test creating TradeManager"""
        assert trade_manager is not None

    def test_trade_manager_with_game_state(self, game_state, trade_manager):
        """Test TradeManager has access to GameState"""
        assert trade_manager.state == game_state


class TestTradeManagerBuyOperation:
    """Tests for buy operations"""

    def test_buy_success(self, loaded_game_state, trade_manager):
        """Test successful buy execution"""
        initial_balance = loaded_game_state.get('balance')
        result = trade_manager.execute_buy(Decimal('0.005'))

        assert result['success'] == True
        assert 'price' in result
        assert 'amount' in result
        assert loaded_game_state.get('balance') == initial_balance - Decimal('0.005')
        assert loaded_game_state.get('position') is not None

    def test_buy_insufficient_balance(self, loaded_game_state, trade_manager):
        """Test buy fails with insufficient balance"""
        result = trade_manager.execute_buy(Decimal('1.0'))  # More than balance

        assert result['success'] == False
        assert 'reason' in result

    def test_buy_below_minimum(self, loaded_game_state, trade_manager):
        """Test buy fails below minimum bet"""
        result = trade_manager.execute_buy(Decimal('0.0001'))

        assert result['success'] == False
        assert 'reason' in result

    def test_buy_above_maximum(self, loaded_game_state, trade_manager):
        """Test buy fails above maximum bet"""
        result = trade_manager.execute_buy(Decimal('10.0'))

        assert result['success'] == False
        assert 'reason' in result

    def test_buy_with_active_position_accumulates(self, loaded_game_state, trade_manager):
        """Test subsequent buys add to active position (DCA)"""
        initial_balance = loaded_game_state.get('balance')

        # First buy succeeds
        result1 = trade_manager.execute_buy(Decimal('0.005'))
        assert result1['success'] is True

        # Second buy also succeeds and adds to position
        result2 = trade_manager.execute_buy(Decimal('0.005'))
        assert result2['success'] is True

        position = loaded_game_state.get('position')
        assert position is not None
        assert position['amount'] == Decimal('0.010')

        # Balance should reflect both buys at price 1.0
        assert loaded_game_state.get('balance') == initial_balance - Decimal('0.010')


class TestTradeManagerSellOperation:
    """Tests for sell operations"""

    def test_sell_success(self, loaded_game_state, trade_manager):
        """Test successful sell execution"""
        # First buy
        trade_manager.execute_buy(Decimal('0.005'))

        # Then sell
        result = trade_manager.execute_sell()

        assert result['success'] == True
        assert 'pnl_sol' in result
        assert 'pnl_percent' in result
        assert loaded_game_state.get('position') is None

    def test_sell_without_position(self, loaded_game_state, trade_manager):
        """Test sell fails without active position"""
        result = trade_manager.execute_sell()

        assert result['success'] == False
        assert 'reason' in result

    def test_sell_pnl_calculation(self, game_state, trade_manager, replay_engine, price_series):
        """Test P&L calculation on sell"""
        # Load game with rising prices
        replay_engine.load_game(price_series, 'test-game')
        replay_engine.set_tick_index(0)  # Price: 1.0

        # Buy at 1.0
        trade_manager.execute_buy(Decimal('0.01'))

        # Move to higher price
        replay_engine.set_tick_index(3)  # Price: 2.0

        # Sell at 2.0
        result = trade_manager.execute_sell()

        assert result['success'] == True
        assert result['pnl_sol'] > Decimal('0')  # Profit
        assert result['pnl_percent'] > Decimal('0')  # Profit


class TestTradeManagerSidebetOperation:
    """Tests for sidebet operations"""

    def test_sidebet_success(self, loaded_game_state, trade_manager):
        """Test successful sidebet placement"""
        initial_balance = loaded_game_state.get('balance')
        result = trade_manager.execute_sidebet(Decimal('0.002'))

        assert result['success'] == True
        assert 'amount' in result
        assert 'potential_win' in result
        assert loaded_game_state.get('balance') == initial_balance - Decimal('0.002')
        assert loaded_game_state.get('sidebet') is not None

    def test_sidebet_insufficient_balance(self, loaded_game_state, trade_manager):
        """Test sidebet fails with insufficient balance"""
        result = trade_manager.execute_sidebet(Decimal('1.0'))

        assert result['success'] == False
        assert 'reason' in result

    def test_sidebet_below_minimum(self, loaded_game_state, trade_manager):
        """Test sidebet fails below minimum bet"""
        result = trade_manager.execute_sidebet(Decimal('0.0001'))

        assert result['success'] == False
        assert 'reason' in result

    def test_sidebet_with_active_sidebet(self, loaded_game_state, trade_manager):
        """Test sidebet fails when sidebet already active"""
        # First sidebet succeeds
        result1 = trade_manager.execute_sidebet(Decimal('0.002'))
        assert result1['success'] == True

        # Second sidebet fails
        result2 = trade_manager.execute_sidebet(Decimal('0.002'))
        assert result2['success'] == False
        assert 'reason' in result2

    def test_sidebet_payout_ratio(self, loaded_game_state, trade_manager):
        """Test sidebet potential payout is correct"""
        result = trade_manager.execute_sidebet(Decimal('0.01'))

        assert result['success'] == True
        # Sidebet pays 5:1
        assert result['potential_win'] == Decimal('0.05')


class TestTradeManagerValidation:
    """Tests for trade validation"""

    def test_trading_not_allowed_when_inactive(self, game_state, trade_manager, replay_engine, sample_tick):
        """Test trading blocked when game not active"""
        sample_tick.active = False
        replay_engine.load_game([sample_tick], 'test-game')
        replay_engine.set_tick_index(0)

        result = trade_manager.execute_buy(Decimal('0.005'))

        assert result['success'] == False
        assert 'reason' in result

    def test_trading_not_allowed_when_rugged(self, game_state, trade_manager, replay_engine, sample_tick):
        """Test trading blocked when game is rugged"""
        sample_tick.rugged = True
        replay_engine.load_game([sample_tick], 'test-game')
        replay_engine.set_tick_index(0)

        result = trade_manager.execute_buy(Decimal('0.005'))

        assert result['success'] == False
        assert 'reason' in result


class TestTradeManagerEdgeCases:
    """Tests for edge cases"""

    def test_multiple_trades_in_game(self, game_state, trade_manager, replay_engine, price_series):
        """Test multiple buy-sell cycles in one game"""
        replay_engine.load_game(price_series, 'test-game')

        # First cycle
        replay_engine.set_tick_index(0)  # Price: 1.0
        result1 = trade_manager.execute_buy(Decimal('0.01'))
        assert result1['success'] == True

        replay_engine.set_tick_index(2)  # Price: 1.5
        result2 = trade_manager.execute_sell()
        assert result2['success'] == True

        # Second cycle
        replay_engine.set_tick_index(3)  # Price: 2.0
        result3 = trade_manager.execute_buy(Decimal('0.01'))
        assert result3['success'] == True

        replay_engine.set_tick_index(5)  # Price: 3.0
        result4 = trade_manager.execute_sell()
        assert result4['success'] == True

        # Verify two positions in history
        assert len(game_state.get_position_history()) == 2

    def test_simultaneous_position_and_sidebet(self, loaded_game_state, trade_manager):
        """Test having both active position and sidebet"""
        # Open position
        result1 = trade_manager.execute_buy(Decimal('0.01'))
        assert result1['success'] == True

        # Place sidebet
        result2 = trade_manager.execute_sidebet(Decimal('0.002'))
        assert result2['success'] == True

        assert loaded_game_state.get('position') is not None
        assert loaded_game_state.get('sidebet') is not None
