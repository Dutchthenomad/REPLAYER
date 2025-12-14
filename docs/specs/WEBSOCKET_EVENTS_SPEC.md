# WebSocket Events Specification
**rugs.fun Socket.IO Protocol** | **Version**: 1.1 | **Date**: December 9, 2025

---

## Overview

This document provides a formal specification of all WebSocket events broadcast by the rugs.fun backend via Socket.IO. It serves as empirical reference data for building the verification layer and expanding our data capture.

### Connection Details
- **Server URL**: `https://backend.rugs.fun?frontend-version=1.0`
- **Protocol**: Socket.IO (WebSocket with polling fallback)
- **Broadcast Rate**: ~4 messages/second (~250ms intervals)

### Message Prefix Convention
| Prefix | Meaning |
|--------|---------|
| `42` | Standard broadcast event |
| `43XXXX` | Response to request with ID `XXXX` |

### Authentication Requirements

**IMPORTANT**: Some events require wallet authentication:

| Event | Auth Required | When Sent |
|-------|---------------|-----------|
| `gameStateUpdate` | No | Every tick (~4/sec) |
| `usernameStatus` | **YES** | Once on connection (if logged in) |
| `playerUpdate` | **YES** | After **server-side** trades only |
| `playerLeaderboardPosition` | **YES** | Once on connection (if logged in) |

**Key Insight**: If the user is not logged in with their Phantom wallet, `usernameStatus`, `playerUpdate`, and `playerLeaderboardPosition` will NOT be sent.

---

## Current Capture Status

### Currently Captured (9 fields)
```
gameId, active, rugged, tickCount, price,
cooldownTimer, allowPreRoundBuys, tradeCount, gameHistory
```

### High-Value Ignored (303+ fields)
See Priority Integration sections below.

---

## Event Taxonomy

### 1. `gameStateUpdate` (Primary Tick Event) ✅ VERIFIED

**Frequency**: ~4x/second (~250ms intervals)
**Purpose**: Complete game state broadcast to all connected clients
**Auth Required**: NO - Broadcast to all connections

```json
42["gameStateUpdate", {
  "gameId": "20251210-80d2ade6a0db4338",
  "gameVersion": "v3",
  "active": true,
  "rugged": true,
  "price": 0.01978688651688796,
  "tickCount": 17,
  "cooldownTimer": 0,
  "cooldownPaused": false,
  "pauseMessage": "",
  "allowPreRoundBuys": false,
  "averageMultiplier": 6.286986541653673,
  "connectedPlayers": 190,
  "count2x": 46,
  "count10x": 8,
  "count50x": 3,
  "count100x": 1,
  "highestToday": 1026.429049568061,
  "highestTodayTimestamp": 1765260384895,
  "leaderboard": [...],
  "partialPrices": {...},
  "gameHistory": [...],
  "provablyFair": {...},
  "rugRoyale": {...},
  "availableShitcoins": [...]
}]
```

#### Root Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `gameId` | string | `"20251210-80d2ade6a0db4338"` | Unique game identifier |
| `gameVersion` | string | `"v3"` | Game version |
| `active` | bool | `true` | Game in progress |
| `rugged` | bool | `true` | Game has rugged |
| `price` | float | `0.01978688651688796` | Current multiplier |
| `tickCount` | int | `17` | Current tick number |
| `cooldownTimer` | int | `0` | Countdown to next game (0 = game active) |
| `cooldownPaused` | bool | `false` | Countdown paused |
| `pauseMessage` | string | `""` | Pause reason |
| `allowPreRoundBuys` | bool | `false` | Pre-round buying enabled |

#### Statistics Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `averageMultiplier` | float | `6.287` | Session average rug point |
| `count2x` | int | `46` | Games reaching 2x |
| `count10x` | int | `8` | Games reaching 10x |
| `count50x` | int | `3` | Games reaching 50x |
| `count100x` | int | `1` | Games reaching 100x |
| `connectedPlayers` | int | `190` | Current player count |
| `highestToday` | float | `1026.43` | Daily high multiplier |
| `highestTodayTimestamp` | int | `1765260384895` | Timestamp of daily high |
| `highestTodayPrices` | array | `[1, 0.99, ...]` | Price history for daily high |

#### God Candle Fields (Celebration Events)

