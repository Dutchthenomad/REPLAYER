# WebSocket Data Discovery Report
**Phase 10.4 Exploration** | December 6, 2025

## Executive Summary

We're currently capturing **9 fields** but ignoring **303+ fields** of high-value data broadcast every ~250ms.

---

## Currently Captured (9 fields)
```
gameId, active, rugged, tickCount, price,
cooldownTimer, allowPreRoundBuys, tradeCount, gameHistory
```

---

## HIGH-VALUE IGNORED DATA

### 🎯 Priority 1: PnL & Position Verification

| Field | Type | Value | Use Case |
|-------|------|-------|----------|
| `leaderboard[].pnl` | float | 0.264879755 | Server-side PnL - verify our calculations |
| `leaderboard[].pnlPercent` | float | 105.38% | Percentage verification |
| `leaderboard[].balance` | float | 3967.07 | Balance verification |
| `leaderboard[].positionQty` | float | 0.222 | Position size verification |
| `leaderboard[].avgCost` | float | 1.259 | Entry price verification |
| `leaderboard[].hasActiveTrades` | bool | True | Trade status sync |
| `leaderboard[].sidebetActive` | bool | - | Sidebet status sync |
| `leaderboard[].sidebetPnl` | int | 0 | Sidebet PnL |

**Impact**: Can independently verify ALL our internal PnL calculations against server truth.

### 🎯 Priority 2: Complete Price History

| Field | Type | Sample | Use Case |
|-------|------|--------|----------|
| `partialPrices.values` | dict | {125: 1.27, 126: 1.30, ...} | Full tick-by-tick prices |
| `partialPrices.startTick` | int | 125 | Window start |
| `partialPrices.endTick` | int | 129 | Window end |

**Impact**: Complete price history for backfill, verification, and latency analysis.

### 🎯 Priority 3: Server Timestamps (Latency)

| Field | Type | Sample | Use Case |
|-------|------|--------|----------|
| `godCandle50xTimestamp` | int | 1765065527257 | Server-side event timestamps |
| `highestTodayTimestamp` | int | 1765010285288 | Server clock reference |
| `globalSidebets[].timestamp` | int | 1765068967229 | Sidebet placement time |

**Impact**: Precise server-to-client latency measurement.

### 🎯 Priority 4: Rugpool (Instarug Prediction)

| Field | Type | Sample | Use Case |
|-------|------|--------|----------|
| `rugpool.rugpoolAmount` | float | 1.025 | Current rugpool |
| `rugpool.threshold` | int | 10 | Instarug trigger threshold |
| `rugpool.instarugCount` | int | 2 | Instarugs this session |

**Impact**: Predict instarugs before they happen.

### 🎯 Priority 5: Game Statistics

| Field | Type | Sample | Use Case |
|-------|------|--------|----------|
| `connectedPlayers` | int | 224 | Player count |
| `averageMultiplier` | float | 9.76 | Session average |
| `count2x/10x/50x/100x` | int | 40/7/4/2 | Multiplier distribution |
| `highestToday` | float | 2251.16 | Daily high |

---

## OTHER EVENTS DISCOVERED

| Event | Count | Description |
|-------|-------|-------------|
| `standard/newTrade` | 18 | **Other players' trades!** |
| `rugRoyaleUpdate` | 2 | Tournament updates |
| `battleEventUpdate` | 1 | Battle mode |
| `newChatMessage` | 3 | Chat messages |

**`standard/newTrade`** is particularly valuable - we can see ALL trades happening in real-time.

---

## Recommended Integration Plan

### Phase 10.4A: Core Verification Data
1. Extract `leaderboard[]` for our player (by wallet/username match)
2. Add PnL verification against `leaderboard[].pnl`
3. Add balance verification against `leaderboard[].balance`
4. Add position verification against `leaderboard[].positionQty`

### Phase 10.4B: Price History & Latency
1. Extract `partialPrices` for complete tick history
2. Calculate server-to-client latency from timestamps
3. Backfill any missed ticks

### Phase 10.4C: Rugpool & Prediction
1. Track `rugpool.rugpoolAmount` vs `threshold`
2. Add instarug probability indicator
3. Alert when threshold approaching

### Phase 10.4D: Trade Feed
1. Subscribe to `standard/newTrade` events
2. Track market activity (trade volume, whale trades)
3. Add to demo recording for ML training data

---

## Files Generated

- `sandbox/websocket_raw_samples.jsonl` - 200 raw data samples
- `sandbox/field_analysis.json` - Complete field analysis
- `sandbox/explore_websocket_data.py` - Exploration script (reusable)

---

## Next Steps

1. **Review this report** - Prioritize which data to integrate first
2. **Design extraction layer** - Extend `_extract_signal()` for priority fields
3. **Add verification hooks** - Compare local state to server state
4. **Auto-start integration** - Use game transitions from feed to trigger recording
