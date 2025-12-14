---
name: "Phase 10.4: WebSocket Verification Layer"
about: Extend WebSocket feed with player-specific server state verification
title: "[Phase 10.4] WebSocket Verification Layer"
labels: enhancement, phase-10
assignees: ''
---

## Summary

Extend `websocket_feed.py` to capture player-specific server state for:
1. **State verification** - Compare local calculations to server truth
2. **Latency tracking** - Measure request-to-confirmation timing
3. **Auto-start recording** - Trigger demo recording on game transitions

## Scope

**In Scope** (Player-specific only):
- `usernameStatus` event - Player identity
- `playerUpdate` event - Server state sync (cash, positionQty, avgCost)
- `gameStatePlayerUpdate` event - Personal leaderboard entry
- Game transition events for auto-recording

**Out of Scope**:
- Rugpool metrics (side game)
- Battle mode events
- Chat messages
- Other players' leaderboard data

## Acceptance Criteria

- [ ] Player identity (`did:privy:*`) captured on WebSocket connection
- [ ] Server state (`cash`, `positionQty`, `avgCost`) received after each trade
- [ ] `StateVerifier` class compares local GameState to server truth
- [ ] State drift logged when local != server (with tolerance)
- [ ] `game_started` event emitted on COOLDOWN → ACTIVE_GAMEPLAY transition
- [ ] `game_ended` event emitted on rug or gameplay → cooldown transition
- [ ] Demo recording auto-starts on game_started (when enabled)
- [ ] Demo recording auto-stops on game_ended
- [ ] All existing 275+ tests still pass
- [ ] New unit tests for all new functionality

## Technical Approach

See `docs/PHASE_10_4_PLAN.md` for detailed implementation plan.

### Files to Modify/Create

| File | Change |
|------|--------|
| `src/sources/websocket_feed.py` | Add 3 event handlers, player identity |
| `src/services/state_verifier.py` | **NEW** - Verification logic |
| `src/ui/controllers/trading_controller.py` | Wire verification |
| `src/ui/main_window.py` | Auto-start recording |
| `src/services/event_bus.py` | Add `STATE_DRIFT_DETECTED` event |

### Test Files to Create

| File | Tests |
|------|-------|
| `tests/test_sources/test_websocket_verification.py` | Player identity, server state handlers |
| `tests/test_services/test_state_verifier.py` | Verification logic |
| `tests/test_ui/test_auto_recording.py` | Game transition auto-start/stop |

## Definition of Done

1. All acceptance criteria met
2. TDD: Tests written before implementation
3. All tests passing (existing + new)
4. Code reviewed via `/review`
5. PR created and merged
6. CLAUDE.md updated with Phase 10.4 completion

## References

- `docs/WEBSOCKET_EVENTS_SPEC.md` - Protocol specification
- `docs/PHASE_10_4_PLAN.md` - Implementation plan
- Issue #1 - Parent issue (Human Demo Recording System)

## Estimated Effort

~10 hours (5 sub-tasks × 2 hours average)