| Field | Type | Description |
|-------|------|-------------|
| `godCandle2x` | float/null | 2x celebration price |
| `godCandle2xTimestamp` | int/null | When 2x was hit |
| `godCandle2xPrices` | array | Price history for 2x candle |
| `godCandle2xMassiveJump` | bool/null | Large price jump indicator |
| `godCandle10x` | float/null | 10x celebration price |
| `godCandle10xTimestamp` | int/null | When 10x was hit |
| `godCandle10xPrices` | array | Price history for 10x candle |
| `godCandle10xMassiveJump` | bool/null | Large price jump indicator |
| `godCandle50x` | float/null | 50x celebration price |
| `godCandle50xTimestamp` | int/null | When 50x was hit |
| `godCandle50xPrices` | array | Price history for 50x candle |
| `godCandle50xMassiveJump` | bool/null | Large price jump indicator |

#### Available Coins

```json
{
  "availableShitcoins": [
    {
      "address": "0xPractice",
      "ticker": "FREE",
      "name": "Practice SOL",
      "max_bet": 10000,
      "max_win": 100000
    }
  ]
}
```

#### Provably Fair

```json
{
  "provablyFair": {
    "serverSeedHash": "bce190330836fffda61bdecbed6d8a83bfb7bb3a6b2bd278002a36df773c809a",
    "version": "v3"
  }
}
```

#### Rug Royale (Tournament Mode)

```json
{
  "rugRoyale": {
    "status": "INACTIVE",
    "activeEventId": null,
    "currentEvent": null,
    "upcomingEvents": [],
    "events": []
  }
}
```

#### Price History (`partialPrices`)

