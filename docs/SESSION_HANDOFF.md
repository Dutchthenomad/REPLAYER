# Session Handoff: Server State Wiring
**Date**: December 9, 2025 | **Branch**: `feat/issue-1-human-demo-recording`

---

## Quick Bootstrap

```
Read this file + docs/plans/2025-12-09-server-state-wiring-plan.md to continue.

Current task: Priority 1 - Wire playerUpdate WebSocket events into recording system.
```

---

## Development Mode: Efficient TDD

**Modified workflow for this phase:**
- Write tests + implementation together per phase
- Run tests at END of each phase (not every step)
- Commit at END of each phase (not every step)
- Avoid redundant verification cycles

**Phases to implement:**
1. **1A**: WebSocketFeed listeners → test + commit
2. **1B**: EventBus events → test + commit
3. **1C**: LiveFeedController integration → test + commit
4. **1D-1E**: Integration verification → test + commit

---

## Context Summary

### What We're Building

Wire `playerUpdate` WebSocket events so recordings capture server truth:

```
playerUpdate (WebSocket) → ServerState → RecordedAction.server_state
```

### Why It Matters

- Current recordings only have `local_state` (REPLAYER calculations)
- Need `server_state` for validation (detect drift between local/server)
- Enables offloading position/balance to server truth (Priority 2)

### What Already Exists

| Component | File | Status |
|-----------|------|--------|
| `ServerState` model | `models/recording_models.py:147` | ✅ Ready |
| `ServerState.from_websocket()` | `models/recording_models.py:173` | ✅ Ready |
| `UnifiedRecorder.update_server_state()` | `services/unified_recorder.py:325` | ✅ Ready |
| `RecordingController.update_server_state()` | `ui/controllers/recording_controller.py:290` | ✅ Ready |
| WebSocket `playerUpdate` listener | `sources/websocket_feed.py` | ❌ Missing |

### What We're Adding

1. **websocket_feed.py**: `usernameStatus` + `playerUpdate` listeners
2. **event_bus.py**: `PLAYER_IDENTITY` + `PLAYER_UPDATE` event types
3. **live_feed_controller.py**: Subscribe to events, forward to recorder

---

## Key Files

| File | Purpose |
|------|---------|
| `src/sources/websocket_feed.py` | WebSocket connection (add listeners here) |
| `src/services/event_bus.py` | Event types |
| `src/ui/controllers/live_feed_controller.py` | Forwards to recorder |
| `src/ui/controllers/recording_controller.py` | Already has update_server_state() |
| `src/services/unified_recorder.py` | Caches _last_server_state |
| `docs/WEBSOCKET_EVENTS_SPEC.md` | Protocol reference |

---

## WebSocket Events Format

### usernameStatus (once on connect)
```json
{"id": "did:privy:cm3xxx", "username": "Dutch"}
```

### playerUpdate (after each trade)
```json
{
  "cash": 3.967072345,
  "cumulativePnL": 0.264879755,
  "positionQty": 0.2222919,
  "avgCost": 1.259605046,
  "totalInvested": 0.251352892
}
```

---

## Implementation Order

### Phase 1A: WebSocketFeed (~40 lines)

**Add to `_setup_event_listeners()`:**

```python
# Player state
self.player_id: Optional[str] = None
self.username: Optional[str] = None
self.last_player_update: Optional[dict] = None

@self.sio.on('usernameStatus')
def on_username_status(data):
    try:
        self.player_id = data.get('id')
        self.username = data.get('username')
        self.logger.info(f'👤 Identity: {self.username}')
        self._emit_event('player_identity', data)
    except Exception as e:
        self.logger.error(f"Error in usernameStatus: {e}")
        self.metrics['errors'] += 1

@self.sio.on('playerUpdate')
def on_player_update(data):
    try:
        self.last_player_update = data
        self._emit_event('player_update', data)
    except Exception as e:
        self.logger.error(f"Error in playerUpdate: {e}")
        self.metrics['errors'] += 1
```

### Phase 1B: EventBus (~5 lines)

**Add to `Events` class:**

```python
PLAYER_IDENTITY = 'player_identity'
PLAYER_UPDATE = 'player_update'
```

### Phase 1C: LiveFeedController (~50 lines)

**Add subscriptions in `enable_live_feed()`:**

```python
@self.parent.live_feed.on('player_identity')
def on_player_identity(info):
    # Marshal to Tk thread, set player info on recorder

@self.parent.live_feed.on('player_update')
def on_player_update(data):
    # Create ServerState.from_websocket(data)
    # Call recording_controller.update_server_state()
```

---

## Test Strategy

Run at end of each phase:
```bash
cd src && python3 -m pytest tests/test_sources/test_websocket_feed.py -v
cd src && python3 -m pytest tests/test_ui/test_live_feed_controller.py -v
```

Final integration verification:
```bash
cd src && python3 -m pytest tests/ -k "server_state or player_update" -v
```

---

## Verification (After All Phases)

1. Run REPLAYER with live feed
2. Check logs for `👤 Identity: <username>`
3. Make a trade, check logs for playerUpdate
4. Stop recording, examine output file for `server_state` field

---

## Priority Stack (After This)

| # | Task | Status |
|---|------|--------|
| 1 | Wire Server State | IN PROGRESS |
| 2 | Offload to Server | Pending |
| 3 | Record 20-30 Games | Pending |
| 4 | RAG Knowledge Base | Pending |
| 5 | Core Bot Framework | Pending |
| 6 | RL Feature Engineering | Pending |

---

## Related Documents

- `docs/plans/2025-12-09-session-summary.md` - Full context
- `docs/plans/2025-12-09-server-state-wiring-plan.md` - Detailed plan
- `docs/plans/2025-12-09-demo-recording-analysis.md` - Recording analysis
- `docs/WEBSOCKET_EVENTS_SPEC.md` - Protocol reference

---

*Session handoff complete. Resume with Phase 1A implementation.*
