"""
Bot Controller - manages bot execution with strategies
"""

import logging
from typing import Dict, Any, Optional

from .interface import BotInterface
from .strategies import get_strategy, TradingStrategy

logger = logging.getLogger(__name__)


class BotController:
    """
    Bot controller manages bot execution

    Responsibilities:
    - Load and manage trading strategy
    - Execute decision cycle (observe → decide → act)
    - Track bot performance
    - Handle errors gracefully
    """

    def __init__(self, bot_interface: BotInterface, strategy_name: str = "conservative"):
        """
        Initialize bot controller

        Args:
            bot_interface: BotInterface instance
            strategy_name: Strategy to use (conservative, aggressive, sidebet)
        """
        self.bot = bot_interface
        self.strategy_name = strategy_name
        self.strategy: TradingStrategy = get_strategy(strategy_name)

        # Track last action
        self.last_action = None
        self.last_reasoning = None
        self.last_result = None

        # Performance tracking
        self.actions_taken = 0
        self.successful_actions = 0
        self.failed_actions = 0

        logger.info(f"BotController initialized with {strategy_name} strategy")

    def execute_step(self) -> Dict[str, Any]:
        """
        Execute one decision cycle

        Steps:
        1. Get observation from game
        2. Get valid actions info
        3. Ask strategy to decide
        4. Execute action
        5. Return result

        Returns:
            Result dictionary from action execution
        """
        try:
            # Step 1: Observe
            observation = self.bot.bot_get_observation()
            if not observation:
                return self._error_result("No game state available")

            # Step 2: Get action info
            info = self.bot.bot_get_info()

            # Step 3: Decide
            action_type, amount, reasoning = self.strategy.decide(observation, info)

            # Store reasoning
            self.last_action = action_type
            self.last_reasoning = reasoning

            # Step 4: Execute
            result = self.bot.bot_execute_action(action_type, amount)

            # Track result
            self.last_result = result
            self.actions_taken += 1

            if result['success']:
                self.successful_actions += 1
            else:
                self.failed_actions += 1

            logger.debug(
                f"Bot action: {action_type} - {reasoning} - "
                f"Success: {result['success']}"
            )

            return result

        except Exception as e:
            logger.error(f"Bot execution error: {e}", exc_info=True)
            return self._error_result(f"Bot error: {e}")

    def change_strategy(self, strategy_name: str):
        """
        Change trading strategy

        Args:
            strategy_name: New strategy name
        """
        self.strategy = get_strategy(strategy_name)
        self.strategy_name = strategy_name
        self.strategy.reset()

        logger.info(f"Strategy changed to: {strategy_name}")

    def reset(self):
        """Reset bot state (new game session)"""
        self.strategy.reset()
        self.last_action = None
        self.last_reasoning = None
        self.last_result = None
        self.actions_taken = 0
        self.successful_actions = 0
        self.failed_actions = 0

        logger.info("Bot controller reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get bot performance statistics"""
        success_rate = 0.0
        if self.actions_taken > 0:
            success_rate = (self.successful_actions / self.actions_taken) * 100

        return {
            'strategy': self.strategy_name,
            'actions_taken': self.actions_taken,
            'successful_actions': self.successful_actions,
            'failed_actions': self.failed_actions,
            'success_rate': success_rate,
            'last_action': self.last_action,
            'last_reasoning': self.last_reasoning
        }

    def _error_result(self, reason: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'success': False,
            'action': 'ERROR',
            'reason': reason
        }

    def __str__(self):
        return f"BotController(strategy={self.strategy_name})"
