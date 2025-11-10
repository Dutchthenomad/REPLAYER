# Rugs.fun Game Rules Specification

**Version**: 1.0
**Date**: 2025-11-03
**Status**: Validated via Replay Viewer Implementation
**Source**: game_ui_replay_viewer.py + BotInterface testing

---

## 🎯 Purpose

This document provides the **authoritative specification** for Rugs.fun game mechanics. All values here have been **validated against actual game recordings** and the replay viewer implementation.

**Critical**: Any bot training MUST use these exact parameters. No assumptions allowed.

---

## 💰 Financial Constants

### Wallet & Betting
```python
INITIAL_BALANCE = 0.100 SOL          # Starting wallet balance
MIN_BET = 0.001 SOL                  # Minimum bet size
MAX_BET = 1.0 SOL                    # Maximum bet size
```

**Validation Status**: ✅ Confirmed via `game_ui_replay_viewer.py` lines 29-32

### Side Bet Mechanics
```python
SIDEBET_MULTIPLIER = 5.0             # Payout multiplier (5:1)
SIDEBET_WINDOW = 40 ticks            # Must rug within 40 ticks to win
SIDEBET_COOLDOWN = 5 ticks           # Must wait 5 ticks after resolution
```

**Validation Status**: ✅ Confirmed via `game_ui_replay_viewer.py` lines 35-37

**Side Bet Rules**:
- Side bet wins if rug occurs **within 40 ticks** of placement
- Payout is **5x the bet amount** (e.g., 0.001 SOL bet → 0.005 SOL payout)
- After a side bet resolves (win or loss), **5 tick cooldown** before next bet
- Only **one active side bet** allowed at a time
- Side bet is **lost** (no refund) if rug occurs after 40 ticks

### Rug Event Liquidation
```python
RUG_LIQUIDATION_PRICE = 0.02         # Price drops to 0.02 on rug
```

**Validation Status**: ✅ Confirmed via `game_ui_replay_viewer.py` line 38

**Rug Rules**:
- All active trading positions are **liquidated at 0.02 price**
- This represents **100% loss** of position value
- Side bets are resolved based on tick placement (see above)

---

## 🎮 Game Phases

Rugs.fun games progress through distinct phases. **Phase determines what actions are valid.**

### Phase Enum
```python
COOLDOWN           # Waiting for next game to start
PRESALE            # Early phase, can buy at 1.0x
GAME_ACTIVATION    # Transition phase
ACTIVE_GAMEPLAY    # Main gameplay, price fluctuates
RUG_EVENT          # Game ended, price crashed to 0.02
RUG_EVENT_1        # Alternative rug event marker
UNKNOWN            # Unrecognized phase
```

**Validation Status**: ✅ Confirmed via `game_ui_replay_viewer.py` lines 90-98

### Phase Action Rules

| Phase | BUY | SELL | SIDE BET |
|-------|-----|------|----------|
| **COOLDOWN** | ❌ No | ❌ No | ❌ No |
| **PRESALE** | ✅ Yes | ✅ Yes (if position) | ✅ Yes |
| **GAME_ACTIVATION** | ✅ Yes | ✅ Yes (if position) | ✅ Yes |
| **ACTIVE_GAMEPLAY** | ✅ Yes | ✅ Yes (if position) | ✅ Yes |
| **RUG_EVENT** | ❌ No | ❌ No | ❌ No |
| **RUG_EVENT_1** | ❌ No | ❌ No | ❌ No |

**Validation Status**: ✅ Confirmed via BotInterface implementation (lines 347, 434, 643-644, 654)

**Key Insight**: In COOLDOWN and RUG phases, **NO actions** are allowed except WAIT.

---

## 📊 Trading Mechanics

### Position Management

**Multiple Positions Allowed**: ✅ YES
**Validation Status**: ✅ Confirmed via `execute_buy()` lines 842-857

When you buy while holding a position:
- New buy **adds to existing position**
- Entry price becomes **weighted average**:
  ```python
  new_entry_price = (old_amount * old_price + new_amount * new_price) / total_amount
  ```

**Example**:
```
Position 1: Buy 0.005 SOL @ 1.0x
Position 2: Buy 0.003 SOL @ 2.0x
Merged: 0.008 SOL @ 1.375x weighted average
```

### Selling Mechanics

