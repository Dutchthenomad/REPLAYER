# RUGS.FUN GAME MECHANICS - COMPREHENSIVE KNOWLEDGE BASE

**Purpose**: RAG-style knowledge system for cumulative learning across sessions
**Version**: 1.0
**Last Updated**: 2025-11-02
**Status**: Initial creation - needs structuring in future sessions

---

## 🎯 CRITICAL MECHANICS (HIGHEST PRIORITY)

### INSTANT LIQUIDATION RULE ⚠️
**THE MOST IMPORTANT RULE IN THE GAME:**

```
ANY TRADER POSITIONS HELD DURING A RUG ARE INSTANTLY LIQUIDATED
CAN ONLY BE HEDGED BY AN ACTIVE SIDE BET
MANAGE BANKROLL AND RISK WISELY!!!
```

**Implications**:
- Holding positions during rug = 100% loss of those positions
- Only defense = active side bet (5:1 payout covers losses)
- Exit timing is CRITICAL - better to exit early than hold through rug
- Multiple positions ALL liquidated simultaneously during rug
- This is the PRIMARY reason for bankruptcy in training (bot holds through rugs)

**Design Note**: Reward system MUST heavily penalize holding positions during rug events

---

## 🏪 PRESALE MECHANICS (CRITICAL STRATEGIC WINDOW)

### Why It's Called PRESALE
**THIS IS WHY IT IS CALLED THE PRESALE!!!**
- Bot CAN enter trading position during presale
- Bot CAN place side bet during presale (if early rug highly likely)
- Presale = guaranteed entry price before game volatility begins

### Presale Constraints
**Position Limits**:
- **ONLY ONE** trading position can be entered during presale
- **ONLY ONE** side bet can be placed during presale
- **CANNOT EXIT** until game begins (positions locked)

**Timing**:
- Duration: 10 seconds fixed
- Tick identifier: -1
- Price: Fixed presale price (typically 1.0x)
- Follows cooldown phase (~15 seconds)

### Strategic Considerations
**Advantages**:
- Guaranteed entry at presale price (no slippage)
- Early position for potential moonshots
- Side bet placement for instarug protection

**Disadvantages**:
- Locked in (cannot exit if conditions change)
- Committed before game dynamics known
- Risk of instarug (< 11 ticks) = instant liquidation

**Optimal Use Cases**:
1. **High-confidence games**: Historical patterns suggest longer duration
2. **Instarug hedging**: Place side bet if post-high-peak game
3. **Position building**: Entry before active volatility
4. **Risk mitigation**: Small position + side bet hedge combo

**Design Note**: Bot needs decision logic for presale entry (not mandatory, but available)

---

## 💰 POSITION & BANKROLL MECHANICS

### Position Entry/Exit
- **Entry**: Buy at current tick price (including presale at tick -1)
- **Exit**: Sell at current tick price (NOT available during presale)
- **Multiple Positions**: YES - can hold multiple positions from different entry ticks
- **Presale Lock**: Presale position cannot be exited until active game begins
- **Tracking**: Unrealized P&L tracked for all ACTIVE positions
- **Settlement**: Sold/rugged/lost positions reflected in wallet balance

### Bankroll Updates (INSTANT)
- **Timing**: ALL transactions are instant debit/credit
- **Active Positions**: Show as unrealized P&L (not yet in wallet)
- **Closed Positions**: Immediately reflected in wallet balance
- **Rugged Positions**: Instant liquidation → balance decreases immediately
- **Side Bet Wins**: Instant credit to wallet (5:1 payout)

**Design Note**: No delayed settlement - all P&L tracking must be real-time

### Position Sizing Guidelines
**Example**: 0.1 SOL bankroll
- Position size: 0.005 SOL (5% of bankroll)
- Side bet hedge: 0.001 SOL (1% of bankroll, 20% of position)
- Rationale: Side bet 5:1 payout covers position loss if rug occurs

**Risk Management Philosophy**:
- Small position sizes (2-5% of bankroll)
- Side bet hedging for risk mitigation
- Profits accumulate over TIME, not all at once
- Drawdown limits prevent catastrophic losses

---

## 🎲 SIDE BET MECHANICS

### Integration with Training Data
**CRITICAL**: Side bets are NOT in recorded game data!
- Training data contains: game state, tick, price, phase
- Training data does NOT contain: player trades, side bets
- Side bets must be HARD-CODED as available bot actions
- Bot must learn WHEN to place side bets (not just main positions)

### Side Bet Placement Windows
**Presale Placement**:
- Available during presale (tick -1)
- Use case: Hedge against instarugs (< 11 ticks)
- Strategy: If post-high-peak game or pattern suggests short duration
- Lock-in: Cannot cancel once placed

**Active Game Placement**:
- Available from tick 0 through final tick
- Use case: Hedge active positions as rug probability increases
- One active side bet at a time
- Can replace after previous resolves

