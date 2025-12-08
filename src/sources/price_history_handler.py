"""
Price History Handler - Phase 10.4D

Maintains tick-by-tick price history per game.
Uses partialPrices to fill gaps from missed ticks.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class PriceHistoryHandler:
    """Maintains complete price history per game."""

    def __init__(self):
        self.current_game_id: Optional[str] = None
        self.prices: List[Optional[Decimal]] = []
        self.peak_multiplier: Decimal = Decimal("1.0")
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

    def handle_tick(self, game_id: str, tick: int, price: Decimal):
        """Handle new price tick."""
        # New game started
        if game_id != self.current_game_id:
            if self.current_game_id:
                self._finalize_game()
            self._start_game(game_id)

        # Extend array if needed
        while len(self.prices) <= tick:
            self.prices.append(None)

        self.prices[tick] = price

        # Track peak
        if price > self.peak_multiplier:
            self.peak_multiplier = price

    def handle_partial_prices(self, partial_prices: dict):
        """Fill gaps using partialPrices from WebSocket."""
        values = partial_prices.get('values', {})
        for tick_str, price_val in values.items():
            tick = int(tick_str)
            if tick < len(self.prices) and self.prices[tick] is None:
                self.prices[tick] = Decimal(str(price_val))
                logger.debug(f"Filled gap at tick {tick}: {price_val}")

    def handle_game_end(self, game_id: str, game_history: list):
        """Handle game completion - extract seed data and finalize."""
        if game_id != self.current_game_id:
            return

        seed_data = None
        if game_history and len(game_history) > 0:
            completed = game_history[0]
            provably_fair = completed.get('provablyFair', {})
            seed_data = {
                'server_seed': provably_fair.get('serverSeed'),
                'server_seed_hash': provably_fair.get('serverSeedHash'),
                'peak_multiplier': Decimal(str(completed.get('peakMultiplier', self.peak_multiplier))),
            }

        self._finalize_game(seed_data)

    def _start_game(self, game_id: str):
        """Start tracking new game."""
        self.current_game_id = game_id
        self.prices = []
        self.peak_multiplier = Decimal("1.0")
        logger.info(f"Started tracking game: {game_id}")

    def _finalize_game(self, seed_data: Optional[dict] = None):
        """Finalize and emit completed game data."""
        gaps = self.prices.count(None)
        if gaps > 0:
            logger.warning(f"Game {self.current_game_id} has {gaps} missing ticks")

        self._emit('game_prices_complete', {
            'game_id': self.current_game_id,
            'prices': self.prices.copy(),
            'peak_multiplier': self.peak_multiplier,
            'duration_ticks': len(self.prices),
            'seed_data': seed_data,
            'has_gaps': gaps > 0
        })

    def get_prices(self) -> List[Optional[Decimal]]:
        """Get current price array."""
        return self.prices.copy()

    def has_gaps(self) -> bool:
        """Check for missing ticks."""
        return None in self.prices
