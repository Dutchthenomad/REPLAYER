# Button Selectors for Rugs.fun Browser Automation

Last updated: 2025-11-23 (Phase 9.3)

## Overview

This document describes the button selectors discovered from the rugs.fun game interface.
The BrowserBridge uses JavaScript to find and click these buttons by their text content.

**Total Buttons**: 15 (16 if you count Connect, which we don't wire)

## Button Classes (from page enumeration)

### Increment Buttons (8 buttons)
| Button | Text | Class Pattern | REPLAYER Handler |
|--------|------|---------------|-----------------|
| +0.001 | `+0.001` | `_controlBtn_73g5s_23` | `increment_bet_amount(0.001)` |
| +0.01  | `+0.01`  | `_controlBtn_73g5s_23` | `increment_bet_amount(0.01)` |
| +0.1   | `+0.1`   | `_controlBtn_73g5s_23` | `increment_bet_amount(0.1)` |
| +1     | `+1`     | `_controlBtn_73g5s_23` | `increment_bet_amount(1)` |
| 1/2    | `1/2`    | `_controlBtn_73g5s_23` | `half_bet_amount()` |
| X2     | `X2`     | `_controlBtn_73g5s_23` | `double_bet_amount()` |
| MAX    | `MAX`    | `_controlBtn_73g5s_23 _uppercase_73g5s_230` | `max_bet_amount()` |
| X (Clear) | `X`   | `_clearButton_1lj20_77` | `clear_bet_amount()` |

### Percentage Buttons (4 buttons)
| Button | Text | Class Pattern | REPLAYER Handler |
|--------|------|---------------|-----------------|
| 10%    | `10%`  | `_percentageBtn_1hwtp_139` | `set_sell_percentage(0.1)` |
| 25%    | `25%`  | `_percentageBtn_1hwtp_139` | `set_sell_percentage(0.25)` |
| 50%    | `50%`  | `_percentageBtn_1hwtp_139` | `set_sell_percentage(0.5)` |
| 100%   | `100%` | `_percentageBtn_1hwtp_139 _active_1hwtp_60` | `set_sell_percentage(1.0)` |

### Action Buttons (3 buttons)
| Button | Text | Class Pattern | REPLAYER Handler |
|--------|------|---------------|-----------------|
| BUY    | `BUY` or `BUY+X.XXX SOL` | `_actionButton_1himf_1 _buy_1himf_114` | `execute_buy()` |
| SELL   | `SELL` | `_actionButton_1himf_1 _sell_1himf_156` | `execute_sell()` |
| SIDEBET| `SIDEBET` | TBD | `execute_sidebet()` |

### Sidebet Button Note
- Requires clicking "open" button first (once per session)
- Text: `SIDEBET` (after sidebet panel is opened)
- Once opened, stays open unless closed

## Click Strategy (browser_bridge.py)

The `_do_click()` method in BrowserBridge uses this priority:

1. **Text-based selection** (primary method):
   - **Exact text match** - `textContent.trim() === searchText`
   - **StartsWith match** - For buttons like `BUY+0.030 SOL` that change dynamically
   - **Contains match** - Only for multi-char buttons (avoids X matching X2)
   - **Visibility filter** - Only clicks visible buttons (improved to handle `position:fixed`)

2. **XPath fallback** (if text-based fails):
   - Used for BUY, SELL, SIDEBET if text matching doesn't work
   - XPaths updated: 2025-11-24
   - Increment/percentage buttons use text matching only (more reliable)

## Architecture: Browser-First Philosophy

**Key Principle**: Browser clicks happen FIRST, before any REPLAYER validation.

When connected to the browser, REPLAYER's internal state is NOT authoritative.
The user can spam buy on 0.001 every 250ms if they want - the browser allows it.

Code pattern:
```python
def execute_buy(self):
    # Browser click FIRST - regardless of REPLAYER state
    self.browser_bridge.on_buy_clicked()

    # Then REPLAYER's internal logic (may show error, but browser got the click)
    amount = self.get_bet_amount()
    if amount is None:
        return  # Browser click already sent
    # ... rest of logic
```

## Known Issues & Fixes

1. **X button matching X2** - Fixed by prioritizing exact match and skipping `contains` for single-char buttons
2. **BUY button text changes** - Dynamic text like `BUY+0.030 SOL` - handled by `startsWith` fallback
3. **Validation blocking browser** - Fixed by moving browser calls before validation

## Files

- `src/bot/browser_bridge.py` - BrowserBridge class, button clicking logic
- `browser_automation/cdp_browser_manager.py` - CDP connection to Chrome
- `src/ui/main_window.py` - UI handlers that call browser bridge methods
