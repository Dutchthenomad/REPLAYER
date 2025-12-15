---
title: "[Priority 2] Server State Authority Migration"
labels: enhancement, priority-high, phase-12
assignees: ""
---

## Goal
Replace local state calculations with authoritative server state from WebSocket events.

## Context
Phase 11 completed CDP WebSocket interception. The server now sends `playerUpdate` events with authoritative balance, position, and PnL data.

## Tasks
- [ ] Use `ServerState.cash` as source of truth for player balance
- [ ] Use `ServerState.position_qty` and `ServerState.avg_cost` for position tracking
- [ ] Deprecate local position/balance calculations (or make them secondary/validation-only)
- [ ] Add drift detection logging when local state diverges from server state
- [ ] Update UI to display server-authoritative data with drift warnings
- [ ] Write tests for drift detection (tolerance thresholds)
- [ ] Update documentation in CLAUDE.md

## Success Criteria
- All balance displays show server truth
- Position calculations use server data
- Drift warnings appear when local != server (with threshold tolerance)
- Zero manual balance tracking in TradingController
- All existing tests pass (796+)

## Dependencies
- ✅ Priority 1 complete (Server state wiring)

## Related Files
- `src/sources/websocket_feed.py` - Server state events
- `src/core/game_state.py` - State management
- `src/ui/controllers/live_feed_controller.py` - Event handling
- `docs/SESSION_HANDOFF.md` - Original priority stack

## Estimated Effort
2-3 hours
