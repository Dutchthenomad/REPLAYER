"""
Position data model
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from .enums import PositionStatus


@dataclass
class Position:
    """
    Represents a trading position

    Attributes:
        entry_price: Price at entry (multiplier, e.g., 1.0 = 1x)
        amount: Amount of SOL invested
        entry_time: Unix timestamp of entry
        entry_tick: Tick number at entry
        status: Position status (active/closed)
        exit_price: Price at exit (if closed)
        exit_time: Unix timestamp of exit (if closed)
        exit_tick: Tick number at exit (if closed)
        pnl_sol: Profit/loss in SOL (if closed)
        pnl_percent: Profit/loss percentage (if closed)
    """
    entry_price: Decimal
    amount: Decimal
    entry_time: float
    entry_tick: int
    status: str = field(default=PositionStatus.ACTIVE)
    exit_price: Optional[Decimal] = None
    exit_time: Optional[float] = None
    exit_tick: Optional[int] = None
    pnl_sol: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None

    def __post_init__(self):
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {self.entry_price}")
        if self.amount <= 0:
            raise ValueError(f"amount must be positive, got {self.amount}")
        if self.entry_tick < 0:
            raise ValueError(f"entry_tick cannot be negative, got {self.entry_tick}")

    def calculate_unrealized_pnl(self, current_price: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculate unrealized P&L for active position

        Args:
            current_price: Current market price

        Returns:
            Tuple of (pnl_sol, pnl_percent)
        """
        price_change = current_price / self.entry_price - 1
        pnl_sol = self.amount * price_change
        pnl_percent = price_change * 100
        return pnl_sol, pnl_percent

    def close(self, exit_price: Decimal, exit_time: float, exit_tick: int):
        """
        Close the position and calculate realized P&L

        Args:
            exit_price: Price at exit
            exit_time: Unix timestamp of exit
            exit_tick: Tick number at exit
        """
        self.status = PositionStatus.CLOSED
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_tick = exit_tick

        # Calculate realized P&L
        price_change = exit_price / self.entry_price - 1
        self.pnl_sol = self.amount * price_change
        self.pnl_percent = price_change * 100

    def add_to_position(self, additional_amount: Decimal, additional_price: Decimal):
        """
        Add to existing position (calculate weighted average entry)

        Args:
            additional_amount: Additional SOL amount
            additional_price: Price of additional purchase
        """
        total_amount = self.amount + additional_amount
        weighted_avg_price = (
            (self.amount * self.entry_price + additional_amount * additional_price) / total_amount
        )
        self.amount = total_amount
        self.entry_price = weighted_avg_price

    def reduce_amount(self, percentage: Decimal) -> Decimal:
        """
        Reduce position amount by a percentage (Phase 8.1)

        Args:
            percentage: Percentage to reduce (0.1 = 10%, 0.25 = 25%, etc.)

        Returns:
            Amount that was reduced

        Raises:
            ValueError: If percentage is invalid or position is closed
        """
        if self.status != PositionStatus.ACTIVE:
            raise ValueError("Cannot reduce closed position")

        valid_percentages = [Decimal('0.1'), Decimal('0.25'), Decimal('0.5'), Decimal('1.0')]
        if percentage not in valid_percentages:
            raise ValueError(f"Invalid percentage: {percentage}. Must be one of {valid_percentages}")

        if percentage == Decimal('1.0'):
            raise ValueError("Cannot reduce by 100% - use close() instead")

        # Calculate reduction
        amount_to_reduce = self.amount * percentage
        self.amount -= amount_to_reduce

        return amount_to_reduce

    def to_dict(self, preserve_precision: bool = False) -> dict:
        """Convert to dictionary

        Args:
            preserve_precision: If True, keep Decimals as strings
        """
        def convert(value):
            if isinstance(value, Decimal):
                return str(value) if preserve_precision else float(value)
            return value

        return {
            'entry_price': convert(self.entry_price),
            'amount': convert(self.amount),
            'entry_time': self.entry_time,
            'entry_tick': self.entry_tick,
            'status': self.status,
            'exit_price': convert(self.exit_price) if self.exit_price else None,
            'exit_time': self.exit_time,
            'exit_tick': self.exit_tick,
            'pnl_sol': convert(self.pnl_sol) if self.pnl_sol else None,
            'pnl_percent': convert(self.pnl_percent) if self.pnl_percent else None
        }
