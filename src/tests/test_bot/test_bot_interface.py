"""
Tests for BotInterface
"""

import pytest
from decimal import Decimal
from bot import BotInterface


class TestBotInterfaceInitialization:
    """Tests for BotInterface initialization"""

    def test_bot_interface_creation(self, bot_interface):
        """Test creating BotInterface"""
        assert bot_interface is not None

    def test_bot_interface_with_dependencies(self, game_state, trade_manager, bot_interface):
        """Test BotInterface has access to dependencies"""
        assert bot_interface.state == game_state
        assert bot_interface.manager == trade_manager


class TestBotInterfaceObservation:
    """Tests for bot_get_observation()"""

    def test_get_observation(self, loaded_game_state, bot_interface):
        """Test getting observation"""
        obs = bot_interface.bot_get_observation()

        assert obs is not None
        assert isinstance(obs, dict)

    def test_observation_has_required_keys(self, loaded_game_state, bot_interface):
        """Test observation contains required keys"""
        obs = bot_interface.bot_get_observation()

        assert 'current_state' in obs
        assert 'wallet' in obs
        assert 'position' in obs
        assert 'sidebet' in obs
        assert 'game_info' in obs

    def test_observation_current_state(self, loaded_game_state, bot_interface):
        """Test observation current_state has correct data"""
        obs = bot_interface.bot_get_observation()

        assert obs['current_state']['price'] == 1.0
        assert obs['current_state']['tick'] == 0
        assert obs['current_state']['phase'] == 'ACTIVE'
        assert obs['current_state']['active'] == True
        assert obs['current_state']['rugged'] == False

    def test_observation_wallet(self, loaded_game_state, bot_interface):
        """Test observation wallet has correct data"""
        obs = bot_interface.bot_get_observation()

        assert obs['wallet']['balance'] == 0.100
        assert obs['wallet']['starting_balance'] == 0.100
        assert 'session_pnl' in obs['wallet']

    def test_observation_position_none_initially(self, loaded_game_state, bot_interface):
        """Test observation position is None when no position"""
        obs = bot_interface.bot_get_observation()

        assert obs['position'] is None

    def test_observation_position_after_buy(self, loaded_game_state, trade_manager, bot_interface):
        """Test observation position after opening position"""
        trade_manager.execute_buy(Decimal('0.005'))
        obs = bot_interface.bot_get_observation()

        assert obs['position'] is not None
        assert 'entry_price' in obs['position']
        assert 'amount' in obs['position']
        assert 'current_pnl_sol' in obs['position']
        assert 'current_pnl_percent' in obs['position']

    def test_observation_sidebet_none_initially(self, loaded_game_state, bot_interface):
        """Test observation sidebet is None when no sidebet"""
        obs = bot_interface.bot_get_observation()

        assert obs['sidebet'] is None

    def test_observation_sidebet_after_placement(self, loaded_game_state, trade_manager, bot_interface):
        """Test observation sidebet after placement"""
        trade_manager.execute_sidebet(Decimal('0.002'))
        obs = bot_interface.bot_get_observation()

        assert obs['sidebet'] is not None


class TestBotInterfaceInfo:
    """Tests for bot_get_info()"""

    def test_get_info(self, loaded_game_state, bot_interface):
        """Test getting info"""
        info = bot_interface.bot_get_info()

        assert info is not None
        assert isinstance(info, dict)

    def test_info_has_required_keys(self, loaded_game_state, bot_interface):
        """Test info contains required keys"""
        info = bot_interface.bot_get_info()

        assert 'valid_actions' in info
        assert 'can_buy' in info
        assert 'can_sell' in info
        assert 'can_sidebet' in info

    def test_info_can_buy_initially(self, loaded_game_state, bot_interface):
        """Test can_buy is True initially"""
        info = bot_interface.bot_get_info()

        assert info['can_buy'] == True
        assert 'BUY' in info['valid_actions']

    def test_info_cannot_sell_initially(self, loaded_game_state, bot_interface):
        """Test can_sell is False initially"""
        info = bot_interface.bot_get_info()

        assert info['can_sell'] == False

    def test_info_can_sell_after_buy(self, loaded_game_state, trade_manager, bot_interface):
        """Test can_sell is True after buying"""
        trade_manager.execute_buy(Decimal('0.005'))
        info = bot_interface.bot_get_info()

        assert info['can_sell'] == True
        assert 'SELL' in info['valid_actions']

    def test_info_can_buy_with_position_dca(self, loaded_game_state, trade_manager, bot_interface):
        """Test can_buy is True when position active (DCA allowed)"""
        trade_manager.execute_buy(Decimal('0.005'))
        info = bot_interface.bot_get_info()

        # DCA (position accumulation) is allowed - can buy even with existing position
        assert info['can_buy'] == True
        assert 'BUY' in info['valid_actions']


