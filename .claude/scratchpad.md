# REPLAYER Session Scratchpad

Last Updated: 2025-12-13 22:00

---

## Quick Start for Fresh Sessions

### Option 1: Issue #8 - WebSocket Server State Fix
```bash
# View issue details
gh issue view 8

# Create worktree and start development
git worktree add .worktrees/issue-8 -b fix/issue-8-websocket-server-state
cd .worktrees/issue-8

# Run tests to verify clean baseline
cd src && python3 -m pytest tests/ -v --tb=short
```

### Option 2: Issue #9 - Socket Event RAG Pipeline
```bash
# View issue details
gh issue view 9

# Create worktree and start development
git worktree add .worktrees/issue-9 -b feat/issue-9-socket-event-rag
cd .worktrees/issue-9

# Run tests to verify clean baseline
cd src && python3 -m pytest tests/ -v --tb=short
```

### Session Bootstrap Prompt (Copy/Paste)
```
Read /home/nomad/Desktop/REPLAYER/docs/plans/2025-12-13-websocket-server-state-design.md

I'm working on REPLAYER. Key context:
- Issue #8: WebSocket fix using hardcoded credentials (Dutch's privy ID)
- Issue #9: RAG pipeline for socket event recording
- Design doc: docs/plans/2025-12-13-websocket-server-state-design.md
- Test cmd: cd src && python3 -m pytest tests/ -v --tb=short

Let's continue development on Issue #[8 or 9].
```

---

## Active Issues

| Issue | Branch | Purpose |
|-------|--------|---------|
| #8 | `fix/issue-8-websocket-server-state` | WebSocket auth fix with hardcoded credentials |
| #9 | `feat/issue-9-socket-event-rag` | RAG pipeline for rugs.fun expert agent |

## Current SDLC Phase
Ready for parallel development on Issues #8 and #9

## Key Decisions (Issue #8 Design - 2025-12-13)

### Authentication Approach
- **Hardcoded credentials** (server only sends auth events to authenticated clients)
- `HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"`
- `HARDCODED_USERNAME = "Dutch"`

### Data Extraction
- Parse `gameStatePlayerUpdate` leaderboard entries for Dutch's player ID
- Extract ALL trading fields: `cash`, `pnl`, `pnlPercent`, `positionQty`, `avgCost`, `totalInvested`, `hasActiveTrades`, `sidebet`

### State Reconciliation
- Server state is ultimate truth
- Update local state silently (no UI notifications)
- Persist state across sessions

### Testing Strategy
- Delete 10 failing tests (designed for different architecture)
- Write new tests for hardcoded credential approach

### Files to Modify (Issue #8)
| File | Changes |
|------|---------|
| `src/sources/websocket_feed.py` | Leaderboard parsing, emit `player_state_update` |
| `src/ui/controllers/live_feed_controller.py` | Subscribe to `player_state_update` |
| `src/core/game_state.py` | Ensure `reconcile_with_server()` handles all fields |
| `src/ui/main_window.py` | Verify balance/position displays update |
| `src/tests/test_sources/test_websocket_feed.py` | Delete/rewrite tests |

### RAG Pipeline (Issue #9)
- Full RAG framework integration with `/home/nomad/Desktop/claude-flow/rag-pipeline/`
- Event categories: game_state, trade, player, social, system, battle
- Storage: `/home/nomad/rugs_recordings/raw_events/{date}/{session}.jsonl`

## Previous Implementation (Reference)
- Phase 11 State Reconciliation COMPLETE (all 9 repairs)
- WebSocket Raw Capture Tool **IMPLEMENTED** (737 tests passing)
- Design implemented exactly as specified in design document

## Implementation Summary

### Raw Capture Tool Files Created
1. `src/debug/__init__.py` - Debug module init
2. `src/debug/raw_capture_recorder.py` - RawCaptureRecorder class (280 lines)
3. `scripts/analyze_raw_capture.py` - Analysis CLI tool (200 lines)
4. `src/tests/test_debug/__init__.py` - Test module init
5. `src/tests/test_debug/test_raw_capture_recorder.py` - 19 unit tests

### Hardcoded Credentials Workaround (websocket_feed.py)
- Added `HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"`
- Added `HARDCODED_USERNAME = "Dutch"`
- Modified connect handler to auto-confirm identity on connection
- Added `gameStatePlayerUpdate` event handler that:
  - Filters for Dutch's player ID only
  - Extracts PnL, position, avgCost, totalInvested, hasActiveTrades, sidebet data
  - Updates `_last_server_state` for Phase 11 reconciliation
  - Emits `player_state_update` event for UI/recording

### Developer Tools Menu Structure
```
Developer Tools
├── Start Raw Capture (toggles to "⏺ Stop Raw Capture")
├── ─────────────────
├── Analyze Last Capture
├── Open Captures Folder
├── ─────────────────
└── Show Capture Status
```

### Output Location
`/home/nomad/rugs_recordings/raw_captures/`

## Test Results
- 737 tests passing
- All existing tests still pass
- No regressions

## Raw Capture Analysis Results (554 events captured)
| Event Type | Count | Percentage |
|------------|-------|------------|
| gameStateUpdate | 510 | 92.1% |
| standard/newTrade | 31 | 5.6% |
| newChatMessage | 11 | 2.0% |
| connect | 1 | 0.2% |
| battleEventUpdate | 1 | 0.2% |

**Key Finding**: No `usernameStatus` or `playerUpdate` events - confirms server only sends these to authenticated clients.

## Completed Steps
1. [x] Create `src/debug/raw_capture_recorder.py` - DONE
2. [x] Create `scripts/analyze_raw_capture.py` - DONE
3. [x] Add "Developer Tools" menu to MainWindow - DONE
4. [x] Wire menu actions to RawCaptureRecorder - DONE
5. [x] Run unit tests - DONE (19 tests pass)
6. [x] Run live capture session - DONE (554 events)
7. [x] Analyze capture results - DONE
8. [x] Fix UI freeze on stop capture - DONE (background thread for disconnect)
9. [x] Implement hardcoded credentials workaround - DONE
10. [x] Verify tests pass - DONE (737 tests)
11. [ ] User live testing with hardcoded credentials

## Context to Preserve
- 737 tests passing
- Test command: `cd src && python3 -m pytest tests/ -v`
- Run command: `./run.sh`
- Location: `/home/nomad/Desktop/REPLAYER/`
- Capture location: `/home/nomad/rugs_recordings/raw_captures/`

## Session History
- 2025-12-12: Hardcoded credentials workaround implemented (737 tests)
- 2025-12-12: Raw capture analysis complete - discovered auth events not sent to anonymous clients
- 2025-12-12: Fixed UI freeze on stop capture (background disconnect)
- 2025-12-10: Raw Capture Tool implementation complete (737 tests)
- 2025-12-10: Phase 11 complete, GitHub #6 closed, Raw Capture Tool designed
- 2025-12-05: Unified Framework implemented
- 2025-11-15: Phase 7A complete, RecorderSink fixes
- 2025-11-14: Phase 6 complete, WebSocket live feed
