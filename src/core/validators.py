"""
Input validation functions

AUDIT FIX: Enhanced with edge case handling and negative value checks
"""

from decimal import Decimal
from typing import Tuple, Optional
from models import GameTick
from config import config


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


def validate_bet_amount(
    amount: Decimal,
    balance: Decimal,
    action: str = "BET"
) -> Tuple[bool, Optional[str]]:
    """
    Validate bet amount is within bounds and affordable

    AUDIT FIX: Added checks for negative, zero, extreme, NaN, and Infinity values

    Args:
        amount: Bet amount in SOL
        balance: Current wallet balance
        action: Action type (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "error message") if invalid
    """
    # AUDIT FIX: Check for NaN or Infinity (critical - prevents all downstream bugs)
    if not amount.is_finite():
        return False, f"Invalid {action} amount: {amount} (must be finite)"

    # AUDIT FIX: Check balance for NaN or Infinity
    if not balance.is_finite():
        return False, f"Invalid balance: {balance} (must be finite)"

    # AUDIT FIX: Check for negative or zero amounts
    if amount <= 0:
        return False, f"{action} amount {amount} below minimum (must be positive)"

    # AUDIT FIX: Check for extreme values (prevent overflow)
    if amount > Decimal('1000000'):
        return False, f"{action} amount {amount} is unreasonably large"

    # Check minimum
    if amount < config.FINANCIAL['min_bet']:
        return False, f"{action} amount {amount} below minimum {config.FINANCIAL['min_bet']} SOL"

    # Check maximum
    if amount > config.FINANCIAL['max_bet']:
        return False, f"{action} amount {amount} exceeds maximum {config.FINANCIAL['max_bet']} SOL"

    # AUDIT FIX: Check for negative balance
    if balance < 0:
        return False, f"Invalid balance state: {balance}"

    # Check balance
    if amount > balance:
        return False, f"Insufficient balance: have {balance:.4f}, need {amount} SOL"

    return True, None


def validate_trading_allowed(
    tick: GameTick,
    action: str = "TRADE"
) -> Tuple[bool, Optional[str]]:
    """
    Validate trading is allowed in current game state

    Args:
        tick: Current game tick
        action: Action type (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if allowed
        - (False, "error message") if not allowed
    """
    # PRESALE phase allows one BUY and one SIDEBET before game starts
    # These positions activate when the game begins
    if tick.phase == "PRESALE":
        return True, None

    # Check if game is active (required for non-PRESALE phases)
    if not tick.active:
        return False, f"{action} not allowed: game not active yet"

    # Check if rugged
    if tick.rugged:
        return False, f"{action} not allowed: game has been rugged"

    # Check phase
    if tick.phase in config.GAME_RULES['blocked_phases']:
        return False, f"{action} not allowed in {tick.phase} phase"

    return True, None


def validate_buy(
    amount: Decimal,
    balance: Decimal,
    tick: GameTick,
    has_position: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate BUY action

    Args:
        amount: Amount to buy
        balance: Current balance
        tick: Current game tick
        has_position: Whether player has an active position

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Allow adding to an active position (DCA) — only block when trading disabled
    is_valid, error = validate_trading_allowed(tick, "BUY")
    if not is_valid:
        return False, error

    # Check bet amount
    is_valid, error = validate_bet_amount(amount, balance, "BUY")
    if not is_valid:
        return False, error

    return True, None


def validate_sell(
    has_position: bool,
    tick: Optional[GameTick] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate SELL action

    Args:
        has_position: Whether player has an active position
        tick: Current game tick (optional, for phase check)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not has_position:
        return False, "No active position to sell"

    # Phase check optional (can sell anytime if have position)
    return True, None


def validate_sidebet(
    amount: Decimal,
    balance: Decimal,
    tick: GameTick,
    has_active_sidebet: bool,
    last_sidebet_resolved_tick: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate SIDEBET action

    Args:
        amount: Sidebet amount
        balance: Current balance
        tick: Current game tick
        has_active_sidebet: Whether player has active sidebet
        last_sidebet_resolved_tick: Tick when last sidebet was resolved

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check trading allowed
    is_valid, error = validate_trading_allowed(tick, "SIDEBET")
    if not is_valid:
        return False, error

    # Check bet amount
    is_valid, error = validate_bet_amount(amount, balance, "SIDEBET")
    if not is_valid:
        return False, error

    # Check for active sidebet
    if has_active_sidebet:
        return False, "Sidebet already active"

    # Check cooldown
    if last_sidebet_resolved_tick is not None:
        ticks_since_resolution = tick.tick - last_sidebet_resolved_tick
        if ticks_since_resolution < config.GAME_RULES['sidebet_cooldown_ticks']:
            remaining = config.GAME_RULES['sidebet_cooldown_ticks'] - ticks_since_resolution
            return False, f"Sidebet cooldown: {remaining} ticks remaining"

    return True, None
