"""
Demo Action Models - Data structures for human demonstration recording

Records human gameplay for imitation learning. Captures:
- All button presses (bet increments, percentage selectors, trades)
- Full state context (balance, position, sidebet, tick, price)
- Round-trip latency (button press -> WebSocket confirmation)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
import time
import uuid


class ActionCategory(str, Enum):
    """Categories of recordable button actions"""
    BET_INCREMENT = "BET_INCREMENT"      # X, +0.001, +0.01, +0.1, +1, 1/2, X2, MAX
    SELL_PERCENTAGE = "SELL_PERCENTAGE"  # 10%, 25%, 50%, 100%
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    TRADE_SIDEBET = "TRADE_SIDEBET"


# Map button text to category
BUTTON_TO_CATEGORY: Dict[str, ActionCategory] = {
    # Bet increment buttons
    'X': ActionCategory.BET_INCREMENT,
    '+0.001': ActionCategory.BET_INCREMENT,
    '+0.01': ActionCategory.BET_INCREMENT,
    '+0.1': ActionCategory.BET_INCREMENT,
    '+1': ActionCategory.BET_INCREMENT,
    '1/2': ActionCategory.BET_INCREMENT,
    'X2': ActionCategory.BET_INCREMENT,
    'MAX': ActionCategory.BET_INCREMENT,
    # Sell percentage buttons
    '10%': ActionCategory.SELL_PERCENTAGE,
    '25%': ActionCategory.SELL_PERCENTAGE,
    '50%': ActionCategory.SELL_PERCENTAGE,
    '100%': ActionCategory.SELL_PERCENTAGE,
    # Trade buttons
    'BUY': ActionCategory.TRADE_BUY,
    'SELL': ActionCategory.TRADE_SELL,
    'SIDEBET': ActionCategory.TRADE_SIDEBET,
}


def get_category_for_button(button: str) -> ActionCategory:
    """Get the action category for a button text.

    Args:
        button: Button text (e.g., '+0.01', 'BUY', '25%')

    Returns:
        ActionCategory for the button

    Raises:
        ValueError: If button is not recognized
    """
    if button not in BUTTON_TO_CATEGORY:
        raise ValueError(f"Unknown button: {button}")
    return BUTTON_TO_CATEGORY[button]


def is_trade_action(category: ActionCategory) -> bool:
    """Check if category is a trade action (requires confirmation tracking)."""
    return category in (
        ActionCategory.TRADE_BUY,
        ActionCategory.TRADE_SELL,
        ActionCategory.TRADE_SIDEBET
    )


@dataclass
class StateSnapshot:
    """Immutable snapshot of game state at action time."""
    balance: Decimal
    position: Optional[Dict[str, Any]]
    sidebet: Optional[Dict[str, Any]]
    bet_amount: Decimal
    sell_percentage: Decimal
    current_tick: int
    current_price: Decimal
    phase: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            'balance': str(self.balance),
            'position': self.position,
            'sidebet': self.sidebet,
            'bet_amount': str(self.bet_amount),
            'sell_percentage': str(self.sell_percentage),
            'current_tick': self.current_tick,
            'current_price': str(self.current_price),
            'phase': self.phase
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        """Create StateSnapshot from dictionary."""
        return cls(
            balance=Decimal(data['balance']),
            position=data.get('position'),
            sidebet=data.get('sidebet'),
            bet_amount=Decimal(data.get('bet_amount', '0')),
            sell_percentage=Decimal(data.get('sell_percentage', '1.0')),
            current_tick=data.get('current_tick', 0),
            current_price=Decimal(data.get('current_price', '1.0')),
            phase=data.get('phase', 'UNKNOWN')
        )


@dataclass
class DemoAction:
    """Single recorded demonstration action with timing and state context."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: ActionCategory = ActionCategory.BET_INCREMENT
    button: str = ""
    timestamp_pressed: int = field(default_factory=lambda: int(time.time() * 1000))

    # State context
    state_before: Optional[StateSnapshot] = None
    state_after: Optional[Dict[str, Any]] = None

    # Confirmation timing (for trade actions)
    timestamp_confirmed: Optional[int] = None
    latency_ms: Optional[float] = None
    confirmation: Optional[Dict[str, Any]] = None

    # Trade-specific fields
    amount: Optional[Decimal] = None

    def record_confirmation(self, timestamp_ms: int, server_data: Optional[Dict] = None) -> float:
        """Record confirmation and calculate latency.

        Args:
            timestamp_ms: Confirmation timestamp in milliseconds
            server_data: Optional server confirmation data

        Returns:
            Latency in milliseconds
        """
        self.timestamp_confirmed = timestamp_ms
        self.latency_ms = timestamp_ms - self.timestamp_pressed
        self.confirmation = server_data
        return self.latency_ms

    def to_jsonl_dict(self) -> Dict[str, Any]:
        """Convert to JSONL-serializable dictionary."""
        result = {
            'type': 'action',
            'action_id': self.action_id,
            'category': self.category.value,
            'button': self.button,
            'timestamp_pressed': self.timestamp_pressed,
            'timestamp_confirmed': self.timestamp_confirmed,
            'latency_ms': self.latency_ms,
        }

        if self.state_before:
            result['state_before'] = self.state_before.to_dict()

        if self.state_after:
            result['state_after'] = self.state_after

        if self.amount is not None:
            result['amount'] = str(self.amount)

        if self.confirmation:
            result['confirmation'] = self.confirmation

        return result

    @classmethod
    def create_bet_action(
        cls,
        button: str,
        state_before: StateSnapshot,
        state_after: Optional[Dict[str, Any]] = None
    ) -> 'DemoAction':
        """Factory method for bet increment actions."""
        return cls(
            category=ActionCategory.BET_INCREMENT,
            button=button,
            state_before=state_before,
            state_after=state_after
        )

    @classmethod
    def create_trade_action(
        cls,
        button: str,
        amount: Decimal,
        state_before: StateSnapshot
    ) -> 'DemoAction':
        """Factory method for trade actions (BUY, SELL, SIDEBET)."""
        category = get_category_for_button(button)
        return cls(
            category=category,
            button=button,
            amount=amount,
            state_before=state_before
        )
