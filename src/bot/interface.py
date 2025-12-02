"""
Bot Interface - API for bot actions and observations
Refactored to remove legacy compatibility layer dependencies.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List

from core import GameState, TradeManager
from config import config

logger = logging.getLogger(__name__)

# Constants previously in Config
BLOCKED_PHASES_FOR_TRADING = ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]

# PRESALE allows one BUY and one SIDEBET before game starts
PRESALE_PHASE = "PRESALE"

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
        snap = self.state.get_snapshot()
        
        # Use metadata active/rugged flags or defaults from snapshot
        # Note: active/rugged were added to StateSnapshot in Phase 3
        is_active = snap.active
        is_rugged = snap.rugged
        
        # Get position info
        position_info = None
        if snap.position and snap.position.get('status') == 'active':
            pos = snap.position
            entry_price = pos['entry_price']
            amount = pos['amount']
            
            # Calculate PnL manually (previously done by Position model)
            current_val = amount * snap.price
            entry_val = amount * entry_price
            unrealized_pnl_sol = current_val - entry_val
            
            if entry_price > 0:
                unrealized_pnl_pct = ((snap.price / entry_price) - 1) * 100
            else:
                unrealized_pnl_pct = Decimal('0')

            position_info = {
                'entry_price': float(entry_price),
                'amount': float(amount),
                'entry_tick': pos['entry_tick'],
                'current_pnl_sol': float(unrealized_pnl_sol),
                'current_pnl_percent': float(unrealized_pnl_pct)
            }

        # Get sidebet info
        sidebet_info = None
        if snap.sidebet and snap.sidebet.get('status') == 'active':
            sb = snap.sidebet
            window = config.GAME_RULES['sidebet_window_ticks']
            multiplier = config.GAME_RULES['sidebet_multiplier']
            
            ticks_remaining = (sb['placed_tick'] + window) - snap.tick
            sidebet_info = {
                'amount': float(sb['amount']),
                'placed_tick': sb['placed_tick'],
                'placed_price': float(sb['placed_price']),
                'ticks_remaining': ticks_remaining,
                'potential_win': float(sb['amount'] * multiplier)
            }

        return {
            'current_state': {
                'price': float(snap.price),
                'tick': snap.tick,
                'phase': snap.phase,
                'active': is_active,
                'rugged': is_rugged,
                'trade_count': self.state.get_stats('total_trades')
            },
            'wallet': {
                'balance': float(snap.balance),
                'starting_balance': float(self.state.get('initial_balance', Decimal('0.1'))),
                'session_pnl': float(self.state.get_stats('total_pnl'))
            },
            'position': position_info,
            'sidebet': sidebet_info,
            'game_info': {
                'game_id': snap.game_id or 'Unknown',
                'current_tick_index': snap.tick,
                'total_ticks': 0 # Legacy compat, was len(self.state._current_game) which was []
            }
        }

    def bot_get_info(self) -> Dict[str, Any]:
        """
        Get information about valid actions and game constraints

        Returns:
            Dictionary with valid_actions, can_buy, can_sell, can_sidebet, constraints
        """
        snap = self.state.get_snapshot()
        
        # Default: no actions available
        valid_actions = ['WAIT']
        can_buy = False
        can_sell = False
        can_sidebet = False

        # Retrieve config values
        min_bet = config.FINANCIAL['min_bet']
        max_bet = config.FINANCIAL['max_bet']
        sidebet_mult = config.GAME_RULES['sidebet_multiplier']
        sidebet_window = config.GAME_RULES['sidebet_window_ticks']
        sidebet_cooldown = config.GAME_RULES['sidebet_cooldown_ticks']

        if snap:
            has_position = snap.position and snap.position.get('status') == 'active'
            has_sidebet = snap.sidebet and snap.sidebet.get('status') == 'active'

            # PRESALE phase allows trading even when not "active" yet
            is_tradeable = (
                snap.phase == PRESALE_PHASE or
                (snap.active and snap.phase not in BLOCKED_PHASES_FOR_TRADING)
            )

            # Check if can buy (position accumulation / DCA allowed)
            if (is_tradeable and
                snap.balance >= min_bet):
                can_buy = True
                valid_actions.append('BUY')

            # Check if can sell
            if has_position:
                can_sell = True
                valid_actions.append('SELL')

            # Check if can sidebet
            if (is_tradeable and
                not has_sidebet and
                snap.balance >= min_bet):

                # Check cooldown
                last_resolved = self.state.get('last_sidebet_resolved_tick')
                if last_resolved is not None:
                    ticks_since = snap.tick - last_resolved
                    if ticks_since > sidebet_cooldown:
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
                'min_bet': float(min_bet),
                'max_bet': float(max_bet),
                'sidebet_multiplier': float(sidebet_mult),
                'sidebet_window_ticks': sidebet_window,
                'sidebet_cooldown_ticks': sidebet_cooldown
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