**Partial Sells**: ❌ NOT IMPLEMENTED in current viewer
**Full Sell Only**: ✅ YES

When you sell:
- **100% of position** is sold
- P&L calculated as: `position_amount * (exit_price / entry_price - 1)`
- Wallet receives: `position_amount + pnl`

**Validation Status**: ✅ Confirmed via `execute_sell()` lines 886-938

### P&L Calculation

```python
price_change = current_price / entry_price - 1
pnl_sol = position_amount * price_change
pnl_percent = price_change * 100
```

**Example**:
- Entry: 0.01 SOL @ 1.0x
- Exit: @ 2.5x
- Price change: 2.5 / 1.0 - 1 = +1.5 (+150%)
- P&L: 0.01 * 1.5 = +0.015 SOL

**Validation Status**: ✅ Confirmed via `execute_sell()` and `_get_position_info()` lines 904-906, 508-510

---

## 🎲 Game Tick Structure

Each game tick contains the following fields:

```python
{
    'timestamp': str,       # ISO 8601 timestamp
    'game_id': str,         # Unique game identifier
    'tick': int,            # Tick number (starts at 0)
    'price': float,         # Current multiplier (e.g. 1.5 = 1.5x)
    'phase': str,           # Current phase (see Phase Enum)
    'active': bool,         # Is game currently active
    'rugged': bool,         # Has rug occurred
    'cooldown_timer': int,  # Milliseconds until next game (in COOLDOWN)
    'trade_count': int      # Total trades in game so far
}
```

**Validation Status**: ✅ Confirmed via `GameTick` dataclass lines 125-154

---

## 🚫 Action Validation Rules

These are the **exact validation rules** implemented in BotInterface:

### BUY Action
```
✅ Allowed if:
   - Phase is NOT [COOLDOWN, RUG_EVENT, RUG_EVENT_1]
   - Amount >= MIN_BET (0.001 SOL)
   - Amount <= MAX_BET (1.0 SOL)
   - Amount <= wallet_balance

❌ Rejected if:
   - Wrong phase → "Cannot buy in {phase} phase"
   - Amount < MIN_BET → "Amount below minimum"
   - Amount > MAX_BET → "Amount exceeds maximum"
   - Amount > balance → "Insufficient balance"
   - Amount is None → "BUY requires amount parameter"
```

**Validation Status**: ✅ Confirmed via `_execute_buy()` lines 322-377

### SELL Action
```
✅ Allowed if:
   - Active position exists
   - Position status is "active"

❌ Rejected if:
   - No position → "No active position to sell"
```

**Validation Status**: ✅ Confirmed via `_execute_sell()` lines 379-407

### SIDE BET Action
```
✅ Allowed if:
   - Phase is NOT [COOLDOWN, RUG_EVENT, RUG_EVENT_1]
   - Amount >= MIN_BET (0.001 SOL)
   - Amount <= MAX_BET (1.0 SOL)
   - Amount <= wallet_balance
   - No active sidebet
   - NOT in cooldown period (5 ticks after last resolution)

❌ Rejected if:
   - Wrong phase → "Cannot place sidebet in {phase} phase"
   - Amount issues → (same as BUY)
   - Active sidebet → "Sidebet already active"
   - In cooldown → "Sidebet cooldown: {N} ticks remaining"
   - Amount is None → "SIDE requires amount parameter"
```

**Validation Status**: ✅ Confirmed via `_execute_sidebet()` lines 409-476

### WAIT Action
```
✅ Always allowed
   - Returns success with 0.0 reward
   - No state changes
```

**Validation Status**: ✅ Confirmed via `_execute_wait()` lines 306-320

---

## 🎁 Reward Structure (BotInterface)

When bot executes actions, it receives immediate rewards:

### Financial Rewards
```python
BUY action:
  reward = -(amount)              # Negative (spent SOL)

SELL action:
  reward = position_amount + pnl  # P&L from trade

SIDE BET action:
  reward = -(amount)              # Negative (bet placed)

  On resolution (if within 40 ticks):
    reward = amount * 5.0         # 5x payout

WAIT action:
  reward = 0.0                    # Neutral

Invalid action:
  reward = -0.05                  # Small penalty
```

**Validation Status**: ✅ Confirmed via `bot_execute_action()` return values lines 263-304

