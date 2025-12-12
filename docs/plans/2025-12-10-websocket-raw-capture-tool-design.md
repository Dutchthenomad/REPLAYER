# WebSocket Raw Capture Tool - Design Document

**Date**: 2025-12-10
**Status**: Approved
**Purpose**: Capture ALL raw WebSocket events for protocol discovery and documentation

---

## Problem Statement

The REPLAYER UI shows "Not Connected" and "Not Authenticated" despite clear evidence of an active game running. The WebSocket connection receives `gameStateUpdate` events (game chart updates), but identity events (`usernameStatus`, `playerUpdate`) appear to not be captured or processed correctly.

**Root Cause Unknown**: We don't know what events the server actually sends vs. what we expect. We need to see the raw protocol.

---

## Solution Overview

A standalone raw capture system that:
1. Records **every** Socket.IO event from connection to disconnection
2. Preserves raw payloads without any filtering or transformation
3. Provides post-processing tools to analyze and document the protocol

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    REPLAYER UI                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Developer Tools Menu                            │   │
│  │  ├── Start/Stop Raw Capture                      │   │
│  │  ├── Analyze Last Capture                        │   │
│  │  └── Open Captures Folder                        │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  RawCaptureRecorder                              │   │
│  │  - Creates OWN Socket.IO client                  │   │
│  │  - Captures ALL events via catch-all handler     │   │
│  │  - Writes to JSONL in real-time                  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  /home/nomad/rugs_recordings/raw_captures/              │
│  ├── 2025-12-10_21-51-14_raw.jsonl                      │
│  ├── 2025-12-10_21-51-14_summary.md      (generated)    │
│  ├── 2025-12-10_21-51-14_events.json     (generated)    │
│  └── TODO.md  (future Developer Tools features)         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  analyze_raw_capture.py (CLI tool)                      │
│  - List unique event types                              │
│  - Extract specific events                              │
│  - Generate summary report                              │
│  - Generate event inventory                             │
└─────────────────────────────────────────────────────────┘
```

---

## Connection Sequence

**Critical**: Raw capture starts BEFORE WebSocket connects to capture full auth sequence.

```
1. User clicks "Start Raw Capture"
2. RawCaptureRecorder initializes
   - Creates JSONL file
   - Sets up catch-all event handler
3. RawCaptureRecorder connects to backend.rugs.fun
   - Separate Socket.IO client from REPLAYER's WebSocketFeed
   - Captures: connect, usernameStatus, playerUpdate, gameStateUpdate, etc.
4. ALL events flow through catch-all handler
   - No filtering, no transformation
   - Raw payload written immediately
5. User interacts with game (via browser)
6. User clicks "Stop Raw Capture"
   - Disconnects Socket.IO client
   - Runs analysis, generates summary
```

**Note**: User manages the sequence - start raw capture from fresh session before connecting REPLAYER.

---

## JSONL Record Format

Each line in the raw capture file:

```json
{"seq": 1, "ts": "2025-12-10T21:51:14.123Z", "event": "connect", "data": null}
{"seq": 2, "ts": "2025-12-10T21:51:14.456Z", "event": "usernameStatus", "data": {"id": "did:privy:...", "username": "Dutch"}}
{"seq": 3, "ts": "2025-12-10T21:51:14.789Z", "event": "playerUpdate", "data": {"cash": 1.5, "positionQty": 0, ...}}
{"seq": 4, "ts": "2025-12-10T21:51:15.012Z", "event": "gameStateUpdate", "data": {"gameId": "...", "price": 1.23, ...}}
```

**Fields**:
- `seq` - Sequence number (order received)
- `ts` - ISO timestamp when received
- `event` - Socket.IO event name (exactly as received)
- `data` - Raw payload (exactly as received, no transformation)

---

## Analysis Script

`scripts/analyze_raw_capture.py` - CLI tool to slice and document captured data:

```bash
# List all unique event types with counts
python analyze_raw_capture.py session.jsonl --summary

# Extract all events of a specific type
python analyze_raw_capture.py session.jsonl --extract usernameStatus

# Show events in a sequence range
python analyze_raw_capture.py session.jsonl --range 1-50

# Generate full documentation report
python analyze_raw_capture.py session.jsonl --report
```

**`--report` generates**:
- `_summary.md` - Human-readable overview with event counts and timeline
- `_events.json` - Inventory of all event types with sample payloads

---

## File Locations

```
/home/nomad/rugs_recordings/
└── raw_captures/
    ├── TODO.md                              # Future Developer Tools features
    ├── 2025-12-10_21-51-14_raw.jsonl       # Raw capture data
    ├── 2025-12-10_21-51-14_summary.md      # Generated report
    └── 2025-12-10_21-51-14_events.json     # Event inventory
```

---

## UI Menu Structure

```
Developer Tools
├── Start Raw Capture     (toggles to "Stop Raw Capture" when active)
├── Analyze Last Capture
└── Open Captures Folder
```

---

## Implementation Tasks

1. Create `raw_captures/` directory structure with `TODO.md`
2. Create `RawCaptureRecorder` class in `src/debug/raw_capture_recorder.py`
3. Create `analyze_raw_capture.py` script in `scripts/`
4. Add "Developer Tools" menu to MainWindow
5. Wire menu actions to RawCaptureRecorder
6. Test full capture cycle (connect → game → disconnect → analyze)

---

## Future Developer Tools (TODO.md)

For later expansion:
- WebSocket connection status panel
- Live event log viewer
- GameState dump/compare tools
- Log level controls
- Session log export
