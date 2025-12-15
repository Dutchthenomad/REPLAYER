# Design: CDP WebSocket Interception for Unified Event Stream

**Date**: 2025-12-14
**Status**: Approved
**Author**: Claude + Dutch

---

## Overview

Intercept WebSocket frames from Chrome via CDP to capture ALL rugs.fun events (including authenticated events like `usernameStatus` and `playerUpdate`) and unify them into a single event stream for the REPLAYER system.

## Problem Statement

REPLAYER currently has two separate connections:
1. **CDP Browser Bridge** - Connects to user's Chrome (authenticated with Phantom wallet)
2. **WebSocketFeed** - Creates its own Socket.IO connection (unauthenticated)

The browser's WebSocket receives auth events (`usernameStatus`, `playerUpdate`, trade responses) but REPLAYER's WebSocket does not. This prevents:
- Accurate player profile display in UI
- Server-state reconciliation for trading
- Complete event cataloging for RAG system

## Solution

Use Chrome DevTools Protocol (CDP) to intercept ALL WebSocket frames the browser sends/receives, providing a unified authenticated event stream.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED EVENT STREAM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐         ┌──────────────────┐                         │
│  │   Chrome     │ ◀──────▶│   rugs.fun       │                         │
│  │  (as Dutch)  │   WS    │   backend        │                         │
│  └──────┬───────┘         └──────────────────┘                         │
│         │                                                               │
│         │ CDP Network.webSocketFrameReceived                           │
│         ▼                                                               │
│  ┌──────────────┐         ┌──────────────────┐                         │
│  │ CDPWebSocket │────────▶│ UnifiedEventBus  │                         │
│  │  Interceptor │         │  (single stream) │                         │
│  └──────────────┘         └────────┬─────────┘                         │
│                                    │                                    │
│         ┌──────────────────────────┼──────────────────────────┐        │
│         ▼                          ▼                          ▼        │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐     │
│  │  GameState  │          │ RAG Ingester│          │  UI Updates │     │
│  │  (balance,  │          │ (catalog    │          │  (charts,   │     │
│  │   position) │          │  events)    │          │   profile)  │     │
│  └─────────────┘          └─────────────┘          └─────────────┘     │
│                                                                         │
│  FALLBACK (browser disconnected):                                       │
│  ┌──────────────┐                                                       │
│  │ WebSocketFeed│──────▶ UnifiedEventBus (public events only)          │
│  │ (existing)   │                                                       │
│  └──────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. CDPWebSocketInterceptor

**File**: `src/sources/cdp_websocket_interceptor.py`

Intercepts WebSocket frames from Chrome via CDP Network domain.

**CDP Events Subscribed:**

| CDP Event | Purpose |
|-----------|---------|
| `Network.webSocketCreated` | Detect when browser opens WS to rugs.fun |
| `Network.webSocketFrameReceived` | Capture incoming frames (server → browser) |
| `Network.webSocketFrameSent` | Capture outgoing frames (browser → server) |
| `Network.webSocketClosed` | Detect disconnection |

**Socket.IO Frame Parsing:**

Input (raw frame):
```
42["gameStateUpdate",{"gameId":"...","price":1.234,...}]
```

Output (structured event):
```python
{
    "event": "gameStateUpdate",
    "data": {"gameId": "...", "price": 1.234, ...},
    "timestamp": "2025-12-14T11:50:47.123Z",
    "direction": "received",
    "raw": "42[\"gameStateUpdate\",...]"
}
```

### 2. EventSourceManager

**File**: `src/services/event_source_manager.py`

Manages which event source is active with automatic fallback.

```python
class EventSourceManager:
    def __init__(self):
        self.cdp_interceptor = CDPWebSocketInterceptor()
        self.fallback_feed = WebSocketFeed()
        self.active_source = None

    def start(self):
        if self.cdp_interceptor.connect():
            self.active_source = "cdp"  # Full events
        else:
            self.active_source = "fallback"  # Public only
            self.fallback_feed.connect()
```

### 3. RAGIngester

**File**: `src/services/rag_ingester.py`

Catalogs WebSocket events for RAG pipeline integration.

**Features:**
- Writes events to JSONL format (compatible with claude-flow event_chunker.py)
- Tracks event type statistics
- Flags novel/undocumented events for RAG indexing
- Output directory: `/home/nomad/rugs_recordings/raw_captures/`

### 4. DebugTerminal

**File**: `src/ui/debug_terminal.py`

Real-time WebSocket event viewer in **separate window**.

**Features:**
- Independent `tk.Toplevel` window (non-blocking)
- Event filtering (by type, auth-only, novel-only)
- Color-coded display
- Live statistics (events/sec)

**Color Coding:**

| Event Type | Color | Meaning |
|------------|-------|---------|
| `gameStateUpdate` | Gray | High-frequency, normal |
| `usernameStatus` | Green | Auth event - identity |
| `playerUpdate` | Cyan | Auth event - balance/position |
| `standard/newTrade` | Yellow | Trade activity |
| `*Response` | Magenta | Trade confirmations |
| Novel events | Red | Undocumented - needs RAG entry |

### 5. Event Bus Extensions

**File**: `src/services/event_bus.py` (modify)

