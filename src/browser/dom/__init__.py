"""
DOM Utilities Module

Utilities for interacting with browser DOM elements.
"""

from browser.dom.selectors import (
    BUY_BUTTON_SELECTORS,
    SELL_BUTTON_SELECTORS,
    SIDEBET_BUTTON_SELECTORS,
    BET_AMOUNT_INPUT_SELECTORS,
    INCREMENT_SELECTOR_MAP,
    PERCENTAGE_TEXT_MAP,
    BALANCE_SELECTORS,
    POSITION_SELECTORS,
)

from browser.dom.timing import ExecutionTiming, TimingMetrics

__all__ = [
    'BUY_BUTTON_SELECTORS',
    'SELL_BUTTON_SELECTORS',
    'SIDEBET_BUTTON_SELECTORS',
    'BET_AMOUNT_INPUT_SELECTORS',
    'INCREMENT_SELECTOR_MAP',
    'PERCENTAGE_TEXT_MAP',
    'BALANCE_SELECTORS',
    'POSITION_SELECTORS',
    'ExecutionTiming',
    'TimingMetrics',
]
