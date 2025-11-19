# Phase B: Foundational Bot Strategy

**Goal**: Create a simple, robust trading strategy based on empirical analysis findings

**Status**: Planning
**Date**: 2025-11-18

---

## Overview

Phase B creates a **foundational trading strategy** that:
- Uses insights from empirical analysis (Phase 3 from rugs-rl-bot project)
- Serves as baseline for RL bot training
- Demonstrates incremental clicking in action
- Provides interpretable, rule-based trading logic

---

## Design Philosophy

### 1. **Evidence-Based**
Use findings from empirical analysis:
- Sweet spot entries (25-50x)
- Temporal risk model (69-tick safe window)
- Optimal hold times (48-60 ticks)
- Dynamic profit targets

### 2. **Simple & Interpretable**
- Clear, understandable rules
- No complex math or ML
- Easy to debug and validate
- Human-readable reasoning

### 3. **Conservative & Robust**
- Prioritize capital preservation
- Avoid bankruptcy
- 30-50% stop losses (not 10%)
- Exit before median rug time (138 ticks)

### 4. **Incremental Clicking Integration**
- Uses `build_amount_incrementally()` for all bets
- Demonstrates Phase A features in action
- Realistic timing patterns for RL observation

---

## Empirical Analysis Findings (Reference)

From `/home/nomad/Desktop/REPLAYER/analyze_trading_patterns.py` and `analyze_position_duration.py`:

### Key Insights

1. **100% Rug Rate**: All games eventually rug → exit timing is EVERYTHING

2. **Sweet Spot (25-50x)**:
   - 75% success rate
   - 186-427% median returns
   - Best risk/reward ratio

3. **Temporal Risk Model**:
   ```python
   TEMPORAL_RUG_PROB = {
       50: 0.234,   # 23.4% rugged by tick 50
       100: 0.386,  # 38.6% rugged by tick 100
       138: 0.500,  # 50% rugged by tick 138 (median)
       200: 0.644,  # 64.4% rugged by tick 200
       300: 0.793   # 79.3% rugged by tick 300
   }
   ```

4. **Safe Window**: First 69 ticks are relatively safe (< 30% rug risk)

5. **Optimal Hold Times**:
   - 1-10x: 65 ticks (61% success)
   - 25-50x: 48-60 ticks (75% success) ⭐ SWEET SPOT
   - 100x+: 71 ticks (36% success)

6. **Stop Losses**: Should be 30-50%, not 10%
   - Average drawdowns: 8-25%
   - Recovery rate: 85-91%

7. **Dynamic Profit Targets**:
   - 1-10x → 25% profit
   - 25-50x → 100-200% profit ⭐ SWEET SPOT
   - 100x+ → 10-25% profit (bubble risk)

---

## FoundationalBot Strategy Design

### Core Principles

1. **Entry**: Buy at sweet spot (25-50x)
2. **Exit**: Use temporal model + profit targets
3. **Risk**: 30-50% stop loss
4. **Timing**: Exit before median rug (138 ticks)

### Strategy Rules

#### Entry Logic

```python
def should_enter(price, tick, balance):
    """
    Enter at sweet spot (25-50x) during safe window
    """
    # Sweet spot range
    if price < Decimal('25.0') or price > Decimal('50.0'):
        return False

    # Safe window (first 69 ticks)
    if tick > 69:
        return False  # Too risky, 30%+ rug probability

    # Sufficient balance
    if balance < Decimal('0.005'):
        return False

    return True
```

#### Exit Logic

```python
def should_exit(position, price, tick, entry_tick):
    """
    Exit based on profit target, stop loss, or temporal risk
    """
    pnl_pct = position['current_pnl_percent']
    ticks_held = tick - entry_tick

    # Profit target (100-200% for sweet spot)
    if pnl_pct >= 100:
        return True, "Take profit at +100%"

    # Stop loss (30% for sweet spot)
    if pnl_pct <= -30:
        return True, "Stop loss at -30%"

    # Temporal risk: Exit before median rug (138 ticks)
    if tick >= 138:
        return True, "Exit before median rug time"

    # Optimal hold time exceeded (60 ticks for sweet spot)
    if ticks_held >= 60:
        return True, "Optimal hold time reached (60 ticks)"

    # Default: hold
    return False, f"Holding (P&L: {pnl_pct:.1f}%, Tick: {tick})"
```

#### Sidebet Logic

```python
def should_sidebet(tick, balance, sidebet_active):
    """
    Place sidebet during danger zone (104-138 ticks)
    """
    if sidebet_active:
        return False

    # Danger zone (P50-P75 of rug probability)
    if tick < 104 or tick > 138:
        return False

    # Sufficient balance
    if balance < Decimal('0.002'):
        return False

    return True
```

---

## Implementation Plan

### Phase B.1: Design Architecture ✅

**Tasks**:
- [x] Review empirical analysis findings
- [x] Design strategy rules
- [x] Define entry/exit logic
- [x] Plan sidebet strategy

**Output**: This planning document

---

### Phase B.2: Implement FoundationalBot Class

**Location**: `src/bot/strategies/foundational.py`

