# WebSocket Foundation Layer Design
**Phase 10.4 Revised** | **Date**: December 7, 2025 | **Status**: In Design

---

## 1. Overview

### Purpose
Build the data foundation for RL/ML training by capturing complete, accurate game and player state from the WebSocket feed.

### Primary Driver
**Training Data Quality** - The foundation layer upon which all advanced ML/RL models will be built. Garbage in = garbage out. This must be rock solid.

### Vision
- Record human gameplay with complete context (prices + actions)
- Enable "player piano" bot mode - visually play through UI with animated buttons
- Provide data for mathematically/statistically optimal gameplay development
- Support future advanced features (PRNG analysis, Bayesian probabilities, treasury algorithm reverse engineering)

---

## 2. Data Architecture

### Two Distinct Layers

#### Game State Layer (the "board")
- Tick-by-tick price data
- Pure market data, no player-specific info
- One file per game
- Used for: chart animation, ML training context

#### Player State Layer (the "moves")
- Actions (BUY, SELL, SIDEBET)
- Balance, position, PnL at each action
- Links to game state via `game_id + tick`
- Used for: action replay, bot ghost mode, ML training labels

### Data Flow
```
WebSocket Events                    Storage
─────────────────                   ───────
gameStateUpdate.price      ───────► Game State File (prices array)
gameStateUpdate.partialPrices ────► Gap filling in prices array
usernameStatus             ───────► Player identity (session metadata)
playerUpdate               ───────► Server state verification
User actions (BUY/SELL)    ───────► Player State File (actions array)
```

---

## 3. File Structure

### Directory Layout
```
recordings/
├── 2025-12-07/
│   ├── games/
│   │   ├── 20251207T143022_e9ac71e7.game.json
│   │   └── 20251207T143245_f8bd92a3.game.json
│   ├── sessions/
│   │   └── 20251207T143000_dutch_session.json
│   └── index.json  ← sortable metadata for all games
```

### Game State File Format
**Filename**: `{ISO_timestamp}_{game_id_short}.game.json`

```json
{
  "meta": {
    "game_id": "20251207-e9ac71e78ebe4f83",
    "start_time": "2025-12-07T14:30:22.456Z",
    "end_time": "2025-12-07T14:32:45.789Z",
    "duration_ticks": 143,
    "peak_multiplier": 45.23,
    "server_seed_hash": "abc123...",
    "server_seed": "xyz789..."
  },
  "prices": [1.0, 1.01, 0.99, 1.03, ...]
}
```

**Metadata Fields** (for sorting/filtering):
- `game_id` - Unique identifier, links to player state
- `start_time` / `end_time` - Exact timestamps (chronological sorting)
- `duration_ticks` - Total game length
- `peak_multiplier` - Maximum price reached (outcome)
- `server_seed_hash` - Before reveal (provably fair)
- `server_seed` - After reveal (provably fair verification)

### Player State File Format
**Filename**: `{ISO_timestamp}_{username}_session.json`

```json
{
  "meta": {
    "player_id": "did:privy:cm3xxx",
    "username": "Dutch",
    "session_start": "2025-12-07T14:30:00.000Z",
    "session_end": "2025-12-07T15:45:00.000Z"
  },
  "actions": [
    {
      "game_id": "20251207-e9ac71e78ebe4f83",
      "tick": 12,
      "timestamp": "2025-12-07T14:30:34.567Z",
      "action": "BUY",
      "amount": 0.001,
      "price": 1.234,
      "balance_after": 0.999,
      "position_qty_after": 0.001,
      "entry_price": 1.234
    },
    {
      "game_id": "20251207-e9ac71e78ebe4f83",
      "tick": 89,
      "timestamp": "2025-12-07T14:31:56.789Z",
      "action": "SELL",
      "amount": 0.001,
      "price": 2.567,
      "balance_after": 1.001,
      "position_qty_after": 0.0,
      "pnl": 0.002
    }
  ]
}
```

### Index File Format
**Filename**: `index.json` (one per day directory)

```json
{
  "date": "2025-12-07",
  "games": [
    {
      "file": "20251207T143022_e9ac71e7.game.json",
      "game_id": "20251207-e9ac71e78ebe4f83",
      "start_time": "2025-12-07T14:30:22.456Z",
      "duration_ticks": 143,
      "peak_multiplier": 45.23
    },
    {
      "file": "20251207T143245_f8bd92a3.game.json",
      "game_id": "20251207-f8bd92a38abc1234",
      "start_time": "2025-12-07T14:32:45.789Z",
      "duration_ticks": 87,
      "peak_multiplier": 12.1
    }
  ],
  "sessions": [
    {
      "file": "20251207T143000_dutch_session.json",
      "player_id": "did:privy:cm3xxx",
      "username": "Dutch",
      "games_played": 2,
      "total_actions": 15
    }
  ]
}
```

---

## 4. WebSocket Data Sources

### Events to Capture

| Event | Data | Purpose |
|-------|------|---------|
| `gameStateUpdate.price` | Current tick price | Primary price data |
| `gameStateUpdate.partialPrices` | Recent price window | Gap filling |
| `gameStateUpdate.tickCount` | Current tick | Array indexing |
| `gameStateUpdate.gameId` | Game identifier | File linking |
| `gameStateUpdate.rugged` | Game ended | Trigger save |
| `gameStateUpdate.gameHistory[0]` | Completed game metadata | seed, peak, etc. |
| `usernameStatus` | Player ID, username | Session identity |
| `playerUpdate` | cash, positionQty, avgCost | Server state verification |

### Price History Handling
**Approach**: Merge on capture (Option A)

- Build complete `prices[]` array in memory as ticks arrive
- Use `partialPrices` to backfill any gaps (missed ticks due to latency)
- On game end, save clean array to file
- No raw window storage (minimal, efficient)

