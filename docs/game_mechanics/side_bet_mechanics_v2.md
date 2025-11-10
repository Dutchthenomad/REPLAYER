# 01 - Side Bet Mechanics: Complete System Rules (v2.0)

## Executive Summary
The Rugs.fun side betting system enables players to wager that the current game will end (rug) within the next 40 ticks. This document provides the definitive mechanical rules based on analysis of 100 games with 22,507 tick intervals, establishing accurate timing models and mathematical frameworks.

## Critical Timing Analysis Update (July 2025)

### Comprehensive Data Analysis
Based on analysis of 100 randomly sampled games containing 22,507 tick intervals:

**Distribution Analysis:**
- 98.14% of ticks fall between 200-300ms
- 95% of ticks occur between 237-269ms
- Only 0.39% of ticks are under 200ms
- 0.44% of ticks exceed 1000ms (outliers/spikes)

---

## Core Mechanical Rules

### 1. Betting Window and Constraints

#### 1.1 Active Bet Limitations
- **One bet limit**: Players can have exactly ONE active side bet at any time
- **No queuing**: Cannot pre-place bets during cooldown periods
- **Immediate deduction**: SOL is instantly debited from wallet upon placement
- **No cancellation**: Once placed, bets cannot be cancelled or modified

#### 1.2 Placement Window
- **Availability**: From tick 0 through the final tick of any active game
- **Presale betting**: Available during 10-second presale phase (startTick: -1)
- **Late game**: Can bet even at tick 500+ (extremely high probability zones)
- **Final tick**: Betting closes when game rugs (no warning period)

#### 1.3 Bet Amount Constraints
- **Minimum**: 0.001 SOL
- **Maximum**: 5.0 SOL (standard game limit)
- **Precision**: System accepts up to 6 decimal places
- **Currency**: SOL only (coinAddress: "So11111111111111111111111111111111111111112")

### 2. Outcome Resolution System

#### 2.1 Win Condition
- **Binary outcome**: Game must rug within exactly 40 ticks of placement
- **Tick precision**: If placed at tick N, covers ticks N through N+39 (inclusive)
- **Timing basis**: Uses tick count, not elapsed time (critical difference)

#### 2.2 Payout Structure
- **Win ratio**: 5:1 (400% profit + original bet returned)
- **Calculation**: `payout = betAmount × 5`
- **Net profit**: `profit = betAmount × 4`
- **Instant credit**: Winning payouts credited immediately upon game rug

#### 2.3 Loss Scenarios
- **Complete loss**: 100% of bet amount lost if game continues past tick window
- **No partial payouts**: Binary win/lose only
- **Cooldown trigger**: ~1 second display period showing "sidebet lost"

### 3. Event Structure Analysis

#### 3.1 newSideBet Event Schema
```javascript
{
  betAmount: 0.001,              // SOL amount wagered
  coinAddress: "So11...112",     // SOL identifier  
  endTick: 108,                  // startTick + 40
  playerId: "did:privy:...",     // Unique player ID
  startTick: 68,                 // Tick when bet placed (-1 for presale)
  tickIndex: 68,                 // Current game tick (matches startTick)
  timestamp: 1753306685322,      // Unix timestamp (milliseconds)
  type: "placed",                // Event type
  username: "PlayerName",        // Display name
  xPayout: 5                     // Payout multiplier
}
```

#### 3.2 gameStateUpdate Integration
```javascript
// Side bet status within main game state
{
  sideBet: {
    startedAtTick: 384,
    gameId: '20250723-...',
    end: 424,                    // startedAtTick + 40
    betAmount: 0.005,
    xPayout: 5
  },
  sidebetActive: true,           // Boolean flag
  sidebetPnl: -0.01             // Running P&L (negative = losing)
}
```

### 4. Updated Timing Analysis and Compensation

#### 4.1 Empirical vs. Theoretical Timing
```javascript
// Theoretical specifications
const THEORETICAL = {
  tickDuration: 250,      // ms per tick
  windowDuration: 10000,  // 40 ticks × 250ms = 10 seconds
  precision: "exact"
};

// Empirical findings (July 2025 analysis)
const EMPIRICAL = {
  meanTickDuration: 271.5,     // 8.6% higher than theoretical
  medianTickDuration: 251.0,   // Very close to theoretical
  stdDev: 295.3,               // High variability
  variance: 87174.6,           // Significant instability
  reliableRange: {
    min: 237,                  // 5th percentile
    max: 269                   // 95th percentile
  },
  expectedWindowDuration: 10860,  // 40 ticks × 271.5ms ≈ 10.86 seconds
  precision: "highly_variable"
};
```

