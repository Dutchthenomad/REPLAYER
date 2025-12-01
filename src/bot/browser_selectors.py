"""
Browser Selectors for Rugs.fun

PRODUCTION FIX (2025-11-30): Updated selectors to handle dynamic button text.

The original selectors used exact text matching like 'button:has-text("BUY")'
which fails when button text is actually "BUY+0.030 SOL" (price appended).

New selectors use:
1. Regex starts-with matching: text=/^BUY/i (primary)
2. Case-insensitive class matching: button[class*="buy" i]
3. Data attributes: [data-action="buy"]
4. Original exact text (fallback)

Centralized DOM selectors for browser automation.
Extracted from browser_executor.py during Phase 1 refactoring.
"""

# ============================================================================
# ACTION BUTTON SELECTORS - PRODUCTION FIX
# ============================================================================

# BUY button selectors - handles "BUY+0.030 SOL" dynamic text
BUY_BUTTON_SELECTORS = [
    # Primary: Regex starts-with (handles "BUY+0.030 SOL")
    'button >> text=/^BUY/i',
    # Case-insensitive class patterns
    'button[class*="buy" i]',
    'button[class*="Buy" i]',
    # Structural fallback (buy is typically first button in trade controls)
    '[class*="tradeControls"] button:first-of-type',
    '[class*="buttonsRow"] button:first-child',
    # Data attributes
    '[data-action="buy"]',
    '[data-testid="buy-button"]',
    # MUI specific patterns
    '.MuiButton-root[class*="buy" i]',
    # Original fallback
    'button:has-text("BUY")',
    'button:has-text("Buy")',
]

# SELL button selectors - handles "SELL-0.030 SOL" dynamic text
SELL_BUTTON_SELECTORS = [
    # Primary: Regex starts-with (handles "SELL-X.XXX SOL")
    'button >> text=/^SELL/i',
    # Case-insensitive class patterns
    'button[class*="sell" i]',
    'button[class*="Sell" i]',
    # Structural fallback (sell is typically second button in trade controls)
    '[class*="tradeControls"] button:nth-of-type(2)',
    '[class*="buttonsRow"] button:nth-child(2)',
    # Data attributes
    '[data-action="sell"]',
    '[data-testid="sell-button"]',
    # MUI specific patterns
    '.MuiButton-root[class*="sell" i]',
    # Original fallback
    'button:has-text("SELL")',
    'button:has-text("Sell")',
]

# SIDEBET button selectors - handles variations like "SIDE BET", "SIDEBET"
SIDEBET_BUTTON_SELECTORS = [
    # Primary: Regex starts-with
    'button >> text=/^SIDE/i',
    'button >> text=/^SIDEBET/i',
    # Case-insensitive class patterns
    'button[class*="side" i]',
    'button[class*="Side" i]',
    'button[class*="sidebet" i]',
    # Structural fallback (sidebet is typically third button)
    '[class*="tradeControls"] button:nth-of-type(3)',
    '[class*="buttonsRow"] button:nth-child(3)',
    # Data attributes
    '[data-action="sidebet"]',
    '[data-action="side"]',
    '[data-testid="sidebet-button"]',
    # Original fallback
    'button:has-text("SIDEBET")',
    'button:has-text("Sidebet")',
    'button:has-text("Side Bet")',
]

# ============================================================================
# BET AMOUNT INPUT SELECTORS
# ============================================================================

BET_AMOUNT_INPUT_SELECTORS = [
    'input[type="number"]',
    'input[placeholder*="amount"]',
    'input[class*="bet"]',
    '[data-input="bet-amount"]',
]

# ============================================================================
# INCREMENT BUTTON SELECTORS (Phase A.3)
# Updated to handle dynamic text variations
# ============================================================================

CLEAR_BUTTON_SELECTORS = [
    # Handle various X/clear button representations
    'button >> text=/^[X×✕✖]/i',
    'button:has-text("X")',
    'button[class*="clear" i]',
    'input[type="number"] ~ button',
    'button[title*="clear"]',
    '[data-action="clear-bet"]',
]

INCREMENT_001_SELECTORS = [
    'button >> text=/^\\+0\\.001/i',
    'button:has-text("+0.001")',
    'button:has-text("+ 0.001")',
    'button[data-increment="0.001"]',
]

INCREMENT_01_SELECTORS = [
    'button >> text=/^\\+0\\.01[^0]/i',  # Match +0.01 but not +0.001
    'button:has-text("+0.01")',
    'button:has-text("+ 0.01")',
    'button[data-increment="0.01"]',
]

INCREMENT_10_SELECTORS = [
    'button >> text=/^\\+0\\.1[^0]/i',  # Match +0.1 but not +0.01
    'button:has-text("+0.1")',
    'button:has-text("+ 0.1")',
    'button[data-increment="0.1"]',
]

INCREMENT_1_SELECTORS = [
    'button >> text=/^\\+1$/i',
    'button:has-text("+1")',
    'button:has-text("+ 1")',
    'button[data-increment="1"]',
]