### Events NOT Captured (this phase)
- `standard/newTrade` - Other player trades (future: meta analysis)
- `rugpool` - Side game mechanics (future: instarug prediction)
- `battleEventUpdate` - Battle mode (out of scope)
- `newChatMessage` - Chat (out of scope)

---

## 5. Code Architecture

### Current Problem
`websocket_feed.py` is **1212 lines** - monolithic, hard to maintain.

### Modular Refactor

**Before** (monolithic):
```
sources/
└── websocket_feed.py (1212 lines)
    ├── LatencySpikeDetector
    ├── ConnectionHealthMonitor
    ├── GracefulDegradationManager
    ├── TokenBucketRateLimiter
    └── WebSocketFeed
```

**After** (modular):
```
sources/
├── websocket_feed.py        (~400 lines) - Core feed, Socket.IO handlers
├── feed_monitors.py         (~300 lines) - LatencySpikeDetector, ConnectionHealthMonitor
├── feed_rate_limiter.py     (~100 lines) - TokenBucket, PriorityRateLimiter
├── feed_degradation.py      (~170 lines) - GracefulDegradationManager
├── player_state_handler.py  (~150 lines) - NEW: usernameStatus, playerUpdate handlers
├── price_history_handler.py (~100 lines) - NEW: partialPrices merging, gap detection
└── game_state_machine.py    (existing)   - Already extracted
```

### Module Responsibilities

#### `websocket_feed.py` (core)
- Socket.IO connection management
- Event listener setup
- Event emission to subscribers
- Imports and uses other modules

#### `feed_monitors.py`
- `LatencySpikeDetector` - Detect latency anomalies
- `ConnectionHealthMonitor` - Track connection health
- `ConnectionHealth` enum

#### `feed_rate_limiter.py`
- `TokenBucketRateLimiter` - Flood protection
- `PriorityRateLimiter` - Critical signal bypass

#### `feed_degradation.py`
- `GracefulDegradationManager` - Reduce functionality under stress
- `OperatingMode` enum

#### `player_state_handler.py` (NEW)
- Handle `usernameStatus` event → store player identity
- Handle `playerUpdate` event → emit for verification
- Handle `gameStatePlayerUpdate` event → personal leaderboard

#### `price_history_handler.py` (NEW)
- Maintain in-memory `prices[]` array per game
- Process `partialPrices` → fill gaps
- Detect missing ticks
- Provide complete array on game end

---

## 6. Integration Points

### Event Flow
```
WebSocketFeed
  │
  ├─── 'signal' (existing) ──────────────► GameState
  │                                         │
  ├─── 'player_identified' (new) ──────────► GameState (stores player_id)
  │                                         │
  ├─── 'server_state_update' (new) ────────► StateVerifier
  │                                         │ (compares local vs server)
  │                                         │
  ├─── 'price_tick' (new) ─────────────────► PriceHistoryHandler
  │                                         │ (builds prices array)
  │                                         │
  └─── 'game_complete' (existing) ─────────► GameStateRecorder
                                            │ (saves game file)
                                            │
                                            ► PlayerStateRecorder
                                              (saves session file)
```

### New Components

#### StateVerifier
- Compares local `GameState` to server `playerUpdate`
- Logs drift when `balance` or `position` doesn't match
- Tolerance: 0.000001 (dust threshold)

#### PriceHistoryHandler
- Subscribes to `gameStateUpdate` ticks
- Builds `prices[]` array indexed by tick
- Uses `partialPrices` to fill gaps
- Emits `price_history_complete` on game end

#### GameStateRecorder
- Subscribes to `game_complete` event
- Writes game state file with metadata + prices
- Updates daily index.json

#### PlayerStateRecorder
- Tracks actions during session
- Links actions to games via `game_id + tick`
- Writes session file on stop/disconnect

---

## 7. Scope & Non-Goals

### In Scope (Phase 10.4)
- [x] Modular refactor of websocket_feed.py
- [x] Player identity capture (usernameStatus)
- [x] Server state sync (playerUpdate)
- [x] Price history with gap filling (partialPrices)
- [x] StateVerifier for drift detection
- [x] Game state file format and recorder
- [x] Player state file format and recorder
- [x] Index file for sorting/filtering

### Out of Scope (Future Phases)
- Auto-start recording on game transitions (Phase 10.5)
- Replayer UI updates for new format (separate phase)
- Other player trade feed (distant future)
- Rugpool/instarug prediction (distant future)
- PRNG reverse engineering (distant future)
- Treasury algorithm analysis (distant future)

---

## 8. Success Criteria

1. **Complete Price Data**: Every game has gap-free `prices[]` array
2. **Player Identity**: `player_id` captured on WebSocket connect
3. **Server Verification**: `playerUpdate` compared to local state, drift logged
4. **Clean Files**: Game state and player state saved as separate JSON files
5. **Sortable Index**: Daily index.json with queryable metadata
6. **Modular Code**: All source files under 400 lines
7. **Test Coverage**: New tests for all new modules
8. **Backward Compatible**: All existing 275+ tests still pass

---

## 9. Open Questions

*To be resolved in remaining design sections:*

1. Data Models - Exact Python class definitions
2. Recorder Integration - How recorders wire to existing DemoRecorderSink
3. Migration - How to handle existing recordings
4. Testing Strategy - Unit vs integration test boundaries

---

## 10. References

- GitHub Issue: #2 (Phase 10.4)
- WebSocket Protocol: `docs/WEBSOCKET_EVENTS_SPEC.md`
- Original Plan: `docs/PHASE_10_4_PLAN.md`
- Session Handoff: `sandbox/SESSION_HANDOFF_PHASE_10_4.md`

---

*Design in progress - Sections 2-4 pending*