**Note**: These are **immediate rewards** from the BotInterface. The actual RL training reward function may differ (see Phase 3.6C reward calculator).

---

## 📋 Observation Space (BotInterface)

When bot requests observation, it receives:

```python
{
    'current_state': {
        'price': float,           # Current multiplier
        'tick': int,              # Current tick number
        'phase': str,             # Current phase name
        'active': bool,           # Is game active
        'rugged': bool,           # Has rug occurred
        'cooldown_timer': int,    # Cooldown milliseconds
        'trade_count': int        # Total trades in game
    },
    'wallet': {
        'balance': float,         # Current SOL balance
        'starting_balance': float,# Session start balance
        'session_pnl': float      # Cumulative P&L
    },
    'position': {                 # None if no position
        'entry_price': float,
        'amount': float,
        'entry_tick': int,
        'current_pnl_sol': float,
        'current_pnl_percent': float
    },
    'sidebet': {                  # None if no sidebet
        'amount': float,
        'placed_tick': int,
        'placed_price': float,
        'ticks_remaining': int,
        'potential_payout': float
    },
    'game_info': {
        'game_id': str,
        'total_ticks': int,
        'progress': float         # 0.0 to 1.0
    }
}
```

**Validation Status**: ✅ Confirmed via `bot_get_observation()` lines 546-604

---

## 🔍 Valid Actions Query (BotInterface)

Bot can query what actions are currently valid:

```python
{
    'valid_actions': List[str],      # e.g. ['WAIT', 'BUY', 'SIDE']
    'game_loaded': bool,
    'game_ended': bool,
    'can_buy': bool,
    'can_sell': bool,
    'can_sidebet': bool,
    'constraints': {
        'min_bet': float,
        'max_bet': float,
        'sidebet_multiplier': float,
        'sidebet_window_ticks': int,
        'sidebet_cooldown_ticks': int
    }
}
```

**Validation Status**: ✅ Confirmed via `bot_get_info()` lines 606-680

---

## ⚠️ Critical Discoveries

### 1. Weighted Average Entry Price
**Misconception**: Each buy creates separate positions
**Reality**: Buys merge into single position with weighted average entry

**Impact on RL**: Bot needs to understand that averaging down (buying at lower prices) or averaging up affects P&L calculations.

### 2. Side Bet Resolution Timing
**Misconception**: Side bet wins if you predict rug correctly
**Reality**: Must rug **within exactly 40 ticks** of bet placement

**Impact on RL**: Timing is critical. Placing sidebet at tick 10 vs tick 30 changes win probability dramatically.

### 3. Phase-Based Action Restrictions
**Misconception**: Can always buy/sell if have balance/position
**Reality**: Phase strictly gates all actions

**Impact on RL**: Bot must learn to recognize phases and not waste actions on invalid attempts.

### 4. Cooldown Period Enforcement
**Misconception**: Can place sidebets freely
**Reality**: 5 tick mandatory cooldown after each resolution

**Impact on RL**: Can't spam sidebets. Must plan timing carefully.

---

## 🧪 Validation History

| Date | Checkpoint | What Was Validated | Status |
|------|-----------|-------------------|--------|
| 2025-11-03 | 1A | BotInterface action execution | ✅ PASS |
| 2025-11-03 | 1A | Observation space structure | ✅ PASS |
| 2025-11-03 | 1A | Game phase action rules | ✅ PASS |
| 2025-11-03 | 1A | Side bet mechanics | ✅ PASS |
| 2025-11-03 | 1A | Position averaging | ✅ PASS |

---

## 📝 Open Questions (To Be Validated)

1. **Multi-game episodes**: How does bankroll persist across games?
2. **Pattern exploitation**: Do post-max-payout patterns actually exist?
3. **Historical context**: What features from past games influence current game?
4. **Meta-context**: Is there treasury adaptation across game sequences?

These will be validated in future checkpoints when we integrate with Phase 3.6 Gymnasium environment.

---

## 🚨 Rules for Future Development

1. **Never assume a parameter value** - Always verify against this document
2. **Update this document** when new mechanics are discovered
3. **Run verification scripts** before deploying any bot with real SOL
4. **Document discrepancies** if replay behavior differs from live game
5. **Version this document** when making changes

---

**Last Updated**: 2025-11-03
**Next Review**: After Checkpoint 1B (Observation Space Builder)
