"""
Tests for trading strategies
"""

import pytest
from decimal import Decimal
from bot import get_strategy, list_strategies


class TestStrategyRegistry:
    """Tests for strategy registration"""

    def test_list_strategies(self):
        """Test listing available strategies"""
        strategies = list_strategies()

        assert isinstance(strategies, list)
        assert len(strategies) >= 3

    def test_all_expected_strategies_exist(self):
        """Test all expected strategies are registered"""
        strategies = list_strategies()

        assert 'conservative' in strategies
        assert 'aggressive' in strategies
        assert 'sidebet' in strategies

    def test_get_strategy(self):
        """Test getting a strategy by name"""
        strategy = get_strategy('conservative')

        assert strategy is not None

    def test_get_invalid_strategy(self):
        """Test getting invalid strategy raises ValueError"""
        import pytest
        with pytest.raises(ValueError):
            get_strategy('nonexistent')


class TestConservativeStrategy:
    """Tests for conservative strategy"""

    def test_conservative_strategy_exists(self):
        """Test conservative strategy can be loaded"""
        strategy = get_strategy('conservative')

        assert strategy is not None
        assert hasattr(strategy, 'decide')

    def test_conservative_decide_method(self):
        """Test conservative strategy decide method"""
        strategy = get_strategy('conservative')

        observation = {
            'current_state': {
                'price': 1.2,
                'tick': 10,
                'phase': 'ACTIVE',
                'active': True,
                'rugged': False,
                'trade_count': 5
            },
            'wallet': {
                'balance': 0.100,
                'starting_balance': 0.100,
                'session_pnl': 0.0
            },
            'position': None,
            'sidebet': None,
            'game_info': {
                'game_id': 'test',
                'current_tick_index': 10,
                'total_ticks': 500
            }
        }

        info = {
            'valid_actions': ['WAIT', 'BUY'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True,
            'constraints': {}
        }

        action_type, amount, reasoning = strategy.decide(observation, info)

        assert action_type in ['BUY', 'WAIT', 'SIDE']
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0

    def test_conservative_returns_valid_amount(self):
        """Test conservative strategy returns valid bet amount"""
        strategy = get_strategy('conservative')

        observation = {
            'current_state': {'price': 1.2, 'tick': 10, 'phase': 'ACTIVE', 'active': True, 'rugged': False, 'trade_count': 5},
            'wallet': {'balance': 0.100, 'starting_balance': 0.100, 'session_pnl': 0.0},
            'position': None,
            'sidebet': None,
            'game_info': {'game_id': 'test', 'current_tick_index': 10, 'total_ticks': 500}
        }

        info = {
            'valid_actions': ['WAIT', 'BUY'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True,
            'constraints': {}
        }

        action_type, amount, reasoning = strategy.decide(observation, info)

        if action_type in ['BUY', 'SIDE']:
            assert amount is not None
            assert isinstance(amount, Decimal)
            assert amount > Decimal('0')


class TestAggressiveStrategy:
    """Tests for aggressive strategy"""

    def test_aggressive_strategy_exists(self):
        """Test aggressive strategy can be loaded"""
        strategy = get_strategy('aggressive')

        assert strategy is not None
        assert hasattr(strategy, 'decide')

    def test_aggressive_decide_method(self):
        """Test aggressive strategy decide method"""
        strategy = get_strategy('aggressive')

        observation = {
            'current_state': {'price': 1.5, 'tick': 5, 'phase': 'ACTIVE', 'active': True, 'rugged': False, 'trade_count': 3},
            'wallet': {'balance': 0.100, 'starting_balance': 0.100, 'session_pnl': 0.0},
            'position': None,
            'sidebet': None,
            'game_info': {'game_id': 'test', 'current_tick_index': 5, 'total_ticks': 500}
        }

        info = {
            'valid_actions': ['WAIT', 'BUY'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True,
            'constraints': {}
        }

        action_type, amount, reasoning = strategy.decide(observation, info)

        assert action_type in ['BUY', 'WAIT', 'SIDE', 'SELL']
        assert isinstance(reasoning, str)


class TestSidebetStrategy:
    """Tests for sidebet strategy"""

    def test_sidebet_strategy_exists(self):
        """Test sidebet strategy can be loaded"""
        strategy = get_strategy('sidebet')

        assert strategy is not None
        assert hasattr(strategy, 'decide')

    def test_sidebet_decide_method(self):
        """Test sidebet strategy decide method"""
        strategy = get_strategy('sidebet')

        observation = {
            'current_state': {'price': 1.8, 'tick': 15, 'phase': 'ACTIVE', 'active': True, 'rugged': False, 'trade_count': 8},
            'wallet': {'balance': 0.100, 'starting_balance': 0.100, 'session_pnl': 0.0},
            'position': None,
            'sidebet': None,
            'game_info': {'game_id': 'test', 'current_tick_index': 15, 'total_ticks': 500}
        }

        info = {
            'valid_actions': ['WAIT', 'SIDE'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True,
            'constraints': {}
        }

        action_type, amount, reasoning = strategy.decide(observation, info)

        assert action_type in ['SIDE', 'WAIT']
        assert isinstance(reasoning, str)


class TestStrategyBehavior:
    """Tests for strategy behavior patterns"""

    def test_strategies_respect_valid_actions(self):
        """Test strategies only return valid actions"""
        for strategy_name in ['conservative', 'aggressive', 'sidebet']:
            strategy = get_strategy(strategy_name)

            observation = {
                'current_state': {'price': 1.2, 'tick': 10, 'phase': 'ACTIVE', 'active': True, 'rugged': False, 'trade_count': 5},
                'wallet': {'balance': 0.100, 'starting_balance': 0.100, 'session_pnl': 0.0},
                'position': None,
                'sidebet': None,
                'game_info': {'game_id': 'test', 'current_tick_index': 10, 'total_ticks': 500}
            }

            # Only WAIT is valid
            info = {
                'valid_actions': ['WAIT'],
                'can_buy': False,
                'can_sell': False,
                'can_sidebet': False,
                'constraints': {}
            }

            action_type, amount, reasoning = strategy.decide(observation, info)

            assert action_type == 'WAIT'

    def test_strategies_provide_reasoning(self):
        """Test all strategies provide reasoning"""
        for strategy_name in ['conservative', 'aggressive', 'sidebet']:
            strategy = get_strategy(strategy_name)

            observation = {
                'current_state': {'price': 1.2, 'tick': 10, 'phase': 'ACTIVE', 'active': True, 'rugged': False, 'trade_count': 5},
                'wallet': {'balance': 0.100, 'starting_balance': 0.100, 'session_pnl': 0.0},
                'position': None,
                'sidebet': None,
                'game_info': {'game_id': 'test', 'current_tick_index': 10, 'total_ticks': 500}
            }

            info = {
                'valid_actions': ['WAIT', 'BUY'],
                'can_buy': True,
                'can_sell': False,
                'can_sidebet': True,
                'constraints': {}
            }

            action_type, amount, reasoning = strategy.decide(observation, info)

            assert reasoning is not None
            assert isinstance(reasoning, str)
            assert len(reasoning) > 0