```json
{
  "partialPrices": {
    "startTick": 125,
    "endTick": 129,
    "values": {
      "125": 1.2749526227232495,
      "126": 1.3019525694480605,
      "127": 1.073446660724414,
      "128": 1.0654483722620864,
      "129": 1.061531247396796
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `startTick` | int | Window start tick |
| `endTick` | int | Window end tick |
| `values` | dict | Tick-indexed price map |

**Use Case**: Backfill missed ticks, verify price continuity, latency analysis.

#### Leaderboard (`leaderboard[]`)

Each entry represents a player with active position or recent activity:

```json
{
  "id": "did:privy:cmigqkf0f00x4jm0cuxvdrunq",
  "username": "Fannyman",
  "level": 43,
  "pnl": 0.264879755,
  "regularPnl": 0.264879755,
  "sidebetPnl": 0,
  "shortPnl": 0,
  "pnlPercent": 105.38,
  "hasActiveTrades": true,
  "positionQty": 0.2222919,
  "avgCost": 1.259605046,
  "totalInvested": 0.251352892,
  "sidebetActive": null,
  "sideBet": null,
  "shortPosition": null,
  "selectedCoin": null,
  "position": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique player ID (`did:privy:*`) |
| `username` | string | Display name (null if not set) |
| `level` | int | Player level |
| `pnl` | float | **SERVER-SIDE PnL** (SOL) |
| `regularPnl` | float | PnL from regular trades |
| `sidebetPnl` | float | PnL from sidebets |
| `shortPnl` | float | PnL from shorts |
| `pnlPercent` | float | PnL as percentage |
| `hasActiveTrades` | bool | Has open position |
| `positionQty` | float | Position size (units) |
| `avgCost` | float | Average entry price |
| `totalInvested` | float | Total SOL invested |
| `sidebetActive` | bool/null | Has active sidebet |
| `sideBet` | object/null | Sidebet details |
| `shortPosition` | object/null | Short position details |
| `position` | int | Leaderboard rank |

**Use Case**: PnL verification, position sync, multi-player activity tracking.

#### Rugpool (`rugpool`)

```json
{
  "rugpool": {
    "rugpoolAmount": 1.025,
    "threshold": 10,
    "instarugCount": 2
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rugpoolAmount` | float | Current rugpool SOL |
| `threshold` | int | Instarug trigger threshold |
| `instarugCount` | int | Instarugs this session |

**Use Case**: Instarug prediction - alert when `rugpoolAmount` approaches `threshold`.

#### Game History (`gameHistory[]`)

Array of recent game summaries:

```json
{
  "id": "20251207-1e01ac417e8043ca",
  "timestamp": 1765068982439,
  "prices": [1, 0.99, 1.01, ...],
  "rugged": true,
  "rugPoint": 45.23
}
```

---

### 2. `usernameStatus` (Identity Event) ✅ VERIFIED

**Frequency**: Once on connection (requires wallet auth)
**Purpose**: Player identity confirmation
**Auth Required**: YES - Must be logged in with Phantom wallet

```json
42["usernameStatus",
  {"__trace": true, "traceparent": "00-92cc45541ea050caeb7518ce83e610ec-5d4369ed14c75a17-01"},
  {"id": "did:privy:cmaibr7rt0094jp0mc2mbpfu4", "hasUsername": true, "username": "Dutch"}
]
```

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `id` | string | `"did:privy:cmaibr7rt0094jp0mc2mbpfu4"` | Unique player ID (Privy DID) |
| `username` | string | `"Dutch"` | Display name |
| `hasUsername` | bool | `true` | Whether username is set |
| `__trace` | bool | `true` | Tracing enabled (internal) |
| `traceparent` | string | `"00-..."` | OpenTelemetry trace ID |

**Use Case**:
- Identify "our" player in leaderboard array
- Filter `playerUpdate` events for our player
- Session identity confirmation
- **Validate connection is authenticated**

**Implementation Note**: This event will NOT fire if the user is not logged in with their wallet. Use presence of this event to confirm authenticated session.

---

### 2.5. `playerLeaderboardPosition` (Leaderboard Rank Event) ✅ VERIFIED

**Frequency**: Once on connection (requires wallet auth)
**Purpose**: Player's current leaderboard standing
**Auth Required**: YES - Must be logged in with Phantom wallet

```json
42["playerLeaderboardPosition",
  {"__trace": true, "traceparent": "00-68b4bec76e0efdf689a9091e89dce4dc-bcb52d7918ef5a5b-01"},
  {
    "success": true,
    "period": "7d",
    "sortDirection": "highest",
    "playerFound": true,
    "rank": 1164,
    "total": 2595,
    "playerEntry": {
      "playerId": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
      "username": "Dutch",
      "pnl": -0.015559657000000001
    },
    "surroundingEntries": [...]
  }
]
```

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `success` | bool | `true` | Query successful |
| `period` | string | `"7d"` | Leaderboard period (7-day) |
| `sortDirection` | string | `"highest"` | Sort order |
| `playerFound` | bool | `true` | Player on leaderboard |
| `rank` | int | `1164` | Current rank position |
| `total` | int | `2595` | Total players on leaderboard |
| `playerEntry` | object | `{...}` | Player's leaderboard entry |
| `surroundingEntries` | array | `[...]` | Nearby players |

**playerEntry Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `playerId` | string | Player's Privy DID |
| `username` | string | Display name |
| `pnl` | float | 7-day PnL (SOL) |

**Use Case**:
- Validate authenticated connection (secondary to `usernameStatus`)
- Display player's current leaderboard standing
- Track competitive position over time

---

### 3. `standard/newTrade` (Trade Broadcast)

**Frequency**: On every trade by any player
**Purpose**: Real-time trade feed

```json
{
  "playerId": "did:privy:cm3xxxxxxxxxxxxxx",
  "type": "BUY",
  "amount": 0.001,
  "price": 1.234,
  "timestamp": 1765069123456
}
```

| Field | Type | Description |
|-------|------|-------------|
| `playerId` | string | Trader's player ID |
| `type` | string | `"BUY"` or `"SELL"` |
| `amount` | float | Trade amount (SOL) |
| `price` | float | Execution price |
| `timestamp` | int | Server timestamp (ms) |

**Use Case**:
- Track all market activity
- Whale trade alerts
- Volume analysis
- ML training data (other players' behavior)

---

### 4. `playerUpdate` (Personal State Sync)

**Frequency**: After each of our trades
**Purpose**: Sync local state with server truth

```json
{
  "cash": 3.967072345,
  "cumulativePnL": 0.264879755,
  "positionQty": 0.2222919,
  "avgCost": 1.259605046,
  "totalInvested": 0.251352892
}
```

| Field | Type | Description |
|-------|------|-------------|
| `cash` | float | **TRUE wallet balance** |
| `cumulativePnL` | float | Total PnL this game |
| `positionQty` | float | Current position size |
| `avgCost` | float | Average entry price |
| `totalInvested` | float | Total invested this game |

**Use Case**:
- **Critical for verification layer**
- Compare local `balance` calculation vs server `cash`
- Compare local position vs server `positionQty`
- Detect calculation drift

---

### 5. `gameStatePlayerUpdate` (Personal Leaderboard Entry)

**Frequency**: After each of our trades
**Purpose**: Our leaderboard entry, same structure as `leaderboard[]` items

Same fields as leaderboard entry above, but specifically for the authenticated player.

---

### 6. Sidebet Response (Request/Response)

**Protocol**: Request ID matching (`43XXXX` response to request `42XXXX`)

#### Request (Client → Server)
```
42424["sidebet", {"target": 10, "betSize": 0.001}]
```

#### Response (Server → Client)
```
43424[{"success": true, "timestamp": 1765068967229}]
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Sidebet accepted |
| `timestamp` | int | **Server timestamp** |

**Use Case**:
- Confirm sidebet placement
- Calculate latency: `local_timestamp - server_timestamp`
- Track sidebet success rate

---

### 7. `buyOrder` / `sellOrder` (Trade Requests)

**Protocol**: Request/response pattern

#### Request (Client → Server)
```
42425["buyOrder", {"amount": 0.001}]
42426["sellOrder", {"percentage": 100}]
```

#### Response (Server → Client)
```
43425[{"success": true, "executedPrice": 1.234, "timestamp": 1765069123456}]
```

---

### 8. Other Events

| Event | Description |
|-------|-------------|
| `rugRoyaleUpdate` | Tournament mode updates |
| `battleEventUpdate` | Battle mode updates |
| `newChatMessage` | Chat messages |
| `godCandle50xUpdate` | 50x candle celebration |
| `globalSidebets` | All active sidebets |

---

## Integration Priority

### Priority 1: Verification Layer (Immediate)

| Data Point | Source | Local Equivalent |
|------------|--------|------------------|
| `playerUpdate.cash` | Server | `GameState.balance` |
| `playerUpdate.positionQty` | Server | `Position.amount` |
| `playerUpdate.avgCost` | Server | `Position.entry_price` |
| `leaderboard[me].pnl` | Server | Calculated PnL |

**Implementation**: Compare on every `playerUpdate`, log discrepancies.

### Priority 2: Price History (High)

| Data Point | Source | Use |
|------------|--------|-----|
| `partialPrices.values` | Server | Backfill missed ticks |
| `partialPrices.startTick/endTick` | Server | Continuity verification |

**Implementation**: Fill gaps in local price history.

### Priority 3: Latency Tracking (High)

| Data Point | Source | Use |
|------------|--------|-----|
| `sidebet.timestamp` | Server | Request-to-confirm latency |
| `buyOrder.timestamp` | Server | Trade execution latency |
| `godCandle50xTimestamp` | Server | Event latency |

**Implementation**: `latency = local_receipt_time - server_timestamp`

### Priority 4: Auto-Start (Medium)

| Trigger | Condition |
|---------|-----------|
| Game start | `active: false → true` transition |
| Game end | `rugged: true` or `active: true → false` |
| Player identity | `usernameStatus` received |

**Implementation**: Start recording on game start, stop on rug.

### Priority 5: Rugpool Prediction (Medium)

| Data Point | Use |
|------------|-----|
| `rugpool.rugpoolAmount` | Current pool |
| `rugpool.threshold` | Trigger point |
| Ratio | Alert when approaching |

### Priority 6: Trade Feed (Lower)

| Data Point | Use |
|------------|-----|
| `standard/newTrade` | All player trades |
| Volume analysis | Market activity |
| Whale detection | Large trade alerts |

---

## Files Generated

| File | Purpose |
|------|---------|
| `sandbox/explore_websocket_data.py` | Data collection script |
| `sandbox/websocket_raw_samples.jsonl` | 200 raw samples |
| `sandbox/field_analysis.json` | Field frequency analysis |
| `sandbox/WEBSOCKET_DISCOVERY_REPORT.md` | Initial discovery report |
| `docs/WEBSOCKET_EVENTS_SPEC.md` | This specification |

---

## Next Steps

1. **Extend `_extract_signal()`** in `websocket_feed.py` for Priority 1-3 fields
2. **Add verification hooks** comparing local state to server truth
3. **Implement auto-start** using game state transitions
4. **Add latency dashboard** displaying real-time latency metrics

---

---

## Verification History

| Date | Events Verified | Notes |
|------|-----------------|-------|
| Dec 6, 2025 | `gameStateUpdate` | Initial discovery, 200 samples |
| Dec 9, 2025 | `usernameStatus`, `playerLeaderboardPosition`, `gameStateUpdate` | Live verification, auth requirements confirmed |

---

*Last updated: December 9, 2025 | Version 1.1*