### Side Bet as Hedge
**Primary Function**: Hedge active positions against rug risk

**Example Scenario 1 (Active Game)**:
1. Bot holds 0.005 SOL position at 2.5x
2. Unrealized P&L: +0.0075 SOL
3. Rug probability increasing (high tick count, volatility spike)
4. Place 0.001 SOL side bet (40-tick window)
5. If rug within 40 ticks:
   - Position liquidated: -0.005 SOL
   - Side bet wins: +0.005 SOL (5:1 payout)
   - Net result: ~break even (vs total loss)

**Example Scenario 2 (Presale)**:
1. Previous game peaked at 80x (huge player win)
2. Meta-layer suggests short next game (treasury recovery)
3. Presale: Enter 0.002 SOL position + 0.001 SOL side bet
4. Game instarugs at tick 8:
   - Position liquidated: -0.002 SOL
   - Side bet wins: +0.005 SOL
   - Net result: +0.003 SOL profit (vs -0.002 loss)

**Design Note**: Bot needs side bet action in action space with strategic placement logic

### Side Bet Parameters (from Knowledge Docs)
- **Payout**: 5:1 (400% profit, breakeven = 16.67%)
- **Window**: Exactly 40 ticks from placement
- **Limit**: ONE active side bet at a time
- **Placement**: Available from presale (tick -1) through active game
- **Timing**: Mean tick duration 271.5ms (not 250ms theoretical)
- **COOLDOWN**: 5 ticks between sidebets (CRITICAL!)

**Cooldown Example**:
- Sidebet placed at tick 160
- Window: ticks 160-200 (40 ticks)
- If game continues past tick 200 (loss)
- Cooldown: ticks 200-205 (cannot place sidebet)
- Next sidebet available: tick 205

**Strategic Implication**: Cannot spam sidebets - must be selective about placement timing!

---

## 🏛️ META-LAYER TREASURY MANAGEMENT SYSTEM

### The Hidden PRNG Layer
**CRITICAL DISCOVERY**: PRNG has adaptive treasury management beyond single-game mechanics

**Treasury Profit Sources**:
1. **Per-Tick Revenue**: House earns on every tick
2. **Rug Liquidations**: House keeps ALL active positions during rug event

**Adaptive Behavior**:
- Games after extremely high peak price → MUCH SHORTER duration
- House mitigates drawdown by extracting income from players
- This creates cross-game patterns (why chronological order matters!)

### Historical Duration Tracking (EXTREMELY VALUABLE)
**Must Track**: Last 5, 10, 20, 50 game durations

**Why This Matters**:
- Pattern 1: Post-high-peak games end faster
- Pattern 2: Treasury balancing across multiple games
- Pattern 3: Recovery sequences after player windfalls
- Pattern 4: Adaptive difficulty based on player success

**Example Pattern**:
```
Game N:   Peak 50x, duration 800 ticks (players win big)
Game N+1: Peak 3x,  duration 80 ticks  (house recovers) ← PRESALE SIDE BET OPPORTUNITY!
Game N+2: Peak 5x,  duration 120 ticks (gradual normalization)
```

**Presale Strategy Application**:
- After 50x peak → high probability of instarug
- Presale side bet = smart hedge
- Can still enter small position for upside
- Risk/reward heavily favors side bet

**Design Note**: Environment MUST preserve game chronological order (no shuffling)

### Alpha from Final Tick Price
**Observation**: Final tick price is "rounded number from liquidations"

**Potential Alpha Sources**:
- Final price = sum of all liquidated positions
- High final price = many positions held during rug
- Low final price = few positions held (most exited early)
- Pattern recognition: final price correlates with next game duration?

**Research Needed**: Study correlation between final tick price and next game characteristics

---

## 🚨 RUG EVENT MECHANICS

### What "RUGGED!" Means
- **Definition**: GAME OVER (not recoverable)
- **Timing**: Instant (no warning beyond volatility/probability signals)
- **Effect**: ALL active positions instantly liquidated (including presale positions)
- **Price**: Drops to near-zero (rounded liquidation value)
- **Recovery**: Impossible - game ends immediately

### Instarug Mechanics
**Definition**: Games that rug in < 11 ticks
- **Frequency**: ~10% baseline probability
- **Presale Risk**: Presale positions locked until tick 0, vulnerable to instarugs
- **Hedge**: Presale side bet can protect against instarugs
- **Meta-layer**: Much higher probability after high-peak games

### Rug Warning Signals (from analysis)
**Volatility Spike** (PRIMARY INDICATOR):
- Normal volatility: ~2-5%
- Near-rug volatility: 20-30%+
- Increase: 10-15x higher (1000%+)
- Knowledge docs cite: 78% increase (conservative estimate)
- Actual observation: 1,129% increase (11.3x)

