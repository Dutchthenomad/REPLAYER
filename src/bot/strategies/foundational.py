"""
Foundational Trading Strategy - Phase B

Evidence-based strategy using empirical analysis findings:
- Sweet spot entries (25-50x)
- Temporal risk model (69-tick safe window)
- Optimal hold times (48-60 ticks)
- Dynamic profit targets (100% for sweet spot)
- Conservative stop losses (30%, not 10%)

Design Philosophy:
- Simple and interpretable
- Conservative and robust
- Evidence-based parameters
- Serves as baseline for RL training
"""

from decimal import Decimal
from typing import Tuple, Optional, Dict, Any

from .base import TradingStrategy


class FoundationalStrategy(TradingStrategy):
    """
    Foundational trading strategy based on empirical analysis

    Entry Rules:
    - Price: 25-50x (sweet spot with 75% success rate)
    - Timing: Tick < 69 (safe window, < 30% rug risk)
    - Balance: At least 0.005 SOL available

    Exit Rules:
    - Profit target: +100% (median return for sweet spot)
    - Stop loss: -30% (accounts for 8-25% drawdowns)
    - Max hold time: 60 ticks (optimal for sweet spot)
    - Temporal limit: Exit before tick 138 (median rug time)

    Sidebet Rules:
    - Timing: Ticks 104-138 (danger zone, P50-P75 rug probability)
    - Amount: 0.002 SOL (conservative)

    Performance Expectations:
    - Win rate: 60-70%
    - Average P&L: 50-80%
    - Rug avoidance: 80-85%
    - Bankruptcy: < 5%
    """

    def __init__(self):
        super().__init__()

        # Entry parameters (sweet spot from empirical analysis)
        self.ENTRY_PRICE_MIN = Decimal('25.0')  # Sweet spot lower bound
        self.ENTRY_PRICE_MAX = Decimal('50.0')  # Sweet spot upper bound
        self.SAFE_WINDOW_TICKS = 69             # < 30% rug risk

        # Exit parameters (based on optimal hold times)
        self.PROFIT_TARGET = Decimal('100')     # 100% (median return for sweet spot)
        self.STOP_LOSS = Decimal('-30')          # -30% (NOT -10%!)
        self.MAX_HOLD_TICKS = 60                 # Optimal for sweet spot (48-60 ticks)
        self.MEDIAN_RUG_TICK = 138               # Exit before median rug time

        # Sidebet parameters (danger zone)
        self.SIDEBET_TICK_MIN = 104  # P50 rug probability (danger zone start)
        self.SIDEBET_TICK_MAX = 138  # Median rug time (danger zone end)

        # Amounts
        self.BUY_AMOUNT = Decimal('0.005')     # Fixed position size
        self.SIDEBET_AMOUNT = Decimal('0.002')  # Conservative sidebet

        # State tracking
        self.entry_tick = None  # Track when we entered position

    def decide(
        self,
        observation: Dict[str, Any],
        info: Dict[str, Any]
    ) -> Tuple[str, Optional[Decimal], str]:
        """
        Make trading decision based on empirical analysis rules

        Args:
            observation: Current game state (from bot_get_observation)
            info: Valid actions and constraints (from bot_get_info)

        Returns:
            Tuple of (action_type, amount, reasoning)
        """

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

        # =====================================================================
        # POSITION MANAGEMENT (Priority 1: Exit existing positions)
        # =====================================================================

        if position is not None and info['can_sell']:
            pnl_pct = Decimal(str(position['current_pnl_percent']))
            ticks_held = tick - self.entry_tick if self.entry_tick else 0

            # Profit target: +100% (sweet spot median return)
            if pnl_pct >= self.PROFIT_TARGET:
                return decide_action(
                    "SELL",
                    None,
                    f"✅ Take profit at +{pnl_pct:.1f}% (target: {self.PROFIT_TARGET}%)"
                )

            # Stop loss: -30% (conservative, prevents large losses)
            if pnl_pct <= self.STOP_LOSS:
                return decide_action(
                    "SELL",
                    None,
                    f"🛑 Stop loss at {pnl_pct:.1f}% (limit: {self.STOP_LOSS}%)"
                )

            # Temporal risk: Exit before median rug time (tick 138)
            if tick >= self.MEDIAN_RUG_TICK:
                return decide_action(
                    "SELL",
                    None,
                    f"⏰ Exit at tick {tick} (median rug time: {self.MEDIAN_RUG_TICK})"
                )

            # Optimal hold time: 60 ticks for sweet spot
            if ticks_held >= self.MAX_HOLD_TICKS:
                return decide_action(
                    "SELL",
                    None,
                    f"⌛ Hold time exceeded ({ticks_held} ticks, optimal: {self.MAX_HOLD_TICKS})"
                )

        # =====================================================================
        # ENTRY LOGIC (Priority 2: Enter at sweet spot during safe window)
        # =====================================================================

        if position is None and info['can_buy']:
            if self._should_enter(price, tick, balance):
                self.entry_tick = tick  # Track entry time
                return decide_action(
                    "BUY",
                    self.BUY_AMOUNT,
                    f"🎯 Enter sweet spot at {price:.1f}x (tick {tick}, safe window: < {self.SAFE_WINDOW_TICKS})"
                )

        # =====================================================================
        # SIDEBET LOGIC (Priority 3: Place sidebet during danger zone)
        # =====================================================================

        if sidebet is None and info['can_sidebet']:
            if self._should_sidebet(tick, balance):
                return decide_action(
                    "SIDE",
                    self.SIDEBET_AMOUNT,
                    f"💰 Sidebet at tick {tick} (danger zone: {self.SIDEBET_TICK_MIN}-{self.SIDEBET_TICK_MAX})"
                )

        # =====================================================================
        # WAIT (Default: Hold position or wait for entry)
        # =====================================================================

        if position:
            pnl_pct = Decimal(str(position['current_pnl_percent']))
            ticks_held = tick - self.entry_tick if self.entry_tick else 0
            return decide_action(
                "WAIT",
                None,
                f"⏳ Holding (Price: {price:.1f}x, P&L: {pnl_pct:.1f}%, Held: {ticks_held} ticks)"
            )
        else:
            if price < self.ENTRY_PRICE_MIN:
                return decide_action(
                    "WAIT",
                    None,
                    f"⏳ Price too low ({price:.1f}x, need: {self.ENTRY_PRICE_MIN}x+)"
                )
            elif price > self.ENTRY_PRICE_MAX:
                return decide_action(
                    "WAIT",
                    None,
                    f"⏳ Price too high ({price:.1f}x, max: {self.ENTRY_PRICE_MAX}x)"
                )
            elif tick >= self.SAFE_WINDOW_TICKS:
                return decide_action(
                    "WAIT",
                    None,
                    f"⏳ Past safe window (tick {tick}, limit: {self.SAFE_WINDOW_TICKS})"
                )
            else:
                return decide_action(
                    "WAIT",
                    None,
                    f"⏳ Waiting for sweet spot (Price: {price:.1f}x, Tick: {tick})"
                )

    def _should_enter(self, price: Decimal, tick: int, balance: Decimal) -> bool:
        """
        Check if we should enter a position

        Entry Criteria:
        1. Price in sweet spot range (25-50x)
        2. Within safe window (tick < 69)
        3. Sufficient balance (>= 0.005 SOL)

        Args:
            price: Current price multiplier
            tick: Current game tick
            balance: Available SOL balance

        Returns:
            True if should enter, False otherwise
        """

        # Sweet spot range check
        if price < self.ENTRY_PRICE_MIN or price > self.ENTRY_PRICE_MAX:
            return False

        # Safe window check (first 69 ticks have < 30% rug risk)
        if tick >= self.SAFE_WINDOW_TICKS:
            return False

        # Balance check
        if balance < self.BUY_AMOUNT:
            return False

        return True

    def _should_sidebet(self, tick: int, balance: Decimal) -> bool:
        """
        Check if we should place a sidebet

        Sidebet Criteria:
        1. Tick in danger zone (104-138)
        2. Sufficient balance (>= 0.002 SOL)

        Args:
            tick: Current game tick
            balance: Available SOL balance

        Returns:
            True if should place sidebet, False otherwise
        """

        # Danger zone check (P50-P75 rug probability)
        if tick < self.SIDEBET_TICK_MIN or tick > self.SIDEBET_TICK_MAX:
            return False

        # Balance check
        if balance < self.SIDEBET_AMOUNT:
            return False

        return True

    def reset(self):
        """Reset strategy state (called on new game)"""
        super().reset()
        self.entry_tick = None

    def __str__(self):
        return "Foundational (Evidence-Based)"
