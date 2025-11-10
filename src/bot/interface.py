"""
Bot Interface - API for bot actions and observations
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List

from core import GameState, TradeManager
from config import config

logger = logging.getLogger(__name__)


class BotInterface:
    """
    API interface for bots to interact with the game

    Provides:
    - bot_get_observation() - Get current game state
    - bot_get_info() - Get valid actions and constraints
    - bot_execute_action() - Execute trading actions
    """

    def __init__(self, game_state: GameState, trade_manager: TradeManager):
        """
        Initialize bot interface

        Args:
            game_state: GameState instance
            trade_manager: TradeManager instance
        """
        self.state = game_state
        self.manager = trade_manager
        logger.info("BotInterface initialized")

    # ========================================================================
    # OBSERVATION
    # ========================================================================

    def bot_get_observation(self) -> Optional[Dict[str, Any]]:
        """
        Get current game state observation

        Returns:
            Dictionary with current state, wallet, position, sidebet, game info
            or None if no game loaded
        """
        tick = self.state.current_tick
        if not tick:
            return None

        # Get position info
        position_info = None
        if self.state.has_active_position():
            pos = self.state.active_position
            unrealized_pnl_sol, unrealized_pnl_pct = pos.calculate_unrealized_pnl(tick.price)
            position_info = {
                'entry_price': float(pos.entry_price),
                'amount': float(pos.amount),
                'entry_tick': pos.entry_tick,
                'current_pnl_sol': float(unrealized_pnl_sol),
                'current_pnl_percent': float(unrealized_pnl_pct)
            }

        # Get sidebet info
        sidebet_info = None
        if self.state.has_active_sidebet():
            sb = self.state.active_sidebet
            ticks_remaining = (sb.placed_tick + config.SIDEBET_WINDOW_TICKS) - tick.tick
            sidebet_info = {
                'amount': float(sb.amount),
                'placed_tick': sb.placed_tick,
                'placed_price': float(sb.placed_price),
                'ticks_remaining': ticks_remaining,
                'potential_win': float(sb.amount * config.SIDEBET_MULTIPLIER)
            }

        return {
            'current_state': {
                'price': float(tick.price),
                'tick': tick.tick,
                'phase': tick.phase,
                'active': tick.active,
                'rugged': tick.rugged,
                'trade_count': tick.trade_count
            },
            'wallet': {
                'balance': float(self.state.balance),
                'starting_balance': float(self.state.initial_balance),
                'session_pnl': float(self.state.session_pnl)
            },
            'position': position_info,
            'sidebet': sidebet_info,
            'game_info': {
                'game_id': self.state.current_game_id or 'Unknown',
                'current_tick_index': self.state._current_tick_index,
                'total_ticks': len(self.state._current_game)
            }
        }

    def bot_get_info(self) -> Dict[str, Any]:
        """
        Get information about valid actions and game constraints

        Returns:
            Dictionary with valid_actions, can_buy, can_sell, can_sidebet, constraints
        """
        tick = self.state.current_tick

        # Default: no actions available
        valid_actions = ['WAIT']
        can_buy = False
        can_sell = False
        can_sidebet = False

        if tick:
            # Check if can buy
            if (tick.active and
                tick.phase not in config.BLOCKED_PHASES_FOR_TRADING and
                self.state.balance >= config.MIN_BET_SOL):
                can_buy = True
                valid_actions.append('BUY')

            # Check if can sell
            if self.state.has_active_position():
                can_sell = True
                valid_actions.append('SELL')

            # Check if can sidebet
            if (tick.active and
                tick.phase not in config.BLOCKED_PHASES_FOR_TRADING and
                not self.state.has_active_sidebet() and
                self.state.balance >= config.MIN_BET_SOL):

                # Check cooldown
                if self.state._last_sidebet_resolved_tick is not None:
                    ticks_since = tick.tick - self.state._last_sidebet_resolved_tick
                    if ticks_since > config.SIDEBET_COOLDOWN_TICKS:
                        can_sidebet = True
                        valid_actions.append('SIDE')
                else:
                    can_sidebet = True
                    valid_actions.append('SIDE')

        return {
            'valid_actions': valid_actions,
            'can_buy': can_buy,
            'can_sell': can_sell,
            'can_sidebet': can_sidebet,
            'constraints': {
                'min_bet': float(config.MIN_BET_SOL),
                'max_bet': float(config.MAX_BET_SOL),
                'sidebet_multiplier': float(config.SIDEBET_MULTIPLIER),
                'sidebet_window_ticks': config.SIDEBET_WINDOW_TICKS,
                'sidebet_cooldown_ticks': config.SIDEBET_COOLDOWN_TICKS
            }
        }

    # ========================================================================
    # ACTION EXECUTION
    # ========================================================================

    def bot_execute_action(
        self,
        action_type: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Execute bot action

        Args:
            action_type: "BUY", "SELL", "SIDE", or "WAIT"
            amount: Amount for BUY or SIDE actions

        Returns:
            Result dictionary with success, reason, and state changes
        """
        action_type = action_type.upper()

        # Validate action type
        if action_type not in ['BUY', 'SELL', 'SIDE', 'WAIT']:
            return {
                'success': False,
                'action': action_type,
                'reason': f'Invalid action type: {action_type}'
            }

        # WAIT action (always succeeds)
        if action_type == 'WAIT':
            return {
                'success': True,
                'action': 'WAIT',
                'reason': 'Waited (no action taken)'
            }

        # BUY action
        if action_type == 'BUY':
            if amount is None:
                return {
                    'success': False,
                    'action': 'BUY',
                    'reason': 'BUY requires amount parameter'
                }
            return self.manager.execute_buy(amount)

        # SELL action
        if action_type == 'SELL':
            return self.manager.execute_sell()

        # SIDE action
        if action_type == 'SIDE':
            if amount is None:
                return {
                    'success': False,
                    'action': 'SIDE',
                    'reason': 'SIDE requires amount parameter'
                }
            return self.manager.execute_sidebet(amount)

        # Should never reach here
        return {
            'success': False,
            'action': action_type,
            'reason': 'Unknown error'
        }
