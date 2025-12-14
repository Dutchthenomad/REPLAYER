# Demo Recording Analysis - Bot System Foundation
**Date**: December 9, 2025
**Status**: Initial Analysis Complete
**Purpose**: Foundation for core bot player framework design

---

## Executive Summary

Analysis of 1 complete human demo session (15 actions, 4 complete trades) reveals clear behavioral patterns that will inform the bot framework design. The human player achieved a **75% win rate** with **+30% average wins** vs **-3% average loss**, demonstrating effective risk management.

---

## Data Inventory

| Dataset | Count | Content |
|---------|-------|---------|
| Game recordings (ticks only) | 2,491 | Price, tick, phase per game |
| Demo sessions | 2 | 1 empty, 1 with 15 actions |
| Complete trades analyzed | 4 | Full entry→exit cycles |

**Sample Size Limitation**: Only 1 game with actions. Need 20-30 games for robust pattern extraction.

---

## Observed Behavioral Patterns

### Action Distribution

| Category | Count | % | Description |
|----------|-------|---|-------------|
| TRADE_BUY | 6 | 40% | Position entries |
| TRADE_SELL | 4 | 27% | Position exits |
| BET_INCREMENT | 3 | 20% | Bet size adjustments |
| TRADE_SIDEBET | 2 | 13% | 5x multiplier bets |

### Trade Performance

| Metric | Value |
|--------|-------|
| Win rate | 75% (3/4) |
| Average win | +30.0% |
| Average loss | -3.1% |
| Risk/Reward ratio | 9.7:1 |
| Average hold time | 27 ticks |
| Session P&L | +0.7% |

### Trade-by-Trade Breakdown

| # | Entry | Exit | P&L | Hold | Result | Notes |
|---|-------|------|-----|------|--------|-------|
| 1 | 1.00x | 1.40x | +40% | 26t | WIN | Presale entry, averaged up |
| 2 | 1.94x | 2.45x | +26% | 17t | WIN | Quick momentum trade |
| 3 | 1.53x | 1.48x | -3% | 52t | LOSS | Held too long, cut loss |
| 4 | 1.30x | 1.61x | +24% | 14t | WIN | Clean entry/exit |

---

## Decision Logic Patterns

### 1. Entry Decisions (TRADE_BUY)

**Pattern A: Presale Entry**
```
IF phase == PRESALE AND price == 1.0x
THEN BUY (game start position)
```

**Pattern B: Momentum Entry**
```
IF price > 1.5x AND no_position AND price_trending_up
THEN BUY (momentum chase)
```

**Pattern C: Dip Entry**
```
IF price < recent_high * 0.7 AND no_position
THEN BUY (buy the dip)
```

**Pattern D: Averaging**
```
IF has_position AND position_pnl > 0 AND price_rising
THEN BUY more (pyramid up)
```

### 2. Exit Decisions (TRADE_SELL)

**Pattern A: Profit Target**
```
IF position_pnl >= 25%
THEN SELL (take profit)
```

**Pattern B: Stop Loss**
```
IF position_pnl < 0 AND hold_time > 50 ticks
THEN SELL (cut losses)
```

### 3. Bet Size Management (BET_INCREMENT)

**Pattern A: Initial Setup**
```
IF bet_amount == 0 AND want_to_trade
THEN +0.001 (minimum viable bet)
```

**Pattern B: Confidence Scaling**
```
IF position_profitable AND want_to_add
THEN X2 (double down)
```

**Pattern C: Risk Reduction**
```
IF just_closed_position OR uncertain
THEN 1/2 (reduce exposure)
```

### 4. Sidebet Timing (TRADE_SIDEBET)

**Pattern A: Early Bet**
```
IF phase == PRESALE AND price == 1.0x
THEN SIDEBET (maximum time for 5x target)
```

**Pattern B: Momentum Bet**
```
IF price > 2x AND trending_up
THEN SIDEBET (riding momentum)
```

---

## State Feature Requirements

### Core State Vector (Minimum for Bot)

| Feature | Type | Source | Description |
|---------|------|--------|-------------|
| `current_tick` | int | GameState | Game time |
| `current_price` | Decimal | GameState | Current multiplier |
| `phase` | enum | GameState | PRESALE, ACTIVE, RUGGED |
| `balance` | Decimal | GameState | Available SOL |
| `bet_amount` | Decimal | TradingController | Current bet size |
| `has_position` | bool | Position | Position exists |
| `position_size` | Decimal | Position | Position amount |
| `position_entry` | Decimal | Position | Entry price |
| `position_pnl_pct` | float | Calculated | Unrealized P&L % |
| `position_hold_ticks` | int | Calculated | Ticks since entry |
| `has_sidebet` | bool | Sidebet | Sidebet active |
| `sidebet_amount` | Decimal | Sidebet | Sidebet size |

### Derived Features (For RL)

| Feature | Calculation | Relevance |
|---------|-------------|-----------|
| `price_velocity` | price[t] - price[t-5] / 5 | Momentum direction |
| `price_volatility` | stddev(price[-20:]) | Risk assessment |
| `drawdown_from_peak` | (peak - current) / peak | Rug warning |
| `risk_exposure` | position_value / balance | Position sizing |
| `time_in_game_pct` | tick / median_game_length | Temporal risk |
| `sidebet_time_remaining` | 40 - (tick - sidebet_tick) | Sidebet urgency |

