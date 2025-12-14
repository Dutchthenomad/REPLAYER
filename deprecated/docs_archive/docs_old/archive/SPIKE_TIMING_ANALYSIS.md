# Volatility Spike Timing & False Positive Analysis

**Analysis Date**: November 7, 2025
**Dataset**: 448 games analyzed (435 rugged, 13 safe)
**Method**: Rolling volatility ratio with 2.0x threshold detection

---

## Executive Summary

### ✅ **Good News: Plenty of Reaction Time**
- **Mean: 166 ticks** between spike detection and rug
- **96.4% of games** give ≥11 ticks to react (highly actionable)
- Only 2.0% of rugs happen too fast (≤5 ticks)

### ❌ **Bad News: High False Positives**
- **76.9% of safe games** trigger spike alerts (10/13 games)
- **Multiple spikes common**: Average 4.04 spikes per rugged game
- **67.4% of rugs** have 2+ spikes before final rug

### 🎯 **Critical Insight**
**The first spike is NOT the "exit now" signal!**
- Games typically spike multiple times before rugging
- Safe games also experience volatility spikes during normal play
- Need strategy to distinguish "normal spike" from "death spike"

---

## ⏱️ Part 1: Reaction Time Analysis

### Detection Success Rate
| Category | Count | Percentage |
|----------|-------|------------|
| **Spike detected BEFORE rug** | 305 / 435 | **70.1%** ✅ |
| Spike detected AT/AFTER rug | 128 / 435 | 29.4% |
| No spike detected | 2 / 435 | 0.5% |

**Key Finding**: 70.1% of rugs have advance warning via spike detection.

### Reaction Time Available

| Metric | Ticks | Interpretation |
|--------|-------|----------------|
| **Mean** | 166.1 ticks | ~2-3 minutes at 1 tick/sec |
| **Median** | 107.0 ticks | ~1.5-2 minutes |
| **Minimum** | 1 tick | ⚠️ Instant rug (rare) |
| **Maximum** | 872 ticks | 🎉 14+ minutes warning |

### Reaction Time Distribution

```
≤ 1 tick (instant):        1 game  (  0.3%) ⚠️  Too fast to react
2-5 ticks (very short):    5 games (  1.6%) ⚠️  Difficult to execute
6-10 ticks (short):        5 games (  1.6%) ⚠️  Challenging
11-20 ticks (moderate):   22 games (  7.2%) ✅ Actionable
> 20 ticks (long):       272 games ( 89.2%) ✅ Plenty of time
                         ---
ACTIONABLE (≥11 ticks): 294 games ( 96.4%)  ← CRITICAL STAT
```

### 💡 Reaction Time Insights

1. **Excellent actionability**: 96.4% of detected rugs give ≥11 ticks to react
2. **Mean 166 ticks** = ~2.5 minutes at typical game speed
3. **Only 2% too fast** to react (≤5 ticks)
4. **Bot has ample time** to close positions when spike detected

---

## 🚨 Part 2: False Positive Analysis

### Safe Game Spike Events

| Metric | Value |
|--------|-------|
| **Safe games with spikes** | 10 / 13 (76.9%) ❌ |
| **Safe games without spikes** | 3 / 13 (23.1%) |
| **Total spike events in safe games** | 45 events |
| **Average spikes per affected safe game** | 4.5 events |

### 🔴 **CRITICAL PROBLEM: 76.9% False Positive Rate**

**What this means:**
- If bot exits on first 2x spike, it will exit **77% of safe games early**
- These are games that continue successfully but experience volatility
- Bot would miss potential profits in 3 out of 4 safe games

### Examples of False Positives

| Game | Spikes | Max Ratio | Outcome |
|------|--------|-----------|---------|
| game_20251030_133436 | 1 | 2.12x | ✅ Safe |
| game_20251030_152205 | 3 | 4.18x | ✅ Safe |
| game_20251030_162056 | 3 | 2.46x | ✅ Safe |
| game_20251030_164913 | 1 | 2.33x | ✅ Safe |
| game_20251030_172049 | 3 | 3.10x | ✅ Safe |