#### 4.2 Adaptive Timing Model v2
```javascript
class AdaptiveTimingEngineV2 {
  constructor() {
    this.tickHistory = [];
    this.adaptiveProbabilities = new Map();
    this.empiricalBaseline = {
      mean: 271.5,
      median: 251.0,
      stdDev: 295.3,
      p5: 237,
      p95: 269
    };
  }
  
  recordTick(timestamp, tickNumber) {
    const interval = timestamp - this.lastTimestamp;
    this.tickHistory.push({ tick: tickNumber, interval, timestamp });
    
    // Maintain rolling window of last 100 intervals
    if (this.tickHistory.length > 100) {
      this.tickHistory.shift();
    }
    
    this.updateAdaptiveProbabilities();
  }
  
  getCurrentTickRate() {
    const recent = this.tickHistory.slice(-20); // Last 20 ticks
    if (recent.length < 10) {
      // Fall back to empirical baseline if insufficient data
      return this.empiricalBaseline.mean;
    }
    
    const avg = recent.reduce((sum, t) => sum + t.interval, 0) / recent.length;
    
    // Blend with empirical baseline for stability
    const blendWeight = Math.min(recent.length / 20, 1);
    return (avg * blendWeight) + (this.empiricalBaseline.mean * (1 - blendWeight));
  }
  
  getActualWindowDuration() {
    const currentRate = this.getCurrentTickRate();
    const baseWindow = currentRate * 40;
    
    // Add variance buffer based on empirical data
    const varianceBuffer = this.empiricalBaseline.stdDev * Math.sqrt(40) / Math.sqrt(20);
    
    return {
      expected: baseWindow,
      conservative: baseWindow + varianceBuffer,
      optimistic: baseWindow - varianceBuffer
    };
  }
  
  getReliabilityScore() {
    const recent = this.tickHistory.slice(-50);
    if (recent.length < 20) return 0.5; // Default medium reliability
    
    const intervals = recent.map(t => t.interval);
    const mean = intervals.reduce((sum, i) => sum + i, 0) / intervals.length;
    const variance = intervals.reduce((sum, i) => sum + Math.pow(i - mean, 2), 0) / intervals.length;
    const cv = Math.sqrt(variance) / mean;
    
    // Score based on coefficient of variation
    // CV < 0.1 = very reliable, CV > 0.5 = very unreliable
    return Math.max(0, Math.min(1, 1 - (cv * 2)));
  }
}
```

### 5. Session and Game Interaction Rules

#### 5.1 Session Limits
- **Winning cap**: 20 SOL maximum winnings per game triggers auto-stop
- **No loss limits**: Players can lose entire wallet if not managed
- **Cross-game tracking**: Winnings/losses accumulate across games
- **Reset conditions**: New wallet or manual reset only

#### 5.2 Main Game Integration
- **Independence**: Side bets do not affect PRNG within single game
- **Combined exposure**: Can maintain both main positions and side bets
- **Visibility**: All players see others' side bet positions and P&L
- **Hedging capability**: Can use side bets to hedge main game positions

#### 5.3 Game Phase Interactions
```javascript
// Phase-specific betting behavior
const PHASE_RULES = {
  presale: {
    sideBetting: true,
    startTick: -1,           // Special identifier
    window: "10_seconds",    // Fixed presale duration
    mainGame: false          // No main game activity
  },
  active: {
    sideBetting: true,
    startTick: "current_tick",
    window: "40_ticks",      // Standard window
    mainGame: true           // Full trading available
  },
  rugged: {
    sideBetting: false,      // No betting during rug events
    settlement: "immediate", // Instant payout processing
    cooldown: "~15_seconds"  // Before next game
  }
};
```

### 6. Mathematical Framework v2

#### 6.1 Expected Value Formula with Empirical Data
```javascript
// Updated EV calculation using empirical timing
function calculateExpectedValueV2(winProbability, betAmount, timingReliability = 1.0) {
  const winOutcome = betAmount * 4;  // Net profit (400%)
  const loseOutcome = -betAmount;    // Total loss
  
  // Adjust probability based on timing reliability
  const adjustedProbability = winProbability * timingReliability;
  
  return (adjustedProbability * winOutcome) + ((1 - adjustedProbability) * loseOutcome);
}

// Breakeven calculation remains the same
const BREAKEVEN_PROBABILITY = 1/6; // 16.67%

// But effective breakeven shifts with timing variance
function getEffectiveBreakeven(timingReliability) {
  return BREAKEVEN_PROBABILITY / timingReliability;
}
```

