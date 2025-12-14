"""
State Verifier - Phase 10.4E

Compares local GameState to server playerUpdate data.
Logs drift when calculations don't match server truth.
"""

from decimal import Decimal
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

BALANCE_TOLERANCE = Decimal('0.000001')
POSITION_TOLERANCE = Decimal('0.000001')


class StateVerifier:
    """Compares local state to server truth."""

    def __init__(self, game_state):
        """
        Initialize verifier with GameState reference.

        Args:
            game_state: GameState instance to compare against server
        """
        self.game_state = game_state
        self.drift_count = 0
        self.total_verifications = 0
        self.last_verification: Optional[Dict[str, Any]] = None

    def verify(self, server_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare local state to server state.

        Args:
            server_state: Dict with cash, position_qty, avg_cost from server

        Returns:
            Dict with verification result and details
        """
        self.total_verifications += 1

        # Get local values
        local_balance = self.game_state.balance
        local_position = self.game_state.position
        local_position_qty = local_position.amount if local_position else Decimal('0')
        local_entry = local_position.entry_price if local_position else Decimal('0')

        # Get server values
        server_balance = server_state.get('cash', Decimal('0'))
        server_position_qty = server_state.get('position_qty', Decimal('0'))
        server_avg_cost = server_state.get('avg_cost', Decimal('0'))

        # Compare
        balance_diff = abs(local_balance - server_balance)
        position_diff = abs(local_position_qty - server_position_qty)
        entry_diff = abs(local_entry - server_avg_cost) if server_position_qty > 0 else Decimal('0')

        balance_ok = balance_diff <= BALANCE_TOLERANCE
        position_ok = position_diff <= POSITION_TOLERANCE
        entry_ok = entry_diff <= POSITION_TOLERANCE

        all_ok = balance_ok and position_ok and entry_ok

        if not all_ok:
            self.drift_count += 1
            logger.warning(
                f"State drift detected! "
                f"balance: {local_balance} vs {server_balance}, "
                f"position: {local_position_qty} vs {server_position_qty}"
            )

        result = {
            'verified': all_ok,
            'balance': {'local': local_balance, 'server': server_balance, 'ok': balance_ok},
            'position': {'local': local_position_qty, 'server': server_position_qty, 'ok': position_ok},
            'entry_price': {'local': local_entry, 'server': server_avg_cost, 'ok': entry_ok},
            'drift_count': self.drift_count,
            'total_verifications': self.total_verifications
        }

        self.last_verification = result
        return result
