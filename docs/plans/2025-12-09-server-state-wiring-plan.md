# Server State Wiring Plan
**Priority 1** | **Date**: December 9, 2025 | **Status**: Planning

---

## Objective

Wire `playerUpdate` WebSocket events into the recording system to capture server truth alongside local state for dual-state validation.

---

## Current State Analysis

### What Exists

| Component | Status | Details |
|-----------|--------|---------|
| `ServerState` model | ✅ Complete | `recording_models.py:147-182` |
| `LocalStateSnapshot` model | ✅ Complete | `recording_models.py:186-220` |
| `validate_states()` function | ✅ Complete | `recording_models.py:313-359` |
| `UnifiedRecorder.update_server_state()` | ✅ Complete | `unified_recorder.py:325-332` |
| `UnifiedRecorder._last_server_state` | ✅ Complete | Caches last server state |
| `RecordingController.update_server_state()` | ✅ Complete | `recording_controller.py:290-300` |
| `WebSocketFeed` `playerUpdate` listener | ❌ Missing | Only listens to `gameStateUpdate` |

### What's Missing

1. **WebSocketFeed**: No listener for `playerUpdate` or `usernameStatus` events
2. **EventBus**: No event type for player state updates
3. **LiveFeedController**: No subscription to forward player updates
4. **Player Identity**: Not tracking which player "we" are (needed to filter leaderboard)

---

## WebSocket Events to Capture

### `usernameStatus` (Identity - Once on Connect)

```json
{
  "id": "did:privy:cm3xxxxxxxxxxxxxx",
  "username": "Dutch"
}
```

**Purpose**: Identify our player ID for filtering leaderboard entries

### `playerUpdate` (After Each Trade)

```json
{
  "cash": 3.967072345,
  "cumulativePnL": 0.264879755,
  "positionQty": 0.2222919,
  "avgCost": 1.259605046,
  "totalInvested": 0.251352892
}
```

**Purpose**: Server truth for position/balance validation

---

## Implementation Plan

### Phase 1A: WebSocketFeed Event Listeners

**File**: `src/sources/websocket_feed.py`

**Changes**:

1. Add player identity state:
```python
# In __init__
self.player_id: Optional[str] = None
self.username: Optional[str] = None
self.last_player_update: Optional[dict] = None
```

2. Add `usernameStatus` listener in `_setup_event_listeners()`:
```python
@self.sio.on('usernameStatus')
def on_username_status(data):
    try:
        self.player_id = data.get('id')
        self.username = data.get('username')
        self.logger.info(f'👤 Identity confirmed: {self.username} ({self.player_id[:20]}...)')
        self._emit_event('player_identity', {
            'player_id': self.player_id,
            'username': self.username
        })
    except Exception as e:
        self.logger.error(f"Error in usernameStatus handler: {e}", exc_info=True)
        self.metrics['errors'] += 1
```

3. Add `playerUpdate` listener:
```python
@self.sio.on('playerUpdate')
def on_player_update(data):
    try:
        self.last_player_update = data
        self.logger.debug(f'💰 Player update: cash={data.get("cash"):.4f}, pos={data.get("positionQty"):.4f}')
        self._emit_event('player_update', data)
    except Exception as e:
        self.logger.error(f"Error in playerUpdate handler: {e}", exc_info=True)
        self.metrics['errors'] += 1
```

4. Add accessor method:
```python
def get_player_info(self) -> dict:
    """Get current player identity and state."""
    return {
        'player_id': self.player_id,
        'username': self.username,
        'last_update': self.last_player_update
    }
```

**Tests to Add**:
- `test_websocket_feed_player_identity()`
- `test_websocket_feed_player_update()`
- `test_websocket_feed_player_update_caching()`

---

### Phase 1B: EventBus Event Types

**File**: `src/services/event_bus.py`

**Changes**:

Add new event types:
```python
class Events:
    # ... existing events ...

    # Phase 10.7: Player state events
    PLAYER_IDENTITY = 'player_identity'
    PLAYER_UPDATE = 'player_update'
```

**Tests**: Update event bus tests to include new event types

---

### Phase 1C: LiveFeedController Integration

**File**: `src/ui/controllers/live_feed_controller.py`

**Changes**:

1. Add player state tracking:
```python
# In __init__
self._player_id: Optional[str] = None
self._username: Optional[str] = None
```

2. Subscribe to `player_identity` event in `enable_live_feed()`:
```python
@self.parent.live_feed.on('player_identity')
def on_player_identity(info):
    info_snapshot = dict(info) if hasattr(info, 'items') else {}

    def handle_identity(captured_info=info_snapshot):
        self._player_id = captured_info.get('player_id')
        self._username = captured_info.get('username')
        self.log(f"👤 Logged in as: {self._username}")

        # Set player info on recording controller
        if self._recording_controller:
            self._recording_controller.set_player_info(
                self._player_id,
                self._username
            )

        # Publish to EventBus
        from services.event_bus import Events
        self.event_bus.publish(Events.PLAYER_IDENTITY, captured_info)

    self.root.after(0, handle_identity)
```

