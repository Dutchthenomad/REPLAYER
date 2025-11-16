# Live Feed Log Analysis - Issue Identification

**Date**: 2025-11-16 12:00:00 - 12:01:30
**Status**: 🔍 Issues Identified

---

## 📊 Issues Found in Logs

### Issue #1: Illegal State Transitions [MEDIUM]
**Severity**: MEDIUM (Warnings, not crashes)
**Frequency**: 4 occurrences in 1 minute

```
2025-11-16 12:00:07 - root - WARNING - Illegal transition: PRESALE → ACTIVE_GAMEPLAY
                                      (allowed: ['PRESALE', 'GAME_ACTIVATION'])
2025-11-16 12:00:07 - root - WARNING - Invalid state transition detected (anomaly #1)
2025-11-16 12:00:07 - root - WARNING - Invalid state transition detected (anomaly #2)
2025-11-16 12:00:07 - root - WARNING - Invalid state transition detected (anomaly #3)
2025-11-16 12:00:07 - root - WARNING - Invalid state transition detected (anomaly #4)
```

**Root Cause**:
- Game state machine in `websocket_feed.py` expects: PRESALE → GAME_ACTIVATION → ACTIVE_GAMEPLAY
- Backend sends: PRESALE → ACTIVE_GAMEPLAY (skips GAME_ACTIVATION)
- State machine is TOO STRICT for actual backend behavior

**Impact**:
- ⚠️ Warnings spam logs
- ⚠️ Anomaly counter increments
- ✅ Data still processed correctly (non-blocking)
- ✅ System continues working

**Fix**: Make state machine more permissive (allow direct PRESALE → ACTIVE_GAMEPLAY transition)

---

### Issue #2: Duplicate Connection Events [LOW]
**Severity**: LOW (Cosmetic, no functional impact)
**Frequency**: Every connection

```
2025-11-16 12:00:01 - INFO - ✅ Live feed connected (Socket ID: None)
2025-11-16 12:00:07 - INFO - ✅ Live feed connected (Socket ID: U9xnN4Ib1mVZKhMuAD6t)
```

**Root Cause**:
- Socket.IO `connect` event fires TWICE
- First time: Socket ID not yet available (None)
- Second time: Socket ID assigned (U9xnN4Ib1mVZKhMuAD6t)
- This is normal Socket.IO behavior during connection negotiation

**Impact**:
- ⚠️ Two "Live feed connected" toasts shown
- ⚠️ Checkbox might flicker
- ✅ Connection works correctly

**Fix**: Debounce connection event or only show toast when Socket ID is available

---

### Issue #3: Unstable Connection [MEDIUM]
**Severity**: MEDIUM (Affects reliability)
**Frequency**: Multiple disconnections in 1 minute

```
2025-11-16 11:59:53 - WARNING - ❌ Disconnected from backend
2025-11-16 12:00:31 - ERROR - packet queue is empty, aborting
2025-11-16 12:00:47 - WARNING - ❌ Disconnected from backend
2025-11-16 12:00:55 - ERROR - 🚨 Connection error: Connection error
2025-11-16 12:01:23 - ERROR - packet queue is empty, aborting
```

**Pattern**:
- Connect → Works for ~1 minute → Disconnect → Reconnect → Repeat

**Root Cause** (Likely):
1. **Backend keep-alive timeout**: Backend closes idle connections after 30-60 seconds
2. **Network instability**: WiFi/network interruptions
3. **Socket.IO ping/pong timeout**: Client not responding to backend pings
4. **Firewall/proxy interference**: Intermediate network equipment dropping long-lived WebSocket connections

**Impact**:
- ⚠️ Frequent reconnections
- ⚠️ Missed game data during disconnection windows (5-10 seconds each)
- ⚠️ User sees "disconnected" toasts repeatedly
- ✅ Auto-reconnect works (connection restores)

**Fix**:
- Implement keep-alive ping mechanism
- Increase reconnection backoff delay
- Add connection health monitoring

---

### Issue #4: "Packet Queue Empty" Errors [LOW]
**Severity**: LOW (Normal disconnection behavior)
**Frequency**: Every disconnection

```
2025-11-16 12:00:31 - engineio.client - ERROR - packet queue is empty, aborting
2025-11-16 12:01:23 - engineio.client - ERROR - packet queue is empty, aborting
```

