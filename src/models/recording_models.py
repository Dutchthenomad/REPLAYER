"""
Recording Data Models - Phase 10.4 Foundation Layer

Separate models for game state and player state recordings.
All monetary values stored as Decimal for precision.

Two-Layer Architecture:
1. Game State Layer (the "board") - tick-by-tick prices
2. Player State Layer (the "moves") - actions with state snapshots
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class GameStateMeta:
    """Metadata for a single game recording."""
    game_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ticks: int = 0
    peak_multiplier: Decimal = field(default_factory=lambda: Decimal("1.0"))
    server_seed_hash: Optional[str] = None
    server_seed: Optional[str] = None


@dataclass
class GameStateRecord:
    """Complete game state - prices tick by tick."""
    meta: GameStateMeta
    prices: List[Optional[Decimal]] = field(default_factory=list)

    def add_price(self, tick: int, price: Decimal):
        """Add price at tick, extending array if needed."""
        while len(self.prices) <= tick:
            self.prices.append(None)
        self.prices[tick] = price

    def fill_gaps(self, partial_prices: dict):
        """Fill gaps using partialPrices data from WebSocket."""
        for tick_str, price in partial_prices.items():
            tick = int(tick_str)
            if tick < len(self.prices) and self.prices[tick] is None:
                self.prices[tick] = Decimal(str(price))

    def has_gaps(self) -> bool:
        """Check if any ticks are missing."""
        return None in self.prices

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "meta": {
                "game_id": self.meta.game_id,
                "start_time": self.meta.start_time.isoformat(),
                "end_time": self.meta.end_time.isoformat() if self.meta.end_time else None,
                "duration_ticks": self.meta.duration_ticks,
                "peak_multiplier": str(self.meta.peak_multiplier),
                "server_seed_hash": self.meta.server_seed_hash,
                "server_seed": self.meta.server_seed,
            },
            "prices": [str(p) if p is not None else None for p in self.prices]
        }


@dataclass
class PlayerAction:
    """Single player action with state snapshot."""
    game_id: str
    tick: int
    timestamp: datetime
    action: str  # BUY, SELL, SIDEBET_PLACE, SIDEBET_WIN, SIDEBET_LOSE
    amount: Decimal
    price: Decimal
    balance_after: Decimal
    position_qty_after: Decimal
    entry_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "game_id": self.game_id,
            "tick": self.tick,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "amount": str(self.amount),
            "price": str(self.price),
            "balance_after": str(self.balance_after),
            "position_qty_after": str(self.position_qty_after),
            "entry_price": str(self.entry_price) if self.entry_price else None,
            "pnl": str(self.pnl) if self.pnl else None,
        }


@dataclass
class PlayerSessionMeta:
    """Metadata for a player recording session."""
    player_id: str
    username: str
    session_start: datetime
    session_end: Optional[datetime] = None


@dataclass
class PlayerSession:
    """Complete player session - all actions across games."""
    meta: PlayerSessionMeta
    actions: List[PlayerAction] = field(default_factory=list)

    def add_action(self, action: PlayerAction):
        """Add action to session."""
        self.actions.append(action)

    def get_games_played(self) -> set:
        """Get unique game IDs in this session."""
        return set(a.game_id for a in self.actions)

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "meta": {
                "player_id": self.meta.player_id,
                "username": self.meta.username,
                "session_start": self.meta.session_start.isoformat(),
                "session_end": self.meta.session_end.isoformat() if self.meta.session_end else None,
            },
            "actions": [a.to_dict() for a in self.actions]
        }