**Other Indicators**:
- High tick count (>100, >200, >500)
- Rapid price acceleration after recovery
- Player exodus (selling volume increases)
- Buy/sell ratio imbalance

---

## 📊 SUCCESS DEFINITION & EVALUATION

### Session-Based Success Criteria
**Example**: 50-game session with 50% max drawdown

**Success Tiers**:
1. **Survival**: Complete 50 games without hitting drawdown limit
2. **Breakeven**: End with 0% profit (acceptable)
3. **Good**: End with +10% profit
4. **Great**: End with +25% profit
5. **Phenomenal**: End with +100% profit

### Drawdown Management
**Stop Conditions**:
- Hit max drawdown limit (e.g., -50%) → STOP immediately
- Example: Start with 0.1 SOL, lose 50% → stop at 0.05 SOL
- Even if only 10 games played (vs 50 planned)

**Why This Matters**:
- Prevents catastrophic losses
- Preserves capital for future sessions
- Focuses on long-term profitability, not short-term wins

### Time Horizon Philosophy
> "This is meant to make money over TIME, not all at once."

**Implications**:
- Small consistent gains > big risky bets
- Compound growth over many games
- Risk management > reward chasing
- Survival > optimization

---

## 🎮 GAME PHASES & STRUCTURE

### Phase Definitions (from Socket.IO data)
1. **Cooldown**: ~15 seconds between games (not recorded in training data)
2. **Presale**: 10 seconds, tick = -1, fixed price, position entry allowed
3. **Active**: Variable duration, ticks 0 → N, dynamic pricing
4. **Rugged**: Game over event, instant liquidation

### Phase Transition Flow
```
Cooldown (15s)
  ↓
Presale (10s, tick -1)
  - Can enter ONE position
  - Can place ONE side bet
  - CANNOT exit until active phase
  ↓
Active (variable, ticks 0 → N)
  - Dynamic pricing
  - Multiple positions allowed
  - Exit/entry available
  - Side bets available
  ↓
Rugged (instant)
  - All positions liquidated
  - Side bets settle
  - Game over
```

### Game Duration Patterns
- **Instarugs**: < 11 ticks (baseline ~10%, higher post-high-peak)
- **Short**: 11-100 ticks
- **Medium**: 100-300 ticks
- **Long**: 300-500 ticks
- **Extreme**: 500+ ticks (rare, very high rug probability)

---

## 💡 TRADING ZONES (from Knowledge Docs)

### Zone Breakdown
1. **Low Risk (1x-2x)**: Safe entry, low volatility (0.5-0.7%)
2. **Sweet Spot (2x-4x)**: BEST risk/reward, moderate volatility (0.7-1.0%)
3. **Growth Zone (4x-9x)**: Good opportunities, higher volatility (1.0-1.5%)
4. **High Risk (9x-25x)**: Quick scalping only, high volatility (1.5-2.5%)
5. **Danger Zone (25x-100x)**: Exit only, very high volatility (2.5-5.0%)
6. **Extreme Zone (100x+)**: Never enter, exit immediately

### Optimal Strategy Recommendations
**Balanced Range Trading (3.2x → 4.8x)**:
- Entry: 3.2x
- Exit: 4.8x (50% gain)
- Stop Loss: 2.8x (12.5% loss)
- Success Rate: ~65%
- Risk-Reward: 1:4

---

## 🔬 VOLATILITY & PROBABILITY ANALYSIS

### Volatility Formula (from Knowledge Docs)
```python
def calc_volatility(prices_list):
    changes = [abs(prices[i] - prices[i-1]) / prices[i-1]
               for i in range(1, len(prices))
               if prices[i-1] > 0]
    return sum(changes) / len(changes)
```

### Probability Curves (from SIDEbET kNOWhOW.txt)
**Base Probabilities** (40-tick window rug probability):
- Tick -1 (Presale): 15% (instarug risk, higher post-high-peak)
- Tick 0-10: 15%
- Tick 50-60: 32%
- Tick 100-120: 50% (CRITICAL ZONE)
- Tick 200-220: 74%
- Tick 300-350: 88%
- Tick 500+: 96% (near-certain)

**Design Note**: Use these for side bet timing and exit decisions

---

## 🧮 MATHEMATICAL FRAMEWORKS

### Expected Value (Side Bet)
```
EV = P(win) × 4 × bet_amount - P(lose) × bet_amount
Breakeven: P(win) = 16.67% (1/6)
```

**Presale Side Bet EV** (post-high-peak game):
- Assume instarug probability: 30% (3x baseline)
- EV = 0.30 × 4 × 0.001 - 0.70 × 0.001
- EV = 0.0012 - 0.0007 = +0.0005 SOL (positive!)

