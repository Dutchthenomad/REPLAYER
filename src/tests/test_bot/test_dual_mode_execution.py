"""
Test Dual-Mode Bot Execution (Phase 8.3)

Tests that BotController works in both BACKEND and UI_LAYER execution modes.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from bot import BotController, BotInterface
from bot.execution_mode import ExecutionMode
from bot.ui_controller import BotUIController


class TestExecutionModeEnum:
    """Test ExecutionMode enum"""

    def test_backend_mode_value(self):
        """ExecutionMode.BACKEND should have value 'backend'"""
        assert ExecutionMode.BACKEND.value == "backend"

    def test_ui_layer_mode_value(self):
        """ExecutionMode.UI_LAYER should have value 'ui_layer'"""
        assert ExecutionMode.UI_LAYER.value == "ui_layer"


class TestBotControllerBackendMode:
    """Test BotController in BACKEND mode (default)"""

    @pytest.fixture
    def mock_bot_interface(self):
        """Mock BotInterface for testing"""
        mock_interface = Mock(spec=BotInterface)
        mock_interface.bot_get_observation.return_value = {
            'current_state': {
                'price': 1.5,
                'tick': 100,
                'phase': 'trading',
                'active': True,
                'rugged': False,
                'trade_count': 10
            },
            'wallet': {
                'balance': 1.0,
                'starting_balance': 1.0,
                'session_pnl': 0.0
            },
            'position': None,  # No position
            'sidebet': None,   # No sidebet
            'game_info': {
                'game_id': 'test_game',
                'current_tick_index': 100,
                'total_ticks': 500
            }
        }
        mock_interface.bot_get_info.return_value = {
            'valid_actions': ['BUY', 'WAIT'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True
        }
        mock_interface.bot_execute_action.return_value = {
            'success': True,
            'action': 'WAIT',
            'reason': 'Waiting'
        }
        return mock_interface

    def test_backend_mode_default(self, mock_bot_interface):
        """BotController should default to BACKEND mode"""
        controller = BotController(mock_bot_interface, "conservative")
        assert controller.execution_mode == ExecutionMode.BACKEND

    def test_backend_mode_explicit(self, mock_bot_interface):
        """BotController can be explicitly set to BACKEND mode"""
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.BACKEND
        )
        assert controller.execution_mode == ExecutionMode.BACKEND

    def test_backend_mode_executes_via_bot_interface(self, mock_bot_interface):
        """BACKEND mode should execute via bot_interface.bot_execute_action()"""
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.BACKEND
        )

        # Execute a step
        result = controller.execute_step()

        # Should have called bot_execute_action
        mock_bot_interface.bot_execute_action.assert_called_once()
        assert result['success'] is True

    def test_backend_mode_no_ui_controller_required(self, mock_bot_interface):
        """BACKEND mode should not require ui_controller parameter"""
        # Should not raise error
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.BACKEND,
            ui_controller=None  # Explicitly None
        )
        assert controller.ui_controller is None


class TestBotControllerUILayerMode:
    """Test BotController in UI_LAYER mode"""

    @pytest.fixture
    def mock_bot_interface(self):
        """Mock BotInterface for testing"""
        mock_interface = Mock(spec=BotInterface)
        mock_interface.bot_get_observation.return_value = {
            'current_state': {
                'price': 1.5,
                'tick': 100,
                'phase': 'trading',
                'active': True,
                'rugged': False,
                'trade_count': 10
            },
            'wallet': {
                'balance': 1.0,
                'starting_balance': 1.0,
                'session_pnl': 0.0
            },
            'position': None,  # No position
            'sidebet': None,   # No sidebet
            'game_info': {
                'game_id': 'test_game',
                'current_tick_index': 100,
                'total_ticks': 500
            }
        }
        mock_interface.bot_get_info.return_value = {
            'valid_actions': ['BUY', 'WAIT'],
            'can_buy': True,
            'can_sell': False,
            'can_sidebet': True
        }
        return mock_interface

    @pytest.fixture
    def mock_ui_controller(self):
        """Mock BotUIController for testing"""
        mock_ui = Mock(spec=BotUIController)
        mock_ui.execute_buy_with_amount.return_value = True
        mock_ui.click_sell.return_value = True
        mock_ui.set_sell_percentage.return_value = True
        mock_ui.execute_sidebet_with_amount.return_value = True
        return mock_ui

    def test_ui_layer_mode_requires_ui_controller(self, mock_bot_interface):
        """UI_LAYER mode should require ui_controller parameter"""
        with pytest.raises(ValueError, match="UI_LAYER mode requires ui_controller"):
            BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=None
            )

    def test_ui_layer_mode_accepts_ui_controller(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should accept ui_controller parameter"""
        # Should not raise error
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.UI_LAYER,
            ui_controller=mock_ui_controller
        )
        assert controller.ui_controller == mock_ui_controller
        assert controller.execution_mode == ExecutionMode.UI_LAYER

    def test_ui_layer_wait_action(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should handle WAIT action without UI interaction"""
        # Force strategy to return WAIT
        with patch('bot.controller.get_strategy') as mock_get_strategy:
            mock_strategy = Mock()
            mock_strategy.decide.return_value = ('WAIT', None, 'Waiting for better entry')
            mock_get_strategy.return_value = mock_strategy

            controller = BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=mock_ui_controller
            )

            result = controller.execute_step()

            # WAIT should succeed without calling UI controller
            assert result['success'] is True
            assert result['action'] == 'WAIT'
            mock_ui_controller.execute_buy_with_amount.assert_not_called()
            mock_ui_controller.click_sell.assert_not_called()

    def test_ui_layer_buy_action(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should execute BUY via ui_controller"""
        # Force strategy to return BUY
        with patch('bot.controller.get_strategy') as mock_get_strategy:
            mock_strategy = Mock()
            mock_strategy.decide.return_value = ('BUY', Decimal('0.01'), 'Good entry point')
            mock_get_strategy.return_value = mock_strategy

            controller = BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=mock_ui_controller
            )

            result = controller.execute_step()

            # Should have called ui_controller.execute_buy_with_amount
            mock_ui_controller.execute_buy_with_amount.assert_called_once_with(Decimal('0.01'))
            assert result['success'] is True
            assert result['action'] == 'BUY'

    def test_ui_layer_sell_action_sets_100_percent(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should always set 100% before SELL (user requirement)"""
        # Force strategy to return SELL
        with patch('bot.controller.get_strategy') as mock_get_strategy:
            mock_strategy = Mock()
            mock_strategy.decide.return_value = ('SELL', None, 'Take profit')
            mock_get_strategy.return_value = mock_strategy

            # Update mock to show position
            mock_bot_interface.bot_get_observation.return_value['has_position'] = True

            controller = BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=mock_ui_controller
            )

            result = controller.execute_step()

            # Should have set 100% before clicking SELL (user requirement)
            mock_ui_controller.set_sell_percentage.assert_called_once_with(1.0)
            mock_ui_controller.click_sell.assert_called_once()
            assert result['success'] is True
            assert result['action'] == 'SELL'

    def test_ui_layer_sidebet_action(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should execute SIDEBET via ui_controller"""
        # Force strategy to return SIDE
        with patch('bot.controller.get_strategy') as mock_get_strategy:
            mock_strategy = Mock()
            mock_strategy.decide.return_value = ('SIDE', Decimal('0.001'), 'Rug expected soon')
            mock_get_strategy.return_value = mock_strategy

            controller = BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=mock_ui_controller
            )

            result = controller.execute_step()

            # Should have called ui_controller.execute_sidebet_with_amount
            mock_ui_controller.execute_sidebet_with_amount.assert_called_once_with(Decimal('0.001'))
            assert result['success'] is True
            assert result['action'] == 'SIDE'

    def test_ui_layer_buy_failure_handling(self, mock_bot_interface, mock_ui_controller):
        """UI_LAYER mode should handle BUY failure gracefully"""
        # Force BUY action
        with patch('bot.controller.get_strategy') as mock_get_strategy:
            mock_strategy = Mock()
            mock_strategy.decide.return_value = ('BUY', Decimal('0.01'), 'Good entry')
            mock_get_strategy.return_value = mock_strategy

            # Make UI controller fail
            mock_ui_controller.execute_buy_with_amount.return_value = False

            controller = BotController(
                mock_bot_interface,
                "conservative",
                execution_mode=ExecutionMode.UI_LAYER,
                ui_controller=mock_ui_controller
            )

            result = controller.execute_step()

            # Should return error result
            assert result['success'] is False
            assert 'BUY via UI failed' in result['reason']


