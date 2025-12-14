"""
Side Bet data model
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from .enums import SideBetStatus


@dataclass
class SideBet:
    """
    Represents a side bet on rug occurrence

    A side bet is a wager that the game will rug within 40 ticks.
    If correct, pays 5:1 (gets back 6x bet amount = 5x profit + original bet)

    Attributes:
        amount: Amount of SOL bet
        placed_tick: Tick number when bet was placed
        placed_price: Price when bet was placed
        status: Bet status (active/won/lost)
    """
    amount: Decimal
    placed_tick: int
    placed_price: Decimal
    status: str = SideBetStatus.ACTIVE

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
            'amount': convert(self.amount),
            'placed_tick': self.placed_tick,
            'placed_price': convert(self.placed_price),
            'status': self.status
        }