---

## Action Space Definition

### Discrete Action Space (for RL)

```python
class BotAction(Enum):
    # No-op
    HOLD = 0

    # Trading
    BUY = 1
    SELL_25 = 2
    SELL_50 = 3
    SELL_100 = 4

    # Bet management
    BET_CLEAR = 5      # X button
    BET_UP_SMALL = 6   # +0.001
    BET_UP_MED = 7     # +0.01
    BET_UP_LARGE = 8   # +0.1
    BET_HALF = 9       # 1/2
    BET_DOUBLE = 10    # X2
    BET_MAX = 11       # MAX

    # Sidebet
    SIDEBET = 12
```

### Action Constraints

| Constraint | Rule |
|------------|------|
| BUY requires | bet_amount > 0, balance >= bet_amount |
| SELL requires | has_position |
| SIDEBET requires | bet_amount > 0, balance >= bet_amount, not already has_sidebet |
| BET_DOUBLE requires | balance >= bet_amount * 2 |
| BET_MAX requires | balance > 0 |

---

## Bot Framework Architecture (Draft)

### Three Execution Modes

```
┌─────────────────────────────────────────────────────────────────┐
│                     CORE BOT LOGIC                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ State       │───▶│ Model       │───▶│ Action      │         │
│  │ Observer    │    │ Inference   │    │ Executor    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ REPLAY MODE │    │TRAINING MODE│    │  LIVE MODE  │
│             │    │             │    │             │
│ Read state  │    │ Read state  │    │ Read state  │
│ from JSONL  │    │ from Gym    │    │ from WS     │
│             │    │             │    │             │
│ Visualize   │    │ Fast epoch  │    │ Execute via │
│ in UI       │    │ training    │    │ CDP browser │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Mode Details

| Mode | State Source | Execution | Speed | Purpose |
|------|--------------|-----------|-------|---------|
| REPLAY | JSONL files | Display only | 1-10x real | Demo, analysis |
| TRAINING | Gym env | Internal | 1000x+ real | Model training |
| LIVE | WebSocket | CDP browser | 1x real | Production |

### Key Interfaces

```python
class BotStateObserver(Protocol):
    """Observe game state from any source."""
    def get_current_state(self) -> BotState: ...
    def get_price_history(self, n: int) -> list[Decimal]: ...

class BotActionExecutor(Protocol):
    """Execute actions in any environment."""
    def execute(self, action: BotAction) -> ActionResult: ...
    def get_available_actions(self) -> list[BotAction]: ...

class BotModel(Protocol):
    """Predict actions from state."""
    def predict(self, state: BotState) -> BotAction: ...
    def predict_proba(self, state: BotState) -> dict[BotAction, float]: ...
```

---

## Translation to RL Training

### Observation Space (79 features from rugs-rl-bot)

The existing rugs-rl-bot uses 79 observation features. These should be extended to capture human behavioral patterns:

```python
observation_space = {
    # Game state (existing)
    'tick': int,
    'price': float,
    'phase': int,  # 0=PRESALE, 1=ACTIVE, 2=RUGGED

    # Position state (existing)
    'has_position': bool,
    'position_size': float,
    'position_entry': float,
    'position_pnl_pct': float,
    'position_hold_ticks': int,

    # NEW: Human-inspired features
    'recent_action': int,  # Last action taken (for momentum)
    'ticks_since_action': int,  # Time since last action
    'trade_count_this_game': int,  # Activity level
    'win_streak': int,  # Confidence indicator
    'loss_streak': int,  # Caution indicator

    # Technical features
    'price_history': float[20],  # Last 20 prices
    'price_velocity': float,
    'price_volatility': float,
    'drawdown_from_peak': float,

    # Sidebet state
    'has_sidebet': bool,
    'sidebet_ticks_remaining': int,
}
```

### Reward Signal Design

Based on observed human behavior, the reward function should:

1. **Reward profit-taking at +25%+** (matches observed pattern)
2. **Penalize holding losing positions >50 ticks** (observed stop-loss behavior)
3. **Reward quick wins** (average win held 19 ticks vs loss held 52)
4. **Neutral on sidebets** (speculative, outcome-based reward only)

---

## Next Steps

1. **Pressure Test Recording** - Play 3-5 games, verify data quality
2. **Record 20-30 Demo Games** - Build robust behavioral dataset
3. **Extract Decision Patterns** - Statistical analysis of state→action mappings
4. **Design Bot State Machine** - Formalize decision logic
5. **Build Behavioral Cloning Model** - Train initial player piano model
6. **Integrate with REPLAYER UI** - Visual validation of bot behavior
7. **RL Feature Engineering** - Design high-quality observation features
8. **RL Training Loop** - Gymnasium environment with refined rewards

---

## Questions for Human Expert (After Demo Sessions)

1. When do you decide to enter presale vs wait for active gameplay?
2. What triggers your decision to take profit (price target, time, gut feel)?
3. How do you decide bet size (fixed, scaled to confidence, other)?
4. What makes you cut a losing position vs hold longer?
5. When do you use sidebets (every game, specific conditions, never)?

---

*Analysis based on 1 demo game (15 actions). Sample size insufficient for robust conclusions. Pending 20-30 game dataset for validation.*