### Bankroll Certainty Zones (from docs)
**With proper sequence**:
- 0.127 SOL → 99.22% success rate (7 attempts at 50% probability)
- 0.511 SOL → 99.80% success rate (9 attempts at 40% probability)
- 2.047 SOL → 99.95% success rate (11 attempts at 30% probability)

**Note**: These assume disciplined execution and proper timing

---

## 🚧 DESIGN NOTES FOR FUTURE STRUCTURING

### Section Reorganization Needed
- [ ] Group by topic hierarchy (Mechanics → Strategy → Math)
- [ ] Cross-reference related concepts
- [ ] Add visual diagrams where helpful
- [ ] Create quick-reference tables
- [ ] Build decision trees for bot logic

### Content Gaps to Fill
- [ ] Exact liquidation calculation mechanics
- [ ] Final tick price alpha extraction methods
- [ ] Meta-layer pattern validation (need data analysis)
- [ ] Optimal side bet timing algorithm
- [ ] Position size optimization formulas
- [ ] Drawdown recovery strategies
- [ ] Presale entry decision algorithm

### Research Questions
1. What's the correlation between final tick price and next game duration?
2. How predictable are post-high-peak game durations?
3. What's the optimal side bet placement threshold (tick count + volatility)?
4. Can we detect meta-layer treasury rebalancing in real-time?
5. What patterns exist in 5/10/20/50-game duration sequences?
6. What's the optimal presale entry rate (% of games to enter)?
7. When should presale side bet be placed vs active game side bet?

---

## 📖 SOURCE DOCUMENTS

**Primary Sources**:
1. `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/SIDEbET kNOWhOW.txt` (side bet mechanics, probability curves, timing analysis)
2. `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/knowledge20f2.txt` (volatility analysis, trading zones, tick-by-tick patterns)
3. User clarifications (2025-11-02 session)

**Validated Through**:
- 528 full game recordings
- Training results (500k timesteps)
- Live game observation (game_20251030_165915_fd634de2.jsonl analysis)

---

## 🎯 CRITICAL TAKEAWAYS FOR BOT DESIGN

### Why Training Failed (94.6% Bankruptcy)
1. ❌ Bot holds positions through rugs (instant liquidation)
2. ❌ No side bet hedging mechanism
3. ❌ Doesn't recognize volatility spike warnings
4. ❌ Ignores probability curves (stays in high-risk zones)
5. ❌ Position sizing too aggressive
6. ❌ No drawdown management
7. ❌ No presale strategy (missing early opportunities)

### What Bot MUST Learn
1. ✅ Exit BEFORE rug (volatility + probability signals)
2. ✅ Use side bets as hedges (not just speculation)
3. ✅ Respect trading zones (exit at danger thresholds)
4. ✅ Track meta-layer patterns (game duration sequences)
5. ✅ Proper position sizing (2-5% of bankroll)
6. ✅ Drawdown limits (stop when hit)
7. ✅ Presale decision logic (when to enter/hedge)
8. ✅ Instarug protection (presale side bets post-high-peak)

### Reward Function Implications
**Current Problem**: Immediate bonuses (+1.3) > Delayed penalties (-2.5)

**Solution Requirements**:
1. Massive penalty for holding positions during rug (-5.0+)
2. Reward early exits in high-risk zones (+0.5)
3. Bonus for side bet hedging (+0.3)
4. Drawdown penalties (progressive)
5. Survival bonuses (completing games without liquidation)
6. Presale strategy rewards (smart entry/hedging)

---

## 🎬 ACTION SPACE REQUIREMENTS

### Bot Actions (Must Include)
**Trading Actions**:
1. WAIT (no action)
2. BUY_MAIN (enter position at current price)
3. SELL_MAIN (exit all or partial positions)
4. SELL_PARTIAL (specify percentage to sell)

**Presale Actions**:
5. PRESALE_BUY (enter position during presale, tick -1)
6. PRESALE_SIDEBET (place side bet during presale)

**Side Bet Actions**:
7. PLACE_SIDEBET (place side bet during active game)

**Emergency Actions**:
8. EMERGENCY_EXIT (exit all positions immediately)

### Action Parameters
- **Position Size**: Index into [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5] SOL
- **Side Bet Size**: Index into same array
- **Sell Percentage**: 0.0 - 1.0 (for partial sells)

### Action Constraints
- BUY only if balance >= bet_size
- SELL only if positions exist
- SIDEBET only if no active sidebet
- PRESALE actions only available during presale phase (tick -1)
- PRESALE positions cannot be sold until active phase (tick ≥ 0)

---

*End of Knowledge Base v1.0*

**Next Steps**:
1. Use this as RAG context in future sessions
2. Update with findings from 528-game audit
3. Add meta-layer pattern analysis results
4. Incorporate optimal strategy algorithms
5. Refine based on bot retraining outcomes
6. Validate presale strategy effectiveness