**Key Observation**: Safe games can spike to 2-4x volatility and continue normally!

---

## 📈 Part 3: Multiple Spike Pattern

### Spike Frequency in Rugged Games

| Spike Count | Games | Percentage |
|-------------|-------|------------|
| **1 spike** | 140 | 32.2% |
| **2+ spikes** | 293 | **67.4%** ← Majority! |
| **Average spikes** | 4.04 per game | |

### 💡 Critical Insight: Multiple Spikes Are Normal

**67.4% of rugged games have multiple spikes before the final rug!**

This means:
- First spike ≠ "exit now"
- First spike = "elevated risk, monitor closely"
- Need to identify which spike is the "death spike"

**Pattern hypothesis:**
```
Game progression:
Tick 0-40:   Baseline period (low volatility)
Tick 100:    First spike 2.0x → False alarm, game continues
Tick 150:    Second spike 2.5x → Still safe, game continues
Tick 200:    Third spike 3.0x → Getting dangerous
Tick 250:    Fourth spike 5.0x → DEATH SPIKE, rug imminent
Tick 257:    RUG OCCURS
```

Average: **4 spikes before rug**, spread over **166 ticks**

---

## 🤔 Part 4: The Differentiation Problem

### Question: How do we know which spike is the "death spike"?

**Challenge**: Need to distinguish:
1. **Normal volatility spikes** (safe games + early rugged game spikes)
2. **Death spike** (final spike before rug)

### Potential Solutions

#### Option 1: Spike Acceleration
Look for **increasing spike intensity**:
```python
if ratio >= 2.0 and ratio < 3.0:
    risk_level = "LOW"  # Monitor, don't exit
elif ratio >= 3.0 and ratio < 5.0:
    risk_level = "MEDIUM"  # Reduce position 50%
elif ratio >= 5.0:
    risk_level = "HIGH"  # Exit 100%
```

**Rationale**: Final death spike should be higher magnitude than early spikes.

#### Option 2: Consecutive Confirmation
Require **2-3 consecutive ticks above threshold**:
```python
if volatility_ratio >= 2.0 for 2 consecutive ticks:
    exit_position()
```

**Rationale**: False alarms might spike briefly, death spike is sustained.

#### Option 3: Pattern Combination
Combine volatility with **pattern signals**:
```python
if volatility_ratio >= 2.0 AND pattern_detected:
    exit_position()  # Higher confidence
elif volatility_ratio >= 5.0:
    exit_position()  # Emergency exit regardless
```

**Rationale**: Patterns (Post-Max-Payout, etc.) + volatility = stronger signal.

#### Option 4: Trailing Stop Loss
Use **trailing stop based on volatility ratio**:
```python
# Track peak volatility ratio seen
if current_ratio > peak_ratio:
    peak_ratio = current_ratio

# Exit if ratio drops significantly from peak
if current_ratio < peak_ratio * 0.7:
    exit_position()  # Volatility cooling, game may continue

# Or exit if ratio climbs too high
if current_ratio >= 5.0:
    exit_position()  # Emergency threshold
```

**Rationale**: Allow for volatility fluctuations, exit on extreme spikes only.

#### Option 5: Time-Weighted Exit
Exit confidence **increases with game duration**:
```python
if game_tick < 100:
    exit_threshold = 5.0x  # Early game, higher tolerance
elif game_tick < 200:
    exit_threshold = 3.0x  # Mid game, moderate
else:
    exit_threshold = 2.0x  # Late game, low tolerance
```

**Rationale**: Late-game spikes more likely to be death spikes.

---

## 📊 Part 5: Comparative Analysis

### True Positives vs False Positives

