"""
Aggressive trading strategy
"""

from decimal import Decimal
from typing import Tuple, Optional, Dict, Any

from .base import TradingStrategy


class AggressiveStrategy(TradingStrategy):
    """
    Aggressive trading strategy

    Rules:
    - Buy more often at higher prices (< 3.0x)
    - Hold for bigger profits (+50%)
    - Wider stop loss (-30%)
    - Higher risk tolerance
    """

    def __init__(self):
        super().__init__()
        self.BUY_THRESHOLD = Decimal('3.0')
        self.TAKE_PROFIT = Decimal('50')  # 50%
        self.STOP_LOSS = Decimal('-30')    # -30%
        self.BUY_AMOUNT = Decimal('0.010')
        self.SIDEBET_AMOUNT = Decimal('0.003')

    def decide(
        self,
        observation: Dict[str, Any],
        info: Dict[str, Any]
    ) -> Tuple[str, Optional[Decimal], str]:
        """Make aggressive trading decision"""

        if not observation:
            return self._validate_action(
                "WAIT",
                None,
                "No game state available",
                info.get("valid_actions", [])
            )

        # Extract state
        state = observation['current_state']
        position = observation['position']
        sidebet = observation['sidebet']
        wallet = observation['wallet']

        price = Decimal(str(state['price']))
        tick = state['tick']
        balance = Decimal(str(wallet['balance']))
        valid_actions = info.get("valid_actions", [])

        def decide_action(action: str, amount: Optional[Decimal], reasoning: str):
            return self._validate_action(action, amount, reasoning, valid_actions)

        # Buy aggressively if no position
        if position is None and info['can_buy']:
            if price < self.BUY_THRESHOLD and balance >= self.BUY_AMOUNT:
                return decide_action(
                    "BUY",
                    self.BUY_AMOUNT,
                    f"Aggressive entry at {price:.2f}x"
                )

        # Have position - hold for bigger gains
        if position is not None and info['can_sell']:
            pnl_pct = Decimal(str(position['current_pnl_percent']))

            # Big profit target
            if pnl_pct > self.TAKE_PROFIT:
                return decide_action(
                    "SELL",
                    None,
                    f"Big profit exit at +{pnl_pct:.1f}%"
                )

            # Wider stop loss
            if pnl_pct < self.STOP_LOSS:
                return decide_action(
                    "SELL",
                    None,
                    f"Stop loss at {pnl_pct:.1f}%"
                )

        # Place sidebets when available
        if sidebet is None and info['can_sidebet']:
            if balance >= self.SIDEBET_AMOUNT:
                return decide_action(
                    "SIDE",
                    self.SIDEBET_AMOUNT,
                    f"Sidebet at tick {tick}"
                )

        # Default: wait
        if position:
            pnl_pct = Decimal(str(position['current_pnl_percent']))
            return decide_action(
                "WAIT",
                None,
                f"Holding for bigger gains (P&L: {pnl_pct:.1f}%)"
            )
        else:
            return decide_action(
                "WAIT",
                None,
                "Waiting for entry"
            )