**Class Structure**:
```python
class FoundationalStrategy(TradingStrategy):
    """
    Foundational trading strategy based on empirical analysis

    Entry: Sweet spot (25-50x) during safe window (tick < 69)
    Exit: Profit target (100%), stop loss (-30%), or temporal risk
    Sidebet: Danger zone (104-138 ticks)
    """

    def __init__(self):
        super().__init__()

        # Entry parameters (sweet spot)
        self.ENTRY_PRICE_MIN = Decimal('25.0')
        self.ENTRY_PRICE_MAX = Decimal('50.0')
        self.SAFE_WINDOW_TICKS = 69  # < 30% rug risk

        # Exit parameters
        self.PROFIT_TARGET = Decimal('100')  # 100% for sweet spot
        self.STOP_LOSS = Decimal('-30')       # -30% (not -10%!)
        self.MAX_HOLD_TICKS = 60              # Optimal for sweet spot
        self.MEDIAN_RUG_TICK = 138            # Exit before this

        # Sidebet parameters (danger zone)
        self.SIDEBET_TICK_MIN = 104  # P50 rug probability
        self.SIDEBET_TICK_MAX = 138  # Median rug time

        # Amounts
        self.BUY_AMOUNT = Decimal('0.005')
        self.SIDEBET_AMOUNT = Decimal('0.002')

        # State tracking
        self.entry_tick = None

    def decide(self, observation, info):
        # Implementation here
        pass

    def reset(self):
        super().reset()
        self.entry_tick = None
```

**Key Methods**:
- `_should_enter()` - Sweet spot + safe window check
- `_should_exit()` - Profit/loss/temporal logic
- `_should_sidebet()` - Danger zone check
- `decide()` - Main decision logic

**Integration**:
- Register in `bot/strategies/__init__.py`
- Add to strategy dropdown in UI
- Test with incremental clicking

---

### Phase B.3: Test and Validate

**Unit Tests** (`tests/test_bot/test_strategy_foundational.py`):
- Test entry logic (sweet spot, safe window)
- Test exit logic (profit, loss, temporal)
- Test sidebet logic (danger zone)
- Test edge cases (no balance, already in position)

**Integration Tests**:
- Run bot with foundational strategy
- Verify incremental clicking works
- Check reasoning output
- Validate decision flow

**Validation Metrics**:
- Win rate (target: > 60%)
- Average P&L (target: > 50%)
- Rug avoidance (target: > 80%)
- Bankruptcy rate (target: < 5%)

---

### Phase B.4: Documentation

**Files to Create**:
1. `FOUNDATIONAL_STRATEGY.md` - Strategy documentation
2. `EMPIRICAL_FOUNDATIONS.md` - Analysis findings reference
3. Update `CLAUDE.md` with Phase B completion

**Documentation Sections**:
- Strategy overview
- Entry/exit rules
- Empirical justification
- Performance expectations
- Usage instructions

---

## Expected Outcomes

### Performance Targets

**Conservative Estimates**:
- Win rate: 60-70% (vs 75% in analysis due to execution delays)
- Average P&L: 50-80% (vs 100-200% median due to early exits)
- Rug avoidance: 80-85% (exit before median rug time)
- Bankruptcy rate: < 5% (30% stop loss prevents large losses)

**Success Criteria**:
✅ No bankruptcies in 100-game test
✅ Positive cumulative P&L
✅ Incremental clicking works correctly
✅ Reasoning output is clear and accurate

---

## Integration with Existing Systems

### Phase A (Incremental Clicking)
- Uses `bot_ui.build_amount_incrementally()` for all bets
- Demonstrates visual feedback in action
- Creates realistic timing patterns

### Phase 8 (UI-Layer Execution)
- Works in both BACKEND and UI_LAYER modes
- Same logic, different execution paths
- Prepares for live browser automation

### Future RL Training
- Serves as baseline strategy
- Expert trajectories from foundational bot
- Comparison benchmark for RL performance

---

## Timeline

**Phase B.1**: Design (1-2 hours) - ✅ **CURRENT**
**Phase B.2**: Implementation (2-3 hours)
**Phase B.3**: Testing (1-2 hours)
**Phase B.4**: Documentation (1 hour)

**Total**: 5-8 hours

---

## Next Steps

1. ✅ Review this plan
2. ⏭️ Implement `FoundationalStrategy` class
3. ⏭️ Write unit tests
4. ⏭️ Run integration tests (100 games)
5. ⏭️ Document findings
6. ⏭️ Move to Phase C (if applicable) or production deployment

---

## Questions to Consider

1. **Should we add position sizing?**
   - Current: Fixed 0.005 SOL bet
   - Alternative: % of balance (e.g., 5%)

2. **Should we use ML sidebet predictor?**
   - Current: Rule-based (danger zone)
   - Alternative: SidebetPredictor (38.1% win rate, 754% ROI)

3. **Should we add partial sells?**
   - Current: All-or-nothing exit
   - Alternative: 50% at profit target, 50% rides

4. **Should we track strategy performance metrics?**
   - Current: None
   - Alternative: Win rate, P&L, rug avoidance stats

**Recommendation**: Start simple (current design), add complexity later if needed.

---

**Status**: Phase B.1 Complete - Ready for Implementation
**Next**: Phase B.2 - Implement FoundationalStrategy class
**Date**: 2025-11-18