HALF_BUTTON_SELECTORS = [
    'button >> text=/^1\\/2/i',
    'button >> text=/^½/i',
    'button:has-text("1/2")',
    'button:has-text("÷2")',
    'button:has-text("½")',
    'button:has-text("0.5x")',
    'button[data-action="half"]',
]

DOUBLE_BUTTON_SELECTORS = [
    'button >> text=/^[X×]2/i',
    'button:has-text("X2")',
    'button:has-text("×2")',
    'button:has-text("x2")',
    'button:has-text("2x")',
    'button[data-action="double"]',
]

MAX_BUTTON_SELECTORS = [
    'button >> text=/^MAX/i',
    'button >> text=/^ALL/i',
    'button:has-text("MAX")',
    'button:has-text("Max")',
    'button:has-text("All")',
    'button:has-text("ALL")',
    'button[data-action="max"]',
]

# ============================================================================
# PERCENTAGE BUTTON SELECTORS (Partial Sell)
# ============================================================================

PERCENTAGE_10_SELECTORS = [
    'button >> text=/^10%/i',
    'button:has-text("10%")',
    'button:has-text("10 %")',
    '[data-percentage="10%"]',
    'button[class*="pct-10"]',
]

PERCENTAGE_25_SELECTORS = [
    'button >> text=/^25%/i',
    'button:has-text("25%")',
    'button:has-text("25 %")',
    '[data-percentage="25%"]',
    'button[class*="pct-25"]',
]

PERCENTAGE_50_SELECTORS = [
    'button >> text=/^50%/i',
    'button:has-text("50%")',
    'button:has-text("50 %")',
    '[data-percentage="50%"]',
    'button[class*="pct-50"]',
]

PERCENTAGE_100_SELECTORS = [
    'button >> text=/^100%/i',
    'button >> text=/^ALL/i',
    'button:has-text("100%")',
    'button:has-text("100 %")',
    'button:has-text("ALL")',
    '[data-percentage="100%"]',
    'button[class*="pct-100"]',
]

# ============================================================================
# STATE READING SELECTORS
# ============================================================================

BALANCE_SELECTORS = [
    'text=/Balance.*([0-9.]+)\\s*SOL/i',
    '[data-balance]',
    '.balance',
    'span:has-text("SOL")',
]

POSITION_SELECTORS = [
    '[data-position]',
    '.position',
    'text=/Position.*([0-9.]+)x/i',
]

# ============================================================================
# SELECTOR MAP (for programmatic access)
# ============================================================================

INCREMENT_SELECTOR_MAP = {
    'X': CLEAR_BUTTON_SELECTORS,
    '+0.001': INCREMENT_001_SELECTORS,
    '+0.01': INCREMENT_01_SELECTORS,
    '+0.1': INCREMENT_10_SELECTORS,
    '+1': INCREMENT_1_SELECTORS,
    '1/2': HALF_BUTTON_SELECTORS,
    'X2': DOUBLE_BUTTON_SELECTORS,
    'MAX': MAX_BUTTON_SELECTORS,
}

PERCENTAGE_SELECTOR_MAP = {
    0.1: PERCENTAGE_10_SELECTORS,
    0.25: PERCENTAGE_25_SELECTORS,
    0.5: PERCENTAGE_50_SELECTORS,
    1.0: PERCENTAGE_100_SELECTORS,
}

PERCENTAGE_TEXT_MAP = {
    0.1: "10%",
    0.25: "25%",
    0.5: "50%",
    1.0: "100%",
}


# ============================================================================
# SELECTOR UTILITIES (Phase 9.3 Production Fix)
# ============================================================================

def get_button_text_patterns(button_type: str) -> list:
    """
    Get text patterns for a button type.
    Used by multi-strategy selector system in browser_bridge.py.
    """
    patterns = {
        'BUY': ['BUY', 'Buy', 'buy'],
        'SELL': ['SELL', 'Sell', 'sell'],
        'SIDEBET': ['SIDEBET', 'SIDE', 'Side', 'sidebet', 'side'],
        'X': ['×', '✕', 'X', 'x', '✖'],
        '+0.001': ['+0.001', '+ 0.001'],
        '+0.01': ['+0.01', '+ 0.01'],
        '+0.1': ['+0.1', '+ 0.1'],
        '+1': ['+1', '+ 1'],
        '1/2': ['1/2', '½', '0.5x', 'Half'],
        'X2': ['X2', 'x2', '2x', '2X', 'Double'],
        'MAX': ['MAX', 'Max', 'max', 'ALL'],
        '10%': ['10%', '10 %'],
        '25%': ['25%', '25 %'],
        '50%': ['50%', '50 %'],
        '100%': ['100%', '100 %', 'ALL'],
    }
    return patterns.get(button_type, [button_type])


def get_class_patterns(button_type: str) -> list:
    """
    Get class name patterns for fallback matching.
    """
    patterns = {
        'BUY': ['buy', 'purchase', 'long', 'bid'],
        'SELL': ['sell', 'exit', 'short', 'ask'],
        'SIDEBET': ['side', 'sidebet', 'hedge', 'insurance'],
    }
    return patterns.get(button_type, [button_type.lower()])
