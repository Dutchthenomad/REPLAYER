"""
Browser Selectors for Rugs.fun

Centralized DOM selectors for browser automation.
Extracted from browser_executor.py during Phase 1 refactoring.

Each selector list provides multiple fallback options for robustness.
"""

# ============================================================================
# ACTION BUTTON SELECTORS
# ============================================================================

BUY_BUTTON_SELECTORS = [
    'button:has-text("BUY")',
    'button:has-text("Buy")',
    'button[class*="buy"]',
    '[data-action="buy"]',
]

SELL_BUTTON_SELECTORS = [
    'button:has-text("SELL")',
    'button:has-text("Sell")',
    'button[class*="sell"]',
    '[data-action="sell"]',
]

SIDEBET_BUTTON_SELECTORS = [
    'button:has-text("SIDEBET")',
    'button:has-text("Sidebet")',
    'button:has-text("Side Bet")',
    'button[class*="sidebet"]',
    '[data-action="sidebet"]',
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
# ============================================================================

CLEAR_BUTTON_SELECTORS = [
    'button:has-text("X")',
    'button[title*="clear"]',
    '[data-action="clear-bet"]',
]

INCREMENT_001_SELECTORS = [
    'button:has-text("+0.001")',
    'button[data-increment="0.001"]',
]

INCREMENT_01_SELECTORS = [
    'button:has-text("+0.01")',
    'button[data-increment="0.01"]',
]

INCREMENT_10_SELECTORS = [
    'button:has-text("+0.1")',
    'button[data-increment="0.1"]',
]

INCREMENT_1_SELECTORS = [
    'button:has-text("+1")',
    'button[data-increment="1"]',
]

HALF_BUTTON_SELECTORS = [
    'button:has-text("1/2")',
    'button:has-text("÷2")',
    'button[data-action="half"]',
]

DOUBLE_BUTTON_SELECTORS = [
    'button:has-text("X2")',
    'button:has-text("×2")',
    'button[data-action="double"]',
]

MAX_BUTTON_SELECTORS = [
    'button:has-text("MAX")',
    'button:has-text("All")',
    'button[data-action="max"]',
]

# ============================================================================
# PERCENTAGE BUTTON SELECTORS (Partial Sell)
# ============================================================================

PERCENTAGE_10_SELECTORS = [
    'button:has-text("10%")',
    '[data-percentage="10%"]',
    'button[class*="pct-10"]',
]

PERCENTAGE_25_SELECTORS = [
    'button:has-text("25%")',
    '[data-percentage="25%"]',
    'button[class*="pct-25"]',
]

PERCENTAGE_50_SELECTORS = [
    'button:has-text("50%")',
    '[data-percentage="50%"]',
    'button[class*="pct-50"]',
]

PERCENTAGE_100_SELECTORS = [
    'button:has-text("100%")',
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