New event types:
```python
class Events:
    # Raw WebSocket events (for RAG cataloging)
    WS_RAW_EVENT = "ws.raw_event"
    WS_AUTH_EVENT = "ws.auth_event"

    # Source switching
    WS_SOURCE_CHANGED = "ws.source_changed"
```

## Event Flow

```
CDPWebSocketInterceptor                    WebSocketFeed (fallback)
        │                                          │
        ▼                                          ▼
┌───────────────────────────────────────────────────────────────┐
│                    UnifiedEventBus                             │
│                                                               │
│  on WS_RAW_EVENT:                                             │
│    ├── RAGIngester.catalog(event)     # Save for RAG         │
│    ├── EventRouter.dispatch(event)    # Route to handler     │
│    └── DebugTerminal.log(event)       # Real-time view       │
│                                                               │
│  EventRouter maps event types to existing handlers:           │
│    "gameStateUpdate"  → LiveFeedController                   │
│    "usernameStatus"   → MainWindow._handle_player_identity   │
│    "playerUpdate"     → MainWindow._handle_player_update     │
│    "standard/newTrade"→ TradingController                    │
└───────────────────────────────────────────────────────────────┘
```

## Connection States & Error Handling

```
STARTUP
   │
   ▼
┌─────────────────┐    success    ┌──────────────────┐
│ Try CDP Connect │──────────────▶│ CDP_ACTIVE       │
└────────┬────────┘               │ (full events)    │
         │ fail                   └────────┬─────────┘
         ▼                                 │
┌─────────────────┐               CDP disconnect
│ FALLBACK_ACTIVE │◀──────────────────────┘
│ (public only)   │
└────────┬────────┘
         │ CDP becomes available
         ▼
┌─────────────────┐
│ Auto-switch to  │──▶ CDP_ACTIVE
│ CDP             │
└─────────────────┘
```

**Error Scenarios:**

| Scenario | Behavior |
|----------|----------|
| Chrome not running | Start with fallback, retry CDP every 30s |
| CDP connection lost | Auto-switch to fallback, notify UI |
| Browser navigates away from rugs.fun | Pause CDP intercept, resume when back |
| Malformed Socket.IO frame | Log warning, skip frame, continue |
| RAG write fails | Buffer in memory, retry, warn if buffer full |

## UI Integration

**Status Bar Indicators:**
```
🟢 CDP: Dutch (authenticated)    ← Full events
🟡 Fallback: Public feed only    ← Limited events
🔴 Disconnected                  ← No events
```

**Menu Integration:**
```
Developer Tools
├── Start Raw Capture
├── ─────────────────
├── Open Debug Terminal          ← NEW
├── ─────────────────
├── Analyze Last Capture
└── Open Captures Folder
```

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/sources/cdp_websocket_interceptor.py` | **Create** | CDP frame interception |
| `src/services/event_source_manager.py` | **Create** | Source switching logic |
| `src/services/rag_ingester.py` | **Create** | RAG cataloging |
| `src/ui/debug_terminal.py` | **Create** | Real-time event viewer |
| `src/services/event_bus.py` | **Modify** | Add new event types |
| `src/ui/main_window.py` | **Modify** | Menu integration, status bar |
| `src/browser_automation/cdp_browser_manager.py` | **Modify** | Add Network domain subscription |

## Testing Strategy

**Unit Tests:**

| Component | Test Focus |
|-----------|------------|
| `CDPWebSocketInterceptor` | Socket.IO frame parsing, event extraction |
| `EventSourceManager` | Source switching, fallback logic |
| `RAGIngester` | JSONL format, novel event detection |
| `DebugTerminal` | Filter logic, color coding |

**Integration Tests:**
- CDP events reach GameState
- Fallback on CDP disconnect
- RAG ingestion captures novel events

**Manual Testing Checklist:**
- [ ] Launch REPLAYER without Chrome → Falls back to public feed
- [ ] Launch Chrome, connect to rugs.fun → Switches to CDP
- [ ] Open Debug Terminal → See all events including auth
- [ ] Place a trade in browser → See tradeResponse in terminal
- [ ] Close Chrome → Falls back gracefully, no crash
- [ ] Check JSONL capture → Contains auth events
- [ ] Run RAG query → Returns newly cataloged events

## RAG Integration

Events are written to `/home/nomad/rugs_recordings/raw_captures/` in JSONL format compatible with `claude-flow/rag-pipeline/ingestion/event_chunker.py`.

After capture sessions:
```bash
cd /home/nomad/Desktop/claude-flow/rag-pipeline
python -m ingestion.ingest  # Index new events

# Query via rugs-expert agent
python -m retrieval.retrieve "what is playerUpdate event"
```

## Success Criteria

1. **Auth events captured**: `usernameStatus` and `playerUpdate` appear in Debug Terminal
2. **Player profile works**: UI shows "Dutch" and correct balance
3. **Seamless fallback**: System works without browser (public events only)
4. **RAG cataloging**: All events saved for rugs-expert agent
5. **No UI blocking**: Debug Terminal is independent window
6. **Existing handlers work**: No changes needed to `_handle_player_identity`, etc.

---

*Design approved: 2025-12-14*
