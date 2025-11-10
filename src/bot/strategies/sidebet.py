"""
Sidebet-focused trading strategy
"""

from decimal import Decimal
from typing import Tuple, Optional, Dict, Any

from .base import TradingStrategy


class SidebetStrategy(TradingStrategy):
    """
    Sidebet-focused strategy

    Rules:
    - Prioritize testing sidebet mechanics
    - Place sidebets frequently
    - Also trade normally but quick profits
    """

    def __init__(self):
        super().__init__()
        self.BUY_THRESHOLD = Decimal('2.0')
        self.TAKE_PROFIT = Decimal('30')  # 30%
        self.BUY_AMOUNT = Decimal('0.005')
        self.SIDEBET_AMOUNT = Decimal('0.003')

    def decide(
        self,
        observation: Dict[str, Any],
        info: Dict[str, Any]
    ) -> Tuple[str, Optional[Decimal], str]:
        """Make sidebet-focused trading decision"""

        if not observation:
            return ("WAIT", None, "No game state available")

        # Extract state
        state = observation['current_state']
        position = observation['position']
        sidebet = observation['sidebet']
        wallet = observation['wallet']

        price = Decimal(str(state['price']))
        tick = state['tick']
        balance = Decimal(str(wallet['balance']))

        # PRIORITY 1: Place sidebets frequently for testing
        if sidebet is None and info['can_sidebet']:
            if balance >= self.SIDEBET_AMOUNT:
                return (
                    "SIDE",
                    self.SIDEBET_AMOUNT,
                    f"Testing sidebet at tick {tick}"
                )

        # PRIORITY 2: Trade normally
        if position is None and info['can_buy']:
            if price < self.BUY_THRESHOLD and balance >= self.BUY_AMOUNT:
                return (
                    "BUY",
                    self.BUY_AMOUNT,
                    f"Entry at {price:.2f}x"
                )

        # Quick profit taking
        if position is not None and info['can_sell']:
            pnl_pct = Decimal(str(position['current_pnl_percent']))

            if pnl_pct > self.TAKE_PROFIT:
                return (
                    "SELL",
                    None,
                    "Quick profit"
                )

        # Default: wait
        return (
            "WAIT",
            None,
            "Waiting for sidebet opportunity"
        )
