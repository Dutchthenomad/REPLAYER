"""
Trade execution manager
"""

import logging
import time
from decimal import Decimal
from typing import Dict, Any

from models import Position, SideBet, GameTick
from config import config
from services import event_bus, Events
from .validators import validate_buy, validate_sell, validate_sidebet
from .game_state import GameState

logger = logging.getLogger(__name__)


class TradeManager:
    """
    Manages trade execution and validation

    Responsibilities:
    - Validate trade requests
    - Execute trades (buy/sell/sidebet)
    - Update game state
    - Publish trade events
    - Handle rug detection and sidebet resolution
    """

    def __init__(self, game_state: GameState):
        self.state = game_state
        logger.info("TradeManager initialized")

    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================

    def execute_buy(self, amount: Decimal) -> Dict[str, Any]:
        """
        Execute buy order

        Args:
            amount: Amount in SOL to buy

        Returns:
            Result dictionary with success, reason, and new state
        """
        tick = self.state.get_current_tick()
        if not tick:
            return self._error_result("No active game", "BUY")

        # Validate
        is_valid, error = validate_buy(amount, self.state.get("balance"), tick, self.state.get("position") is not None)
        if not is_valid:
            return self._error_result(error, "BUY")

        # Execute buy - create position in state
        position_data = {
            'entry_price': tick.price,
            'amount': amount,
            'entry_tick': tick.tick,
            'status': 'active'
        }

        # open_position will deduct the cost from balance automatically
        success = self.state.open_position(position_data)

        if not success:
            return self._error_result("Failed to open position", "BUY")

        # Publish event
        event_bus.publish(Events.TRADE_BUY, {
            'price': float(tick.price),
            'amount': float(amount),
            'tick': tick.tick,
            'phase': tick.phase
        })

        logger.info(f"BUY: {amount} SOL at {tick.price}x (tick {tick.tick})")

        # Calculate balance change (cost = amount * price)
        cost = amount * tick.price

        return self._success_result(
            action='BUY',
            amount=amount,
            price=tick.price,
            tick=tick,
            balance_change=-cost
        )

    def execute_sell(self) -> Dict[str, Any]:
        """
        Execute sell order (close active position)

        Phase 8.1: Now supports partial sells based on sell_percentage in GameState

        Returns:
            Result dictionary with success, reason, and P&L
        """
        tick = self.state.get_current_tick()
        if not tick:
            return self._error_result("No active game", "SELL")

        # Validate
        is_valid, error = validate_sell(self.state.get("position") is not None, tick)
        if not is_valid:
            return self._error_result(error, "SELL")

        # Get position info before closing
        position = self.state.get("position")
        entry_price = position['entry_price']
        original_amount = position['amount']

        # Phase 8.1: Get current sell percentage
        sell_percentage = self.state.get_sell_percentage()

        # Calculate amount being sold
        amount_sold = original_amount * sell_percentage

        # Calculate P&L for the portion being sold
        price_change = tick.price / entry_price - Decimal('1')
        pnl_sol = original_amount * price_change
        pnl_percent = price_change * Decimal('100')
        # Adjust P&L for partial sell
        pnl_sol = pnl_sol * sell_percentage

        # Phase 8.1: Use partial_close_position or close_position based on percentage
        if sell_percentage < Decimal('1.0'):
            # Partial sell
            result = self.state.partial_close_position(sell_percentage, tick.price, exit_tick=tick.tick)

            if not result:
                return self._error_result("Failed to partially close position", "SELL")

            # Publish event with partial sell flag
            event_bus.publish(Events.TRADE_SELL, {
                'partial': True,
                'percentage': float(sell_percentage),
                'entry_price': float(entry_price),
                'exit_price': float(tick.price),
                'amount': float(amount_sold),
                'remaining_amount': float(result['remaining_amount']),
                'pnl_sol': float(pnl_sol),
                'pnl_percent': float(pnl_percent),
                'tick': tick.tick
            })

            logger.info(
                f"PARTIAL SELL ({sell_percentage*100:.0f}%): {amount_sold} SOL at {tick.price}x, "
                f"P&L: {pnl_sol} SOL ({pnl_percent:.1f}%), "
                f"Remaining: {result['remaining_amount']} SOL"
            )

            # Calculate proceeds
            exit_value = amount_sold * tick.price

            return self._success_result(
                action='SELL',
                amount=amount_sold,
                price=tick.price,
                tick=tick,
                balance_change=exit_value,
                pnl_sol=pnl_sol,
                pnl_percent=pnl_percent,
                partial=True,
                percentage=sell_percentage,
                remaining_amount=result['remaining_amount']
            )
        else:
            # Full sell (100%)
            closed_position = self.state.close_position(tick.price, exit_tick=tick.tick)

            if not closed_position:
                return self._error_result("Failed to close position", "SELL")

            # Publish event
            event_bus.publish(Events.TRADE_SELL, {
                'partial': False,
                'percentage': 1.0,
                'entry_price': float(entry_price),
                'exit_price': float(tick.price),
                'amount': float(original_amount),
                'pnl_sol': float(pnl_sol),
                'pnl_percent': float(pnl_percent),
                'tick': tick.tick
            })

            logger.info(f"SELL: {original_amount} SOL at {tick.price}x, P&L: {pnl_sol} SOL ({pnl_percent:.1f}%)")

            # Calculate proceeds
            exit_value = original_amount * tick.price

            return self._success_result(
                action='SELL',
                amount=original_amount,
                price=tick.price,
                tick=tick,
                balance_change=exit_value,
                pnl_sol=pnl_sol,
                pnl_percent=pnl_percent,
                partial=False,
                percentage=Decimal('1.0')
            )

    def execute_sidebet(self, amount: Decimal) -> Dict[str, Any]:
        """
        Execute side bet

        Args:
            amount: Amount in SOL to bet

        Returns:
            Result dictionary with success and details
        """
        tick = self.state.get_current_tick()
        if not tick:
            return self._error_result("No active game", "SIDEBET")

        # Validate
        is_valid, error = validate_sidebet(
            amount,
            self.state.get("balance"),
            tick,
            self.state.get("sidebet") is not None,
            self.state.get("last_sidebet_resolved_tick")
        )
        if not is_valid:
            return self._error_result(error, "SIDEBET")

        # Execute sidebet - place in state
        success = self.state.place_sidebet(amount, tick.tick, tick.price)

        if not success:
            return self._error_result("Failed to place sidebet", "SIDEBET")

        # Publish event
        potential_win = amount * config.GAME_RULES['sidebet_multiplier']
        event_bus.publish(Events.TRADE_SIDEBET, {
            'amount': float(amount),
            'placed_tick': tick.tick,
            'placed_price': float(tick.price),
            'potential_win': float(potential_win)
        })

        logger.info(f"SIDEBET: {amount} SOL at tick {tick.tick} (potential win: {potential_win} SOL)")

        return self._success_result(
            action='SIDE',
            amount=amount,
            price=tick.price,
            tick=tick,
            balance_change=-amount,
            potential_win=potential_win
        )

    # ========================================================================
    # RUG DETECTION & SIDEBET RESOLUTION
    # ========================================================================

    def check_and_handle_rug(self, tick: GameTick):
        """
        Check for rug event and resolve sidebet if applicable

        Args:
            tick: Current game tick
        """
        if not tick.rugged:
            return

        # Rug detected - publish event
        event_bus.publish(Events.RUG_DETECTED, {
            'tick': tick.tick,
            'price': float(tick.price)
        })

        # Check if we have active sidebet
        # AUDIT FIX: Simplified double-negative logic
        if self.state.get("sidebet") is None:
            return

        sidebet = self.state.get("sidebet")
        ticks_since_placed = tick.tick - sidebet.placed_tick

        # Check if within window
        if ticks_since_placed <= config.GAME_RULES['sidebet_window_ticks']:
            # WON sidebet (resolve_sidebet will update balance automatically)
            self.state.resolve_sidebet(won=True, tick=tick.tick)

            payout = sidebet.amount * config.GAME_RULES['sidebet_multiplier']
            logger.info(f"SIDEBET WON: {payout} SOL (placed at tick {sidebet.placed_tick}, rugged at {tick.tick})")
        else:
            # LOST sidebet (rugged after window)
            self.state.resolve_sidebet(won=False, tick=tick.tick)

            logger.info(f"SIDEBET LOST: Rugged after {ticks_since_placed} ticks (window: {config.GAME_RULES['sidebet_window_ticks']})")

    def check_sidebet_expiry(self, tick: GameTick):
        """
        Check if sidebet has expired (game didn't rug in time)

        Args:
            tick: Current game tick
        """
        # AUDIT FIX: Simplified double-negative logic
        if self.state.get("sidebet") is None:
            return

        sidebet = self.state.get("sidebet")
        ticks_since_placed = tick.tick - sidebet.placed_tick
        expiry_tick = sidebet.placed_tick + config.GAME_RULES['sidebet_window_ticks']

        # Check if expired
        if tick.tick > expiry_tick:
            # LOST sidebet (expired without rug)
            self.state.resolve_sidebet(won=False, tick=tick.tick)

            logger.info(f"SIDEBET EXPIRED: Lost {sidebet.amount} SOL (no rug in {config.GAME_RULES['sidebet_window_ticks']} ticks)")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _success_result(
        self,
        action: str,
        amount: Decimal,
        price: Decimal,
        tick: GameTick,
        balance_change: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """Create success result dictionary"""
        result = {
            'success': True,
            'action': action,
            'amount': float(amount),
            'price': float(price),
            'tick': tick.tick,
            'phase': tick.phase,
            'new_balance': float(self.state.get("balance")),
            'balance_change': float(balance_change),
            'reason': f'{action} executed successfully'
        }
        result.update(kwargs)
        return result

    def _error_result(self, reason: str, action: str) -> Dict[str, Any]:
        """Create error result dictionary"""
        return {
            'success': False,
            'action': action,
            'reason': reason,
            'balance': float(self.state.get("balance"))
        }