| Scenario | Using 2.0x Threshold |
|----------|---------------------|
| **True Positives** (rugs detected) | 305 / 435 = **70.1%** |
| **False Negatives** (rugs missed) | 130 / 435 = 29.9% |
| **False Positives** (safe games exited) | 10 / 13 = **76.9%** |
| **True Negatives** (safe games stayed) | 3 / 13 = 23.1% |

### Cost-Benefit Analysis

**If bot exits on first 2.0x spike:**
- ✅ Catches 70.1% of rugs (305 games saved from loss)
- ❌ Exits 76.9% of safe games early (10 games, missed profits)
- ❌ Exits early in 67.4% of rugged games (293 games, potential lost profits before rug)

**Net effect:**
- Survival rate: HIGH ✅
- Profit optimization: LOW ❌
- Risk: Very conservative (may be too conservative)

**If bot waits for 5.0x spike:**
- ✅ Catches ~23.7% of rugs (from previous analysis)
- ✅ Stays in most safe games (lower false positives)
- ❌ Misses 76.3% of rugs (late/no detection)

**Net effect:**
- Survival rate: LOW ❌
- Profit optimization: MEDIUM
- Risk: Aggressive (too risky)

---

## 🎯 Part 6: Recommended Strategy

### Graduated Risk Response

Based on analysis, recommend **multi-threshold strategy**:

```python
class VolatilityStrategy:
    def decide(self, volatility_ratio, game_tick, position_size, pattern_detected):
        # Stage 1: Monitoring (2.0-3.0x)
        if 2.0 <= volatility_ratio < 3.0:
            action = "MONITOR"
            # No exit, but prepare
            # Optional: Reduce position 25%

        # Stage 2: Caution (3.0-5.0x)
        elif 3.0 <= volatility_ratio < 5.0:
            action = "REDUCE"
            # Exit 50% of position
            # Tighten stop loss

        # Stage 3: Warning (5.0-10.0x)
        elif 5.0 <= volatility_ratio < 10.0:
            action = "EXIT_MOST"
            # Exit 75-100% of position
            # High risk of imminent rug

        # Stage 4: Emergency (≥10.0x)
        elif volatility_ratio >= 10.0:
            action = "EXIT_ALL"
            # Immediate exit 100%
            # Death spike detected

        # Pattern Confirmation Bonus
        if pattern_detected and volatility_ratio >= 2.0:
            # Lower threshold when pattern confirms
            if volatility_ratio >= 2.0:
                action = "EXIT_MOST"  # Upgrade to 75% exit

        return action
```

### Alternative: Consecutive Confirmation

```python
class ConsecutiveStrategy:
    def __init__(self):
        self.spike_count = 0
        self.consecutive_ticks = 0

    def decide(self, volatility_ratio):
        if volatility_ratio >= 2.0:
            self.consecutive_ticks += 1
        else:
            self.consecutive_ticks = 0

        # Require 3 consecutive ticks above 2.0x
        if self.consecutive_ticks >= 3:
            return "EXIT_ALL"

        # Or single tick above 5.0x
        elif volatility_ratio >= 5.0:
            return "EXIT_ALL"

        return "HOLD"
```

### Recommended: Hybrid Approach

```python
# Combine thresholds + confirmation + patterns
if volatility_ratio >= 5.0:
    # High spike = immediate exit
    exit_position(100%)

elif volatility_ratio >= 3.0 and pattern_detected:
    # Moderate spike + pattern = likely death spike
    exit_position(75%)

elif volatility_ratio >= 2.0 for 3 consecutive ticks:
    # Sustained moderate spike = exit
    exit_position(50%)

elif game_tick > 200 and volatility_ratio >= 2.5:
    # Late game + moderate spike = elevated risk
    exit_position(50%)

else:
    # Low risk, continue trading
    monitor()
```

---

## 💡 Part 7: Key Recommendations for RL Training

### 1. Don't Exit on First 2x Spike

**Reason**: 67.4% of rugged games have multiple spikes, 76.9% of safe games spike too.

**Instead**: Use graduated response or higher threshold.

### 2. Use Multi-Threshold System

