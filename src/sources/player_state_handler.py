"""
Player State Handler - Phase 10.4C

Handles player-specific WebSocket events:
- usernameStatus: Player identity on connect
- playerUpdate: Server state after trades
- gameStatePlayerUpdate: Personal leaderboard entry
"""

from decimal import Decimal
from typing import Optional, Dict, Any, Callable, List
import logging

logger = logging.getLogger(__name__)


class PlayerStateHandler:
    """Handles player-specific WebSocket events."""

    def __init__(self):
        self.player_id: Optional[str] = None
        self.player_username: Optional[str] = None
        self.last_server_state: Optional[Dict[str, Any]] = None
        self._event_handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable):
        """Register event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: str, data: Any):
        """Emit event to handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in {event} handler: {e}")

    def handle_username_status(self, data: dict):
        """Handle usernameStatus event - player identity."""
        self.player_id = data.get('id')
        self.player_username = data.get('username')
        logger.info(f"Player identified: {self.player_username} ({self.player_id})")
        self._emit('player_identified', {
            'player_id': self.player_id,
            'username': self.player_username
        })

    def handle_player_update(self, data: dict):
        """Handle playerUpdate event - server state sync."""
        self.last_server_state = {
            'cash': Decimal(str(data.get('cash', 0))),
            'position_qty': Decimal(str(data.get('positionQty', 0))),
            'avg_cost': Decimal(str(data.get('avgCost', 0))),
            'cumulative_pnl': Decimal(str(data.get('cumulativePnL', 0))),
            'total_invested': Decimal(str(data.get('totalInvested', 0))),
        }
        self._emit('server_state_update', self.last_server_state)

    def handle_game_state_player_update(self, data: dict):
        """Handle gameStatePlayerUpdate - personal leaderboard."""
        self._emit('personal_leaderboard', data)

    def get_player_info(self) -> Dict[str, Any]:
        """Get current player info."""
        return {
            'player_id': self.player_id,
            'username': self.player_username
        }
