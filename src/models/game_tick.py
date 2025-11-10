"""
Game Tick data model
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class GameTick:
    """
    Represents a single tick/frame of game state

    Attributes:
        game_id: Unique game identifier
        tick: Tick number (0-based)
        timestamp: ISO format timestamp
        price: Current token price (multiplier, e.g., 1.0 = 1x)
        phase: Game phase (UNKNOWN, ACTIVE, COOLDOWN, RUG_EVENT, etc.)
        active: Whether game is active (not presale/cooldown)
        rugged: Whether rug event has occurred
        cooldown_timer: Milliseconds until next game (if in cooldown)
        trade_count: Number of trades executed
    """
    game_id: str
    tick: int
    timestamp: str
    price: Decimal
    phase: str
    active: bool
    rugged: bool
    cooldown_timer: int
    trade_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameTick':
        """
        Create GameTick from JSON data

        Args:
            data: Dictionary from JSONL file

        Returns:
            GameTick instance

        Raises:
            ValueError: If data is invalid
        """
        try:
            # Convert price to Decimal for precision
            price_value = data.get('price', 1.0)
            price = Decimal(str(price_value))

            return cls(
                game_id=str(data.get('game_id', 'unknown')),
                tick=int(data.get('tick', 0)),
                timestamp=str(data.get('timestamp', '')),
                price=price,
                phase=str(data.get('phase', 'UNKNOWN')),
                active=bool(data.get('active', False)),
                rugged=bool(data.get('rugged', False)),
                cooldown_timer=int(data.get('cooldown_timer', 0)),
                trade_count=int(data.get('trade_count', 0))
            )
        except (ValueError, InvalidOperation, KeyError) as e:
            logger.error(f"Failed to parse GameTick: {e}, data: {data}")
            raise ValueError(f"Invalid game tick data: {e}")

    def is_tradeable(self) -> bool:
        """Check if trading actions are allowed at this tick"""
        return (
            self.active and
            not self.rugged and
            self.phase not in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'game_id': self.game_id,
            'tick': self.tick,
            'timestamp': self.timestamp,
            'price': float(self.price),
            'phase': self.phase,
            'active': self.active,
            'rugged': self.rugged,
            'cooldown_timer': self.cooldown_timer,
            'trade_count': self.trade_count
        }
