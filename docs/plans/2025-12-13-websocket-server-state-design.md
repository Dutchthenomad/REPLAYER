# WebSocket Server State Integration Design

**Date**: 2025-12-13
**Status**: Approved
**Author**: Dutch + Claude

---

## Overview

Two parallel development branches to fix WebSocket integration and build a RAG knowledge system:

| Branch | Issue | Purpose |
|--------|-------|---------|
| `fix/issue-8-websocket-server-state` | #8 | Fix WebSocket integration with hardcoded credentials |
| `feat/issue-9-socket-event-rag` | #9 | Socket event recording for RAG framework |

---

## Branch A: WebSocket Server State Integration

### Problem

- 10 failing tests expect player identity/state methods that don't exist
- Server only sends `usernameStatus` and `playerUpdate` to authenticated clients
- Our WebSocket connection is read-only/unauthenticated
- UI shows local state but never syncs with server truth

### Solution: Hardcoded Credentials Fallback

Parse player data from the public `gameStatePlayerUpdate` leaderboard entries using hardcoded credentials.

### Hardcoded Credentials

```python
HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"
HARDCODED_USERNAME = "Dutch"
```

### Data Flow

```
gameStateUpdate (every ~250ms)
    │
    ├── leaderboard[] array
    │       │
    │       └── Find entry where id == HARDCODED_PLAYER_ID
    │               │
    │               └── Extract all trading fields
    │
    └── ServerState object
            │
            ├── GameState.reconcile_with_server() → silent update
            │
            └── Persist to session file
```

### Fields to Extract

| Field | Description | UI Target |
|-------|-------------|-----------|
| `cash` | Wallet balance | Balance label |
| `pnl` | Profit/loss in SOL | Position panel |
| `pnlPercent` | P&L as percentage | Position panel |
| `positionQty` | Current position size | Position panel |
| `avgCost` | Average entry price | Position panel |
| `totalInvested` | Total SOL invested | Position panel |
| `hasActiveTrades` | Boolean - in position? | Position indicator |
| `sidebet` | Active sidebet info | Sidebet display |

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth approach | Hardcoded credentials | Works now, no server changes needed |
| UI changes | Update existing displays | Minimal changes, wire into current components |
| State conflicts | Server wins silently | Server is truth, auto-correct local state |
| Persistence | Save to session | State persists across sessions |
| Test approach | Delete failing, write new | Tests were for different design |

### Files to Modify

| File | Changes |
|------|---------|
| `src/sources/websocket_feed.py` | Add leaderboard parsing, player filtering, emit `player_state_update` event |
| `src/ui/controllers/live_feed_controller.py` | Subscribe to `player_state_update`, forward to GameState |
| `src/core/game_state.py` | Ensure `reconcile_with_server()` handles all fields silently |
| `src/ui/main_window.py` | Verify balance/position displays update from state changes |
| `src/tests/test_sources/test_websocket_feed.py` | Delete 10 failing tests, write new ones |

### Implementation Tasks

1. Add hardcoded credentials constants to `websocket_feed.py`
2. Parse leaderboard array in `_handle_game_state_update()`
3. Filter for `HARDCODED_PLAYER_ID` entry
4. Extract all trading fields into `ServerState` object
5. Emit `player_state_update` event
6. Update `LiveFeedController` to handle event
7. Call `GameState.reconcile_with_server()` with server data
8. Verify UI displays update correctly
9. Add session persistence for server state
10. Delete 10 failing tests
11. Write new tests for hardcoded approach

---

## Branch B: Socket Event RAG Pipeline

### Purpose

Build a comprehensive event recording and categorization system that will feed into the claude-flow RAG framework for a dedicated rugs.fun expert agent.

### Architecture

```
WebSocket Server
    │
    └── ALL events (gameStateUpdate, newTrade, chat, etc.)
            │
            └── RawEventRecorder
                    │
                    ├── raw_events/{date}/{session}.jsonl  (raw capture)
                    │
                    ├── EventCategorizer
                    │       └── Classify: game_state, trade, chat, system, etc.
                    │
                    └── RAGIngestionQueue
                            └── Feed to claude-flow RAG system when ready
```

### Event Categories

| Category | Events | Purpose |
|----------|--------|---------|
| `game_state` | gameStateUpdate | Price/tick data |
| `trade` | newTrade, buyOrder, sellOrder | Trading activity |
| `player` | playerUpdate, usernameStatus | Player state |
| `social` | newChatMessage | Chat messages |
| `system` | connect, disconnect, error | Connection events |
| `battle` | battleEventUpdate | Battle mode events |

### Files to Create

| File | Purpose |
|------|---------|
| `src/sources/event_recorder.py` | Capture ALL socket events raw |
| `src/sources/event_categorizer.py` | Classify events by type |
| `src/rag/ingestion_queue.py` | Queue for RAG pipeline |
| `raw_events/` | Storage directory (gitignored) |

### Storage Format

```jsonl
{"timestamp": "2025-12-13T20:45:00.123Z", "event": "gameStateUpdate", "category": "game_state", "data": {...}}
{"timestamp": "2025-12-13T20:45:00.456Z", "event": "standard/newTrade", "category": "trade", "data": {...}}
```

### Implementation Phases

1. **Phase 1**: Raw event capture to JSONL files
2. **Phase 2**: Event categorization and indexing
3. **Phase 3**: Integration with claude-flow RAG system

### Integration Point

Branch B will integrate with `/home/nomad/Desktop/claude-flow/rag-pipeline/` once that system is ready.

---

## Branch Dependencies

```
main
├── fix/issue-8-websocket-server-state    (Branch A - no dependencies)
│
└── feat/issue-9-socket-event-rag         (Branch B - no dependencies)
```

Both branches can develop in parallel. Neither depends on the other.

---

## Success Criteria

### Branch A
- [ ] All trading fields extracted from leaderboard
- [ ] UI displays server state (balance, PnL, position)
- [ ] State persists across sessions
- [ ] Server state silently corrects local drift
- [ ] New tests pass for hardcoded approach
- [ ] 0 failing tests

### Branch B
- [ ] All socket events captured to JSONL
- [ ] Events categorized by type
- [ ] Storage organized by date/session
- [ ] Ready for RAG pipeline integration

---

## References

- `docs/specs/WEBSOCKET_EVENTS_SPEC.md` - Event documentation
- `src/sources/websocket_feed.py` - Current implementation
- `src/core/game_state.py` - State management with reconciliation
- `/home/nomad/Desktop/claude-flow/rag-pipeline/` - Future RAG integration
