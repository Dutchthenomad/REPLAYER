"""
Conservative trading strategy
"""

from decimal import Decimal
from typing import Tuple, Optional, Dict, Any

from .base import TradingStrategy


class ConservativeStrategy(TradingStrategy):
    """
    Conservative trading strategy

    Rules:
    - Buy at low prices (< 1.5x)
    - Sell on modest profit (+20%) or stop loss (-15%)
    - Exit at bubble risk (> 10x)
    - Place sidebets late game (tick > 100)
    """

    def __init__(self):
        super().__init__()
        self.BUY_THRESHOLD = Decimal('1.5')
        self.TAKE_PROFIT = Decimal('20')  # 20%
        self.STOP_LOSS = Decimal('-15')    # -15%
        self.BUBBLE_EXIT = Decimal('10.0')
        self.SIDEBET_TICK = 100
        self.BUY_AMOUNT = Decimal('0.005')
        self.SIDEBET_AMOUNT = Decimal('0.002')

    def decide(
        self,
        observation: Dict[str, Any],
        info: Dict[str, Any]
    ) -> Tuple[str, Optional[Decimal], str]:
        """Make conservative trading decision"""

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

        # No position - look to buy at good price
        if position is None and info['can_buy']:
            if price < self.BUY_THRESHOLD and balance >= self.BUY_AMOUNT:
                return (
                    "BUY",
                    self.BUY_AMOUNT,
                    f"Entry at {price:.2f}x (low price, good entry point)"
                )

        # Have position - manage it
        if position is not None and info['can_sell']:
            pnl_pct = Decimal(str(position['current_pnl_percent']))

            # Take profit at 20%
            if pnl_pct > self.TAKE_PROFIT:
                return (
                    "SELL",
                    None,
                    f"Take profit at +{pnl_pct:.1f}% (target: {self.TAKE_PROFIT}%)"
                )

            # Cut losses at -15%
            if pnl_pct < self.STOP_LOSS:
                return (
                    "SELL",
                    None,
                    f"Stop loss at {pnl_pct:.1f}% (limit: {self.STOP_LOSS}%)"
                )

            # Emergency exit if price too high (bubble risk)
            if price > self.BUBBLE_EXIT:
                return (
                    "SELL",
                    None,
                    f"Exit at {price:.2f}x (bubble risk, take gains)"
                )

        # Place sidebet conservatively (late game only)
        if sidebet is None and info['can_sidebet']:
            if tick > self.SIDEBET_TICK and balance >= self.SIDEBET_AMOUNT:
                return (
                    "SIDE",
                    self.SIDEBET_AMOUNT,
                    f"Sidebet at tick {tick} (late game rug risk)"
                )

        # Default: wait
        if position:
            pnl_pct = Decimal(str(position['current_pnl_percent']))
            return (
                "WAIT",
                None,
                f"Holding position (Price: {price:.2f}x, P&L: {pnl_pct:.1f}%)"
            )
        else:
            return (
                "WAIT",
                None,
                f"Waiting for entry (Price: {price:.2f}x too high)"
            )
