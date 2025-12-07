# Session Handoff: Phase 10.4
**Created**: December 6, 2025 | **Status**: Ready for Implementation

---

## Quick Start (Copy for Fresh Session)

```
Read these files to restore context:
1. ~/CLAUDE.md (global workflow)
2. /home/nomad/Desktop/REPLAYER/CLAUDE.md (project context)
3. /home/nomad/Desktop/REPLAYER/docs/PHASE_10_4_PLAN.md (implementation plan)
4. /home/nomad/Desktop/REPLAYER/docs/WEBSOCKET_EVENTS_SPEC.md (protocol spec)

Current state:
- Branch: feat/issue-1-human-demo-recording
- Phase 10.1-10.3: COMPLETE (demo recording working)
- Phase 10.4: READY TO IMPLEMENT

First step: Create GitHub issue from template, then begin TDD implementation.
```

---

## Current State Summary

### What's Done (Phase 10.1-10.3)
- DemoRecorderSink with demo_action models (32 TDD tests)
- TradingController demo recording integration (22 tests)
- MainWindow menu integration (Recording → Start/Stop Demo)
- Human gameplay recording verified working (15 actions recorded)
- Commits: `7c3ae06`, `706b0b0`, `971c092`

### What's Next (Phase 10.4)
- WebSocket verification layer (player-specific only)
- Auto-start recording on game transitions
- State verification comparing local vs server

---

## SDLC Workflow for Phase 10.4

### Step 1: Create GitHub Issue
```bash
# Re-authenticate first
gh auth login -h github.com

# Create issue from template
gh issue create \
  --title "[Phase 10.4] WebSocket Verification Layer" \
  --body-file .github/ISSUE_TEMPLATE/phase-10-4-websocket-verification.md \
  --label "enhancement,phase-10"
```

### Step 2: Create Feature Branch
```bash
git checkout -b feat/issue-X-websocket-verification
# Replace X with the issue number from Step 1
```

### Step 3: TDD Implementation Order

Follow this exact sequence using `/tdd` for each:

#### 3A: Player Identity (usernameStatus)
```bash
# Write test first
/tdd "websocket_feed captures player identity from usernameStatus event"

# Test file: tests/test_sources/test_websocket_verification.py
# Test: test_username_status_captures_player_identity
```

#### 3B: Server State Sync (playerUpdate)
```bash
/tdd "websocket_feed captures server state from playerUpdate event"

# Tests: test_player_update_captures_server_state
#        test_player_update_converts_to_decimal
```

#### 3C: State Verifier
```bash
/tdd "StateVerifier compares local GameState to server truth"

# Test file: tests/test_services/test_state_verifier.py
# Tests: test_verify_matching_state
#        test_verify_balance_drift
#        test_verify_position_drift
#        test_verify_entry_price_drift
```

#### 3D: Game Transition Events
```bash
/tdd "websocket_feed emits game_started and game_ended events"

# Tests: test_game_started_on_cooldown_to_active
#        test_game_ended_on_rug
#        test_game_ended_on_active_to_cooldown
```

#### 3E: Auto-Start Recording
```bash
/tdd "MainWindow auto-starts demo recording on game_started"

# Test file: tests/test_ui/test_auto_recording.py
# Tests: test_auto_start_on_game_started
#        test_auto_stop_on_game_ended
#        test_auto_record_disabled_by_default
```

### Step 4: Verification
```bash
# After all tests pass
/verify

# Run full test suite
cd src && python3 -m pytest tests/ -v --tb=short
```

### Step 5: Code Review
```bash
/review
```

### Step 6: Create PR
```bash
gh pr create \
  --title "feat(websocket): Add verification layer and auto-recording" \
  --body "Closes #X

## Summary
- Added player identity capture (usernameStatus)
- Added server state sync (playerUpdate)
- Added StateVerifier for drift detection
- Added game transition events
- Added auto-start/stop demo recording

## Test Plan
- [ ] All 275+ existing tests pass
- [ ] New unit tests for verification layer
- [ ] Manual test: connect to live feed, verify player identity logged
- [ ] Manual test: make trade, verify server state received
- [ ] Manual test: auto-recording starts/stops on game transitions"
```

---

## Key Files Reference

### To Read First
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project context, Phase 10 status |
| `docs/WEBSOCKET_EVENTS_SPEC.md` | Protocol specification |
| `docs/PHASE_10_4_PLAN.md` | Implementation plan with code examples |

### To Modify
| File | Change |
|------|--------|
| `src/sources/websocket_feed.py` | Add event handlers (lines ~680-810) |
| `src/services/event_bus.py` | Add `STATE_DRIFT_DETECTED` event |
| `src/ui/controllers/trading_controller.py` | Wire verification |
| `src/ui/main_window.py` | Auto-start recording |

### To Create
| File | Purpose |
|------|---------|
| `src/services/state_verifier.py` | Verification logic (~80 lines) |
| `tests/test_sources/test_websocket_verification.py` | WebSocket handler tests |
| `tests/test_services/test_state_verifier.py` | Verifier tests |
| `tests/test_ui/test_auto_recording.py` | Auto-recording tests |

---

## Architecture Notes

### Thread Safety
- All new event handlers must use try/except (error boundary pattern)
- UI updates from WebSocket handlers → `TkDispatcher.submit()`
- State modifications → GameState lock (already handled)

### Decimal Precision
- All money values from server MUST convert to Decimal
- Pattern: `Decimal(str(data.get('cash', 0)))`

### Event Flow
```
WebSocket → usernameStatus → player_id stored
WebSocket → playerUpdate → StateVerifier.verify() → drift logged
WebSocket → gameStateUpdate → phase transition → game_started/ended emitted
MainWindow → game_started → _start_demo_recording()
MainWindow → game_ended → _stop_demo_recording()
```

---

## Test Commands

```bash
# Run all tests
cd /home/nomad/Desktop/REPLAYER/src && python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_sources/test_websocket_verification.py -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=term-missing

# Quick verification
python3 -m pytest tests/ -v --tb=short -q
```

---

## Success Criteria Checklist

- [ ] GitHub issue created
- [ ] Feature branch created from issue
- [ ] TDD: Tests written BEFORE implementation
- [ ] 10.4A: Player identity captured
- [ ] 10.4B: Server state sync working
- [ ] 10.4C: StateVerifier detecting drift
- [ ] 10.4D: Controller wired to verification
- [ ] 10.4E: Auto-recording on transitions
- [ ] All existing tests still pass
- [ ] `/verify` confirms all green
- [ ] `/review` completed
- [ ] PR created and merged
- [ ] CLAUDE.md updated to show 10.4 complete

---

*Session handoff complete. Ready for fresh context bootstrap.*