**Root Cause**:
- This is Socket.IO's internal error when connection drops
- Not actually an error - just Socket.IO logging disconnection
- Logged at ERROR level by python-socketio library (can't change)

**Impact**:
- ⚠️ Scary ERROR messages in logs
- ✅ No functional impact (expected behavior)

**Fix**: Suppress these specific ERROR messages (they're normal)

---

## 📈 Positive Observations

### ✅ What's Working:
1. **Live feed connects successfully** ✅
2. **Games are recorded** ✅
   - game_20251116_115951.jsonl (131 ticks, 27KB)
   - game_20251116_120007.jsonl (24 ticks, 5.6KB)
3. **Multi-game detection works** ✅
   - Detected game transitions correctly
   - Auto-started new recordings
4. **RUG EVENT detection works** ✅
   - "RUG EVENT detected at tick 119"
5. **Auto-reconnect works** ✅
   - Connection restored after disconnections

---

## 🎯 Priority Fixes

### Priority 1: Fix State Transition Warnings [MEDIUM]
**File**: `src/sources/websocket_feed.py`
**Location**: Line ~131 (legal_transitions map)

**Current**:
```python
legal_transitions = {
    'PRESALE': ['PRESALE', 'GAME_ACTIVATION'],  # ❌ Too strict!
    'GAME_ACTIVATION': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
    'ACTIVE_GAMEPLAY': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
    ...
}
```

**Fix**:
```python
legal_transitions = {
    'PRESALE': ['PRESALE', 'GAME_ACTIVATION', 'ACTIVE_GAMEPLAY'],  # ✅ Allow direct jump
    'GAME_ACTIVATION': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
    'ACTIVE_GAMEPLAY': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
    ...
}
```

---

### Priority 2: Debounce Duplicate Connection Events [LOW]
**File**: `src/ui/main_window.py`
**Location**: Line ~548 (handle_connected)

**Current**:
```python
def handle_connected():
    self.live_feed_connected = True
    self.live_feed_var.set(True)
    self.log(f"✅ Live feed connected (Socket ID: {info.get('socketId', 'N/A')})")
    if self.toast:
        self.toast.show("Live feed connected", "success")  # ❌ Shows twice!
```

**Fix**:
```python
def handle_connected():
    socket_id = info.get('socketId')

    # Skip first connection event (Socket ID not yet assigned)
    if socket_id is None or socket_id == 'N/A':
        self.log("🔌 Connection negotiating...")
        return

    # Only process when Socket ID is available
    self.live_feed_connected = True
    self.live_feed_var.set(True)
    self.log(f"✅ Live feed connected (Socket ID: {socket_id})")
    if self.toast:
        self.toast.show("Live feed connected", "success")  # ✅ Shows once!
```

---

### Priority 3: Suppress "Packet Queue Empty" Logs [LOW]
**File**: `src/sources/websocket_feed.py`
**Location**: Line ~206 (WebSocketFeed.__init__)

**Current**:
```python
self.sio = socketio.Client(logger=False, engineio_logger=False)
```

**Fix**: Already suppressed! These are coming from the library itself. We can filter them in our logger config.

**Alternative**: Add custom logging filter in `src/services/logger.py`

---

### Priority 4: Investigate Connection Stability [MEDIUM]
**Potential causes**:
1. Backend timeout (most likely)
2. Network instability
3. Missing keep-alive pings

**Fix**: Add keep-alive mechanism to Socket.IO client

---

## 🧪 Testing Plan

### Test 1: State Transition Fix
1. Apply Priority 1 fix
2. Connect to live feed
3. Watch logs - should see NO "Illegal transition" warnings
4. Verify games still detected correctly

### Test 2: Duplicate Connection Fix
1. Apply Priority 2 fix
2. Disconnect and reconnect to live feed
3. Should see ONE "Live feed connected" toast (not two)
4. Socket ID should be valid (not None)

### Test 3: Connection Stability
1. Connect to live feed
2. Monitor for 5 minutes
3. Count disconnections
4. Note: This might be backend-side issue (nothing we can do)

---

## 📊 Summary

| Issue | Severity | Impact | Fix Difficulty | Priority |
|-------|----------|--------|----------------|----------|
| Illegal state transitions | MEDIUM | Logs spam | Easy | 1 |
| Duplicate connection events | LOW | Cosmetic | Easy | 2 |
| "Packet queue empty" logs | LOW | Cosmetic | Easy | 3 |
| Unstable connection | MEDIUM | Reliability | Hard | 4 |

**Immediate action**: Fix Priority 1 & 2 (easy, high impact)
**Investigate**: Priority 4 (connection stability - might be backend issue)

---

## ✅ Positive Conclusion

**Despite the warnings and disconnections, the system is working!**
- ✅ Live feed connects
- ✅ Games are recorded
- ✅ Data is processed
- ✅ Auto-reconnect works
- ✅ Multi-game support works

**The issues are mostly cosmetic (warnings/logs) and do not prevent functionality.**

---

**Next Steps**: Apply Priority 1 & 2 fixes to clean up logs and improve UX.