3. Subscribe to `player_update` event:
```python
@self.parent.live_feed.on('player_update')
def on_player_update(data):
    data_snapshot = dict(data) if hasattr(data, 'items') else {}

    def handle_update(captured_data=data_snapshot):
        # Create ServerState from WebSocket data
        from models.recording_models import ServerState
        server_state = ServerState.from_websocket(captured_data)

        # Forward to recording controller
        if self._recording_controller:
            self._recording_controller.update_server_state(server_state)

        # Publish to EventBus for other consumers
        from services.event_bus import Events
        self.event_bus.publish(Events.PLAYER_UPDATE, {
            'server_state': server_state,
            'raw_data': captured_data
        })

    self.root.after(0, handle_update)
```

**Tests to Add**:
- `test_live_feed_controller_player_identity()`
- `test_live_feed_controller_player_update_forwarding()`

---

### Phase 1D: Recording Controller Wiring

**File**: `src/ui/controllers/recording_controller.py`

**Status**: Already complete. The `update_server_state()` method exists and forwards to UnifiedRecorder.

**Verification**: Write integration test confirming flow:
1. WebSocket emits `playerUpdate`
2. LiveFeedController receives and creates `ServerState`
3. RecordingController.update_server_state() called
4. UnifiedRecorder._last_server_state updated
5. Next button press includes server_state in RecordedAction

---

### Phase 1E: Data Flow Verification

**Integration Test**: `test_server_state_end_to_end.py`

```python
def test_server_state_capture_in_recording():
    """Verify server state is captured in recorded actions."""
    # 1. Setup: Create mock WebSocket feed with playerUpdate
    # 2. Connect and receive usernameStatus
    # 3. Receive playerUpdate with known values
    # 4. Trigger button press via TradingController
    # 5. Verify RecordedAction contains server_state
    # 6. Verify drift_detected flag is correct
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WEBSOCKET SERVER                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            usernameStatus    playerUpdate    gameStateUpdate
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WebSocketFeed                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ player_id    │  │ last_player_ │  │ last_signal  │                      │
│  │ username     │  │ update       │  │              │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
│           │               │                  │                              │
│           ▼               ▼                  ▼                              │
│    emit('player_   emit('player_      emit('signal')                       │
│     identity')      update')                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                    │               │
                    ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LiveFeedController                                    │
│  ┌──────────────┐  ┌──────────────────────────────────┐                    │
│  │ _player_id   │  │ Creates ServerState.from_ws()    │                    │
│  │ _username    │  │ Calls recording_controller.      │                    │
│  └──────────────┘  │        update_server_state()     │                    │
│           │        └──────────────────────────────────┘                    │
│           │                       │                                         │
│           ▼                       ▼                                         │
│   set_player_info()      EventBus.publish(PLAYER_UPDATE)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RecordingController                                   │
│  ┌────────────────────────────────────────────────────┐                    │
│  │ update_server_state(server_state) → UnifiedRecorder │                   │
│  └────────────────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UnifiedRecorder                                     │
│  ┌──────────────────┐                                                       │
│  │ _last_server_    │ ◄── Cached for next button press                     │
│  │ state            │                                                       │
│  └──────────────────┘                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  record_button_press() includes server_state in RecordedAction             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Changes Summary

| File | Changes | Lines Est. |
|------|---------|------------|
| `websocket_feed.py` | Add `usernameStatus`, `playerUpdate` listeners | +40 |
| `event_bus.py` | Add `PLAYER_IDENTITY`, `PLAYER_UPDATE` events | +5 |
| `live_feed_controller.py` | Subscribe to player events, forward to recorder | +50 |
| `test_websocket_feed.py` | Tests for new listeners | +60 |
| `test_live_feed_controller.py` | Tests for player event handling | +40 |
| `test_server_state_integration.py` | End-to-end integration test | +80 |

**Total**: ~275 lines (implementation + tests)

---

## Verification Checklist

After implementation, verify with live session:

- [ ] `usernameStatus` received on connect
- [ ] Player ID logged correctly
- [ ] `playerUpdate` received after each trade
- [ ] `ServerState` created from WebSocket data
- [ ] `RecordingController.update_server_state()` called
- [ ] `UnifiedRecorder._last_server_state` populated
- [ ] Recorded actions include `server_state` field
- [ ] `drift_detected` flag set correctly when local != server
- [ ] Recording file contains dual-state data

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| `playerUpdate` format differs from spec | Log raw data first, validate before parsing |
| Event timing (update before trade recorded) | Cache last state, use cached if no fresh update |
| Thread safety | All handlers use `root.after()` for Tk thread |
| Performance (frequent updates) | Only cache, don't process on every update |

---

## Success Criteria

1. **Recording includes server_state**: Every `RecordedAction` has both `local_state` and `server_state`
2. **Drift detection works**: When local != server, `drift_detected: true`
3. **Player identity tracked**: Recordings include `player_id` and `username`
4. **No toast confusion**: Sidebet status correctly tracked via server state

---

## Next Steps After Completion

1. **Verify with 1 game** - Test recording with server state
2. **Record 20-30 games** - Build behavioral dataset (Priority 3)
3. **Priority 2**: Refactor to use server as source of truth for position/balance

---

*Plan complete. Ready for TDD implementation.*