class TestBotControllerStats:
    """Test BotController statistics with execution mode"""

    @pytest.fixture
    def mock_bot_interface(self):
        """Mock BotInterface for testing"""
        mock_interface = Mock(spec=BotInterface)
        mock_interface.bot_get_observation.return_value = {
            'current_state': {
                'price': 1.5,
                'tick': 100,
                'phase': 'trading',
                'active': True,
                'rugged': False,
                'trade_count': 10
            },
            'wallet': {
                'balance': 1.0,
                'starting_balance': 1.0,
                'session_pnl': 0.0
            },
            'position': None,  # No position
            'sidebet': None,   # No sidebet
            'game_info': {
                'game_id': 'test_game',
                'current_tick_index': 100,
                'total_ticks': 500
            }
        }
        mock_interface.bot_get_info.return_value = {
            'valid_actions': ['WAIT'],
            'can_buy': False,
            'can_sell': False,
            'can_sidebet': False
        }
        mock_interface.bot_execute_action.return_value = {
            'success': True,
            'action': 'WAIT'
        }
        return mock_interface

    def test_stats_include_execution_mode_backend(self, mock_bot_interface):
        """get_stats() should include execution_mode for BACKEND"""
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.BACKEND
        )

        stats = controller.get_stats()

        assert 'execution_mode' in stats
        assert stats['execution_mode'] == 'backend'

    def test_stats_include_execution_mode_ui_layer(self, mock_bot_interface):
        """get_stats() should include execution_mode for UI_LAYER"""
        mock_ui = Mock(spec=BotUIController)

        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.UI_LAYER,
            ui_controller=mock_ui
        )

        stats = controller.get_stats()

        assert 'execution_mode' in stats
        assert stats['execution_mode'] == 'ui_layer'

    def test_str_includes_execution_mode(self, mock_bot_interface):
        """__str__() should include execution mode"""
        controller = BotController(
            mock_bot_interface,
            "conservative",
            execution_mode=ExecutionMode.BACKEND
        )

        str_repr = str(controller)

        assert 'backend' in str_repr
        assert 'conservative' in str_repr
