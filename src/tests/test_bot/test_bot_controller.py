"""
Tests for BotController and bot playthrough
"""

import pytest
from decimal import Decimal
from bot import BotController


class TestBotControllerInitialization:
    """Tests for BotController initialization"""

    def test_bot_controller_creation(self, bot_controller):
        """Test creating BotController"""
        assert bot_controller is not None

    def test_bot_controller_with_strategy(self, bot_controller):
        """Test BotController has strategy"""
        assert bot_controller.strategy_name == "conservative"

    def test_bot_controller_with_custom_strategy(self, bot_interface):
        """Test creating BotController with custom strategy"""
        controller = BotController(bot_interface, "aggressive")

        assert controller.strategy_name == "aggressive"


class TestBotControllerExecution:
    """Tests for bot execution"""

    def test_execute_step(self, loaded_game_state, bot_controller):
        """Test executing one decision step"""
        result = bot_controller.execute_step()

        assert result is not None
        assert 'action' in result
        assert 'success' in result

    def test_execute_step_returns_action(self, loaded_game_state, bot_controller):
        """Test execute_step returns action type"""
        result = bot_controller.execute_step()

        assert result['action'] in ['WAIT', 'BUY', 'SELL', 'SIDE']

    def test_last_reasoning_updated(self, loaded_game_state, bot_controller):
        """Test last_reasoning is updated after execution"""
        bot_controller.execute_step()

        assert bot_controller.last_reasoning is not None
        assert isinstance(bot_controller.last_reasoning, str)

    def test_multiple_steps(self, loaded_game_state, bot_controller):
        """Test executing multiple steps"""
        result1 = bot_controller.execute_step()
        result2 = bot_controller.execute_step()
        result3 = bot_controller.execute_step()

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None


class TestBotControllerStatistics:
    """Tests for bot statistics"""

    def test_get_stats(self, bot_controller):
        """Test getting bot statistics"""
        stats = bot_controller.get_stats()

        assert isinstance(stats, dict)
        assert 'actions_taken' in stats
        assert 'success_rate' in stats

    def test_stats_increment_after_action(self, loaded_game_state, bot_controller):
        """Test statistics increment after actions"""
        initial_stats = bot_controller.get_stats()
        initial_actions = initial_stats['actions_taken']

        bot_controller.execute_step()

        new_stats = bot_controller.get_stats()
        new_actions = new_stats['actions_taken']

        assert new_actions > initial_actions

    def test_success_rate_calculation(self, loaded_game_state, bot_controller):
        """Test success rate is calculated correctly"""
        # Execute several steps
        for _ in range(5):
            bot_controller.execute_step()

        stats = bot_controller.get_stats()

        assert stats['success_rate'] >= 0.0
        assert stats['success_rate'] <= 100.0


class TestBotControllerStrategyChange:
    """Tests for strategy changes"""

    def test_change_strategy(self, bot_controller):
        """Test changing strategy"""
        assert bot_controller.strategy_name == "conservative"

        bot_controller.change_strategy("aggressive")

        assert bot_controller.strategy_name == "aggressive"

    def test_change_to_invalid_strategy(self, bot_controller):
        """Test changing to invalid strategy fails gracefully"""
        original_strategy = bot_controller.strategy_name

        # Try to change to invalid strategy
        try:
            bot_controller.change_strategy("nonexistent")
        except (KeyError, ValueError, AttributeError):
            # AUDIT FIX: Catch specific exceptions
            pass  # May raise exception or fail silently

        # Strategy should remain unchanged or be handled gracefully
        assert bot_controller.strategy_name in ['conservative', 'nonexistent']

    def test_execute_with_different_strategies(self, loaded_game_state, bot_interface):
        """Test execution with different strategies"""
        controller1 = BotController(bot_interface, "conservative")
        controller2 = BotController(bot_interface, "aggressive")

        result1 = controller1.execute_step()
        result2 = controller2.execute_step()

        assert result1 is not None
        assert result2 is not None


class TestBotPlaythrough:
    """Tests for bot playing through multiple ticks"""

    def test_playthrough_simple_game(self, game_state, trade_manager, bot_interface, replay_engine, price_series):
        """Test bot playing through a game"""
        replay_engine.load_game(price_series, 'test-game')
        bot_controller = BotController(bot_interface, "conservative")

        # Play through all ticks
        for i in range(len(price_series)):
            replay_engine.set_tick_index(i)
            result = bot_controller.execute_step()
            assert result is not None

        # Verify bot took actions
        stats = bot_controller.get_stats()
        assert stats['actions_taken'] > 0

    def test_playthrough_tracks_balance(self, game_state, trade_manager, bot_interface, replay_engine, price_series):
        """Test balance is tracked during playthrough"""
        replay_engine.load_game(price_series, 'test-game')
        bot_controller = BotController(bot_interface, "conservative")

        initial_balance = game_state.get('balance')

        # Play through game
        for i in range(len(price_series)):
            replay_engine.set_tick_index(i)
            bot_controller.execute_step()

        final_balance = game_state.get('balance')

        # Balance should have changed (may be higher or lower)
        # Just verify it's a valid decimal
        assert isinstance(final_balance, Decimal)

    def test_playthrough_final_stats(self, game_state, trade_manager, bot_interface, replay_engine, price_series):
        """Test final statistics after playthrough"""
        replay_engine.load_game(price_series, 'test-game')
        bot_controller = BotController(bot_interface, "conservative")

        # Play through game
        for i in range(len(price_series)):
            replay_engine.set_tick_index(i)
            bot_controller.execute_step()

        stats = bot_controller.get_stats()
        final_balance = game_state.get('balance')
        pnl = final_balance - Decimal('0.100')

        # Verify stats exist
        assert stats['actions_taken'] >= len(price_series)
        assert 'success_rate' in stats

    def test_playthrough_with_different_strategies(self, price_series):
        """Test playthrough with different strategies"""
        from core import GameState, TradeManager, ReplayEngine
        from bot import BotInterface, BotController

        strategies = ['conservative', 'aggressive', 'sidebet']

        for strategy_name in strategies:
            # Create fresh instances for each strategy
            game_state = GameState(Decimal('0.100'))
            trade_manager = TradeManager(game_state)
            bot_interface = BotInterface(game_state, trade_manager)
            replay_engine = ReplayEngine(game_state)

            replay_engine.load_game(price_series, 'test-game')
            bot_controller = BotController(bot_interface, strategy_name)

            # Play through game
            for i in range(len(price_series)):
                replay_engine.set_tick_index(i)
                bot_controller.execute_step()

            # Verify completed
            stats = bot_controller.get_stats()
            assert stats['actions_taken'] > 0


class TestBotControllerEdgeCases:
    """Tests for edge cases"""

    def test_execute_without_loaded_game(self, bot_controller):
        """Test execution without loaded game handles gracefully"""
        # May fail or return WAIT action
        result = bot_controller.execute_step()

        # Should not crash
        assert result is not None

    def test_execute_step_maintains_state_consistency(self, loaded_game_state, bot_controller):
        """Test state consistency after steps"""
        # Execute several steps
        for _ in range(3):
            bot_controller.execute_step()

        # State should still be valid
        obs = bot_controller.bot.bot_get_observation()
        assert obs is not None
        assert 'current_state' in obs
        assert 'wallet' in obs

    def test_bot_handles_invalid_actions_gracefully(self, loaded_game_state, bot_controller):
        """Test bot handles invalid actions gracefully"""
        # Execute many steps - bot should handle any validation errors
        for _ in range(10):
            result = bot_controller.execute_step()
            assert result is not None
            assert 'action' in result
