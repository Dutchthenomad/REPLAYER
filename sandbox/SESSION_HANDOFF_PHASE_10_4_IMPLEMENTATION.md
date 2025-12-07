# Session Handoff: Phase 10.4 Implementation
**Created**: December 7, 2025 | **Status**: Ready for TDD Implementation

---

## Fresh Session Bootstrap Prompt

Copy everything below the line into a fresh Claude Code session:

---

```
# REPLAYER Phase 10.4 Implementation Session

## Context Restoration

Read these files in order to restore full context:

1. ~/CLAUDE.md - Global development workflow (Superpowers methodology)
2. /home/nomad/Desktop/REPLAYER/CLAUDE.md - Project context
3. /home/nomad/Desktop/REPLAYER/docs/plans/2025-12-07-websocket-foundation-layer-design.md - COMPLETE DESIGN (read fully)

## Current State

- **Branch**: feat/issue-1-human-demo-recording
- **GitHub Issue**: #2 (Phase 10.4 WebSocket Verification Layer)
- **Design Status**: COMPLETE - Ready for implementation
- **Commits**:
  - 8e54b24: Initial design doc
  - 95aab19: Complete design doc (946 lines)

## What We're Building

**WebSocket Foundation Layer** - High-quality training data capture for RL/ML:

1. **Two-Layer Data Architecture**:
   - Game State Layer: tick-by-tick prices (one file per game)
   - Player State Layer: actions with state snapshots (one file per session)

2. **Modular Refactor**:
   - Split websocket_feed.py (1212 lines) into 9 focused modules (<400 lines each)

3. **New Components**:
   - PlayerStateHandler (usernameStatus, playerUpdate events)
   - PriceHistoryHandler (partialPrices gap filling)
   - StateVerifier (local vs server drift detection)
   - GameStateRecorder + PlayerSessionRecorder

## Development Workflow: Superpowers Methodology

This project uses the **5 Iron Laws**:

| Principle | Command | Rule |
|-----------|---------|------|
| TDD | `/tdd` | NO code without failing test first |
| Verification | `/verify` | Fresh test run before claiming complete |
| Debugging | `/debug` | 4-phase root cause analysis |
| Planning | `/plan` | Zero-context executable plans |
| Isolation | `/worktree` | Isolated workspace per feature |

### TDD Iron Law (MANDATORY)

For EVERY piece of code:
1. Write the test FIRST
2. Run test - it MUST FAIL (RED)
3. Write minimal code to pass (GREEN)
4. Refactor if needed
5. Repeat

**Never skip the RED phase.** If a test passes immediately, it's testing nothing.

### Test Command
```bash
cd /home/nomad/Desktop/REPLAYER/src && python3 -m pytest tests/ -v --tb=short
```

## Implementation Order (TDD)

Follow this exact sequence. Each phase has tests written FIRST.

### Phase 10.4A: Modular Refactor (FIRST)
```bash
/tdd "Extract LatencySpikeDetector and ConnectionHealthMonitor to feed_monitors.py"
```
1. Create `src/sources/feed_monitors.py`
2. Extract classes from websocket_feed.py
3. Update imports
4. Verify existing tests still pass

### Phase 10.4B: Data Models
```bash
/tdd "Create recording_models.py with GameStateRecord and PlayerSession dataclasses"
```
1. Create `src/models/recording_models.py`
2. Test serialization/deserialization
3. Test gap filling logic

### Phase 10.4C: Player State Handler
```bash
/tdd "PlayerStateHandler captures player identity from usernameStatus event"
```
1. Create `src/sources/player_state_handler.py`
2. Wire into WebSocketFeed
3. Test event emission

### Phase 10.4D: Price History Handler
```bash
/tdd "PriceHistoryHandler builds gap-free price array using partialPrices"
```
1. Create `src/sources/price_history_handler.py`
2. Wire into tick processing
3. Test gap detection and filling

### Phase 10.4E: State Verifier
```bash
/tdd "StateVerifier detects drift between local GameState and server playerUpdate"
```
1. Create `src/services/state_verifier.py`
2. Wire to server_state_update events
3. Test drift detection with tolerance

### Phase 10.4F: Recorders
```bash
/tdd "GameStateRecorder saves game prices to JSON with metadata"
/tdd "PlayerSessionRecorder saves player actions to session JSON"
```
1. Create `src/core/game_state_recorder.py`
2. Create `src/core/player_session_recorder.py`
3. Wire to events
4. Test file creation and index updates

### Phase 10.4G: Final Integration
```bash
/verify
```
1. Run full test suite
2. Manual test with live WebSocket
3. Create PR

## Key File Paths

### Design Document (READ THIS)
```
/home/nomad/Desktop/REPLAYER/docs/plans/2025-12-07-websocket-foundation-layer-design.md
```

### Files to Create
```
src/models/recording_models.py       (~120 lines)
src/sources/feed_monitors.py         (~280 lines)
src/sources/feed_rate_limiter.py     (~80 lines)
src/sources/feed_degradation.py      (~160 lines)
src/sources/player_state_handler.py  (~80 lines)
src/sources/price_history_handler.py (~100 lines)
src/services/state_verifier.py       (~80 lines)
src/core/game_state_recorder.py      (~100 lines)
src/core/player_session_recorder.py  (~100 lines)
```

### Files to Modify
```
src/sources/websocket_feed.py        (reduce to ~400 lines)
src/ui/controllers/trading_controller.py (wire recorders)
```

### Test Files to Create
```
src/tests/test_models/test_recording_models.py
src/tests/test_sources/test_player_state_handler.py
src/tests/test_sources/test_price_history_handler.py
src/tests/test_services/test_state_verifier.py
src/tests/test_core/test_game_state_recorder.py
src/tests/test_core/test_player_session_recorder.py
```

## Success Criteria

Before claiming Phase 10.4 complete, ALL must be true:

- [ ] All source files under 400 lines
- [ ] Gap-free prices[] array per game
- [ ] Player identity captured on connect
- [ ] Server state drift detection working
- [ ] Separate game/player JSON files
- [ ] Daily index.json with queryable metadata
- [ ] Unit tests for all new modules
- [ ] All existing 275+ tests still pass
- [ ] /verify passes with fresh test run

## First Action

Start with Phase 10.4A - the modular refactor:

```bash
/tdd "Extract LatencySpikeDetector and ConnectionHealthMonitor from websocket_feed.py to feed_monitors.py"
```

This establishes the clean architecture before adding new features.

---

Acknowledge you've read and understood:
1. The design document at docs/plans/2025-12-07-websocket-foundation-layer-design.md
2. The Superpowers methodology (TDD Iron Law)
3. The implementation order (A through G)

Then begin with Phase 10.4A.
```

---

## Quick Reference

### Git Commands
```bash
git status
git add -A && git commit -m "feat: <description>"
gh pr create --title "feat: Phase 10.4 WebSocket Foundation Layer" --body "Closes #2"
```

### Test Commands
```bash
# All tests
cd /home/nomad/Desktop/REPLAYER/src && python3 -m pytest tests/ -v --tb=short

# Specific test file
python3 -m pytest tests/test_sources/test_player_state_handler.py -v

# With coverage
python3 -m pytest tests/ --cov=. --cov-report=term-missing
```

### Slash Commands
```
/tdd "requirement"   - Start TDD cycle
/verify              - Run verification before claiming complete
/debug               - 4-phase root cause analysis
/review              - Code review before PR
```

---

## Design Document Location

**CRITICAL**: The complete design with all Python code is at:
```
/home/nomad/Desktop/REPLAYER/docs/plans/2025-12-07-websocket-foundation-layer-design.md
```

This 946-line document contains:
- Full Python code for all new modules
- Data model definitions
- Event wiring diagrams
- File format specifications
- Integration examples

The fresh session should READ THIS FULLY before implementing.

---

*Session handoff complete. Ready for fresh context implementation.*