**Implementation**:
```yaml
# Reward penalties scale with volatility ratio
volatility_ratio < 2.0:   penalty = 0.0       # Normal
volatility_ratio 2.0-3.0: penalty = -0.1      # Caution
volatility_ratio 3.0-5.0: penalty = -0.5      # Warning
volatility_ratio ≥ 5.0:   penalty = -2.0      # Emergency
```

### 3. Combine with Pattern Signals

**Implementation**:
```python
# Amplify penalty when pattern + volatility align
if pattern_detected and volatility_ratio >= 2.0:
    penalty *= 2.0  # Double penalty for confirmed danger
```

### 4. Time-Weighted Risk

**Implementation**:
```python
# Late-game spikes more dangerous
risk_multiplier = 1.0 + (game_tick / max_ticks)
penalty = base_penalty * risk_multiplier
```

### 5. Survival Bonus for Weathering Spikes

**Implementation**:
```python
# Reward bot for staying in game despite spikes (if game doesn't rug)
if volatility_ratio >= 2.0 and position_size > 0 and not rugged:
    bonus = 0.2  # Reward calculated risk-taking
```

---

## 📈 Part 8: Expected Outcomes

### With Graduated Strategy (3.0x threshold)

**Estimated results:**
- **Survival rate**: 75-85% (vs 5.4% baseline)
- **Rug detection**: 50-60% of rugs caught
- **False positives**: 20-30% (vs 76.9% at 2.0x)
- **Profit per episode**: Higher (stays in games longer)

**Trade-off**: Moderate risk, moderate reward

### With 5.0x Threshold

**Estimated results:**
- **Survival rate**: 50-60%
- **Rug detection**: 23.7% of rugs caught
- **False positives**: 5-10%
- **Profit per episode**: Highest (aggressive strategy)

**Trade-off**: High risk, high reward

### With Consecutive Confirmation (2.0x, 3 ticks)

**Estimated results:**
- **Survival rate**: 70-80%
- **Rug detection**: 60-70% of rugs caught
- **False positives**: 30-40% (still moderate)
- **Profit per episode**: Moderate

**Trade-off**: Balanced approach

---

## 🎓 Part 9: Conclusion

### What We Learned

1. ✅ **Reaction time is NOT the problem** (mean 166 ticks, 96.4% actionable)
2. ❌ **False positives ARE the problem** (76.9% of safe games spike)
3. ⚠️ **Multiple spikes are normal** (67.4% of rugs have 2+ spikes)
4. 🎯 **Need sophisticated strategy** (not just "exit on first spike")

### The Core Challenge

**How to distinguish:**
- Normal volatility fluctuations (safe games)
- Early warning spikes (rugged games, but game continues)
- Death spike (imminent rug)

### Recommended Solution

**Graduated multi-threshold system:**
- 2.0x = Monitor (no action)
- 3.0x = Reduce (exit 50%)
- 5.0x = Exit (exit 100%)
- Combine with patterns for confirmation

**Expected result:**
- Survival rate: 70-85%
- Profit optimization: Better than immediate exit
- Balance between risk and reward

---

## 📊 Appendix: Raw Statistics

### Dataset
- Total games analyzed: 448
- Rugged games: 435 (97.1%)
- Safe games: 13 (2.9%)

### Reaction Time (305 detected rugs)
- Mean: 166.1 ticks
- Median: 107.0 ticks
- Min: 1 tick
- Max: 872 ticks
- Actionable (≥11 ticks): 96.4%

### False Positives (13 safe games)
- Safe games with spikes: 10 (76.9%)
- Total spike events: 45
- Average spikes per safe game: 4.5

### Multiple Spikes (435 rugged games)
- Games with 1 spike: 140 (32.2%)
- Games with 2+ spikes: 293 (67.4%)
- Average spikes per game: 4.04

---

**Analysis Script**: `/home/nomad/Desktop/REPLAYER/analyze_spike_timing.py`
**Last Updated**: November 7, 2025
