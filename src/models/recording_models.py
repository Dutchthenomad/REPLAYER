"""
Recording Data Models - Phase 10.4/10.6 Foundation Layer

Separate models for game state and player state recordings.
All monetary values stored as Decimal for precision.

Two-Layer Architecture:
1. Game State Layer (the "board") - tick-by-tick prices
2. Player State Layer (the "moves") - actions with state snapshots

Phase 10.6 Additions:
- ServerState: WebSocket server-reported state for validation
- LocalStateSnapshot: REPLAYER's calculated state
- RecordedAction: Full button press with dual-state validation
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import uuid
import time


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


# =============================================================================
# Phase 10.6: Validation-Aware Recording Models
# =============================================================================

@dataclass
class ServerState:
    """
    Server-reported state from WebSocket playerUpdate event.

    This is the SOURCE OF TRUTH from the game server.
    Used for zero-tolerance validation against local calculations.
    """
    cash: Decimal
    position_qty: Decimal
    avg_cost: Decimal
    cumulative_pnl: Decimal
    total_invested: Decimal
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "cash": str(self.cash),
            "position_qty": str(self.position_qty),
            "avg_cost": str(self.avg_cost),
            "cumulative_pnl": str(self.cumulative_pnl),
            "total_invested": str(self.total_invested),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_websocket(cls, data: Dict[str, Any]) -> "ServerState":
        """Create ServerState from WebSocket playerUpdate data."""
        return cls(
            cash=Decimal(str(data.get("cash", 0))),
            position_qty=Decimal(str(data.get("positionQty", 0))),
            avg_cost=Decimal(str(data.get("avgCost", 0))),
            cumulative_pnl=Decimal(str(data.get("cumulativePnL", 0))),
            total_invested=Decimal(str(data.get("totalInvested", 0))),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class LocalStateSnapshot:
    """
    REPLAYER's locally calculated state at action time.

    Used for validation against ServerState to ensure
    REPLAYER logic perfectly matches the real game.
    """
    balance: Decimal
    position_qty: Decimal
    position_entry_price: Optional[Decimal]
    position_pnl: Optional[Decimal]
    sidebet_active: bool
    sidebet_amount: Optional[Decimal]
    bet_amount: Decimal
    sell_percentage: Decimal
    current_tick: int
    current_price: Decimal
    phase: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "balance": str(self.balance),
            "position_qty": str(self.position_qty),
            "position_entry_price": str(self.position_entry_price) if self.position_entry_price else None,
            "position_pnl": str(self.position_pnl) if self.position_pnl else None,
            "sidebet_active": self.sidebet_active,
            "sidebet_amount": str(self.sidebet_amount) if self.sidebet_amount else None,
            "bet_amount": str(self.bet_amount),
            "sell_percentage": str(self.sell_percentage),
            "current_tick": self.current_tick,
            "current_price": str(self.current_price),
            "phase": self.phase,
        }


@dataclass
class DriftDetails:
    """Details of a drift between local and server state."""
    field: str
    local_value: str
    server_value: str
    difference: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "local": self.local_value,
            "server": self.server_value,
            "diff": self.difference,
        }


@dataclass
class RecordedAction:
    """
    Single recorded action with full validation context.

    Phase 10.6: Captures ALL button presses (not just trades) with
    dual-state validation (local vs server) for zero-tolerance drift detection.

    Categories:
    - BET_INCREMENT: X, +0.001, +0.01, +0.1, +1, 1/2, X2, MAX
    - SELL_PERCENTAGE: 10%, 25%, 50%, 100%
    - TRADE_BUY, TRADE_SELL, TRADE_SIDEBET
    """
    # Identity
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str = ""
    tick: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Action details
    category: str = "BET_INCREMENT"  # BET_INCREMENT, SELL_PERCENTAGE, TRADE_*
    button: str = ""  # Exact button text: "BUY", "+0.01", "25%", etc.
    amount: Optional[Decimal] = None  # For trades

    # Dual-state validation
    local_state: Optional[LocalStateSnapshot] = None
    server_state: Optional[ServerState] = None
    drift_detected: bool = False
    drift_details: Optional[List[DriftDetails]] = None

    # Timing (for trade confirmations)
    timestamp_pressed_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    timestamp_confirmed_ms: Optional[int] = None
    latency_ms: Optional[float] = None

    def record_confirmation(self, timestamp_ms: int) -> float:
        """Record trade confirmation and calculate latency."""
        self.timestamp_confirmed_ms = timestamp_ms
        self.latency_ms = timestamp_ms - self.timestamp_pressed_ms
        return self.latency_ms

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSONL storage."""
        result = {
            "type": "action",
            "action_id": self.action_id,
            "game_id": self.game_id,
            "tick": self.tick,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "button": self.button,
            "drift_detected": self.drift_detected,
            "timestamp_pressed_ms": self.timestamp_pressed_ms,
        }

        if self.amount is not None:
            result["amount"] = str(self.amount)

        if self.local_state:
            result["local_state"] = self.local_state.to_dict()

        if self.server_state:
            result["server_state"] = self.server_state.to_dict()

        if self.drift_details:
            result["drift_details"] = [d.to_dict() for d in self.drift_details]

        if self.timestamp_confirmed_ms is not None:
            result["timestamp_confirmed_ms"] = self.timestamp_confirmed_ms
            result["latency_ms"] = self.latency_ms

        return result


def validate_states(
    local: LocalStateSnapshot,
    server: ServerState
) -> tuple[bool, Optional[List[DriftDetails]]]:
    """
    Zero-tolerance validation of local state against server state.

    Args:
        local: REPLAYER's calculated state
        server: Server-reported state from WebSocket

    Returns:
        Tuple of (drift_detected: bool, drift_details: Optional[List])
    """
    drifts = []

    # Compare balance
    if local.balance != server.cash:
        drifts.append(DriftDetails(
            field="balance",
            local_value=str(local.balance),
            server_value=str(server.cash),
            difference=str(abs(local.balance - server.cash)),
        ))

    # Compare position quantity
    if local.position_qty != server.position_qty:
        drifts.append(DriftDetails(
            field="position_qty",
            local_value=str(local.position_qty),
            server_value=str(server.position_qty),
            difference=str(abs(local.position_qty - server.position_qty)),
        ))

    # Compare entry price (if position exists)
    if local.position_entry_price is not None and server.avg_cost > 0:
        if local.position_entry_price != server.avg_cost:
            drifts.append(DriftDetails(
                field="entry_price",
                local_value=str(local.position_entry_price),
                server_value=str(server.avg_cost),
                difference=str(abs(local.position_entry_price - server.avg_cost)),
            ))

    if drifts:
        return True, drifts
    return False, None