#### 6.2 Adaptive Probability Calculation v2
```javascript
function getAdaptiveProbabilityV2(tickCount, timingEngine) {
  const baseProb = getBaseProbability(tickCount);
  const currentTickRate = timingEngine.getCurrentTickRate();
  const reliability = timingEngine.getReliabilityScore();
  
  // Use empirical baseline for stability
  const empiricalMean = 271.5;
  const theoreticalMean = 250;
  
  // Calculate timing adjustment factor
  const timingRatio = currentTickRate / theoreticalMean;
  const empiricalRatio = empiricalMean / theoreticalMean;
  
  // Blend current observations with empirical baseline
  const blendedRatio = (timingRatio * reliability) + (empiricalRatio * (1 - reliability));
  
  // Adjust probability for actual window duration
  // Longer windows = higher chance of rug occurring
  const durationAdjustment = Math.pow(blendedRatio, 0.3); // Dampened adjustment
  
  return Math.min(baseProb * durationAdjustment, 0.98); // Cap at 98%
}
```

### 7. Risk Analysis Framework v2

#### 7.1 Gap Risk Assessment with Empirical Data
```javascript
function calculateGapRiskV2(currentTickRate, lastBetTick) {
  const expectedCooldown = 1000; // 1 second theoretical
  
  // Use empirical data for more accurate gap estimation
  const empiricalTickRate = 271.5;
  const actualCooldown = Math.max(currentTickRate, empiricalTickRate) * 4; // ~4 ticks observed
  
  const gapTicks = actualCooldown / currentTickRate;
  const missedWindow = lastBetTick + gapTicks;
  
  return {
    gapDuration: actualCooldown,
    ticksAtRisk: gapTicks,
    probabilityMissed: getProbabilityAtTick(missedWindow),
    reliability: currentTickRate <= empiricalTickRate * 1.2 ? 'high' : 'low'
  };
}
```

#### 7.2 Timing Reliability Score v2
```javascript
function calculateReliabilityScoreV2(tickHistory) {
  const empiricalBaseline = {
    mean: 271.5,
    stdDev: 295.3,
    cv: 1.09
  };
  
  if (tickHistory.length < 20) {
    // Use empirical baseline for insufficient data
    return 1 - empiricalBaseline.cv;
  }
  
  const intervals = tickHistory.map(t => t.interval);
  const mean = intervals.reduce((sum, i) => sum + i, 0) / intervals.length;
  const variance = intervals.reduce((sum, i) => sum + Math.pow(i - mean, 2), 0) / intervals.length;
  const cv = Math.sqrt(variance) / mean;
  
  // Compare to empirical baseline
  const relativeReliability = empiricalBaseline.cv / cv;
  
  // Score between 0 and 1
  return Math.max(0, Math.min(1, relativeReliability));
}
```

### 8. Implementation Guidelines v2

#### 8.1 Core Requirements
- [ ] Implement adaptive timing model with empirical baseline
- [ ] Use median (251ms) for short-term predictions, mean (271.5ms) for long-term
- [ ] Account for 98.14% of ticks falling in 200-300ms range
- [ ] Handle outliers (0.44% of ticks > 1000ms) gracefully
- [ ] Maintain reliability scoring based on recent vs empirical performance

#### 8.2 Advanced Features
- [ ] Dynamic probability adjustment using real-time reliability scores
- [ ] Variance-aware betting strategies
- [ ] Outlier detection and filtering
- [ ] Empirical baseline fallback for new games
- [ ] Multi-game timing pattern recognition

#### 8.3 Safety Features
- [ ] Conservative estimates using 95th percentile (269ms) for critical decisions
- [ ] Reliability warnings when CV exceeds empirical baseline
- [ ] Automatic strategy adjustment for high-variance periods
- [ ] Emergency stop when timing exceeds 2x empirical mean
- [ ] Continuous model validation against new data

---

## Conclusion

The comprehensive analysis of 22,507 tick intervals reveals that while the Rugs.fun side betting system operates close to its theoretical specifications (median 251ms vs theoretical 250ms), significant variance exists that requires sophisticated adaptive modeling. The mean tick interval of 271.5ms represents an 8.6% increase over theoretical, primarily driven by occasional timing spikes.

Key operational insights:
1. **Median-based calculations** are appropriate for real-time decisions
2. **Mean-based calculations** should be used for expected value and long-term planning
3. **High variance** (CV of 1.09) mandates adaptive probability models
4. **98%+ reliability** within the 200-300ms range enables confident betting in normal conditions
5. **Outlier handling** is critical for the 0.44% of extreme timing events

This updated framework provides the mathematical foundation for building robust, profitable side betting strategies that adapt to real-world timing variations while maintaining edge in the face of uncertainty.

---

*Version 2.0 - Updated July 2025 with empirical analysis of 100 games*
*Next: [02-probability-framework-v2.md](./02-probability-framework-v2.md) - Updated probability models with empirical data*