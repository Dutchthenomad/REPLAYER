"""
Decimal Utilities Module - Consistent handling of Decimal operations
Ensures precision and prevents float/Decimal mixing issues
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, InvalidOperation
from typing import Union, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

# Type alias for numeric types
Numeric = Union[Decimal, float, str, int]

__all__ = [
    "to_decimal",
    "to_float",
    "safe_float",
    "round_sol",
    "round_price",
    "round_percent",
    "floor_sol",
    "safe_divide",
    "percentage_change",
    "calculate_pnl",
    "is_valid_amount",
    "clamp",
    "format_sol",
    "format_price",
    "format_percent",
    "format_pnl",
    "decimal_equal",
    "is_positive",
    "is_negative",
    "is_zero",
    "sum_decimals",
    "average_decimals",
    "ZERO",
    "ONE",
    "HUNDRED",
    "THOUSAND",
    "PERCENT_10",
    "PERCENT_25",
    "PERCENT_50",
    "PERCENT_75",
    "SOL_PRECISION",
    "MIN_SOL_AMOUNT",
    "MAX_PERCENTAGE",
]

_QUANTIZER_CACHE = {
    4: Decimal("0.0001"),
    6: Decimal("0.000001"),
    9: Decimal("0.000000001"),
}


def _get_quantizer(precision: int) -> Decimal:
    """Return cached quantizer for given precision."""
    if precision not in _QUANTIZER_CACHE:
        _QUANTIZER_CACHE[precision] = Decimal(10) ** -precision
    return _QUANTIZER_CACHE[precision]


def _validate_precision(precision: int) -> int:
    if precision < 0:
        raise ValueError(f"Precision must be non-negative, got {precision}")
    return precision


# ========================================================================
# CONVERSION UTILITIES
# ========================================================================

def to_decimal(
    value: Numeric,
    default: Optional[Decimal] = None,
    round_places: Optional[int] = None
) -> Decimal:
    """
    Safely convert value to Decimal
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        round_places: Optional rounding precision after conversion
        
    Returns:
        Decimal value
        
    Raises:
        ValueError if conversion fails and no default provided
    """
    if isinstance(value, Decimal):
        return value
    
    try:
        result = Decimal(str(value))
        if round_places is not None:
            precision = _validate_precision(round_places)
            quantizer = _get_quantizer(precision)
            result = result.quantize(quantizer, rounding=ROUND_HALF_UP)
        return result
    except (InvalidOperation, ValueError, TypeError) as e:
        if default is not None:
            logger.warning(f"Failed to convert {value} to Decimal: {e}, using default {default}")
            return default
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def to_float(value: Numeric) -> float:
    """
    Convert Decimal to float for display/JSON
    
    Args:
        value: Value to convert
        
    Returns:
        Float value
    """
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def safe_float(value: Optional[Numeric], default: float = 0.0) -> float:
    """
    Safely convert to float with default
    
    Args:
        value: Value to convert
        default: Default if None or conversion fails
        
    Returns:
        Float value
    """
    if value is None:
        return default
    
    try:
        return to_float(value)
    except (ValueError, TypeError):
        return default


# ========================================================================
# ROUNDING UTILITIES
# ========================================================================

def round_sol(value: Decimal, precision: int = 4) -> Decimal:
    """
    Round to SOL precision (default 4 decimal places)
    
    Args:
        value: Value to round
        precision: Decimal places (default 4)
        
    Returns:
        Rounded Decimal
    """
    _validate_precision(precision)
    quantizer = _get_quantizer(precision)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def round_price(value: Decimal, precision: int = 6) -> Decimal:
    """
    Round price multiplier (default 6 decimal places)
    
    Args:
        value: Price to round
        precision: Decimal places (default 6)
        
    Returns:
        Rounded price
    """
    _validate_precision(precision)
    quantizer = _get_quantizer(precision)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def round_percent(value: Decimal, precision: int = 2) -> Decimal:
    """
    Round percentage (default 2 decimal places)
    
    Args:
        value: Percentage to round
        precision: Decimal places (default 2)
        
    Returns:
        Rounded percentage
    """
    _validate_precision(precision)
    quantizer = _get_quantizer(precision)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def floor_sol(value: Decimal, precision: int = 4) -> Decimal:
    """
    Floor to SOL precision (round down)
    
    Args:
        value: Value to floor
        precision: Decimal places
        
    Returns:
        Floored Decimal
    """
    _validate_precision(precision)
    quantizer = _get_quantizer(precision)
    return value.quantize(quantizer, rounding=ROUND_DOWN)


# ========================================================================
# ARITHMETIC UTILITIES
# ========================================================================

def safe_divide(
    numerator: Numeric,
    denominator: Numeric,
    default: Decimal = Decimal('0')
) -> Decimal:
    """
    Safe division with zero check
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Result of division or default
    """
    num = to_decimal(numerator)
    den = to_decimal(denominator)
    
    if den == 0:
        logger.debug(f"Division by zero: {num} / 0, returning {default}")
        return default
    
    return num / den


def percentage_change(
    old_value: Numeric,
    new_value: Numeric,
    precision: int = 2
) -> Decimal:
    """
    Calculate percentage change
    
    Args:
        old_value: Original value
        new_value: New value
        precision: Decimal places for result
        
    Returns:
        Percentage change (e.g., 10.5 for 10.5% increase)
    """
    old = to_decimal(old_value)
    new = to_decimal(new_value)
    
    if old == 0:
        if new == 0:
            return Decimal('0')
        logger.debug("Percentage change from zero; returning sentinel max percentage")
        return MAX_PERCENTAGE if new > 0 else -MAX_PERCENTAGE
    
    change = ((new - old) / old) * 100
    return round_percent(change, precision)


def calculate_pnl(
    entry_price: Numeric,
    exit_price: Numeric,
    amount: Numeric
) -> Tuple[Decimal, Decimal]:
    """
    Calculate P&L for a trade
    
    Args:
        entry_price: Entry price multiplier
        exit_price: Exit price multiplier
        amount: Position size in SOL
        
    Returns:
        Tuple of (pnl_sol, pnl_percent)
    """
    entry = to_decimal(entry_price)
    exit = to_decimal(exit_price)
    amt = to_decimal(amount)

    if amt <= 0:
        raise ValueError(f"Amount must be positive, got {amt}")
    if entry <= 0:
        raise ValueError(f"Entry price must be positive, got {entry}")
    if exit < 0:
        raise ValueError(f"Exit price cannot be negative, got {exit}")
    
    # For price multiplier trading:
    # If you buy at 2x and sell at 4x, you've doubled your money (100% gain)
    price_ratio = safe_divide(exit, entry, Decimal('1'))
    pnl_percent = (price_ratio - 1) * 100
    
    # P&L in SOL
    pnl_sol = amt * (price_ratio - 1)
    
    return round_sol(pnl_sol), round_percent(pnl_percent)


# ========================================================================
# VALIDATION UTILITIES
# ========================================================================

def is_valid_amount(value: Any, allow_zero: bool = False) -> bool:
    """
    Check if value is a valid amount
    
    Args:
        value: Value to check
        allow_zero: Whether zero is valid
        
    Returns:
        True if valid amount
    """
    try:
        decimal_value = to_decimal(value)
        
        if decimal_value.is_nan() or decimal_value.is_infinite():
            return False
        
        if allow_zero:
            return decimal_value >= 0
        else:
            return decimal_value > 0
            
    except (ValueError, TypeError):
        return False


def clamp(
    value: Numeric,
    min_value: Numeric,
    max_value: Numeric
) -> Decimal:
    """
    Clamp value between min and max
    
    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value
        
    Returns:
        Clamped value
    """
    val = to_decimal(value)
    min_val = to_decimal(min_value)
    max_val = to_decimal(max_value)
    
    return max(min_val, min(val, max_val))


# ========================================================================
# FORMATTING UTILITIES
# ========================================================================

def format_sol(value: Numeric, precision: int = 4) -> str:
    """
    Format SOL amount for display
    
    Args:
        value: Amount in SOL
        precision: Decimal places
        
    Returns:
        Formatted string (e.g., "1.2345 SOL")
    """
    decimal_value = to_decimal(value)
    rounded = round_sol(decimal_value, precision)
    return f"{rounded:.{precision}f} SOL"


def format_price(value: Numeric, precision: int = 2) -> str:
    """
    Format price multiplier for display
    
    Args:
        value: Price multiplier
        precision: Decimal places
        
    Returns:
        Formatted string (e.g., "2.50x")
    """
    decimal_value = to_decimal(value)
    
    if decimal_value >= 100:
        return f"{decimal_value:.0f}x"
    elif decimal_value >= 10:
        return f"{decimal_value:.1f}x"
    else:
        return f"{decimal_value:.{precision}f}x"


def format_percent(value: Numeric, precision: int = 2) -> str:
    """
    Format percentage for display
    
    Args:
        value: Percentage value
        precision: Decimal places
        
    Returns:
        Formatted string (e.g., "+10.50%")
    """
    decimal_value = to_decimal(value)
    rounded = round_percent(decimal_value, precision)
    
    sign = "+" if rounded > 0 else ""
    return f"{sign}{rounded:.{precision}f}%"


def format_pnl(pnl_sol: Numeric, pnl_percent: Numeric) -> str:
    """
    Format P&L for display
    
    Args:
        pnl_sol: P&L in SOL
        pnl_percent: P&L percentage
        
    Returns:
        Formatted string (e.g., "+0.1234 SOL (+12.34%)")
    """
    sol_str = format_sol(pnl_sol)
    pct_str = format_percent(pnl_percent)
    
    # Add sign to SOL if positive
    if to_decimal(pnl_sol) > 0:
        sol_str = "+" + sol_str
    
    return f"{sol_str} ({pct_str})"


# ========================================================================
# COMPARISON UTILITIES
# ========================================================================

def decimal_equal(
    a: Numeric,
    b: Numeric,
    tolerance: Decimal = Decimal('0.0001')
) -> bool:
    """
    Check if two decimals are approximately equal
    
    Args:
        a: First value
        b: Second value
        tolerance: Maximum difference allowed
        
    Returns:
        True if approximately equal
    """
    val_a = to_decimal(a)
    val_b = to_decimal(b)
    
    return abs(val_a - val_b) <= tolerance


def is_positive(value: Numeric) -> bool:
    """Check if value is positive"""
    return to_decimal(value) > 0


def is_negative(value: Numeric) -> bool:
    """Check if value is negative"""
    return to_decimal(value) < 0


def is_zero(value: Numeric, tolerance: Decimal = Decimal('0.0001')) -> bool:
    """Check if value is approximately zero"""
    return abs(to_decimal(value)) <= tolerance


# ========================================================================
# AGGREGATION UTILITIES
# ========================================================================

def sum_decimals(values: list) -> Decimal:
    """
    Sum a list of values as Decimals
    
    Args:
        values: List of numeric values
        
    Returns:
        Sum as Decimal
    """
    total = Decimal('0')
    for value in values:
        if value is not None:
            total += to_decimal(value)
    return total


def average_decimals(values: list) -> Optional[Decimal]:
    """
    Calculate average of values as Decimal
    
    Args:
        values: List of numeric values
        
    Returns:
        Average as Decimal or None if empty
    """
    if not values:
        return None
    
    valid_values = [v for v in values if v is not None]
    if not valid_values:
        return None
    
    total = sum_decimals(valid_values)
    count = Decimal(str(len(valid_values)))
    
    return total / count


# ========================================================================
# CONSTANTS
# ========================================================================

# Common Decimal constants
ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')
THOUSAND = Decimal('1000')

# Common percentages
PERCENT_10 = Decimal('0.1')
PERCENT_25 = Decimal('0.25')
PERCENT_50 = Decimal('0.5')
PERCENT_75 = Decimal('0.75')

# SOL precision
SOL_PRECISION = 9  # Solana has 9 decimal places
MIN_SOL_AMOUNT = Decimal('0.000000001')  # 1 lamport
MAX_PERCENTAGE = Decimal('999999999')
