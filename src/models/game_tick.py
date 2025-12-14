"""
Game Tick data model
"""

from dataclasses import dataclass, field
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

    def __post_init__(self):
        """Coerce price to Decimal with safe precision"""
        if not isinstance(self.price, Decimal):
            try:
                self.price = Decimal(str(round(float(self.price), 8)))
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.error(f"Invalid price value: {self.price} ({e}), defaulting to 1.0")
                self.price = Decimal('1.0')

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
        """Check if trading actions are allowed at this tick.

        Trading is allowed during:
        - ACTIVE_GAMEPLAY: Normal active game
        - PRESALE: Pre-round buy window (one BUY + one SIDEBET allowed)
        - GAME_ACTIVATION: Instant transition from presale
        """
        # Presale phase allows pre-round buys even when not fully "active"
        if self.phase == "PRESALE":
            return True

        # Normal active gameplay
        return (
            self.active and
            not self.rugged and
            self.phase not in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "RUG_EVENT_2", "UNKNOWN"]
        )

    def to_dict(self, preserve_precision: bool = False) -> Dict[str, Any]:
        """Convert to dictionary

        Args:
            preserve_precision: If True, keep Decimals as strings
        """
        def convert(val):
            if isinstance(val, Decimal):
                return str(val) if preserve_precision else float(val)
            return val

        return {
            'game_id': self.game_id,
            'tick': self.tick,
            'timestamp': self.timestamp,
            'price': convert(self.price),
            'phase': self.phase,
            'active': self.active,
            'rugged': self.rugged,
            'cooldown_timer': self.cooldown_timer,
            'trade_count': self.trade_count
        }