class TestBotInterfaceActions:
    """Tests for bot_execute_action()"""

    def test_execute_wait_action(self, loaded_game_state, bot_interface):
        """Test executing WAIT action"""
        result = bot_interface.bot_execute_action("WAIT")

        assert result['success'] == True
        assert result['action'] == 'WAIT'

    def test_execute_buy_action(self, loaded_game_state, bot_interface):
        """Test executing BUY action"""
        result = bot_interface.bot_execute_action("BUY", Decimal('0.005'))

        assert result['success'] == True
        assert result['action'] == 'BUY'
        assert 'price' in result
        assert 'amount' in result

    def test_execute_sell_action(self, loaded_game_state, trade_manager, bot_interface):
        """Test executing SELL action"""
        # First buy
        trade_manager.execute_buy(Decimal('0.005'))

        # Then sell
        result = bot_interface.bot_execute_action("SELL")

        assert result['success'] == True
        assert result['action'] == 'SELL'

    def test_execute_side_action(self, loaded_game_state, bot_interface):
        """Test executing SIDE action"""
        result = bot_interface.bot_execute_action("SIDE", Decimal('0.002'))

        assert result['success'] == True
        assert result['action'] == 'SIDE'
        assert 'amount' in result

    def test_execute_invalid_action(self, loaded_game_state, bot_interface):
        """Test executing invalid action"""
        result = bot_interface.bot_execute_action("INVALID")

        assert result['success'] == False
        assert 'reason' in result

    def test_execute_buy_without_amount(self, loaded_game_state, bot_interface):
        """Test executing BUY without amount fails"""
        result = bot_interface.bot_execute_action("BUY")

        assert result['success'] == False
        assert 'reason' in result

    def test_execute_side_without_amount(self, loaded_game_state, bot_interface):
        """Test executing SIDE without amount fails"""
        result = bot_interface.bot_execute_action("SIDE")

        assert result['success'] == False
        assert 'reason' in result


class TestBotInterfaceValidation:
    """Tests for action validation"""

    def test_cannot_buy_with_insufficient_balance(self, loaded_game_state, bot_interface):
        """Test buy fails with insufficient balance"""
        result = bot_interface.bot_execute_action("BUY", Decimal('1.0'))

        assert result['success'] == False
        assert 'reason' in result

    def test_cannot_sell_without_position(self, loaded_game_state, bot_interface):
        """Test sell fails without position"""
        result = bot_interface.bot_execute_action("SELL")

        assert result['success'] == False
        assert 'reason' in result

    def test_can_buy_twice_accumulates_position(self, loaded_game_state, bot_interface):
        """Test buying twice accumulates position (DCA allowed)"""
        # First buy
        result1 = bot_interface.bot_execute_action("BUY", Decimal('0.005'))
        assert result1['success'] == True

        # Second buy succeeds (position accumulation / DCA)
        result2 = bot_interface.bot_execute_action("BUY", Decimal('0.005'))
        assert result2['success'] == True

        # Verify position accumulated
        obs = bot_interface.bot_get_observation()
        assert obs['position'] is not None
        assert obs['position']['amount'] == 0.010  # 0.005 + 0.005


class TestBotInterfaceEdgeCases:
    """Tests for edge cases"""

    def test_multiple_wait_actions(self, loaded_game_state, bot_interface):
        """Test multiple WAIT actions succeed"""
        result1 = bot_interface.bot_execute_action("WAIT")
        result2 = bot_interface.bot_execute_action("WAIT")
        result3 = bot_interface.bot_execute_action("WAIT")

        assert result1['success'] == True
        assert result2['success'] == True
        assert result3['success'] == True

    def test_observation_updates_after_action(self, loaded_game_state, bot_interface):
        """Test observation updates after action"""
        obs1 = bot_interface.bot_get_observation()
        initial_balance = obs1['wallet']['balance']

        bot_interface.bot_execute_action("BUY", Decimal('0.005'))

        obs2 = bot_interface.bot_get_observation()
        new_balance = obs2['wallet']['balance']

        assert new_balance < initial_balance
        assert obs2['position'] is not None
