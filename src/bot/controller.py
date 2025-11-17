"""
Bot Controller - manages bot execution with strategies
Phase 8.3: Now supports dual-mode execution (BACKEND vs UI_LAYER)
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from .interface import BotInterface
from .strategies import get_strategy, TradingStrategy
from .execution_mode import ExecutionMode

logger = logging.getLogger(__name__)


class BotController:
    """
    Bot controller manages bot execution

    Responsibilities:
    - Load and manage trading strategy
    - Execute decision cycle (observe → decide → act)
    - Track bot performance
    - Handle errors gracefully

    Phase 8.3: Supports dual-mode execution
    - BACKEND: Direct TradeManager calls (fast, for training)
    - UI_LAYER: UI interaction via BotUIController (realistic, for live prep)
    """

    def __init__(
        self,
        bot_interface: BotInterface,
        strategy_name: str = "conservative",
        execution_mode: ExecutionMode = ExecutionMode.BACKEND,
        ui_controller: Optional['BotUIController'] = None
    ):
        """
        Initialize bot controller

        Args:
            bot_interface: BotInterface instance
            strategy_name: Strategy to use (conservative, aggressive, sidebet)
            execution_mode: Execution mode (BACKEND or UI_LAYER)
            ui_controller: BotUIController instance (required for UI_LAYER mode)
        """
        self.bot = bot_interface
        self.strategy_name = strategy_name
        self.strategy: TradingStrategy = get_strategy(strategy_name)

        # Phase 8.3: Execution mode
        self.execution_mode = execution_mode
        self.ui_controller = ui_controller

        # Validate UI_LAYER mode requirements
        if execution_mode == ExecutionMode.UI_LAYER and ui_controller is None:
            raise ValueError("UI_LAYER mode requires ui_controller parameter")

        # Track last action
        self.last_action = None
        self.last_reasoning = None
        self.last_result = None

        # Performance tracking
        self.actions_taken = 0
        self.successful_actions = 0
        self.failed_actions = 0

        logger.info(
            f"BotController initialized with {strategy_name} strategy, "
            f"execution_mode={execution_mode.value}"
        )

    def execute_step(self) -> Dict[str, Any]:
        """
        Execute one decision cycle

        Steps:
        1. Get observation from game
        2. Get valid actions info
        3. Ask strategy to decide
        4. Execute action (via BACKEND or UI_LAYER)
        5. Return result

        Phase 8.3: Routes execution based on execution_mode

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

            # Step 4: Execute (Phase 8.3: Route based on execution mode)
            if self.execution_mode == ExecutionMode.BACKEND:
                result = self._execute_action_backend(action_type, amount)
            else:  # ExecutionMode.UI_LAYER
                result = self._execute_action_ui(action_type, amount)

            # Track result
            self.last_result = result
            self.actions_taken += 1

            if result['success']:
                self.successful_actions += 1
            else:
                self.failed_actions += 1

            logger.debug(
                f"Bot action ({self.execution_mode.value}): {action_type} - {reasoning} - "
                f"Success: {result['success']}"
            )

            return result

        except Exception as e:
            logger.error(f"Bot execution error: {e}", exc_info=True)
            return self._error_result(f"Bot error: {e}")

    # ========================================================================
    # EXECUTION METHODS (Phase 8.3)
    # ========================================================================

    def _execute_action_backend(
        self,
        action_type: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Execute action via backend (TradeManager direct calls)

        Phase 8.3: BACKEND mode execution
        - Fast (0ms delay)
        - Perfect for training
        - Uses existing bot_execute_action()

        Args:
            action_type: "BUY", "SELL", "SIDE", or "WAIT"
            amount: Amount for BUY or SIDE actions

        Returns:
            Result dictionary from action execution
        """
        return self.bot.bot_execute_action(action_type, amount)

    def _execute_action_ui(
        self,
        action_type: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Execute action via UI layer (BotUIController clicks)

        Phase 8.3: UI_LAYER mode execution
        - Realistic timing (10-50ms delays)
        - Prepares bot for live browser automation
        - Simulates human interaction

        Args:
            action_type: "BUY", "SELL", "SIDE", or "WAIT"
            amount: Amount for BUY or SIDE actions

        Returns:
            Result dictionary from action execution
        """
        action_type = action_type.upper()

        try:
            # WAIT action (no UI interaction needed)
            if action_type == 'WAIT':
                return {
                    'success': True,
                    'action': 'WAIT',
                    'reason': 'Waited (no action taken)'
                }

            # BUY action
            if action_type == 'BUY':
                if amount is None:
                    return self._error_result("BUY action requires amount")

                success = self.ui_controller.execute_buy_with_amount(amount)
                if success:
                    return {
                        'success': True,
                        'action': 'BUY',
                        'reason': f'BUY executed via UI ({amount} SOL)'
                    }
                else:
                    return self._error_result("BUY via UI failed")

            # SELL action (Phase 8.3: Always press 100% before SELL)
            if action_type == 'SELL':
                # Set 100% sell percentage first (user requirement)
                if not self.ui_controller.set_sell_percentage(1.0):
                    return self._error_result("Failed to set 100% sell percentage")

                # Click SELL button
                success = self.ui_controller.click_sell()
                if success:
                    return {
                        'success': True,
                        'action': 'SELL',
                        'reason': 'SELL executed via UI (100%)'
                    }
                else:
                    return self._error_result("SELL via UI failed")

            # SIDEBET action
            if action_type == 'SIDE':
                if amount is None:
                    return self._error_result("SIDE action requires amount")

                success = self.ui_controller.execute_sidebet_with_amount(amount)
                if success:
                    return {
                        'success': True,
                        'action': 'SIDE',
                        'reason': f'SIDEBET executed via UI ({amount} SOL)'
                    }
                else:
                    return self._error_result("SIDEBET via UI failed")

            # Unknown action
            return self._error_result(f"Unknown action type: {action_type}")

        except Exception as e:
            logger.error(f"UI execution error: {e}", exc_info=True)
            return self._error_result(f"UI execution error: {e}")

    # ========================================================================
    # STRATEGY MANAGEMENT
    # ========================================================================

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
        """Get bot performance statistics (Phase 8.3: includes execution_mode)"""
        success_rate = 0.0
        if self.actions_taken > 0:
            success_rate = (self.successful_actions / self.actions_taken) * 100

        return {
            'strategy': self.strategy_name,
            'execution_mode': self.execution_mode.value,  # Phase 8.3
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
        return f"BotController(strategy={self.strategy_name}, mode={self.execution_mode.value})"
